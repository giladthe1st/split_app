from dataclasses import dataclass
from typing import List

@dataclass
class Participant:
    id: int
    name: str

@dataclass
class Transaction:
    id: int
    description: str
    amount: float
    payer_id: int
    involved_ids: List[int]
    timestamp: str
