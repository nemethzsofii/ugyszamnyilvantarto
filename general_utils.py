
from datetime import datetime

def parse_time(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%H:%M").time()
    except ValueError:
        return datetime.strptime(value, "%H:%M:%S").time()
