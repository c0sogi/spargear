# ruff: noqa: F403
import subprocess
from os import environ

LOWEST_SUPPORT_PYTHON_VERSION = "3.8"
HIGHEST_SUPPORT_PYTHON_VERSION = "3.12"

if environ.get("SPARGEAR_TEST_SUBPROCESS") == "1":
    import sys
    import unittest

    from tests.test_spec import *
    from tests.test_specless import *
    from tests.test_subcommands import *

    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RESET = "\033[0m"
    print(f"{GREEN}[*] Running tests ... {YELLOW}{' '.join(sys.version.splitlines())}{RESET}")
    unittest.main()

else:

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

    def install_uv() -> None:
        try:
            subprocess.run(
                ["pip", "install", "uv"],
                check=True,
            )
        except subprocess.CalledProcessError as e:
            print(f"Failed to install uv: {e}")
            exit(1)

    if not is_uv_available():
        print("uv is not installed. Installing uv...")
        install_uv()

    for python_version in (LOWEST_SUPPORT_PYTHON_VERSION, HIGHEST_SUPPORT_PYTHON_VERSION):
        subprocess.run(
            ["uv", "run", "--python", python_version, __file__],
            check=True,
            env={**environ, "SPARGEAR_TEST_SUBPROCESS": "1"},
        )
