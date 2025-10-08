# test_enum_literal.py
import unittest
import enum
from typing import Literal, Optional, List, Tuple

from spargear import ArgumentSpec, BaseArguments


# ===== Enum 정의 =====
class Color(enum.Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"


class Mode(enum.IntEnum):
    FAST = 1
    SLOW = 2
    SAFE = 3


# ===== Spec 기반 Enum & Literal =====
class SpecEnumLiteralArguments(BaseArguments):
    """Enum 및 Literal 타입을 사용하는 spec 기반 인자"""

    color: ArgumentSpec[Color] = ArgumentSpec(["--color"], help="Choose a color", default=Color.RED)
    mode: ArgumentSpec[Mode] = ArgumentSpec(["--mode"], help="Choose a mode", default=Mode.SAFE)
    level: ArgumentSpec[Literal["low", "medium", "high"]] = ArgumentSpec(["--level"], default="medium")
    combo: ArgumentSpec[Tuple[Literal["x", "y"], Literal["1", "2"]]] = ArgumentSpec(["--combo"], help="Literal tuple")
    colors: ArgumentSpec[List[Color]] = ArgumentSpec(["--colors"], nargs="*", help="List of enum values", default=[])
    option: ArgumentSpec[Optional[Color]] = ArgumentSpec(["--option"], default=None, help="Optional enum")


# ===== Specless 기반 Enum & Literal =====
class SpeclessEnumLiteralArguments(BaseArguments):
    """Enum 및 Literal 타입을 specless로 테스트"""

    color: Color
    mode: Mode = Mode.SLOW
    level: Literal["low", "medium", "high"] = "low"
    colors: List[Color]
    combo: Tuple[Literal["x", "y"], Literal["1", "2"]]
    optional_color: Optional[Color] = None


# ===== 테스트 =====
class TestSpecEnumLiteralArguments(unittest.TestCase):
    def test_basic_parsing(self):
        args = SpecEnumLiteralArguments(
            [
                "--color",
                "GREEN",
                "--mode",
                "FAST",
                "--level",
                "high",
                "--combo",
                "y",
                "2",
                "--colors",
                "RED",
                "BLUE",
                "--option",
                "BLUE",
            ]
        )
        self.assertEqual(args.color.unwrap(), Color.GREEN)
        self.assertEqual(args.mode.unwrap(), Mode.FAST)
        self.assertEqual(args.level.unwrap(), "high")
        self.assertEqual(args.combo.unwrap(), ("y", "2"))
        self.assertEqual(args.colors.unwrap(), [Color.RED, Color.BLUE])
        self.assertEqual(args.option.unwrap(), Color.BLUE)

    def test_invalid_enum_value(self):
        with self.assertRaises(KeyError):
            SpecEnumLiteralArguments(["--color", "PURPLE"])  # 잘못된 값

    def test_invalid_literal_value(self):
        with self.assertRaises(SystemExit):
            SpecEnumLiteralArguments(["--level", "invalid"])  # 잘못된 리터럴


class TestSpeclessEnumLiteralArguments(unittest.TestCase):
    def test_basic_parsing(self):
        args = SpeclessEnumLiteralArguments(
            [
                "--color",
                "RED",
                "--mode",
                "SAFE",
                "--level",
                "medium",
                "--colors",
                "GREEN",
                "BLUE",
                "--combo",
                "x",
                "1",
            ]
        )
        self.assertEqual(args.color, Color.RED)
        self.assertEqual(args.mode, Mode.SAFE)
        self.assertEqual(args.level, "medium")
        self.assertEqual(args.colors, [Color.GREEN, Color.BLUE])
        self.assertEqual(args.combo, ("x", "1"))
        self.assertIsNone(args.optional_color)

    def test_optional_enum(self):
        args = SpeclessEnumLiteralArguments(
            [
                "--color",
                "BLUE",
                "--mode",
                "SLOW",
                "--level",
                "low",
                "--colors",
                "RED",
                "--combo",
                "y",
                "1",
                "--optional-color",
                "GREEN",
            ]
        )
        self.assertEqual(args.optional_color, Color.GREEN)

    def test_invalid_enum_or_literal(self):
        with self.assertRaises(KeyError):
            SpeclessEnumLiteralArguments(
                [
                    "--color",
                    "invalid",
                    "--mode",
                    "SAFE",
                    "--level",
                    "low",
                    "--colors",
                    "RED",
                    "--combo",
                    "x",
                    "1",
                ]
            )
        with self.assertRaises(SystemExit):
            SpeclessEnumLiteralArguments(
                [
                    "--color",
                    "RED",
                    "--mode",
                    "SAFE",
                    "--level",
                    "bad",
                    "--colors",
                    "RED",
                    "--combo",
                    "x",
                    "1",
                ]
            )


if __name__ == "__main__":
    unittest.main()
