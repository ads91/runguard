import time
import os
import json
import multiprocessing
from pathlib import Path

import pytest

from runguard import once

STATE_FILE = Path(".once_state.json")
LOCK_FILE = Path(".once_lock")


# ---------- Helpers ----------

def cleanup():
    if STATE_FILE.exists():
        STATE_FILE.unlink()
    if LOCK_FILE.exists():
        LOCK_FILE.unlink()


@pytest.fixture(autouse=True)
def run_around_tests():
    cleanup()
    yield
    cleanup()


# ---------- Basic behaviour ----------
def test_runs_once_per_day():
    calls = {"count": 0}

    @once(schedule="daily")
    def fn():
        calls["count"] += 1
        return 123

    assert fn() == 123
    assert fn() == 123
    assert calls["count"] == 1


# ---------- Per-input behaviour ----------
def test_runs_per_input():
    calls = {"count": 0}

    @once(schedule="daily")
    def fn(x):
        calls["count"] += 1
        return x

    fn(1)
    fn(1)
    fn(2)

    assert calls["count"] == 2


# ---------- TTL expiry ----------
def test_ttl_expiry():
    calls = {"count": 0}

    @once(ttl_seconds=1)
    def fn():
        calls["count"] += 1

    fn()
    fn()
    assert calls["count"] == 1

    time.sleep(1.2)

    fn()
    assert calls["count"] == 2


# ---------- Result caching ----------
def test_returns_cached_result():
    @once(schedule="daily")
    def fn():
        return {"value": 42}

    r1 = fn()
    r2 = fn()

    assert r1 == r2


# ---------- Cross-process safety ----------
def _worker(counter_file):
    from runguard import once

    @once(ttl_seconds=60)
    def fn():
        # increment shared counter file
        if not os.path.exists(counter_file):
            count = 0
        else:
            with open(counter_file, "r") as f:
                count = int(f.read())

        count += 1

        with open(counter_file, "w") as f:
            f.write(str(count))

    fn()


def test_cross_process_single_execution(tmp_path):
    counter_file = tmp_path / "count.txt"

    processes = []
    for _ in range(5):
        p = multiprocessing.Process(target=_worker, args=(str(counter_file),))
        p.start()
        processes.append(p)

    for p in processes:
        p.join()

    with open(counter_file, "r") as f:
        count = int(f.read())

    assert count == 1


# ---------- State file integrity ----------
def test_state_file_created():
    @once(schedule="daily")
    def fn():
        return 1

    fn()

    assert STATE_FILE.exists()

    with open(STATE_FILE) as f:
        data = json.load(f)

    assert len(data) == 1


# ---------- Handles exceptions (should not cache failure) ----------
def test_exception_does_not_cache():
    calls = {"count": 0}

    @once(schedule="daily")
    def fn():
        calls["count"] += 1
        raise ValueError("fail")

    with pytest.raises(ValueError):
        fn()

    # retry should run again
    with pytest.raises(ValueError):
        fn()

    assert calls["count"] == 2
