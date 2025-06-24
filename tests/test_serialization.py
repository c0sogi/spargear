#!/usr/bin/env python3
"""Test script for serialization and dataclass conversion features."""

import os
import tempfile
import unittest
import uuid
from typing import Dict, List, Optional

from spargear import ArgumentSpec, BaseArguments


class ConfigExample(BaseArguments):
    """Example configuration with various argument types."""

    # Basic arguments
    name: str = "default_app"
    """Application name"""

    port: int = 8080
    """Server port"""

    debug: bool = False
    """Enable debug mode"""

    # Optional arguments
    database_url: Optional[str] = None
    """Database connection URL"""

    # List arguments
    allowed_hosts: List[str] = ["localhost", "127.0.0.1"]
    """List of allowed hosts"""

    # ArgumentSpec with default factory
    session_id: ArgumentSpec[str] = ArgumentSpec(
        name_or_flags=["--session-id"],
        default_factory=lambda: str(uuid.uuid4()),
        help="Unique session identifier",
    )

    # ArgumentSpec with regular default
    log_level: ArgumentSpec[str] = ArgumentSpec(
        name_or_flags=["--log-level"],
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level",
    )


class TestSerialization(unittest.TestCase):
    def test_dataclass_conversion(self) -> None:
        """Test converting BaseArguments to dataclass."""
        print("=== Testing Dataclass Conversion ===")

        # Create instance with some arguments
        config = ConfigExample(["--name", "myapp", "--port", "9000", "--debug"])

        # Convert to dataclass
        config_dc = config.to_dataclass()
        print(f"Dataclass type: {type(config_dc)}")
        print(f"Dataclass name: {config_dc.name}")
        print(f"Dataclass port: {config_dc.port}")
        print(f"Dataclass debug: {config_dc.debug}")
        print(f"Dataclass session_id: {config_dc.session_id}")
        print()

    def test_dict_conversion(self) -> None:
        """Test converting BaseArguments to dictionary."""
        print("=== Testing Dictionary Conversion ===")

        config = ConfigExample(["--name", "testapp", "--log-level", "DEBUG"])
        config_dict = config.to_dict()

        print("Configuration as dictionary:")
        for key, value in config_dict.items():
            print(f"  {key}: {value}")
        print()

    def test_json_serialization(self) -> None:
        """Test JSON serialization and deserialization."""
        print("=== Testing JSON Serialization ===")

        # Create original config
        config1 = ConfigExample(["--name", "jsonapp", "--port", "3000"])

        # Serialize to JSON string
        json_str = config1.to_json()
        print("JSON representation:")
        print(json_str)
        print()

        # Save to file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config1.save_config(f.name, format="json")
            json_file = f.name

        try:
            # Load from file
            config2 = ConfigExample.load_config(json_file)
            print("Loaded from JSON file:")
            print(f"  name: {config2.name}")
            print(f"  port: {config2.port}")
            print(f"  session_id: {config2.session_id.unwrap()}")
            print()

            # Test from_json with string
            config3 = ConfigExample.from_json(json_str)
            print("Loaded from JSON string:")
            print(f"  name: {config3.name}")
            print(f"  debug: {config3.debug}")
            print()

        finally:
            os.unlink(json_file)

    def test_pickle_serialization(self) -> None:
        """Test pickle serialization and deserialization."""
        print("=== Testing Pickle Serialization ===")

        config1 = ConfigExample(["--name", "pickleapp", "--debug"])

        # Save to pickle file
        with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as f:
            config1.save_config(f.name, format="pickle")
            pickle_file = f.name

        try:
            # Load from pickle file
            config2 = ConfigExample.load_config(pickle_file)
            print("Loaded from pickle file:")
            print(f"  name: {config2.name}")
            print(f"  debug: {config2.debug}")
            print(f"  session_id: {config2.session_id.unwrap()}")
            print()

        finally:
            os.unlink(pickle_file)

    def test_update_functionality(self) -> None:
        """Test updating configuration from dictionary."""
        print("=== Testing Update Functionality ===")

        config = ConfigExample([])
        print("Original config:")
        print(f"  name: {config.name}")
        print(f"  port: {config.port}")

        # Update from dictionary
        updates: Dict[str, object] = {
            "name": "updated_app",
            "port": 5000,
            "debug": True,
        }
        config.update_from_dict(updates)

        print("After update:")
        print(f"  name: {config.name}")
        print(f"  port: {config.port}")
        print(f"  debug: {config.debug}")
        print()

    def test_command_line_override(self) -> None:
        """Test loading config with command line override."""
        print("=== Testing Command Line Override ===")

        # Create config data
        config_data: Dict[str, object] = {
            "name": "config_app",
            "port": 4000,
            "debug": False,
        }

        # Create instance with command line args that override config
        config = ConfigExample.from_dict(
            config_data, args=["--port", "6000", "--debug"]
        )

        print("Config with command line override:")
        print(f"  name: {config.name} (from config)")
        print(f"  port: {config.port} (overridden by command line)")
        print(f"  debug: {config.debug} (overridden by command line)")
        print()


if __name__ == "__main__":
    unittest.main()
