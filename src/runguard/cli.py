import argparse
import json

from runguard.guard import invalidate_cache


def _build_parser():
    parser = argparse.ArgumentParser(prog="runguard")
    subparsers = parser.add_subparsers(dest="command", required=True)

    invalidate_parser = subparsers.add_parser("invalidate", help="Invalidate cached entries")
    invalidate_parser.add_argument("--state-path", help="Path to the state file")
    invalidate_parser.add_argument("--module", help="Module that defines the function")
    invalidate_parser.add_argument("--function", help="Function name to invalidate")
    invalidate_parser.add_argument("--args", default="[]", help="JSON list of positional args")
    invalidate_parser.add_argument("--kwargs", default="{}", help="JSON object of keyword args")

    return parser


class _HashTarget:
    def __init__(self, module_name, function_name):
        self.__module__ = module_name
        self.__name__ = function_name


def main(argv=None):
    parser = _build_parser()
    parsed = parser.parse_args(argv)

    if parsed.command == "invalidate":
        has_module = bool(parsed.module)
        has_function = bool(parsed.function)
        if has_module != has_function:
            parser.error("--module and --function must be provided together")

        if has_module:
            fn = _HashTarget(parsed.module, parsed.function)
            args = json.loads(parsed.args)
            kwargs = json.loads(parsed.kwargs)

            if not isinstance(args, list):
                parser.error("--args must decode to a JSON list")
            if not isinstance(kwargs, dict):
                parser.error("--kwargs must decode to a JSON object")

            removed = invalidate_cache(
                fn=fn,
                args=tuple(args),
                kwargs=kwargs,
                state_path=parsed.state_path,
            )
        else:
            removed = invalidate_cache(state_path=parsed.state_path)

        print(f"Removed {removed} cache entr{'y' if removed == 1 else 'ies'}")
        return 0

    parser.error("Unknown command")
