import sqlite3
import json
from typing import List, Tuple, Optional

DB_FILE = 'split_app.db'

def get_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_db():
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            split_id INTEGER NOT NULL,
            UNIQUE(name, split_id),
            FOREIGN KEY(split_id) REFERENCES splits(id)
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS splits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            date TEXT NOT NULL,
            created_at TEXT NOT NULL
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            split_id INTEGER NOT NULL,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            payer_id INTEGER NOT NULL,
            involved_ids TEXT NOT NULL,
            settled_ids TEXT NOT NULL DEFAULT '[]',
            timestamp TEXT NOT NULL,
            FOREIGN KEY(payer_id) REFERENCES participants(id),
            FOREIGN KEY(split_id) REFERENCES splits(id)
        )''')
        conn.commit()

def add_participant(name: str, split_id: int):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('INSERT INTO participants (name, split_id) VALUES (?, ?)', (name, split_id))
        conn.commit()

def remove_participant(pid: int, split_id: int):
    with get_connection() as conn:
        c = conn.cursor()
        # Get all transactions for this split
        c.execute('SELECT id, payer_id, involved_ids, description, amount, timestamp FROM transactions WHERE split_id=?', (split_id,))
        txns = c.fetchall()
        for tid, payer_id, involved_json, description, amount, timestamp in txns:
            involved = json.loads(involved_json)
            if pid in involved:
                involved = [x for x in involved if x != pid]
                if len(involved) < 2:
                    # Not enough people to split, delete transaction
                    c.execute('DELETE FROM transactions WHERE id=?', (tid,))
                    continue
                # If payer is being removed, reassign payer to first remaining involved participant
                if payer_id == pid:
                    payer_id = involved[0]
                # Update transaction
                c.execute('''UPDATE transactions SET payer_id=?, involved_ids=? WHERE id=?''',
                          (payer_id, json.dumps(involved), tid))
        # Remove participant from participants table
        c.execute('DELETE FROM participants WHERE id=? AND split_id=?', (pid, split_id))
        conn.commit()

def get_participants(split_id: int) -> List[Tuple[int, str]]:
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT id, name FROM participants WHERE split_id=? ORDER BY name', (split_id,))
        return c.fetchall()

# --- Split/Hangout Functions ---
def create_split(name: str, description: str, date: str, created_at: str) -> int:
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('INSERT INTO splits (name, description, date, created_at) VALUES (?, ?, ?, ?)', (name, description, date, created_at))
        conn.commit()
        return c.lastrowid

def get_splits() -> List[Tuple]:
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT id, name, description, date, created_at FROM splits ORDER BY date DESC')
        return c.fetchall()

def get_split(split_id: int) -> Tuple:
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT id, name, description, created_at FROM splits WHERE id=?', (split_id,))
        return c.fetchone()

def add_transaction(split_id: int, description: str, amount: float, payer_id: int, involved_ids: List[int], timestamp: str, settled_ids: List[int] = None):
    if settled_ids is None:
        settled_ids = []
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('''INSERT INTO transactions (split_id, description, amount, payer_id, involved_ids, settled_ids, timestamp)
                     VALUES (?, ?, ?, ?, ?, ?, ?)''',
                  (split_id, description, amount, payer_id, json.dumps(involved_ids), json.dumps(settled_ids), timestamp))
        conn.commit()

def update_transaction(tid: int, split_id: int, description: str, amount: float, payer_id: int, involved_ids: List[int], timestamp: str, settled_ids: List[int] = None):
    if settled_ids is None:
        settled_ids = []
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('''UPDATE transactions SET split_id=?, description=?, amount=?, payer_id=?, involved_ids=?, settled_ids=?, timestamp=? WHERE id=?''',
                  (split_id, description, amount, payer_id, json.dumps(involved_ids), json.dumps(settled_ids), timestamp, tid))
        conn.commit()

def delete_transaction(tid: int):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('DELETE FROM transactions WHERE id=?', (tid,))
        conn.commit()

def get_transactions(split_id: int = None) -> List[Tuple]:
    with get_connection() as conn:
        c = conn.cursor()
        if split_id is not None:
            c.execute('SELECT id, split_id, description, amount, payer_id, involved_ids, settled_ids, timestamp FROM transactions WHERE split_id=? ORDER BY timestamp DESC', (split_id,))
        else:
            c.execute('SELECT id, split_id, description, amount, payer_id, involved_ids, settled_ids, timestamp FROM transactions ORDER BY timestamp DESC')
        return c.fetchall()
