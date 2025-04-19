import sqlite3
import json
from typing import List, Tuple

DB_FILE = 'split_app.db'

def get_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_db():
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            payer_id INTEGER NOT NULL,
            involved_ids TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY(payer_id) REFERENCES participants(id)
        )''')
        conn.commit()

def add_participant(name: str):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('INSERT INTO participants (name) VALUES (?)', (name,))
        conn.commit()

def remove_participant(pid: int):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('DELETE FROM participants WHERE id=?', (pid,))
        c.execute('DELETE FROM transactions WHERE payer_id=?', (pid,))
        conn.commit()

def get_participants() -> List[Tuple[int, str]]:
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT id, name FROM participants ORDER BY name')
        return c.fetchall()

def add_transaction(description: str, amount: float, payer_id: int, involved_ids: List[int], timestamp: str):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('''INSERT INTO transactions (description, amount, payer_id, involved_ids, timestamp)
                     VALUES (?, ?, ?, ?, ?)''',
                  (description, amount, payer_id, json.dumps(involved_ids), timestamp))
        conn.commit()

def update_transaction(tid: int, description: str, amount: float, payer_id: int, involved_ids: List[int], timestamp: str):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('''UPDATE transactions SET description=?, amount=?, payer_id=?, involved_ids=?, timestamp=? WHERE id=?''',
                  (description, amount, payer_id, json.dumps(involved_ids), timestamp, tid))
        conn.commit()

def delete_transaction(tid: int):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('DELETE FROM transactions WHERE id=?', (tid,))
        conn.commit()

def get_transactions() -> List[Tuple]:
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT id, description, amount, payer_id, involved_ids, timestamp FROM transactions ORDER BY timestamp DESC')
        return c.fetchall()
