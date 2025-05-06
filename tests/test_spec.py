import os
import sys
import tempfile
import unittest
from typing import List, Literal, Optional, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from spargear import SUPPRESS, ArgumentSpec, BaseArguments, FileProtocol, TypedFileType


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


# raise Exception(SimpleArguments.__arguments__)


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


if __name__ == "__main__":
    unittest.main()
