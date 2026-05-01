import asyncio
import json
import logging
import argparse
import sys
from pathlib import Path

# Add AMS to path if installed locally
_ams_candidates = [
    Path.home() / "GitHub" / "ams",
    Path.home() / "github" / "ams",
    Path(__file__).resolve().parent.parent.parent / "GitHub" / "ams",
    Path(__file__).resolve().parent.parent.parent / "github" / "ams",
]
for _ams_path in _ams_candidates:
    if _ams_path.is_dir() and (_ams_path / "ams" / "__init__.py").is_file():
        if str(_ams_path) not in sys.path:
            sys.path.insert(0, str(_ams_path))
        break

import ams
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from database import (
    init_db, get_connection, insert_simulation, get_latest_tick,
    get_ticks, get_device_states_for_tick, get_actions, get_simulation,
)
from simulator import AMSSimulator
from case_exporter import export_case

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="GridUniverse Backend (AMS)")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

simulator: Optional[AMSSimulator] = None
case_data_cache: Optional[dict] = None
db_path: Optional[str] = None
ws_clients: list[WebSocket] = []


# --- Pydantic models ---

class SimStartRequest(BaseModel):
    end_soc: Optional[int] = None
    routine: str = "PFlow"

class PowerRequest(BaseModel):
    mw: float

class MvarRequest(BaseModel):
    mvar: float

class SimRunToRequest(BaseModel):
    seconds: int


# --- Startup ---

@app.on_event("startup")
async def startup():
    asyncio.create_task(simulation_loop())


# --- REST endpoints: Health ---

@app.get("/api/health")
async def health():
    return {"status": "ok", "simulator": simulator is not None}


# --- REST endpoints: Case data ---

@app.get("/api/case")
async def get_case():
    if case_data_cache is None:
        raise HTTPException(500, "No case loaded")
    return case_data_cache


@app.get("/api/case/devices/{device_type}")
async def get_devices(device_type: str):
    if case_data_cache is None:
        raise HTTPException(500, "No case loaded")
    content = case_data_cache.get("content", case_data_cache)
    return content.get(device_type, {})


# --- REST endpoints: Simulation control ---

@app.post("/api/sim/start")
async def sim_start(req: SimStartRequest = SimStartRequest()):
    if simulator is None:
        raise HTTPException(500, "No simulator loaded")
    result = simulator.start(end_soc=req.end_soc, routine=req.routine)
    await broadcast({"type": "event", "data": result["message"]})
    return result


@app.post("/api/sim/pause")
async def sim_pause():
    if simulator is None:
        raise HTTPException(500, "No simulator loaded")
    result = simulator.pause()
    await broadcast({"type": "event", "data": result["message"]})
    return result


@app.post("/api/sim/continue")
async def sim_continue():
    if simulator is None:
        raise HTTPException(500, "No simulator loaded")
    result = simulator.continue_sim()
    await broadcast({"type": "event", "data": result["message"]})
    return result


@app.post("/api/sim/abort")
async def sim_abort():
    if simulator is None:
        raise HTTPException(500, "No simulator loaded")
    result = simulator.abort()
    await broadcast({"type": "event", "data": result["message"]})
    return result


@app.post("/api/sim/run-to")
async def sim_run_to(req: SimRunToRequest):
    if simulator is None:
        raise HTTPException(500, "No simulator loaded")
    result = simulator.start(end_soc=req.seconds)
    await broadcast({"type": "event", "data": result["message"]})
    return result


@app.get("/api/sim/status")
async def sim_status():
    if simulator is None:
        return {"status": "offline", "soc": 0, "routine": None}
    return {
        "status": simulator.status,
        "soc": simulator.soc,
        "routine": simulator.routine,
        "total_cost": round(simulator.total_cost, 2),
        "total_mwh": round(simulator.total_mwh, 2),
    }


# --- REST endpoints: Device commands ---

@app.post("/api/devices/gen/{key}/open")
async def gen_open(key: str):
    return _device_command("Gen", key, "OPEN")


@app.post("/api/devices/gen/{key}/close")
async def gen_close(key: str):
    return _device_command("Gen", key, "CLOSE")


@app.post("/api/devices/gen/{key}/power")
async def gen_power(key: str, req: PowerRequest):
    return _device_command("Gen", key, f"Set Power {req.mw} MW")


@app.post("/api/devices/gen/{key}/agc/enable")
async def gen_agc_enable(key: str):
    return _device_command("Gen", key, "AGC ENABLE")


@app.post("/api/devices/gen/{key}/agc/disable")
async def gen_agc_disable(key: str):
    return _device_command("Gen", key, "AGC DISABLE")


@app.post("/api/devices/load/{key}/open")
async def load_open(key: str):
    return _device_command("Load", key, "OPEN")


@app.post("/api/devices/load/{key}/close")
async def load_close(key: str):
    return _device_command("Load", key, "CLOSE")


