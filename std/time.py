"""Wolfera std time module (Python)."""

import time


def now():
    return time.time()


def time_exec(fn):
    start = now()
    result = fn()
    end = now()
    return [result, end - start]


def exports():
    return {
        "now": now,
        "time_exec": time_exec,
    }
