from datetime import timedelta

PRIORITY_SLA_HOURS = {
    "HIGH": 4,
    "MEDIUM": 24,
    "LOW": 72,
}

def get_sla_hours(priority: str, fallback: int = 24) -> int:
    return int(PRIORITY_SLA_HOURS.get(priority, fallback))

def calc_due_at(now, sla_hours: int):
    return now + timedelta(hours=int(sla_hours))
