# ⚙️ spargear

![PyPI](https://img.shields.io/pypi/v/spargear?label=pypi%20package)
![PyPI - Downloads](https://img.shields.io/pypi/dm/spargear)

A powerful yet simple Python library for declarative command-line argument parsing, built on top of `argparse`. spargear enables elegant, type-safe definitions of CLI arguments and subcommands with minimal boilerplate.

## Why spargear?

- ✅ **Declarative**: Define your CLI arguments neatly using Python data classes.
- 🚀 **Typed and Safe**: Leveraging Python typing and dataclasses to ensure type safety and developer productivity.
- 🔧 **Flexible**: Supports complex argument parsing scenarios, including subcommands and nested configurations.
- 📦 **Minimal Dependencies**: Pure Python, built directly upon the reliable `argparse` module.
- 🎯 **Modern API**: Beautiful `@subcommand` or `@subcommandclass` decorator for intuitive subcommand definition.

## Installation

Install with pip:

```bash
pip install spargear
```

## Quick Start

Define your arguments:

```python
from typing import Annotated, Optional

from spargear import BaseArguments


class MyArgs(BaseArguments):
    input_file: Annotated[Optional[str], "-i", "--input"] = None
    """Input file path"""
    verbose: Annotated[bool, "-v", "--verbose"] = False
    """Enable verbose output"""


# Parse the command-line arguments
args = MyArgs()

# Access the parsed arguments
input_file: Optional[str] = args.input_file
# input_file: str | None = args.input_file.value
verbose: bool = args.verbose  # store_true `-v` or `--verbose` to True
print(f"Input file: {input_file}")
print(f"Verbose mode: {verbose}")
```

Run your CLI:

```bash
python app.py --input example.txt --verbose
```

## Subcommands with @subcommand or @subcommandclass decorator

The easiest and most intuitive way to define subcommands is using the `@subcommand` or `@subcommandclass` decorator:

```python
from spargear import BaseArguments, subcommandclass


class GitCLI(BaseArguments):
    """A Git-like CLI tool."""

    @subcommandclass(help="Initialize a new repository")
    class Init(BaseArguments):
        """Initialize a new Git repository."""

        NAME: str

    @subcommandclass(help="Record changes to the repository")
    class Commit(BaseArguments):
        """Record changes."""

        message: str
        amend: bool = False


# Parse and use
args = GitCLI()

# Access the active subcommand
args.inspect(GitCLI.Init, lambda init_args: print(f"Initializing project: {init_args.NAME}"))
args.inspect(
    GitCLI.Commit,
    lambda commit_args: print(f"Committing: {commit_args.message} (amend: {commit_args.amend}"),
)
```

Run your CLI:

```bash
python app.py init my_project
python app.py commit -m "Initial commit" --amend
```

### @subcommand Features

The `@subcommand` decorator automatically:
- Extracts the subcommand name from the method name (or use `name=` parameter to override)
- Uses the method's docstring as help text and description
- Treats the method as a factory that returns the argument class
- No need for `@staticmethod` - the decorator handles it automatically!

```python
class MyApp(BaseArguments):
    @subcommand()  # Name will be "serve", help from docstring
    def serve():
        """Start the development server.
        
        Launches a local development server on the specified port
        with hot reload capabilities.
        """
        return ServeArguments
    
    @subcommand(name="db-migrate", help="Run database migrations")
    def database_migrate():  # Custom name overrides method name
        return MigrateArguments
```

## Advanced Usage

### Manual SubcommandSpec (Alternative approach)

For more control or complex scenarios, you can still use `SubcommandSpec` directly:

```python
from spargear import BaseArguments, SubcommandSpec, ArgumentSpec


class InitArgs(BaseArguments):
    name: ArgumentSpec[str] = ArgumentSpec(["name"], help="Project name")


class CommitArgs(BaseArguments):
    message: ArgumentSpec[str] = ArgumentSpec(["-m"], required=True, help="Commit message")


class GitCLI(BaseArguments):
    init = SubcommandSpec("init", InitArgs, help="Initialize a new repository")
    commit = SubcommandSpec("commit", CommitArgs, help="Commit changes")
```

**Note**: The `@subcommand` decorator is the recommended approach for most use cases as it provides a cleaner, more maintainable syntax.

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

### @subcommand Decorator

```python
@subcommand(name=None, help="", description=None, argument_class=None)
def method_name():
    return ArgumentClass
```

Parameters:
- `name` (optional): Override the subcommand name (defaults to method name)
- `help` (optional): Brief help text (defaults to first line of docstring)
- `description` (optional): Detailed description (defaults to rest of docstring)
- `argument_class` (optional): Directly specify the argument class instead of using the factory

### BaseArguments Methods

#### Serialization
- `to_dict() -> Dict[str, Any]` - Convert to dictionary
- `to_json() -> str` - Serialize to JSON
- `to_pickle() -> bytes` - Serialize to pickle format
- `to_dataclass()` - Convert to dataclass instance

#### Deserialization
- `from_dict(data, args=None)` - Create from dictionary
- `from_json(json_data, args=None)` - Create from JSON string/file
- `from_pickle(file_path, args=None)` - Create from pickle file

#### Configuration Management
- `save_config(file_path, format="json")` - Save configuration
- `load_config(file_path, format=None, args=None)` - Load configuration
- `update_from_dict(data)` - Update current instance

#### Subcommand Access
- `last_subcommand` - Get the active subcommand instance (if any)

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
