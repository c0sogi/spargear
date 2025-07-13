import unittest

from spargear import ArgumentSpec, BaseArguments


class TestGetSetAttr(unittest.TestCase):
    def test_set_get_attr(self):
        """Test setting and getting attributes in BaseArguments."""

        class ExampleArgs(BaseArguments):
            attr1: str = "default"
            attr2: int = 42
            attr3: ArgumentSpec[str] = ArgumentSpec(name_or_flags=["--attr3"], default="spec_default")
            attr4: ArgumentSpec[int] = ArgumentSpec(name_or_flags=["--attr4"], default_factory=lambda: 100)

        args = ExampleArgs()

        # Set attributes
        args.attr1 = "new_value"
        args.attr2 = 100
        args.attr3.value = "new_spec_value"
        args.attr4.value = 200

        # Get attributes
        self.assertEqual(args.attr1, "new_value")
        self.assertEqual(args.attr2, 100)
        self.assertEqual(args.attr3.value, "new_spec_value")
        self.assertEqual(args.attr4.value, 200)
