#!/usr/bin/env python3
"""Simple test for default factory functionality."""

import unittest
import uuid
from typing import Union, Callable
from spargear import BaseArguments


class SimpleArgs(BaseArguments):
    """Simple test arguments."""

    session_id: Union[str, Callable[[], str]] = lambda: str(uuid.uuid4())
    """Unique session ID"""


class TestSimpleCallable(unittest.TestCase):
    def test_simple_callable(self) -> None:
        print("Creating first instance...")
        args1 = SimpleArgs([])
        print(f"args1 session_id: {args1.get('session_id')}")

        print("Creating second instance...")
        args2 = SimpleArgs([])
        print(f"args2 session_id: {args2.get('session_id')}")

        print(
            f"Are they different? {args1.get('session_id') != args2.get('session_id')}"
        )


if __name__ == "__main__":
    unittest.main()
