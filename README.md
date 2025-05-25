# ⚙️ spargear

![PyPI](https://img.shields.io/pypi/v/spargear?label=pypi%20package)
![PyPI - Downloads](https://img.shields.io/pypi/dm/spargear)

A powerful yet simple Python library for declarative command-line argument parsing, built on top of `argparse`. spargear enables elegant, type-safe definitions of CLI arguments and subcommands with minimal boilerplate.

## Why spargear?

- ✅ **Declarative**: Define your CLI arguments neatly using Python data classes.
- 🚀 **Typed and Safe**: Leveraging Python typing and dataclasses to ensure type safety and developer productivity.
- 🔧 **Flexible**: Supports complex argument parsing scenarios, including subcommands and nested configurations.
- 📦 **Minimal Dependencies**: Pure Python, built directly upon the reliable `argparse` module.

## Installation

Install with pip:

```bash
pip install spargear
```

## Quick Start

Define your arguments:

```python
from spargear import ArgumentSpec, BaseArguments


class MyArgs(BaseArguments):
    input_file: ArgumentSpec[str] = ArgumentSpec(["-i", "--input"], required=True, help="Input file path")
    verbose: ArgumentSpec[bool] = ArgumentSpec(["-v", "--verbose"], action="store_true", help="Enable verbose output")

# Parse the command-line arguments
args = MyArgs()

# Access the parsed arguments
input_file: str = args.input_file.unwrap()  # If none, it raises an error
# input_file: str | None = args.input_file.value
verbose: bool = args.verbose.unwrap()  # If none, it raises an error
# verbose: str | bool = args.verbose.value
print(f"Input file: {input_file}")
print(f"Verbose mode: {verbose}")
```

Run your CLI:

```bash
python app.py --input example.txt --verbose
```

## Features

- Automatic inference of argument types
- Nested subcommands with clear definitions
- Typed file handlers via custom protocols
- Suppress arguments seamlessly
- **Default factories** for dynamic value generation (UUIDs, timestamps, etc.)
- **Dataclass conversion** for easy integration with other libraries
- **JSON/Pickle serialization** for configuration management
- **Configuration file support** with command-line override capabilities

## Advanced Usage

Subcommands:

```python
from typing import Optional
from spargear import BaseArguments, SubcommandSpec, ArgumentSpec


class InitArgs(BaseArguments):
    name: ArgumentSpec[str] = ArgumentSpec(["name"], help="Project name")


class CommitArgs(BaseArguments):
    message: ArgumentSpec[str] = ArgumentSpec(["-m"], required=True, help="Commit message")


class GitCLI(BaseArguments):
    init = SubcommandSpec("init", InitArgs, help="Initialize a new repository")
    commit = SubcommandSpec("commit", CommitArgs, help="Commit changes")


# Parse the command line arguments
args = GitCLI()

# Print the parsed arguments
name: Optional[str] = args.init.argument_class.name.value
message: Optional[str] = args.commit.argument_class.message.value
print(f"Name: {name}")
print(f"Message: {message}")

```

Run your CLI:

```bash
python app.py init my_project
python app.py commit -m "Initial commit"
```

### Default Factories

Generate dynamic values at parse time:

```python
import uuid
from datetime import datetime
from spargear import BaseArguments, ArgumentSpec


class AppConfig(BaseArguments):
    # Method 1: Direct callable assignment (auto-detected)
    session_id: str = lambda: str(uuid.uuid4())
    
    # Method 2: Explicit ArgumentSpec with default_factory
    log_file: ArgumentSpec[str] = ArgumentSpec(
        ["--log-file"],
        default_factory=lambda: f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        help="Log file path"
    )
    
    name: str = "myapp"  # Regular default value


config = AppConfig()
print(f"Session ID: {config.session_id}")  # Unique UUID each time
print(f"Log file: {config.log_file.unwrap()}")  # Timestamp-based filename
```

### Configuration Management

Save and load configurations:

```python
from spargear import BaseArguments
from typing import List


class ServerConfig(BaseArguments):
    host: str = "localhost"
    port: int = 8080
    debug: bool = False
    allowed_hosts: List[str] = ["127.0.0.1", "localhost"]


# Create and configure
config = ServerConfig(["--port", "3000", "--debug"])

# Convert to dataclass
config_dc = config.to_dataclass()
print(f"Dataclass: {config_dc}")

# Save to JSON
config.save_config("server.json")

# Load from JSON with command-line overrides
loaded_config = ServerConfig.load_config("server.json", args=["--port", "9000"])
print(f"Port: {loaded_config.port}")  # 9000 (overridden)
print(f"Debug: {loaded_config.debug}")  # True (from file)

# Update from dictionary
config.update_from_dict({"host": "0.0.0.0", "port": 5000})
```

## API Reference

### BaseArguments Methods

#### Serialization
- `to_dict() -> Dict[str, Any]` - Convert to dictionary
- `to_json(file_path=None, **kwargs) -> str` - Serialize to JSON
- `to_pickle(file_path)` - Serialize to pickle file
- `to_dataclass(class_name=None)` - Convert to dataclass instance

#### Deserialization
- `from_dict(data, args=None)` - Create from dictionary
- `from_json(json_data, args=None)` - Create from JSON string/file
- `from_pickle(file_path, args=None)` - Create from pickle file

#### Configuration Management
- `save_config(file_path, format="json")` - Save configuration
- `load_config(file_path, format=None, args=None)` - Load configuration
- `update_from_dict(data)` - Update current instance

### ArgumentSpec Features

#### Default Factories
```python
ArgumentSpec(
    name_or_flags=["--arg"],
    default_factory=lambda: generate_value(),  # Called at parse time
    help="Description"
)
```

## Compatibility

- Python 3.8+

## License

MIT
