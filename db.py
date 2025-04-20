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
        # New table for settled transfers
        c.execute('''CREATE TABLE IF NOT EXISTS settled_transfers (
            from_id INTEGER NOT NULL,
            to_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            settled INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (from_id, to_id, amount)
        )''')
        conn.commit()

# --- Settled Transfers Helpers ---
def is_transfer_settled(from_id: int, to_id: int, amount: float) -> bool:
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('''SELECT settled FROM settled_transfers WHERE from_id=? AND to_id=? AND amount=?''', (from_id, to_id, amount))
        row = c.fetchone()
        return bool(row and row[0])

def set_transfer_settled(from_id: int, to_id: int, amount: float, settled: bool):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO settled_transfers (from_id, to_id, amount, settled) VALUES (?, ?, ?, ?)''',
                  (from_id, to_id, amount, int(settled)))
        conn.commit()

def get_all_settled_transfers() -> list:
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT from_id, to_id, amount, settled FROM settled_transfers WHERE settled=1')
        return c.fetchall()


def add_participant(name: str):
    with get_connection() as conn:
        c = conn.cursor()
        c.execute('INSERT INTO participants (name) VALUES (?)', (name,))
        conn.commit()

def remove_participant(pid: int):
    with get_connection() as conn:
        c = conn.cursor()
        # Get all transactions
        c.execute('SELECT id, payer_id, involved_ids, description, amount, timestamp FROM transactions')
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
        c.execute('DELETE FROM participants WHERE id=?', (pid,))
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
