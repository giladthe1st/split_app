from dataclasses import dataclass
from typing import List

@dataclass
class Participant:
    id: int
    name: str

@dataclass
class Transaction:
    id: int
    split_id: int
    description: str
    amount: float
    payer_id: int
    involved_ids: List[int]
    settled_ids: List[int]
    timestamp: str

@dataclass
class Split:
    id: int
    name: str
    description: str
    date: str
    created_at: str
