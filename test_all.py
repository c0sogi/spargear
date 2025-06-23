from os import environ
from pathlib import Path
from typing import List

GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"

TESTS_DIR = "tests"
LOWEST_SUPPORT_PYTHON_VERSION = "3.8"
HIGHEST_SUPPORT_PYTHON_VERSION = "3.12"

if version := environ.get("SPARGEAR_TEST_PYTHON_VERSION"):
    import sys

    VERSION = " ".join(sys.version.splitlines())
    assert version in VERSION, f"Python version {version} is not supported"

    # ruff: noqa: F403
    for test in (Path(__file__).parent / TESTS_DIR).glob("test_*.py"):
        from_str = f"from {TESTS_DIR}.{test.stem} import *"
        print(from_str)
        exec(from_str)

    print(f"{GREEN}[*] Running tests ... {YELLOW}{VERSION}{RESET}")
    import unittest

    unittest.main()

else:
    import subprocess

    def is_uv_available() -> bool:
        try:
            subprocess.run(
                ["uv", "--version"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            return True
        except subprocess.CalledProcessError:
            return False

    if not is_uv_available():

        def install_uv() -> None:
            subprocess.run(["pip", "install", "uv"], check=True)

        install_uv()

    def run(args: List[str], python_version: str):
        subprocess.run(
            args,
            check=True,
            env={
                **environ,
                "UV_PROJECT_ENVIRONMENT": f".venv{python_version}",  # e.g. ".venv3.8", ".venv3.12"
                "SPARGEAR_TEST_PYTHON_VERSION": python_version,
            },
        )

    for python_version in (LOWEST_SUPPORT_PYTHON_VERSION, HIGHEST_SUPPORT_PYTHON_VERSION):
        run(["uv", "run", "--python", python_version, __file__], python_version=python_version)

    print(f"{GREEN}[*] All tests passed{RESET}")
