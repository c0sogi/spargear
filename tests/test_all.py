import os
import sys
import tempfile
import unittest
from typing import List, Literal, Optional, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from spargear import (
    SUPPRESS,
    ArgumentSpec,
    BaseArguments,
    FileProtocol,
    SubcommandSpec,
    TypedFileType,
)


class SimpleArguments(BaseArguments):
    """Example argument parser demonstrating various features."""

    my_str_arg: ArgumentSpec[str] = ArgumentSpec(
        ["-s", "--string-arg"], default="Hello", help="A string argument.", metavar="TEXT"
    )
    my_int_arg: ArgumentSpec[int] = ArgumentSpec(["-i", "--integer-arg"], help="A required integer argument.")
    verbose: ArgumentSpec[bool] = ArgumentSpec(
        ["-v", "--verbose"], action="store_true", help="Increase output verbosity."
    )
    my_list_arg: ArgumentSpec[List[str]] = ArgumentSpec(
        ["--list-values"], nargs=3, help="One or more values.", default=None
    )
    input_file: ArgumentSpec[FileProtocol] = ArgumentSpec(
        ["input_file"], type=TypedFileType("r", encoding="utf-8"), help="Input file", metavar="INPUT"
    )
    output_file: ArgumentSpec[Optional[FileProtocol]] = ArgumentSpec(
        ["output_file"], type=TypedFileType("w", encoding="utf-8"), nargs="?", default=None, help="Output file"
    )
    log_level: ArgumentSpec[Literal["DEBUG", "INFO", "WARNING", "ERROR"]] = ArgumentSpec(
        ["--log-level"], default="INFO", help="Set log level."
    )
    mode: ArgumentSpec[Literal["fast", "slow", "careful"]] = ArgumentSpec(
        ["--mode"], choices=["fast", "slow"], default="fast", help="Mode"
    )
    enabled_features: ArgumentSpec[List[Literal["CACHE", "LOGGING", "RETRY"]]] = ArgumentSpec(
        ["--features"], nargs="*", default=[], help="Enable features"
    )
    tuple_features: ArgumentSpec[Tuple[Literal["CACHE", "LOGGING", "RETRY"], Literal["CACHE", "LOGGING", "RETRY"]]] = (
        ArgumentSpec(["--tuple-features"], help="Tuple features")
    )
    optional_flag: ArgumentSpec[str] = ArgumentSpec(
        ["--opt-flag"], default=SUPPRESS, help="Optional flag suppressed if missing"
    )


class TestSimpleArguments(unittest.TestCase):
    def test_missing_required(self):
        parser = SimpleArguments.get_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args([])  # my_int_arg and input_file are required positional/required

    def test_basic_parsing_and_defaults(self):
        temp_in = tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".txt")
        temp_out = tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".txt")

        temp_in_path = temp_in.name
        temp_out_path = temp_out.name

        # 파일 닫기
        temp_in.close()
        temp_out.close()

        argv = [
            "-i",
            "42",
            "-s",
            "World",
            "--verbose",
            "--list-values",
            "a",
            "b",
            "c",
            temp_in_path,
            temp_out_path,
            "--log-level",
            "DEBUG",
            "--mode",
            "careful",
            "--features",
            "CACHE",
            "RETRY",
            "--tuple-features",
            "CACHE",
            "LOGGING",
        ]
        simple_args = SimpleArguments(argv)

        # 파일 객체가 열려 있다면 명시적으로 닫기
        input_file = simple_args.input_file.unwrap()
        output_file = simple_args.output_file.unwrap()
        input_file.close()
        os.remove(temp_in_path)  # 임시 파일 삭제
        if output_file is not None:
            output_file.close()
            os.remove(temp_out_path)

        self.assertEqual(simple_args.my_int_arg.unwrap(), 42)
        self.assertEqual(simple_args.my_str_arg.unwrap(), "World")
        self.assertTrue(simple_args.verbose.unwrap())

        self.assertListEqual(simple_args.my_list_arg.unwrap(), ["a", "b", "c"])
        self.assertIsNotNone(simple_args.input_file.unwrap())
        self.assertIsNotNone(simple_args.output_file.unwrap())
        self.assertEqual(simple_args.log_level.unwrap(), "DEBUG")
        self.assertEqual(simple_args.mode.unwrap(), "careful")
        self.assertListEqual(simple_args.enabled_features.unwrap(), ["CACHE", "RETRY"])
        self.assertTupleEqual(simple_args.tuple_features.unwrap(), ("CACHE", "LOGGING"))
        # optional_flag was SUPPRESS
        self.assertIsNone(simple_args.optional_flag.value)

    def test_literal_choices_enforced(self):
        parser = SimpleArguments.get_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["-i", "1", "in.txt", "--tuple-features", "BAD", "LOGGING"])


