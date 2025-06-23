import unittest
from typing import List, Optional, Tuple

from spargear import Annotated, ArgumentSpec, BaseArguments


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
    def test_specless_type_no_optional(self):
        args = SpeclessBasicArguments([
            "--float-without-default",
            "3.14",
            "--list-of-ints-without-default",
            "1",
            "2",
            "3",
        ])
        self.assertEqual(args.optional_int_with_default, None)
        self.assertEqual(args.optional_int_without_default, None)
        self.assertEqual(args.float_with_default, 0.0)
        self.assertEqual(args.float_without_default, 3.14)
        self.assertEqual(args.float_with_str_default, 1.23)
        self.assertEqual(args.list_of_ints_without_default, [1, 2, 3])

    def test_specless_type_optional(self):
        args = SpeclessBasicArguments([
            "--optional-int-with-default",
            "3",
            "--optional-int-without-default",
            "4",
            "--float-without-default",
            "3.14",
            "--list-of-ints-without-default",
            "1",
            "2",
            "3",
        ])
        self.assertEqual(args.optional_int_with_default, 3)
        self.assertEqual(args.optional_int_without_default, 4)

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


class SpeclessPositionalArguments(BaseArguments):
    flag: int
    """--flag"""
    POSITIONAL: int
    """positional"""
    AnotherFlag: int


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


class TestSpeclessPositionalArguments(unittest.TestCase):
    def test_basic_things(self):
        args = SpeclessPositionalArguments(["2", "--flag", "1", "--anotherflag", "3"])
        self.assertEqual(args.flag, 1)
        self.assertEqual(args.POSITIONAL, 2)
        self.assertEqual(args.AnotherFlag, 3)


class TestSpeclessInheritance(unittest.TestCase):
    def test_basic_things(self):
        class SpeclessInheritance(BaseArguments):
            """Example argument parser demonstrating specless inheritance."""

            flag1: int
            """--flag1"""

        class SpeclessInheritance2(SpeclessInheritance):
            flag1: str  # pyright: ignore[reportIncompatibleVariableOverride]
            """--flag1"""
            flag2: int
            """--flag2"""

        args = SpeclessInheritance2(["--flag1", "1", "--flag2", "2"])
        self.assertEqual(args.flag1, "1")
        self.assertEqual(args.flag2, 2)


class TestAnnotated(unittest.TestCase):
    def test_basic_things(self):
        def negation(x: str) -> int:
            return -int(x)

        class SpeclessAnnotated(BaseArguments):
            a: Annotated[int, negation]
            """--a"""
            b: int
            """--b"""
            c: Annotated[int, None]

        args = SpeclessAnnotated(["--a", "1", "--b", "2", "--c", "3"])
        self.assertEqual(args.a, -1)
        self.assertEqual(args.b, 2)
        self.assertEqual(args.c, 3)

    def test_list(self):
        def as_list(x: str) -> List[int]:
            return [int(i) for i in x.split(",")]

        class SpeclessAnnotated(BaseArguments):
            a: Annotated[List[int], None]
            b: Annotated[List[int], None] = [-2, -3, -4]
            c: Annotated[List[int], as_list]
            d: Annotated[List[int], as_list] = [-4, -5, -6]
            e: Annotated[int, as_list]  # Wrong case! (anti-pattern)
            f: Annotated[int, as_list] = 1  # Wrong case! (anti-pattern)

        args = SpeclessAnnotated([
            "--a",
            "1",
            "2",
            "3",
            "--b",
            "2",
            "3",
            "4",
            "--c",
            "3,4,5",
            "--d",
            "4,5,6",
            "--e",
            "5",
            "--f",
            "6",
        ])
        self.assertEqual(args.a, [1, 2, 3])
        self.assertEqual(args.b, [2, 3, 4])
        self.assertEqual(args.c, [3, 4, 5])
        self.assertEqual(args.d, [4, 5, 6])
        self.assertEqual(args.e, [5])
        self.assertEqual(args.f, [6])


if __name__ == "__main__":
    unittest.main()
