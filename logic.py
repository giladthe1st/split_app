import json
from collections import defaultdict
from typing import List, Dict, Tuple

def calculate_balances(participants: List[Tuple[int, str]], transactions: List[Tuple]) -> Dict[int, float]:
    # Returns {participant_id: net_balance}
    balances = defaultdict(float)
    for tid, desc, amount, payer_id, involved_ids_json, timestamp in transactions:
        involved_ids = json.loads(involved_ids_json)
        split = amount / len(involved_ids)
        for pid in involved_ids:
            balances[pid] -= split
        balances[payer_id] += amount
    return balances

def min_transfers(balances: Dict[int, float]) -> List[Tuple[int, int, float]]:
    # Returns list of (from_id, to_id, amount) to settle debts
    creditors = [(pid, bal) for pid, bal in balances.items() if bal > 0.01]
    debtors = [(pid, -bal) for pid, bal in balances.items() if bal < -0.01]
    creditors.sort(key=lambda x: -x[1])
    debtors.sort(key=lambda x: -x[1])
    transfers = []
    i = j = 0
    while i < len(debtors) and j < len(creditors):
        d_id, d_amt = debtors[i]
        c_id, c_amt = creditors[j]
        amt = min(d_amt, c_amt)
        transfers.append((d_id, c_id, round(amt, 2)))
        debtors[i] = (d_id, d_amt - amt)
        creditors[j] = (c_id, c_amt - amt)
        if debtors[i][1] < 0.01:
            i += 1
        if creditors[j][1] < 0.01:
            j += 1
    return transfers
