"""Shared deterministic serialization and task-specific correctness predicates."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import math
from pathlib import Path
import signal

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pack(value):
    if isinstance(value, tuple):
        return {"__tuple__": [pack(item) for item in value]}
    if isinstance(value, list):
        return [pack(item) for item in value]
    if isinstance(value, dict):
        return {"__dict__": [[pack(key), pack(item)] for key, item in value.items()]}
    if value is None or isinstance(value, (str, int, float, bool)):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("Non-finite reference result")
        return value
    raise TypeError(f"Unsupported reference result: {type(value).__name__}")


def unpack(value):
    if isinstance(value, list):
        return [unpack(item) for item in value]
    if isinstance(value, dict):
        if "__tuple__" in value:
            return tuple(unpack(item) for item in value["__tuple__"])
        if "__dict__" in value:
            return {unpack(key): unpack(item) for key, item in value["__dict__"]}
        raise ValueError("Invalid encoded reference value")
    return value


def exact_digest(value):
    encoded = json.dumps(pack(value), ensure_ascii=False, sort_keys=True,
                         allow_nan=False, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def expected_fields(value):
    """Keep very large exact outputs as hashes; retain full floating-point oracles."""
    packed = pack(value)
    encoded = json.dumps(packed, ensure_ascii=False, sort_keys=True,
                         allow_nan=False, separators=(",", ":")).encode()
    def has_float(item):
        if isinstance(item, float):
            return True
        if isinstance(item, (tuple, list)):
            return any(has_float(x) for x in item)
        if isinstance(item, dict):
            return any(has_float(x) for pair in item.items() for x in pair)
        return False
    if len(encoded) > 4096 and not has_float(value):
        return {"expected_digest": hashlib.sha256(encoded).hexdigest(),
                "expected_preview": repr(value)[:500]}
    return {"expected": packed}


def equivalent(actual, expected, atol=0):
    """Python equality, with explicit float tolerance and preserved container types."""
    if isinstance(expected, float):
        return isinstance(actual, (int, float)) and math.isfinite(actual) and math.isclose(
            actual, expected, rel_tol=1e-7, abs_tol=atol or 1e-6)
    if isinstance(expected, (tuple, list)):
        return type(actual) is type(expected) and len(actual) == len(expected) and all(
            equivalent(left, right, atol) for left, right in zip(actual, expected))
    if isinstance(expected, dict):
        return isinstance(actual, dict) and actual.keys() == expected.keys() and all(
            equivalent(actual[key], value, atol) for key, value in expected.items())
    return actual == expected


def accepts(task_id, args, actual, expected, atol):
    if task_id == "he_032":
        # Any real root is valid; comparison with one reference root is unfair.
        if not isinstance(actual, (int, float)) or not math.isfinite(actual):
            return False
        residual = sum(coefficient * actual ** i for i, coefficient in enumerate(args[0]))
        return math.isfinite(residual) and abs(residual) <= atol
    if task_id == "he_020":
        # Ties between different closest pairs are not resolved by the specification.
        if not isinstance(actual, tuple) or len(actual) != 2 or actual[0] > actual[1]:
            return False
        remaining = list(args[0])
        for value in actual:
            if value not in remaining:
                return False
            remaining.remove(value)
        numbers = sorted(args[0])
        closest = min(right - left for left, right in zip(numbers, numbers[1:]))
        return math.isclose(actual[1] - actual[0], closest, rel_tol=1e-7, abs_tol=1e-6)
    return equivalent(actual, expected, atol)


class CaseTimeout(TimeoutError):
    pass


@contextmanager
def deadline(seconds):
    def expired(signum, frame):
        raise CaseTimeout(f"Case exceeded {seconds:g} seconds")
    previous = signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)
