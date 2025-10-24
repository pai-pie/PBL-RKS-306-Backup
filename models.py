from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class User:
    id: int
    username: str
    email: str
    password_hash: str
    role: str
    created_at: Optional[datetime] = None

@dataclass
class Event:
    id: int
    name: str
    event_date: datetime
    location: str
    status: str

@dataclass
class Ticket:
    id: int
    event_id: int
    type_name: str
    price: float
    quota: int
    sold: int

@dataclass
class Payment:
    id: int
    user_id: int
    event_id: int
    amount: float
    status: str
    va_number: str
    created_at: datetime

@dataclass
class Order:
    id: int
    user_id: int
    event_id: int
    total_amount: float
    payment_status: str
    ticket_details: str