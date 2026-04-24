import sqlite3
import json
from pathlib import Path

DB_PATH = Path(__file__).parent / "simulation.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS simulations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_name TEXT NOT NULL,
    area_id INTEGER DEFAULT 2,
    status TEXT DEFAULT 'offline',
    routine TEXT DEFAULT 'PFlow',
    started_at TEXT,
    ended_at TEXT
);

CREATE TABLE IF NOT EXISTS ticks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sim_id INTEGER REFERENCES simulations(id),
    soc INTEGER NOT NULL,
    timestamp TEXT DEFAULT (datetime('now')),
    gen_mw REAL,
    gen_mvar REAL,
    load_mw REAL,
    load_mvar REAL,
    shunt_mvar REAL,
    export_mw REAL,
    frequency REAL,
    ace REAL,
    loss_mw REAL,
    total_cost REAL,
    total_mwh REAL,
    risk_index INTEGER
);

CREATE TABLE IF NOT EXISTS device_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tick_id INTEGER REFERENCES ticks(id),
    device_type TEXT NOT NULL,
    device_key TEXT NOT NULL,
    data_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sim_id INTEGER REFERENCES simulations(id),
    soc INTEGER NOT NULL,
    username TEXT,
    device_type TEXT,
    device_key TEXT,
    action TEXT,
    timestamp TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_ticks_sim_soc ON ticks(sim_id, soc);
CREATE INDEX IF NOT EXISTS idx_device_states_tick ON device_states(tick_id);
CREATE INDEX IF NOT EXISTS idx_actions_sim ON actions(sim_id);
"""


def get_connection(db_path: str = None) -> sqlite3.Connection:
    path = db_path or str(DB_PATH)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_db(db_path: str = None):
    conn = get_connection(db_path)
    conn.executescript(SCHEMA)
    conn.close()


def insert_simulation(conn: sqlite3.Connection, case_name: str, area_id: int) -> int:
    cur = conn.execute(
        "INSERT INTO simulations (case_name, area_id, status) VALUES (?, ?, 'offline')",
        (case_name, area_id),
    )
    conn.commit()
    return cur.lastrowid


def update_simulation_status(conn: sqlite3.Connection, sim_id: int, status: str):
    if status in ("running",):
        conn.execute(
            "UPDATE simulations SET status = ?, started_at = datetime('now') WHERE id = ?",
            (status, sim_id),
        )
    elif status in ("finished", "aborted"):
        conn.execute(
            "UPDATE simulations SET status = ?, ended_at = datetime('now') WHERE id = ?",
            (status, sim_id),
        )
    else:
        conn.execute(
            "UPDATE simulations SET status = ? WHERE id = ?",
            (status, sim_id),
        )
    conn.commit()


def insert_tick(conn: sqlite3.Connection, sim_id: int, soc: int, area: dict,
                total_cost: float = 0, total_mwh: float = 0,
                risk_index: int = 100) -> int:
    cur = conn.execute(
        """INSERT INTO ticks
           (sim_id, soc, gen_mw, gen_mvar, load_mw, load_mvar, shunt_mvar,
            export_mw, frequency, ace, loss_mw, total_cost, total_mwh, risk_index)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (sim_id, soc,
         area.get("gen_mw"), area.get("gen_mvar"),
         area.get("load_mw"), area.get("load_mvar"), area.get("shunt_mvar"),
         area.get("export_mw"), area.get("frequency"),
         area.get("ace"), area.get("loss_mw"),
         total_cost, total_mwh, risk_index),
    )
    conn.commit()
    return cur.lastrowid


def insert_device_states(conn: sqlite3.Connection, tick_id: int,
                         device_type: str, devices: dict):
    rows = [
        (tick_id, device_type, key, json.dumps(val, default=float))
        for key, val in devices.items()
    ]
    conn.executemany(
        "INSERT INTO device_states (tick_id, device_type, device_key, data_json) VALUES (?, ?, ?, ?)",
        rows,
    )
    conn.commit()


def insert_action(conn: sqlite3.Connection, sim_id: int, soc: int,
                  username: str, device_type: str, device_key: str, action: str):
    conn.execute(
        "INSERT INTO actions (sim_id, soc, username, device_type, device_key, action) VALUES (?, ?, ?, ?, ?, ?)",
        (sim_id, soc, username, device_type, device_key, action),
    )
    conn.commit()


def get_latest_tick(conn: sqlite3.Connection, sim_id: int) -> dict | None:
    row = conn.execute(
        "SELECT * FROM ticks WHERE sim_id = ? ORDER BY soc DESC LIMIT 1",
        (sim_id,),
    ).fetchone()
    if row is None:
        return None
    return dict(row)


def get_ticks(conn: sqlite3.Connection, sim_id: int,
              from_soc: int = None, to_soc: int = None,
              limit: int = 1000) -> list[dict]:
    query = "SELECT * FROM ticks WHERE sim_id = ?"
    params: list = [sim_id]
    if from_soc is not None:
        query += " AND soc >= ?"
        params.append(from_soc)
    if to_soc is not None:
        query += " AND soc <= ?"
        params.append(to_soc)
    query += " ORDER BY soc ASC LIMIT ?"
    params.append(limit)
    return [dict(r) for r in conn.execute(query, params).fetchall()]


def get_device_states_for_tick(conn: sqlite3.Connection, tick_id: int,
                                device_type: str = None) -> list[dict]:
    query = "SELECT device_key, data_json FROM device_states WHERE tick_id = ?"
    params: list = [tick_id]
    if device_type:
        query += " AND device_type = ?"
        params.append(device_type)
    rows = conn.execute(query, params).fetchall()
    return [{"key": r["device_key"], "data": json.loads(r["data_json"])} for r in rows]


def get_actions(conn: sqlite3.Connection, sim_id: int, limit: int = 500) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM actions WHERE sim_id = ? ORDER BY soc ASC LIMIT ?",
        (sim_id, limit),
    ).fetchall()
    return [dict(r) for r in rows]


def get_simulation(conn: sqlite3.Connection, sim_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM simulations WHERE id = ?", (sim_id,)).fetchone()
    return dict(row) if row else None
