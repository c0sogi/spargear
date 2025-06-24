#!/usr/bin/env python3
"""Test script for default factory functionality in spargear."""

import datetime
import unittest
import uuid
from typing import Callable, List, Optional, Union

from spargear import ArgumentSpec, BaseArguments


class MyArguments(BaseArguments):
    """Test arguments with default factory support."""

    # Regular default value
    name: str = "default_name"
    """Name of the user"""

    # Default factory using lambda
    timestamp: Union[str, Callable[[], str]] = (
        lambda: datetime.datetime.now().isoformat()
    )
    """Current timestamp (generated at parse time)"""

    # Default factory using function
    session_id: Union[str, Callable[[], str]] = lambda: str(uuid.uuid4())
    """Unique session ID (generated at parse time)"""

    # Explicit ArgumentSpec with default_factory
    log_file: ArgumentSpec[str] = ArgumentSpec(
        name_or_flags=["--log-file"],
        default_factory=lambda: f"log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        help="Log file name (auto-generated with timestamp)",
    )

    # Optional argument with no default
    config_file: Optional[str] = None
    """Optional configuration file"""

    # List with default factory
    tags: Union[List[str], Callable[[], List[str]]] = lambda: ["default", "auto"]
    """List of tags"""


class TestDefaultFactory(unittest.TestCase):
    def test_default_factory(self) -> None:
        """Test the default factory functionality."""
        print("Testing default factory functionality...")

        # Test 1: No arguments provided - should use default factories
        print("\n=== Test 1: No arguments ===")
        args1 = MyArguments([])
        print(f"name: {args1.get('name')}")
        print(f"timestamp: {args1.get('timestamp')}")
        print(f"session_id: {args1.get('session_id')}")
        print(f"log_file: {args1.get('log_file')}")
        print(f"config_file: {args1.get('config_file')}")
        print(f"tags: {args1.get('tags')}")

        # Test 2: Some arguments provided
        print("\n=== Test 2: Some arguments provided ===")
        args2 = MyArguments(["--name", "custom_name", "--config-file", "config.yaml"])
        print(f"name: {args2.get('name')}")
        print(f"timestamp: {args2.get('timestamp')}")
        print(f"session_id: {args2.get('session_id')}")
        print(f"log_file: {args2.get('log_file')}")
        print(f"config_file: {args2.get('config_file')}")
        print(f"tags: {args2.get('tags')}")

        # Test 3: Verify that default factories generate different values
        print("\n=== Test 3: Different instances have different generated values ===")
        args3 = MyArguments([])
        args4 = MyArguments([])

        print(f"args3 session_id: {args3.get('session_id')}")
        print(f"args4 session_id: {args4.get('session_id')}")
        print(
            f"Session IDs are different: {args3.get('session_id') != args4.get('session_id')}"
        )


if __name__ == "__main__":
    unittest.main()
