#!/usr/bin/env python3
"""Test script to verify different instances get different default factory values."""

import datetime
import unittest
import uuid
from typing import Union, Callable
from spargear.base import BaseArguments, ArgumentSpec


class TestArguments(BaseArguments):
    """Test arguments with default factory support."""

    # Default factory using lambda
    session_id: Union[str, Callable[[], str]] = lambda: str(uuid.uuid4())
    """Unique session ID (generated at parse time)"""

    # Explicit ArgumentSpec with default_factory
    timestamp: ArgumentSpec[str] = ArgumentSpec(
        name_or_flags=["--timestamp"],
        default_factory=lambda: datetime.datetime.now().isoformat(),
        help="Current timestamp (auto-generated)",
    )


class TestDifferentInstances(unittest.TestCase):
    def test_different_instances(self) -> None:
        """Test that different instances get different default factory values."""
        print("Testing different instances...")

        # Create multiple instances
        args1 = TestArguments([])
        args2 = TestArguments([])
        args3 = TestArguments([])

        print(f"Instance 1 session_id: {args1.get('session_id')}")
        print(f"Instance 1 timestamp: {args1.get('timestamp')}")

        print(f"Instance 2 session_id: {args2.get('session_id')}")
        print(f"Instance 2 timestamp: {args2.get('timestamp')}")

        print(f"Instance 3 session_id: {args3.get('session_id')}")
        print(f"Instance 3 timestamp: {args3.get('timestamp')}")

        # Check if values are different
        session_ids = [
            args1.get("session_id"),
            args2.get("session_id"),
            args3.get("session_id"),
        ]
        timestamps = [
            args1.get("timestamp"),
            args2.get("timestamp"),
            args3.get("timestamp"),
        ]

        print(
            f"\nAll session IDs are unique: {len(set(session_ids)) == len(session_ids)}"
        )
        print(f"All timestamps are unique: {len(set(timestamps)) == len(timestamps)}")


if __name__ == "__main__":
    unittest.main()