@app.post("/api/devices/load/{key}/power")
async def load_power(key: str, req: PowerRequest):
    return _device_command("Load", key, f"Set MW {req.mw}")


@app.post("/api/devices/load/{key}/reactive")
async def load_reactive(key: str, req: MvarRequest):
    return _device_command("Load", key, f"Set Mvar {req.mvar}")


@app.post("/api/devices/shunt/{key}/open")
async def shunt_open(key: str):
    return _device_command("Shunt", key, "OPEN")


@app.post("/api/devices/shunt/{key}/close")
async def shunt_close(key: str):
    return _device_command("Shunt", key, "CLOSE")


@app.post("/api/devices/branch/{key}/open")
async def branch_open(key: str):
    return _device_command("Branch", key, "OPEN BOTH")


@app.post("/api/devices/branch/{key}/close")
async def branch_close(key: str):
    return _device_command("Branch", key, "CLOSE BOTH")


def _device_command(device_type: str, key: str, action: str) -> dict:
    if simulator is None:
        raise HTTPException(500, "No simulator loaded")
    result = simulator.apply_command(device_type, key, action)

    if result.get("success"):
        asyncio.create_task(broadcast({
            "type": "note",
            "data": f"#Admin just issued {action} at {key}",
        }))

    return result


# --- REST endpoints: History ---

@app.get("/api/history/ticks")
async def history_ticks(sim_id: int, from_soc: int = None, to_soc: int = None, limit: int = 1000):
    conn = get_connection(db_path)
    ticks = get_ticks(conn, sim_id, from_soc, to_soc, limit)
    conn.close()
    return ticks


@app.get("/api/history/ticks/{tick_id}/devices")
async def history_tick_devices(tick_id: int, device_type: str = None):
    conn = get_connection(db_path)
    states = get_device_states_for_tick(conn, tick_id, device_type)
    conn.close()
    return states


@app.get("/api/history/actions")
async def history_actions(sim_id: int, limit: int = 500):
    conn = get_connection(db_path)
    actions = get_actions(conn, sim_id, limit)
    conn.close()
    return actions


@app.get("/api/history/simulations")
async def history_simulations():
    conn = get_connection(db_path)
    rows = conn.execute("SELECT id, case_name, area_id, status, routine, started_at, ended_at FROM simulations ORDER BY id DESC LIMIT 50").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# --- WebSocket ---

@app.websocket("/ws/sim")
async def ws_sim(websocket: WebSocket):
    await websocket.accept()
    ws_clients.append(websocket)
    logger.info(f"WebSocket client connected (total: {len(ws_clients)})")
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        ws_clients.remove(websocket)
        logger.info(f"WebSocket client disconnected (total: {len(ws_clients)})")


async def broadcast(message: dict):
    dead = []
    text = json.dumps(message, default=float)
    for ws in ws_clients:
        try:
            await ws.send_text(text)
        except Exception:
            dead.append(ws)
    for ws in dead:
        ws_clients.remove(ws)


# --- Background simulation loop ---

async def simulation_loop():
    global simulator
    while True:
        if simulator and simulator.status == "running":
            state = simulator.tick()
            if state:
                await broadcast({"type": "tick", "data": state})
                if state["status"] in ("finished", "aborted"):
                    await broadcast({"type": "event", "data": state.get("message", state["status"])})
        await asyncio.sleep(1.0)


# --- Main ---

def main():
    global simulator, case_data_cache, db_path

    parser = argparse.ArgumentParser(description="GridUniverse Backend (AMS)")
    parser.add_argument("--case", type=str, required=True, help="Path to AMS case file (.xlsx or .m)")
    parser.add_argument("--port", type=int, default=8000, help="Server port")
    parser.add_argument("--area", type=int, default=2, help="Area ID to simulate")
    parser.add_argument("--db", type=str, default=None, help="SQLite database path")
    args = parser.parse_args()

    db_path = args.db or str(Path(__file__).parent / "simulation.db")
    init_db(db_path)
    logger.info(f"Database initialized at {db_path}")

    logger.info(f"Loading AMS case: {args.case}")
    ss = ams.load(args.case, setup=True, no_output=True)
    logger.info(f"AMS case loaded. MVA base: {ss.config.mva}")

    simulator = AMSSimulator(ss, area_id=args.area)

    logger.info("Exporting case data...")
    case_data_cache = export_case(ss)
    logger.info(f"Case data exported: {len(case_data_cache.get('content', {}))} device types")

    conn = get_connection(db_path)
    sim_id = insert_simulation(conn, Path(args.case).name, args.area)
    simulator.set_db(conn, sim_id)
    logger.info(f"Simulation ID: {sim_id}")

    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=args.port, log_level="info")


if __name__ == "__main__":
    import uvicorn
    main()
