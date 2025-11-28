# app/core/ids.py
import random


def make_short_id(n: int = 6) -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # без 0/O/1/I
    return "".join(random.choice(alphabet) for _ in range(n))
