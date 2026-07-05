import os
import json
import time
import hashlib
import functools
import logging

from datetime import datetime, timedelta
from pathlib import Path


STATE_FILE = Path(".guard_state.json")
LOCK_FILE = Path(".guard_lock")
logger = logging.getLogger(__name__)


class FileLock(object):

    def __init__(self, lock_file):
        self.lock_file = Path(lock_file)

    def __enter__(self):
        self.lock_file.parent.mkdir(parents=True, exist_ok=True)
        while True:
            try:
                # atomic create
                self.fd = os.open(self.lock_file, os.O_CREAT | os.O_EXCL | os.O_RDWR)
                return self
            except FileExistsError:
                time.sleep(0.05)

    def __exit__(self, exc_type, exc, tb):
        os.close(self.fd)
        if self.lock_file.exists():
            os.unlink(self.lock_file)


def _resolve_paths(state_path):
    if state_path is None:
        state_file = STATE_FILE
        lock_file = LOCK_FILE
    else:
        state_file = Path(state_path)
        lock_file = state_file.with_suffix(f"{state_file.suffix}.lock")

    return state_file, lock_file


def _load_state(state_file):
    if state_file.exists():
        with open(state_file, "r") as f:
            return json.load(f)
    return {}


def _save_state(
        state,
        state_file
):
    state_file.parent.mkdir(parents=True, exist_ok=True)
    tmp = state_file.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, state_file)  # atomic write


def _hash_call(
        fn,
        args,
        kwargs
):
    raw = json.dumps(
        [fn.__module__, fn.__name__, args, kwargs],
        sort_keys=True,
        default=str
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def _next_window(
        now,
        schedule,
        ttl_seconds
):
    if ttl_seconds:
        return now + timedelta(seconds=ttl_seconds)

    if schedule == "hourly":
        return now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

    if schedule == "daily":
        return now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)

    if schedule == "weekly":
        start_of_week = now - timedelta(days=now.weekday())
        return start_of_week.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=7)

    raise ValueError("Invalid schedule")


def guard(
    schedule="daily",
    ttl_seconds=None,
    state_path=None
):
    """
        schedule: 'hourly', 'daily', 'weekly'
            OR
        ttl_seconds: int
    """

    def decorator(fn):

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            now = datetime.utcnow()
            key = _hash_call(fn, args, kwargs)
            state_file, lock_file = _resolve_paths(state_path)

            with FileLock(lock_file):
                state = _load_state(state_file)
                entry = state.get(key)

                if entry:
                    expires_at = datetime.fromisoformat(entry["expires_at"])

                    if now < expires_at:
                        logger.info(f"[SKIP] {fn.__name__} (cached)")
                        return entry.get("result")

                # run function
                logger.debug(f"[RUN] {fn.__name__}")
                result = fn(*args, **kwargs)

                expires_at = _next_window(now, schedule, ttl_seconds)

                state[key] = {
                    "expires_at": expires_at.isoformat(),
                    "result": result,
                }

                _save_state(state, state_file)

                return result

        return wrapper

    return decorator
