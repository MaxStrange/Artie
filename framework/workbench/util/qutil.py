"""
Queue utilities.
"""
import queue
from typing import Any

def get(q: queue.Queue, blocking=True, timeout_s=None) -> Any|None:
    """
    Queue.get(), but instead of raising an exception,
    it returns None in the case of failing to fetch an item.
    """
    try:
        return q.get(blocking, timeout=timeout_s)
    except queue.Empty:
        return None

def get_nowait(q: queue.Queue) -> Any|None:
    """
    Queue.get_nowait(), but instead of raising an exception,
    it returns None in the case of failing to fetch an item.
    """
    try:
        return q.get_nowait()
    except queue.Empty:
        return None
