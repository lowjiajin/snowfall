from datetime import datetime


def get_current_timestamp_ms() -> int:
    return int(datetime.utcnow().timestamp() * 1000)
