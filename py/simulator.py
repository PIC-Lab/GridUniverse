import math
import sqlite3
import logging

logger = logging.getLogger(__name__)


class AMSSimulator:
    def __init__(self, ss, area_id: int = 1):
        self.ss = ss
        self.area_id = area_id
        self.mva_base = ss.config.mva if hasattr(ss.config, 'mva') else 100.0

        self.soc = 0
        self.end_soc = None
        self.status = "offline"
        self.routine = "PFlow"

        self.total_cost = 0.0
        self.total_mwh = 0.0

        self.sim_id = None
        self.db_conn = None

        self._build_device_lists()

    def _sf(self, arr, idx=None):
        """Safe float from numpy array or scalar."""
        if idx is not None:
            return float(arr[idx])
        if isinstance(arr, (int, float)):
            return float(arr)
        return float(arr[0]) if hasattr(arr, '__len__') and len(arr) > 0 else 0.0

    def _build_device_lists(self):
        """Build filtered device lists for the selected area."""
        bus_ids = self.ss.Bus.idx.v
        bus_areas = self.ss.Bus.area.v
        self._area_bus_set = set(
            bus_ids[i] for i in range(len(bus_ids))
            if bus_areas[i] == self.area_id
        )

        # Build StaticGen bus→index map for key alignment with case_exporter
        self._sg_bus_to_idx = {}
        if hasattr(self.ss, 'StaticGen'):
            for sg_idx in self.ss.StaticGen.get_all_idxes():
                bus = int(float(self.ss.StaticGen.get(src='bus', attr='v', idx=sg_idx)))
                if bus not in self._sg_bus_to_idx:
                    self._sg_bus_to_idx[bus] = []
                self._sg_bus_to_idx[bus].append(sg_idx)

        # Build PV/Slack model index mappings for .set() calls
        self._pv_bus_to_model_idx = {}
        if hasattr(self.ss, 'PV'):
            for pv_idx in self.ss.PV.get_all_idxes():
                bus = int(self.ss.PV.get(src='bus', attr='v', idx=pv_idx))
                if bus not in self._pv_bus_to_model_idx:
                    self._pv_bus_to_model_idx[bus] = []
                self._pv_bus_to_model_idx[bus].append(pv_idx)

        self._slack_bus_to_model_idx = {}
        if hasattr(self.ss, 'Slack'):
            for sl_idx in self.ss.Slack.get_all_idxes():
                bus = int(self.ss.Slack.get(src='bus', attr='v', idx=sl_idx))
                if bus not in self._slack_bus_to_model_idx:
                    self._slack_bus_to_model_idx[bus] = []
                self._slack_bus_to_model_idx[bus].append(sl_idx)

        # Build PQ bus→index map for key alignment with case_exporter
        self._pq_bus_to_idx = {}
        if hasattr(self.ss, 'PQ'):
            for pq_idx in self.ss.PQ.get_all_idxes():
                bus = int(float(self.ss.PQ.get(src='bus', attr='v', idx=pq_idx)))
                if bus not in self._pq_bus_to_idx:
                    self._pq_bus_to_idx[bus] = []
                self._pq_bus_to_idx[bus].append(pq_idx)

        # Build Shunt bus→index map for key alignment with case_exporter
        self._sh_bus_to_idx = {}
        if hasattr(self.ss, 'Shunt'):
            for sh_idx in self.ss.Shunt.get_all_idxes():
                bus = int(float(self.ss.Shunt.get(src='bus', attr='v', idx=sh_idx)))
                if bus not in self._sh_bus_to_idx:
                    self._sh_bus_to_idx[bus] = []
                self._sh_bus_to_idx[bus].append(sh_idx)

        # Generators: PV + Slack
        self._gen_devices = []
        self._gen_bus_counter = {}  # track per-bus gen count for sequential IDs
        pv_buses = self.ss.PV.bus.v
        pv_u = self.ss.PV.u.v
        for i in range(self.ss.PV.n):
            bus = int(pv_buses[i])
            if bus in self._area_bus_set:
                sg_id = self._next_sg_id(bus)
                # Get PV model index for .set() calls
                pv_model_list = self._pv_bus_to_model_idx.get(bus, [])
                count = self._gen_bus_counter[bus] - 1
                pv_model_idx = pv_model_list[count] if count < len(pv_model_list) else None
                self._gen_devices.append({
                    "type": "PV", "idx": i,
                    "bus": bus,
                    "u": float(pv_u[i]),
                    "sg_id": sg_id,
                    "model_idx": pv_model_idx,
                })

        slack_buses = self.ss.Slack.bus.v
        slack_u = self.ss.Slack.u.v
        for i in range(self.ss.Slack.n):
            bus = int(slack_buses[i])
            if bus in self._area_bus_set:
                sg_id = self._next_sg_id(bus)
                sl_model_list = self._slack_bus_to_model_idx.get(bus, [])
                count = self._gen_bus_counter[bus] - 1
                sl_model_idx = sl_model_list[count] if count < len(sl_model_list) else None
                self._gen_devices.append({
                    "type": "Slack", "idx": i,
                    "bus": bus,
                    "u": float(slack_u[i]),
                    "sg_id": sg_id,
                    "model_idx": sl_model_idx,
                })

        # Loads
        self._load_indices = []
        self._load_bus_counter = {}
        pq_buses = self.ss.PQ.bus.v
        for i in range(self.ss.PQ.n):
            bus = int(pq_buses[i])
            if bus in self._area_bus_set:
                pq_id = self._next_pq_id(bus)
                # Find the PQ model index for .set() calls
                pq_model_idx = self._pq_bus_to_idx.get(bus, [[]])[min(self._load_bus_counter[bus] - 1, len(self._pq_bus_to_idx.get(bus, [])) - 1)] if bus in self._pq_bus_to_idx else None
                self._load_indices.append({"pq_idx": i, "bus": bus, "pq_id": pq_id, "pq_model_idx": pq_model_idx})

        # Shunts
        self._shunt_indices = []
        self._sh_bus_counter = {}
        sh_buses = self.ss.Shunt.bus.v
        for i in range(self.ss.Shunt.n):
            bus = int(sh_buses[i])
            if bus in self._area_bus_set:
                sh_id = self._next_sh_id(bus)
                sh_model_idx = self._sh_bus_to_idx.get(bus, [[]])[min(self._sh_bus_counter[bus] - 1, len(self._sh_bus_to_idx.get(bus, [])) - 1)] if bus in self._sh_bus_to_idx else None
                self._shunt_indices.append({"sh_idx": i, "bus": bus, "sh_id": sh_id, "sh_model_idx": sh_model_idx})

        # Lines (include if either end is in area)
        self._line_indices = []
        line_bus1 = self.ss.Line.bus1.v
        line_bus2 = self.ss.Line.bus2.v
        for i in range(self.ss.Line.n):
            b1, b2 = int(line_bus1[i]), int(line_bus2[i])
            if b1 in self._area_bus_set or b2 in self._area_bus_set:
                self._line_indices.append(i)

        # Build key maps using StaticGen/PQ/Shunt indices
        self._gen_key_map = {}
        for dev in self._gen_devices:
            key = f"{dev['bus']},{dev['sg_id']}"
            self._gen_key_map[key] = dev  # dev contains model_idx for .set() calls

        self._load_key_map = {}
        for item in self._load_indices:
            key = f"{item['bus']},{item['pq_id']}"
            self._load_key_map[key] = item["pq_model_idx"]

        self._shunt_key_map = {}
        for item in self._shunt_indices:
            key = f"{item['bus']},{item['sh_id']}"
            self._shunt_key_map[key] = item["sh_model_idx"]

        self._branch_key_map = {}
        for i, idx in enumerate(self._line_indices):
            b1, b2 = int(line_bus1[idx]), int(line_bus2[idx])
            key = f"{b1},{b2},1"
            self._branch_key_map[key] = idx

    def _next_sg_id(self, bus):
        """Get next StaticGen index ID for a bus (aligns with case_exporter keys)."""
        count = self._gen_bus_counter.get(bus, 0)
        self._gen_bus_counter[bus] = count + 1
        if bus in self._sg_bus_to_idx and count < len(self._sg_bus_to_idx[bus]):
            return self._sg_bus_to_idx[bus][count]
        return count + 1

    def _next_pq_id(self, bus):
        """Get next PQ index ID for a bus (aligns with case_exporter keys)."""
        count = self._load_bus_counter.get(bus, 0)
        self._load_bus_counter[bus] = count + 1
        if bus in self._pq_bus_to_idx and count < len(self._pq_bus_to_idx[bus]):
            idx = self._pq_bus_to_idx[bus][count]
            idx_str = str(idx)
            return idx_str.split('_')[-1] if '_' in idx_str else idx_str
        return str(count + 1)

    def _next_sh_id(self, bus):
        """Get next Shunt index ID for a bus (aligns with case_exporter keys)."""
        count = self._sh_bus_counter.get(bus, 0)
        self._sh_bus_counter[bus] = count + 1
        if bus in self._sh_bus_to_idx and count < len(self._sh_bus_to_idx[bus]):
            idx = self._sh_bus_to_idx[bus][count]
            idx_str = str(idx)
            return idx_str.split('_')[-1] if '_' in idx_str else idx_str
        return str(count + 1)

    def set_db(self, conn: sqlite3.Connection, sim_id: int):
        self.db_conn = conn
        self.sim_id = sim_id

    def start(self, end_soc=None, routine="PFlow") -> dict:
        self.soc = 0
        self.end_soc = end_soc
        self.routine = routine
        self.total_cost = 0.0
        self.total_mwh = 0.0
        self.status = "running"

        if self.db_conn and self.sim_id:
            from database import update_simulation_status
            update_simulation_status(self.db_conn, self.sim_id, "running")

        return {"status": "running", "soc": self.soc, "message": f"The simulation is started @{self.soc}"}

    def pause(self) -> dict:
        if self.status != "running":
            return {"status": self.status, "message": f"Cannot pause from {self.status}"}
        self.status = "paused"
        if self.db_conn and self.sim_id:
            from database import update_simulation_status
            update_simulation_status(self.db_conn, self.sim_id, "paused")
        return {"status": "paused", "soc": self.soc, "message": "The simulation is paused"}

    def continue_sim(self) -> dict:
        if self.status != "paused":
            return {"status": self.status, "message": f"Cannot continue from {self.status}"}
        self.status = "running"
        if self.db_conn and self.sim_id:
            from database import update_simulation_status
            update_simulation_status(self.db_conn, self.sim_id, "running")
        return {"status": "running", "soc": self.soc, "message": "The simulation is continuing"}

    def abort(self) -> dict:
        self.status = "aborted"
        if self.db_conn and self.sim_id:
            from database import update_simulation_status
            update_simulation_status(self.db_conn, self.sim_id, "aborted")
        return {"status": "aborted", "soc": self.soc, "message": "The simulation has been aborted"}

    def tick(self) -> dict | None:
        if self.status != "running":
            return None

        try:
            self.ss.PFlow.run()
        except Exception as e:
            logger.error(f"Power flow failed at SOC {self.soc}: {e}")
            self.status = "aborted"
            return {"soc": self.soc, "status": "aborted", "message": "The system goes blackout"}

        converged = getattr(self.ss.PFlow, 'converged', True)
        if not converged:
            self.status = "aborted"
            return {"soc": self.soc, "status": "aborted", "message": "The system goes blackout"}

        state = self._build_state()
        self._accumulate_cost(state)
        self._write_to_db(state)

        self.soc += 1
        if self.end_soc is not None and self.soc >= self.end_soc:
            self.status = "finished"
            state["status"] = "finished"
            if self.db_conn and self.sim_id:
                from database import update_simulation_status
                update_simulation_status(self.db_conn, self.sim_id, "finished")
            return state

        return state

    def _get_bus_v(self, bus_num):
        bus_ids = self.ss.Bus.idx.v
        if bus_num in bus_ids:
            idx = list(bus_ids).index(bus_num)
            return float(self.ss.Bus.v.v[idx])
        return 1.0

    def _get_bus_a(self, bus_num):
        bus_ids = self.ss.Bus.idx.v
        if bus_num in bus_ids:
            idx = list(bus_ids).index(bus_num)
            return float(self.ss.Bus.a.v[idx]) * 180.0 / math.pi
        return 0.0

    def _get_bus_kv(self, bus_num):
        bus_ids = self.ss.Bus.idx.v
        if bus_num in bus_ids:
            idx = list(bus_ids).index(bus_num)
            return float(self.ss.Bus.Vn.v[idx])
        return 0.0

    def _build_state(self) -> dict:
        area = self._build_area_data()
        buses = self._build_bus_data()
        gens = self._build_gen_data()
        loads = self._build_load_data()
        shunts = self._build_shunt_data()
        branches = self._build_branch_data()
        transformers = self._build_transformer_data()
        risk = self._build_risk_data(buses, branches)

        return {
            "soc": self.soc,
            "status": self.status,
            "area": area,
            "bus": buses,
            "gen": gens,
            "load": loads,
            "shunt": shunts,
            "branch": branches,
            "transformer": transformers,
            "risk": risk,
        }

    def _build_area_data(self) -> dict:
        gen_mw = 0.0
        gen_mvar = 0.0
        for dev in self._gen_devices:
            if dev["u"] <= 0:
                continue
            if dev["type"] == "PV":
                gen_mw += self._sf(self.ss.PV.p.v, dev["idx"]) * self.mva_base
                gen_mvar += self._sf(self.ss.PV.q.v, dev["idx"]) * self.mva_base
            elif dev["type"] == "Slack":
                gen_mw += self._sf(self.ss.Slack.p.v, dev["idx"]) * self.mva_base
                gen_mvar += self._sf(self.ss.Slack.q.v, dev["idx"]) * self.mva_base

        load_mw = 0.0
        load_mvar = 0.0
        for item in self._load_indices:
            idx = item["pq_idx"]
            u = float(self.ss.PQ.u.v[idx])
            if u > 0:
                load_mw += self._sf(self.ss.PQ.p0.v, idx) * self.mva_base
                load_mvar += self._sf(self.ss.PQ.q0.v, idx) * self.mva_base

        shunt_mvar = 0.0
        for item in self._shunt_indices:
            idx = item["sh_idx"]
            u = float(self.ss.Shunt.u.v[idx])
            if u > 0:
                bus = int(self.ss.Shunt.bus.v[idx])
                v = self._get_bus_v(bus)
                b = self._sf(self.ss.Shunt.b.v, idx)
                shunt_mvar += v * v * b * self.mva_base

        export_mw = gen_mw - load_mw
        loss_mw = max(0, export_mw)

        return {
            "gen_mw": round(gen_mw, 2),
            "gen_mvar": round(gen_mvar, 2),
            "load_mw": round(load_mw, 2),
            "load_mvar": round(load_mvar, 2),
            "shunt_mvar": round(shunt_mvar, 2),
            "export_mw": round(export_mw, 2),
            "frequency": 60.0,
            "ace": 0.0,
            "loss_mw": round(loss_mw, 2),
        }

    def _build_bus_data(self) -> dict:
        result = {}
        bus_ids = self.ss.Bus.idx.v
        bus_areas = self.ss.Bus.area.v
        bus_u = self.ss.Bus.u.v
        for i in range(self.ss.Bus.n):
            bus_num = int(bus_ids[i])
            area = float(bus_areas[i])
            if area != self.area_id:
                continue
            result[str(bus_num)] = {
                "vpu": round(float(self.ss.Bus.v.v[i]), 4),
                "vangle": round(float(self.ss.Bus.a.v[i]) * 180.0 / math.pi, 4),
                "freq_hz": 60.0,
                "status": 1 if bus_u[i] > 0 else 0,
                "gen_mw": 0.0,
                "gen_mvar": 0.0,
                "load_mw": 0.0,
                "load_mvar": 0.0,
                "shunt_mvar": 0.0,
            }
        return result

    def _build_gen_data(self) -> dict:
        result = {}
        for dev in self._gen_devices:
            key = f"{dev['bus']},{dev['sg_id']}"
            bus = dev["bus"]
            if dev["type"] == "PV":
                p = self._sf(self.ss.PV.p.v, dev["idx"])
                q = self._sf(self.ss.PV.q.v, dev["idx"])
                pmax = self._sf(self.ss.PV.pmax.v, dev["idx"])
                p0 = self._sf(self.ss.PV.p0.v, dev["idx"])
                sn = self._sf(self.ss.PV.Sn.v, dev["idx"]) if self.ss.PV.Sn.v is not None else 0
            elif dev["type"] == "Slack":
                p = self._sf(self.ss.Slack.p.v, dev["idx"])
                q = self._sf(self.ss.Slack.q.v, dev["idx"])
                pmax = p * 10
                p0 = p
                sn = p * 10

            result[key] = {
                "mw": round(p * self.mva_base, 2),
                "mvar": round(q * self.mva_base, 2),
                "mw_setpoint": round(p0 * self.mva_base, 2),
                "vpu_setpoint": round(1.0, 4),
                "status": 1 if dev["u"] > 0 else 0,
                "vpu": round(self._get_bus_v(bus), 4),
                "vangle": round(self._get_bus_a(bus), 4),
                "kv": self._get_bus_kv(bus),
                "freq_hz": 60.0,
                "bus_status": 1,
                "agc_status": 0,
            }
        return result

    def _build_load_data(self) -> dict:
        result = {}
        for item in self._load_indices:
            idx = item["pq_idx"]
            bus = item["bus"]
            key = f"{bus},{item['pq_id']}"
            u = float(self.ss.PQ.u.v[idx])
            result[key] = {
                "mw": round(self._sf(self.ss.PQ.p0.v, idx) * self.mva_base, 2),
                "mvar": round(self._sf(self.ss.PQ.q0.v, idx) * self.mva_base, 2),
                "status": 1 if u > 0 else 0,
                "vpu": round(self._get_bus_v(bus), 4),
                "vangle": round(self._get_bus_a(bus), 4),
                "kv": self._get_bus_kv(bus),
                "freq_hz": 60.0,
                "bus_status": 1,
            }
        return result

    def _build_shunt_data(self) -> dict:
        result = {}
        for item in self._shunt_indices:
            idx = item["sh_idx"]
            bus = item["bus"]
            key = f"{bus},{item['sh_id']}"
            u = float(self.ss.Shunt.u.v[idx])
            v = self._get_bus_v(bus)
            b = self._sf(self.ss.Shunt.b.v, idx)
            result[key] = {
                "mvar": round(v * v * b * self.mva_base, 2),
                "status": 1 if u > 0 else 0,
                "vpu": round(v, 4),
                "vangle": round(self._get_bus_a(bus), 4),
                "kv": self._get_bus_kv(bus),
                "freq_hz": 60.0,
                "bus_status": 1,
            }
        return result

    def _build_branch_data(self) -> dict:
        result = {}
        line_bus1 = self.ss.Line.bus1.v
        line_bus2 = self.ss.Line.bus2.v
        line_u = self.ss.Line.u.v
        line_rate_a = self.ss.Line.rate_a.v

        for i, idx in enumerate(self._line_indices):
            b1, b2 = int(line_bus1[idx]), int(line_bus2[idx])
            key = f"{b1},{b2},1"
            u = float(line_u[idx])
            rate_a = float(line_rate_a[idx])

            # Estimate power flow from bus angle difference and voltage
            v1 = self._get_bus_v(b1)
            v2 = self._get_bus_v(b2)
            a1 = self._get_bus_a(b1)
            a2 = self._get_bus_a(b2)
            theta = math.radians(a2 - a1)

            # Approximate MW flow using Zbus = 1 assumption
            x = round(abs(v2 * math.sin(theta) - v1 * math.sin(a1) + 0.5), 6)

            mva = round(abs(x) * self.mva_base, 2) if rate_a > 0 else 0

            result[key] = {
                "status": 1 if u > 0 else 0,
                "mw_from": round(abs(x) * self.mva_base, 2),
                "mvar_from": 0.0,
                "mva_from": mva,
                "amps_from": 0.0,
                "mva_limit": rate_a,
            }
        return result

    def _build_transformer_data(self) -> dict:
        result = {}
        line_bus1 = self.ss.Line.bus1.v
        line_bus2 = self.ss.Line.bus2.v
        line_u = self.ss.Line.u.v
        line_tap = self.ss.Line.tap.v if hasattr(self.ss.Line, 'tap') else None
        line_phi = self.ss.Line.phi.v if hasattr(self.ss.Line, 'phi') else None

        if line_tap is None and line_phi is None:
            return result

        for i, idx in enumerate(self._line_indices):
            tap = float(line_tap[idx]) if line_tap is not None else 1.0
            phi = float(line_phi[idx]) if line_phi is not None else 0.0
            if abs(tap - 1.0) > 1e-6 or abs(phi) > 1e-6:
                b1, b2 = int(line_bus1[idx]), int(line_bus2[idx])
                key = f"{b1},{b2},1"
                u = float(line_u[idx])
                result[key] = {
                    "phase": round(phi * 180.0 / math.pi, 4),
                    "tap": round(tap, 4),
                    "status": 1 if u > 0 else 0,
                }
        return result

    def _build_risk_data(self, buses, branches) -> dict:
        risk_buses = []
        for bus_num, data in buses.items():
            vpu = data.get("vpu", 1.0)
            if vpu <= 0.95 or vpu >= 1.05:
                risk_buses.append({
                    "bus_key": bus_num,
                    "vpu": vpu,
                    "status": "low" if vpu < 0.95 else "high",
                })

        risk_branches = []
        for key, data in branches.items():
            mva = data.get("mva_from", 0)
            limit = data.get("mva_limit", 0)
            if limit > 0 and mva >= 0.85 * limit:
                risk_branches.append({
                    "key": key,
                    "mva": mva,
                    "mva_limit": limit,
                    "ratio": round(mva / limit * 100, 2) if limit > 0 else 0,
                })

        count_overload = sum(1 for b in risk_branches if b.get("ratio", 0) > 100)
        r_index = round(50 * (math.exp(-0.05 * len(risk_buses)) + math.exp(-0.1 * count_overload)))

        return {"buses": risk_buses, "branches": risk_branches, "risk_index": r_index}

    def _accumulate_cost(self, state):
        delta_cost = 0.0
        for key, gen in state["gen"].items():
            mw = gen.get("mw", 0)
            mc = mw * 0.01
            delta_cost += mc
        delta_mwh = state["area"]["load_mw"] / 3600.0 if self.status == "running" else 0
        self.total_cost += delta_cost
        self.total_mwh += delta_mwh
        state["area"]["total_cost"] = round(self.total_cost, 2)
        state["area"]["total_mwh"] = round(self.total_mwh, 2)

    def _write_to_db(self, state):
        if not self.db_conn or not self.sim_id:
            return
        from database import insert_tick, insert_device_states
        tick_id = insert_tick(
            self.db_conn, self.sim_id, self.soc,
            state["area"], self.total_cost, self.total_mwh,
            state["risk"]["risk_index"],
        )
        device_types = ["bus", "gen", "load", "shunt", "branch", "transformer"]
        for dtype in device_types:
            if dtype in state and state[dtype]:
                insert_device_states(self.db_conn, tick_id, dtype, state[dtype])

    def apply_command(self, device_type: str, device_key: str, action: str,
                      username: str = "unknown") -> dict:
        try:
            if device_type == "Gen":
                return self._handle_gen(device_key, action, username)
            elif device_type == "Load":
                return self._handle_load(device_key, action, username)
            elif device_type == "Shunt":
                return self._handle_shunt(device_key, action, username)
            elif device_type == "Branch":
                return self._handle_branch(device_key, action, username)
            else:
                return {"success": False, "message": f"Unknown device type: {device_type}"}
        except Exception as e:
            logger.error(f"Command failed: {device_type} {device_key} {action}: {e}")
            return {"success": False, "message": str(e)}

    def _handle_gen(self, device_key: str, action: str, username: str) -> dict:
        dev = self._gen_key_map.get(device_key)
        if not dev:
            return {"success": False, "message": f"Generator not found: {device_key}"}

        model_idx = dev.get("model_idx", dev["idx"])
        if dev["type"] == "PV":
            if action == "OPEN":
                self.ss.PV.set(src='u', idx=model_idx, attr='v', value=0)
            elif action == "CLOSE":
                self.ss.PV.set(src='u', idx=model_idx, attr='v', value=1)
            elif action.startswith("Set Power"):
                parts = action.split()
                mw = float(parts[2])
                self.ss.PV.set(src='p0', idx=model_idx, attr='v', value=mw / self.mva_base)
            else:
                return {"success": False, "message": f"Unknown gen action: {action}"}
        elif dev["type"] == "Slack":
            if action == "OPEN":
                self.ss.Slack.set(src='u', idx=model_idx, attr='v', value=0)
            elif action == "CLOSE":
                self.ss.Slack.set(src='u', idx=model_idx, attr='v', value=1)
            else:
                return {"success": False, "message": f"Unknown gen action: {action}"}

        self._log_action(username, "Gen", device_key, action)
        return {"success": True, "message": f"Gen {device_key}: {action}"}

    def _handle_load(self, device_key: str, action: str, username: str) -> dict:
        idx = self._load_key_map.get(device_key)
        if idx is None:
            return {"success": False, "message": f"Load not found: {device_key}"}

        if action == "OPEN":
            self.ss.PQ.set(src='u', idx=idx, attr='v', value=0)
        elif action == "CLOSE":
            self.ss.PQ.set(src='u', idx=idx, attr='v', value=1)
        elif action.startswith("Set MW"):
            parts = action.split()
            mw = float(parts[2])
            self.ss.PQ.set(src='p0', idx=idx, attr='v', value=mw / self.mva_base)
        elif action.startswith("Set Mvar"):
            parts = action.split()
            mvar = float(parts[2])
            self.ss.PQ.set(src='q0', idx=idx, attr='v', value=mvar / self.mva_base)
        else:
            return {"success": False, "message": f"Unknown load action: {action}"}

        self._log_action(username, "Load", device_key, action)
        return {"success": True, "message": f"Load {device_key}: {action}"}

    def _handle_shunt(self, device_key: str, action: str, username: str) -> dict:
        idx = self._shunt_key_map.get(device_key)
        if idx is None:
            return {"success": False, "message": f"Shunt not found: {device_key}"}

        if action == "OPEN":
            self.ss.Shunt.set(src='u', idx=idx, attr='v', value=0)
        elif action == "CLOSE":
            self.ss.Shunt.set(src='u', idx=idx, attr='v', value=1)
        else:
            return {"success": False, "message": f"Unknown shunt action: {action}"}

        self._log_action(username, "Shunt", device_key, action)
        return {"success": True, "message": f"Shunt {device_key}: {action}"}

    def _handle_branch(self, device_key: str, action: str, username: str) -> dict:
        idx = self._branch_key_map.get(device_key)
        if idx is None:
            return {"success": False, "message": f"Branch not found: {device_key}"}

        if "OPEN" in action:
            self.ss.Line.set(src='u', idx=idx, attr='v', value=0)
        elif "CLOSE" in action:
            self.ss.Line.set(src='u', idx=idx, attr='v', value=1)
        else:
            return {"success": False, "message": f"Unknown branch action: {action}"}

        self._log_action(username, "Branch", device_key, action)
        return {"success": True, "message": f"Branch {device_key}: {action}"}

    def _log_action(self, username, device_type, device_key, action):
        if self.db_conn and self.sim_id:
            from database import insert_action
            insert_action(self.db_conn, self.sim_id, self.soc, username, device_type, device_key, action)

    def get_case_data(self) -> dict:
        """Export static case data for the frontend (all areas, all devices)."""
        bus_ids = self.ss.Bus.idx.v
        bus_areas = self.ss.Bus.area.v
        bus_kv = self.ss.Bus.Vn.v
        bus_u = self.ss.Bus.u.v
        bus_vmin = self.ss.Bus.vmin.v
        bus_vmax = self.ss.Bus.vmax.v

        # Build bus→area lookup
        bus_area_map = {}
        for i in range(self.ss.Bus.n):
            bus_area_map[int(bus_ids[i])] = int(float(bus_areas[i]))

        buses = {}
        for i in range(self.ss.Bus.n):
            bus_num = str(int(bus_ids[i]))
            buses[bus_num] = {
                "Int.Bus Number": bus_num,
                "Int.Area Number": int(float(bus_areas[i])),
                "Int.Sub Number": 0,
                "String.Name": bus_num,
                "Single.Nominal kV": float(bus_kv[i]),
                "Single.Min Limit": float(bus_vmin[i]),
                "Single.Max Limit": float(bus_vmax[i]),
            }

        # Export all generators using StaticGen
        gens = {}
        if hasattr(self.ss, 'StaticGen'):
            sg_idxes = self.ss.StaticGen.get_all_idxes()
            for idx in sg_idxes:
                bus = int(float(self.ss.StaticGen.get(src='bus', attr='v', idx=idx)))
                gen_id = str(idx)
                if '_' in gen_id:
                    gen_id = gen_id.split('_')[-1]
                key = f"{bus},{gen_id}"
                gens[key] = {
                    "Int.Bus Number": bus,
                    "Int.Area Number": bus_area_map.get(bus, 0),
                    "String.ID": gen_id,
                    "Single.MW Max Limit": round(self._sf(self.ss.StaticGen.get(src='pmax', attr='v', idx=idx)) * self.mva_base, 2),
                    "Single.MW Min Limit": round(self._sf(self.ss.StaticGen.get(src='pmin', attr='v', idx=idx)) * self.mva_base, 2),
                    "Single.MW Setpoint": round(self._sf(self.ss.StaticGen.get(src='p0', attr='v', idx=idx)) * self.mva_base, 2),
                    "Single.Voltage Setpoint": 1.0,
                    "OperationCost": 0,
                    "MarginalCostCoefficients": [0.01],
                }

        # Export all loads
        loads = {}
        for i in range(self.ss.PQ.n):
            bus = int(self.ss.PQ.bus.v[i])
            key = f"{bus},{i+1}"
            loads[key] = {
                "Int.Bus Number": bus,
                "Int.Area Number": bus_area_map.get(bus, 0),
                "String.ID": str(i+1),
            }

        # Export all shunts
        shunts = {}
        for i in range(self.ss.Shunt.n):
            bus = int(self.ss.Shunt.bus.v[i])
            key = f"{bus},{i+1}"
            shunts[key] = {
                "Int.Bus Number": bus,
                "Int.Area Number": bus_area_map.get(bus, 0),
                "String.ID": str(i+1),
            }

        # Export all branches
        line_bus1 = self.ss.Line.bus1.v
        line_bus2 = self.ss.Line.bus2.v
        line_rate_a = self.ss.Line.rate_a.v

        branches = {}
        for i in range(self.ss.Line.n):
            b1, b2 = int(line_bus1[i]), int(line_bus2[i])
            key = f"{b1},{b2},1"
            branches[key] = {
                "Int.From Bus Number": b1,
                "Int.To Bus Number": b2,
                "Byte.Type": 0,
                "Single.MVA Limit": float(line_rate_a[i]),
                "String.CircuitID": "1",
            }

        # Export all areas
        areas = {}
        if hasattr(self.ss, 'Area'):
            for i in range(self.ss.Area.n):
                area_num = str(int(float(self.ss.Area.idx.v[i])))
                areas[area_num] = {
                    "Int.Number": int(area_num),
                    "String.Name": f"Area {area_num}",
                }

        return {
            "type": "dsmDictionary",
            "content": {
                "Substation": {},
                "Bus": buses,
                "Gen": gens,
                "Load": loads,
                "Shunt": shunts,
                "Branch": branches,
                "Transformer": {},
                "Area": areas,
            },
        }
