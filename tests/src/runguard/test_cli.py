import json

from runguard import guard
from runguard.cli import main


def test_cli_invalidate_all_with_custom_state_path(tmp_path, capsys):
    state_path = tmp_path / "state.json"

    @guard(schedule="daily", state_path=state_path)
    def fn(x):
        return x

    fn(1)
    fn(2)

    exit_code = main(["invalidate", "--state-path", str(state_path)])
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "Removed 2 cache entries" in out


def test_cli_invalidate_specific_entry(tmp_path, capsys):
    state_path = tmp_path / "state.json"

    @guard(schedule="daily", state_path=state_path)
    def fn(x):
        return x

    fn(1)
    fn(2)

    exit_code = main(
        [
            "invalidate",
            "--state-path",
            str(state_path),
            "--module",
            fn.__module__,
            "--function",
            fn.__name__,
            "--args",
            json.dumps([1]),
            "--kwargs",
            json.dumps({}),
        ]
    )
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "Removed 1 cache entry" in out
