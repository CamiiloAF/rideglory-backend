from dataclasses import dataclass
from datetime import datetime


@dataclass
class DomainEvent:
    name: str
    occurred_at: datetime
