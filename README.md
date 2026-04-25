# runguard

**Make Python functions safe to run more than once.**

`runguard` ensures a function only executes once within a given time window
(e.g. once per day, per hour, or per input) — even across multiple processes.

---

## Why?

In real systems, the same function can get called multiple times:

* retries
* cron jobs
* API triggers
* AI-generated scripts
* accidental double execution

This can lead to:

* duplicate DB writes
* repeated API calls
* inconsistent state

`runguard` prevents that with a simple decorator.

---

## Install

```bash
pip install runguard  # (or drop the file into your project)
```

---

## Quick Example

```python
from runguard import guard

@guard(schedule="daily")
def generate_report(user_id):
    print("Running expensive job...")
    return {"user": user_id}

generate_report(1)
generate_report(1)  # skipped
generate_report(2)  # runs (different input)
```

---

## Features

* Runs once per time window (daily, hourly, weekly, or custom TTL)
* Parameter-aware (per input)
* Cross-process safe (file locking, works on Windows & Unix)
* Returns cached result
* Zero infrastructure required

---

## Schedules

### Daily / Hourly / Weekly

```python
@guard(schedule="daily")
@guard(schedule="hourly")
@guard(schedule="weekly")
```

---

### Custom TTL

```python
@guard(ttl_seconds=600)  # once every 10 minutes
```

---

## Intended Usage

* scripts that may be triggered multiple times
* cron jobs / schedulers
* API endpoints with side effects
* anything that “should not run twice”

---

## Future Improvements

* SQLite / Redis backend
* async support
* manual invalidation
* "run but don’t cache result" mode

---

## Notes

`runguard` is not a framework.

It’s a small, reliable utility to make unsafe execution safe by default.
