"""Persistencia SQLite e criacao automatica do schema."""
import os
import sqlite3
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.environ.get('TICKETS_DB', str(BASE / 'tickets.sqlite3')))

SCHEMA = '''
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS departments (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 name TEXT NOT NULL UNIQUE COLLATE NOCASE,
 prefix TEXT NOT NULL UNIQUE COLLATE NOCASE CHECK(length(prefix) BETWEEN 1 AND 4),
 active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
 created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS service_points (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 name TEXT NOT NULL UNIQUE COLLATE NOCASE,
 active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1))
);
CREATE TABLE IF NOT EXISTS tickets (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 code TEXT NOT NULL UNIQUE,
 department_id INTEGER NOT NULL REFERENCES departments(id) ON DELETE RESTRICT,
 service_point_id INTEGER REFERENCES service_points(id) ON DELETE SET NULL,
 customer_name TEXT NOT NULL CHECK(length(trim(customer_name)) BETWEEN 1 AND 100),
 description TEXT NOT NULL DEFAULT '',
 priority TEXT NOT NULL DEFAULT 'NORMAL' CHECK(priority IN ('NORMAL','PREFERENCIAL')),
 status TEXT NOT NULL DEFAULT 'WAITING' CHECK(status IN ('WAITING','CALLED','IN_SERVICE','FINISHED','CANCELLED')),
 created_at TEXT NOT NULL DEFAULT (datetime('now')),
 updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_ticket_queue ON tickets(status, priority, created_at);
CREATE INDEX IF NOT EXISTS idx_ticket_department ON tickets(department_id);
CREATE TABLE IF NOT EXISTS ticket_events (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 ticket_id INTEGER NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
 old_status TEXT,
 new_status TEXT NOT NULL,
 note TEXT NOT NULL DEFAULT '',
 created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
'''

class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback):
        try: return super().__exit__(exc_type, exc_value, traceback)
        finally: self.close()

def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(DB_PATH), timeout=10, factory=ClosingConnection)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys = ON')
    return db

def initialize():
    with connect() as db:
        db.executescript(SCHEMA)
        db.execute("INSERT OR IGNORE INTO departments (name,prefix) VALUES ('Atendimento Geral','AT')")
        db.execute("INSERT OR IGNORE INTO departments (name,prefix) VALUES ('Suporte Tecnico','ST')")
        db.execute("INSERT OR IGNORE INTO service_points (name) VALUES ('Guiche 1')")
        db.execute("INSERT OR IGNORE INTO service_points (name) VALUES ('Guiche 2')")
