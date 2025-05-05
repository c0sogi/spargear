import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from spargear import ArgumentSpec, BaseArguments, SubcommandSpec


class BazArgs(BaseArguments):
    qux: ArgumentSpec[str] = ArgumentSpec(["--qux"], help="qux argument")


class BarArgs(BaseArguments):
    baz = SubcommandSpec("baz", help="do baz", argument_class=BazArgs)


class RootArgs(BaseArguments):
    foo: ArgumentSpec[str] = ArgumentSpec(["foo"], help="foo argument")
    bar = SubcommandSpec("bar", help="do bar", argument_class=BarArgs)


class TestNestedSubcommands(unittest.TestCase):
    def test_two_levels(self):
        baz = RootArgs.load(["FOO_VAL", "bar", "baz", "--qux", "QUX_VAL"])
        assert isinstance(baz, BazArgs), f"baz should be an instance of BarArgs: {type(baz)}"
        self.assertEqual(baz.qux.unwrap(), "QUX_VAL")

    def test_error_on_missing(self):
        with self.assertRaises(SystemExit):
            RootArgs.load([])  # missing foo positional
        with self.assertRaises(SystemExit):
            RootArgs.load(["FOO_VAL", "VAL", "bar"])  # missing baz sub-subcommand


if __name__ == "__main__":
    unittest.main()
