import sys


def log(msg: str, phase: str = "") -> None:
    prefix = f"[{phase}] " if phase else ""
    print(f"{prefix}{msg}", flush=True)


def banner(msg: str) -> None:
    sep = "═" * 55
    print(f"\n{sep}\n  {msg}\n{sep}", flush=True)


def warn(msg: str) -> None:
    print(f"[WARN] {msg}", file=sys.stderr, flush=True)