class GitCommitArguments(BaseArguments):
    """Git commit command arguments."""

    message: ArgumentSpec[str] = ArgumentSpec(["-m", "--message"], required=True, help="Commit message")
    amend: ArgumentSpec[bool] = ArgumentSpec(["--amend"], action="store_true", help="Amend previous commit")


class GitPushArguments(BaseArguments):
    """Git push command arguments."""

    remote: ArgumentSpec[str] = ArgumentSpec(["remote"], nargs="?", default="origin", help="Remote name")
    branch: ArgumentSpec[Optional[str]] = ArgumentSpec(["branch"], nargs="?", help="Branch name")
    force: ArgumentSpec[bool] = ArgumentSpec(["-f", "--force"], action="store_true", help="Force push")


class GitArguments(BaseArguments):
    """Git command line interface example."""

    verbose: ArgumentSpec[bool] = ArgumentSpec(["-v", "--verbose"], action="store_true", help="Increase verbosity")
    commit_cmd = SubcommandSpec(name="commit", help="Record changes", argument_class=GitCommitArguments)
    push_cmd = SubcommandSpec(name="push", help="Update remote", argument_class=GitPushArguments)


class TestGitArguments(unittest.TestCase):
    def test_commit_subcommand(self):
        # commit requires -m
        with self.assertRaises(SystemExit):
            GitArguments(["commit"])
        commit = GitArguments.load(["commit", "-m", "fix"])
        assert isinstance(commit, GitCommitArguments), "commit should be an instance of GitCommitArguments"
        self.assertEqual(commit.message.unwrap(), "fix")
        self.assertFalse(commit.amend.unwrap())

    def test_commit_with_amend(self):
        commit = GitArguments.load(["commit", "-m", "msg", "--amend"])
        assert isinstance(commit, GitCommitArguments), "commit should be an instance of GitCommitArguments"
        self.assertTrue(commit.amend.unwrap())

    def test_push_subcommand_defaults(self):
        push = GitArguments.load(["push"])
        assert isinstance(push, GitPushArguments), "push should be an instance of GitPushArguments"
        self.assertEqual(push.remote.unwrap(), "origin")
        self.assertIsNone(push.branch.value)
        self.assertFalse(push.force.unwrap())

    def test_push_with_overrides(self):
        push = GitArguments.load(["push", "upstream", "dev", "--force"])
        assert isinstance(push, GitPushArguments), "push should be an instance of GitPushArguments"
        self.assertEqual(push.remote.unwrap(), "upstream")
        self.assertEqual(push.branch.unwrap(), "dev")
        self.assertTrue(push.force.unwrap())


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


class BareTypeArguments(BaseArguments):
    """Example argument parser demonstrating bare type."""

    optional_int_with_default: Optional[int] = None
    optional_int_without_default: Optional[int]
    float_with_default: float = 0.0
    """float_with_default"""
    float_without_default: float
    float_with_str_default: float = "1.23"  # type: ignore[assignment]
    list_of_ints_without_default: List[int]
    """list_of_ints_without_default"""
    some_argument: ArgumentSpec[bool] = ArgumentSpec(["--some-argument"], action="store_true", help="some_argument")
    """This should be ignored"""


class TestBareType(unittest.TestCase):
    def test_bare_type_without_default(self):
        args = BareTypeArguments(["--float-without-default", "3.14", "--list-of-ints-without-default", "1", "2", "3"])
        self.assertEqual(args.optional_int_without_default, None)
        self.assertEqual(args.float_without_default, 3.14)
        self.assertEqual(args.list_of_ints_without_default, [1, 2, 3])

    def test_bare_type_with_default(self):
        args = BareTypeArguments(["--float-without-default", "3.14", "--list-of-ints-without-default", "1", "2", "3"])
        self.assertEqual(args.optional_int_with_default, None)
        self.assertEqual(args.float_with_default, 0.0)
        self.assertEqual(args.float_with_str_default, 1.23)

    def test_bare_type_docs(self):
        args = BareTypeArguments(["--float-without-default", "3.14", "--list-of-ints-without-default", "1", "2", "3"])
        self.assertEqual(args.__arguments__["float_with_default"][0].help, "float_with_default")
        self.assertEqual(args.__arguments__["list_of_ints_without_default"][0].help, "list_of_ints_without_default")
        self.assertEqual(args.__arguments__["some_argument"][0].help, "some_argument")


if __name__ == "__main__":
    unittest.main()
