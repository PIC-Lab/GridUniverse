import logging
from pathlib import Path

logger = logging.getLogger(__name__)

COORDINATES_FALLBACK = Path(__file__).parent.parent / "src" / "assets" / "2000.json"


def load_substation_coordinates(fallback_path: str = None) -> dict:
    path = fallback_path or str(COORDINATES_FALLBACK)
    try:
        with open(path, 'r') as f:
            data = json_load(f)
        coords = {}
        for sub_id, sub_data in data.get("content", data).get("Substation", {}).items():
            coords[int(sub_id)] = {
                "latitude": sub_data.get("Double.Latitude", 0),
                "longitude": sub_data.get("Double.Longitude", 0),
                "name": sub_data.get("String.Name", ""),
                "sub_id": sub_data.get("String.SubID", sub_id),
            }
        return coords
    except FileNotFoundError:
        logger.warning(f"Coordinates fallback file not found: {path}")
        return {}
    except Exception as e:
        logger.error(f"Error loading coordinates: {e}")
        return {}


def json_load(f):
    import json
    return json.load(f)


def export_case(ss, coordinates: dict = None) -> dict:
    """Export full case data (all areas, all devices) for the frontend."""
    if coordinates is None:
        coordinates = load_substation_coordinates()

    mva_base = ss.config.mva if hasattr(ss.config, 'mva') else 100.0
    result = {"type": "dsmDictionary", "ObjectType Count": 25, "content": {}}

    _export_areas(ss, result["content"])
    _export_substations(ss, result["content"], coordinates)
    _export_buses(ss, result["content"], coordinates, mva_base)
    _export_gens(ss, result["content"], mva_base)
    _export_loads(ss, result["content"], mva_base)
    _export_shunts(ss, result["content"], mva_base)
    _export_branches(ss, result["content"], mva_base)
    _export_transformers(ss, result["content"], mva_base)

    return result


def _safe(val, default=0.0):
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _get_area_for_bus(ss, bus_num):
    """Get area number for a bus using array-based access."""
    bus_ids = ss.Bus.idx.v
    if bus_num in bus_ids:
        idx = bus_ids.index(bus_num)
        return int(float(ss.Bus.area.v[idx]))
    return 0


def _export_substations(ss, content: dict, coordinates: dict):
    """Copy substations from the fallback JSON file."""
    path = str(COORDINATES_FALLBACK)
    try:
        with open(path, 'r') as f:
            data = json_load(f)
        content["Substation"] = data.get("content", data).get("Substation", {})
    except FileNotFoundError:
        content["Substation"] = {}


def _export_areas(ss, content: dict):
    content["Area"] = {}
    content["Case"] = {}
    if not hasattr(ss, 'Area'):
        return
    area_names = ss.Area.name.v if hasattr(ss.Area, 'name') else ss.Area.idx.v
    for i in range(ss.Area.n):
        area_num = int(float(ss.Area.idx.v[i]))
        content["Area"][str(area_num)] = {
            "Byte.Option": 1,
            "Int.Number": area_num,
            "String.Name": str(area_names[i]) if area_names else f"Area {area_num}",
            "String.Superarea Name": "",
        }


def _export_buses(ss, content: dict, coordinates: dict, mva_base: float):
    content["Bus"] = {}
    bus_ids = ss.Bus.idx.v
    bus_areas = ss.Bus.area.v
    bus_zones = ss.Bus.zone.v if hasattr(ss.Bus, 'zone') else None
    bus_kv = ss.Bus.Vn.v
    bus_vmax = ss.Bus.vmax.v
    bus_vmin = ss.Bus.vmin.v
    bus_u = ss.Bus.u.v

    # Build bus→sub mapping from the fallback JSON
    bus_to_sub = {}
    path = str(COORDINATES_FALLBACK)
    try:
        with open(path, 'r') as f:
            ref = json_load(f)
        ref_content = ref.get("content", ref)
        for bk, bv in ref_content.get("Bus", {}).items():
            bus_to_sub[int(bk)] = bv.get("Int.Sub Number", int(bk))
    except (FileNotFoundError, KeyError):
        pass

    for i in range(ss.Bus.n):
        bus_num = int(bus_ids[i])
        area = int(float(bus_areas[i]))
        zone = int(float(bus_zones[i])) if bus_zones and i < len(bus_zones) else 0
        sub_num = bus_to_sub.get(bus_num, bus_num)

        content["Bus"][str(bus_num)] = {
            "Int.Bus Number": bus_num,
            "Int.Area Number": area,
            "Int.Zone Number": zone,
            "Int.Sub Number": int(sub_num),
            "Single.Nominal kV": float(bus_kv[i]),
            "Single.Max Limit": float(bus_vmax[i]),
            "Single.Min Limit": float(bus_vmin[i]),
            "String.Name": str(bus_num),
        }


