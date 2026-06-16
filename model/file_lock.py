"""Small cross-process file lock helper for local data writes."""

from __future__ import annotations

from contextlib import contextmanager
import os
import threading
from typing import Iterator

try:
    import fcntl
except ImportError:  # pragma: no cover - POSIX path is used in deployment.
    fcntl = None


_LOCKS_GUARD = threading.Lock()
_THREAD_LOCKS: dict[str, threading.Lock] = {}


def _thread_lock_for(path: str) -> threading.Lock:
    key = os.path.abspath(path)
    with _LOCKS_GUARD:
        lock = _THREAD_LOCKS.get(key)
        if lock is None:
            lock = threading.Lock()
            _THREAD_LOCKS[key] = lock
        return lock


@contextmanager
def exclusive_file_lock(target_path: str) -> Iterator[None]:
    """Serialize writes to a data file across Streamlit sessions/processes."""
    lock_path = f"{target_path}.lock"
    lock_dir = os.path.dirname(os.path.abspath(lock_path))
    if lock_dir:
        os.makedirs(lock_dir, exist_ok=True)

    thread_lock = _thread_lock_for(lock_path)
    with thread_lock:
        with open(lock_path, "a", encoding="utf-8") as lock_file:
            if fcntl is not None:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                if fcntl is not None:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
