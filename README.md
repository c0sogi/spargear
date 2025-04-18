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

## Compatibility

- Python 3.8+

## License

MIT