def _export_gens(ss, content: dict, mva_base: float):
    content["Gen"] = {}
    # Use StaticGen which aggregates PV + Slack
    if not hasattr(ss, 'StaticGen'):
        return
    sg_idxes = ss.StaticGen.get_all_idxes()
    for idx in sg_idxes:
        bus_num = int(float(ss.StaticGen.get(src='bus', attr='v', idx=idx)))
        gen_id = _extract_device_id(idx)
        key = f"{bus_num},{gen_id}"

        pmax = _safe(ss.StaticGen.get(src='pmax', attr='v', idx=idx), 999) * mva_base
        pmin = _safe(ss.StaticGen.get(src='pmin', attr='v', idx=idx), 0) * mva_base
        p0 = _safe(ss.StaticGen.get(src='p0', attr='v', idx=idx), 0) * mva_base
        v0 = _safe(ss.StaticGen.get(src='v0', attr='v', idx=idx), 1.0)
        area = _get_area_for_bus(ss, bus_num)

        mc0 = pmax * 0.01
        mc1 = 10.0

        content["Gen"][key] = {
            "Int.Bus Number": bus_num,
            "Int.Area Number": area,
            "Int.Zone Number": 0,
            "Single.Voltage Setpoint": round(v0, 4),
            "Single.MW Setpoint": round(p0, 2),
            "Single.MVA Base": _safe(ss.StaticGen.get(src='Sn', attr='v', idx=idx), mva_base),
            "Single.MW Max Limit": round(pmax, 2),
            "Single.MW Min Limit": round(pmin, 2),
            "String.ID": gen_id,
            "OperationCost": round(mc1, 2),
            "MarginalCostCoefficients": [round(mc0, 2), round(mc1, 2)],
        }


def _export_loads(ss, content: dict, mva_base: float):
    content["Load"] = {}
    if not hasattr(ss, 'PQ'):
        return
    pq_idxes = ss.PQ.get_all_idxes()
    for idx in pq_idxes:
        bus_num = int(float(ss.PQ.get(src='bus', attr='v', idx=idx)))
        load_id = _extract_device_id(idx)
        key = f"{bus_num},{load_id}"
        area = _get_area_for_bus(ss, bus_num)

        content["Load"][key] = {
            "Int.Bus Number": bus_num,
            "Int.Area Number": area,
            "Int.Zone Number": 0,
            "Single.Load Scalar": 1.0,
            "Single.Nominal Mvar": _safe(ss.PQ.get(src='q0', attr='v', idx=idx), 0) * mva_base,
            "String.ID": load_id,
        }


def _export_shunts(ss, content: dict, mva_base: float):
    content["Shunt"] = {}
    if not hasattr(ss, 'Shunt'):
        return
    sh_idxes = ss.Shunt.get_all_idxes()
    for idx in sh_idxes:
        bus_num = int(float(ss.Shunt.get(src='bus', attr='v', idx=idx)))
        shunt_id = _extract_device_id(idx)
        key = f"{bus_num},{shunt_id}"
        area = _get_area_for_bus(ss, bus_num)

        content["Shunt"][key] = {
            "Int.Bus Number": bus_num,
            "Int.Area Number": area,
            "Int.Zone Number": 0,
            "Single.Nominal Mvar": abs(_safe(ss.Shunt.get(src='b', attr='v', idx=idx), 0)) * mva_base,
            "String.ID": shunt_id,
        }


def _export_branches(ss, content: dict, mva_base: float):
    content["Branch"] = {}
    if not hasattr(ss, 'Line'):
        return
    line_idxes = ss.Line.get_all_idxes()

    for idx in line_idxes:
        if _is_transformer(ss, idx):
            continue

        bus1 = int(float(ss.Line.get(src='bus1', attr='v', idx=idx)))
        bus2 = int(float(ss.Line.get(src='bus2', attr='v', idx=idx)))
        key = f"{bus1},{bus2},1"

        content["Branch"][key] = {
            "Int.From Bus Number": bus1,
            "Int.To Bus Number": bus2,
            "String.CircuitID": "1",
            "Byte.Type": 0,
            "Single.MVA Limit": _safe(ss.Line.get(src='rate_a', attr='v', idx=idx), 999) * mva_base,
        }


def _export_transformers(ss, content: dict, mva_base: float):
    content["Transformer"] = {}
    if not hasattr(ss, 'Line'):
        return
    line_idxes = ss.Line.get_all_idxes()

    for idx in line_idxes:
        if not _is_transformer(ss, idx):
            continue

        bus1 = int(float(ss.Line.get(src='bus1', attr='v', idx=idx)))
        bus2 = int(float(ss.Line.get(src='bus2', attr='v', idx=idx)))
        key = f"{bus1},{bus2},1"

        tap = _safe(ss.Line.get(src='tap', attr='v', idx=idx), 1.0)
        content["Transformer"][key] = {
            "Int.From Bus Number": bus1,
            "Int.To Bus Number": bus2,
            "String.CircuitID": "1",
            "Single.Min Tap/PA": round(tap - 0.2, 4),
            "Single.Max Tap/PA": round(tap + 0.2, 4),
            "Single.Step Size": 0.00625,
        }


def _is_transformer(ss, idx):
    try:
        tap = ss.Line.get(src='tap', attr='v', idx=idx)
        phi = ss.Line.get(src='phi', attr='v', idx=idx)
        if tap is not None and abs(float(tap) - 1.0) > 1e-6:
            return True
        if phi is not None and abs(float(phi)) > 1e-6:
            return True
        trans = ss.Line.get(src='trans', attr='v', idx=idx)
        if trans is not None and float(trans) == 1:
            return True
    except Exception:
        pass
    return False


def _extract_device_id(idx):
    idx_str = str(idx)
    if '_' in idx_str:
        return idx_str.split('_')[-1]
    return idx_str
