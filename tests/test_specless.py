import os
import sys
import unittest
from typing import List, Optional, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from spargear import ArgumentSpec, BaseArguments


class SpeclessBasicArguments(BaseArguments):
    """Example argument parser demonstrating specless type."""

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


class TestSpeclessBasic(unittest.TestCase):
    def test_specless_type_without_default(self):
        args = SpeclessBasicArguments([
            "--float-without-default",
            "3.14",
            "--list-of-ints-without-default",
            "1",
            "2",
            "3",
        ])
        self.assertEqual(args.optional_int_without_default, None)
        self.assertEqual(args.float_without_default, 3.14)
        self.assertEqual(args.list_of_ints_without_default, [1, 2, 3])

    def test_specless_type_with_default(self):
        args = SpeclessBasicArguments([
            "--float-without-default",
            "3.14",
            "--list-of-ints-without-default",
            "1",
            "2",
            "3",
        ])
        self.assertEqual(args.optional_int_with_default, None)
        self.assertEqual(args.float_with_default, 0.0)
        self.assertEqual(args.float_with_str_default, 1.23)

    def test_specless_type_docs(self):
        args = SpeclessBasicArguments([
            "--float-without-default",
            "3.14",
            "--list-of-ints-without-default",
            "1",
            "2",
            "3",
        ])
        self.assertEqual(args.__arguments__["float_with_default"][0].help, "float_with_default")
        self.assertEqual(args.__arguments__["list_of_ints_without_default"][0].help, "list_of_ints_without_default")
        self.assertEqual(args.__arguments__["some_argument"][0].help, "some_argument")


class SpeclessBooleanArguments(BaseArguments):
    """Example argument parser demonstrating specless boolean arguments."""

    bool_without_default: bool
    """bool_without_default"""
    optional_bool_with_default: Optional[bool] = None
    """optional_bool_with_default"""
    optional_bool_without_default: Optional[bool]
    """optional_bool_without_default"""
    bool_with_default_false: bool = False
    """bool_with_default_false"""
    bool_with_default_true: bool = True
    """bool_with_default_true"""


class TestSpeclessBooleanArguments(unittest.TestCase):
    def test_basic_things(self):
        with self.assertRaises(SystemExit):
            SpeclessBooleanArguments([])

        args = SpeclessBooleanArguments(["--bool-without-default", "False"])
        self.assertEqual(args.bool_without_default, False)
        self.assertEqual(args.optional_bool_with_default, None)
        self.assertEqual(args.optional_bool_without_default, None)
        self.assertEqual(args.bool_with_default_false, False)
        self.assertEqual(args.bool_with_default_true, True)

    def test_explicit_bool(self):
        args = SpeclessBooleanArguments(["--bool-without-default", "False"])
        self.assertEqual(args.bool_without_default, False)

        args = SpeclessBooleanArguments(["--bool-without-default", "True"])
        self.assertEqual(args.bool_without_default, True)

        with self.assertRaises(SystemExit):
            SpeclessBooleanArguments(["--bool-without-default", "not-a-bool"])

    def test_store_action(self):
        args = SpeclessBooleanArguments(["--bool-without-default", "False"])
        self.assertEqual(args.bool_with_default_false, False)
        self.assertEqual(args.bool_with_default_true, True)

        args = SpeclessBooleanArguments([
            "--bool-without-default",
            "False",
            "--bool-with-default-true",
            "--bool-with-default-false",
        ])
        self.assertEqual(args.bool_with_default_false, True)
        self.assertEqual(args.bool_with_default_true, False)


class TestSpeclessTupleAndLists(unittest.TestCase):
    def test_basic_things(self):
        class SpeclessTupleAndLists(BaseArguments):
            """Example argument parser demonstrating specless tuple and list arguments."""

            tuple_of_ints: Tuple[int, int]
            """tuple_of_ints"""
            list_of_ints_without_default: List[int]
            """list_of_ints_without_default"""

        with self.assertRaises(SystemExit):
            SpeclessTupleAndLists([])
        with self.assertRaises(SystemExit):
            SpeclessTupleAndLists(["--tuple-of-ints", "1"])
        with self.assertRaises(SystemExit):
            SpeclessTupleAndLists(["--list-of-ints", "1", "2"])
        args1 = SpeclessTupleAndLists(["--tuple-of-ints", "1", "2", "--list-of-ints", "3"])
        self.assertEqual(args1.tuple_of_ints, (1, 2))
        self.assertEqual(args1.list_of_ints_without_default, [3])
        args1 = SpeclessTupleAndLists(["--tuple-of-ints", "1", "2", "--list-of-ints"])
        self.assertEqual(args1.tuple_of_ints, (1, 2))
        self.assertEqual(args1.list_of_ints_without_default, [])

    def test_basic_things2(self):
        class SpeclessTupleAndLists(BaseArguments):
            list_of_ints_with_default: List[int] = [1, 2, 3]
            """list_of_ints_with_default"""

        args2 = SpeclessTupleAndLists([])
        self.assertEqual(args2.list_of_ints_with_default, [1, 2, 3])
        args2 = SpeclessTupleAndLists(["--list-of-ints-with-default", "4", "5"])
        self.assertEqual(args2.list_of_ints_with_default, [4, 5])

    def test_basic_things3(self):
        class SpeclessTupleAndLists(BaseArguments):
            optional_list_of_ints_with_default: Optional[List[int]] = None
            """optional_list_of_ints_with_default"""

        args3 = SpeclessTupleAndLists([])
        self.assertEqual(args3.optional_list_of_ints_with_default, None)
        args3 = SpeclessTupleAndLists(["--optional-list-of-ints-with-default", "4", "5"])
        self.assertEqual(args3.optional_list_of_ints_with_default, [4, 5])

    def test_basic_things4(self):
        class SpeclessTupleAndLists(BaseArguments):
            optional_list_of_ints_without_default: Optional[List[int]]
            """optional_list_of_ints_without_default"""

        args4 = SpeclessTupleAndLists([])
        self.assertEqual(args4.optional_list_of_ints_without_default, None)
        args4 = SpeclessTupleAndLists(["--optional-list-of-ints-without-default", "4", "5"])
        self.assertEqual(args4.optional_list_of_ints_without_default, [4, 5])


if __name__ == "__main__":
    unittest.main()
