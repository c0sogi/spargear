import unittest
from typing import List, Type

from spargear import ArgumentSpec, BaseArguments, SubcommandSpec


class DynamicCommitArguments(BaseArguments):
    """Dynamically created commit command arguments."""

    message: ArgumentSpec[str] = ArgumentSpec(
        ["-m", "--message"], required=True, help="Commit message"
    )
    amend: ArgumentSpec[bool] = ArgumentSpec(
        ["--amend"], action="store_true", help="Amend previous commit"
    )


class DynamicPushArguments(BaseArguments):
    """Dynamically created push command arguments."""

    remote: ArgumentSpec[str] = ArgumentSpec(
        ["remote"], nargs="?", default="origin", help="Remote name"
    )
    force: ArgumentSpec[bool] = ArgumentSpec(
        ["-f", "--force"], action="store_true", help="Force push"
    )


def create_commit_class() -> Type[DynamicCommitArguments]:
    """Factory function to create commit arguments class."""
    return DynamicCommitArguments


def create_push_class() -> Type[BaseArguments]:
    """Factory function to create push arguments class."""
    return DynamicPushArguments


class DynamicGitArguments(BaseArguments):
    """Git CLI with dynamic subcommand creation."""

    verbose: ArgumentSpec[bool] = ArgumentSpec(
        ["-v", "--verbose"], action="store_true", help="Increase verbosity"
    )

    # Using factory function
    commit_cmd: SubcommandSpec[DynamicCommitArguments] = SubcommandSpec(
        name="commit",
        argument_class_factory=create_commit_class,
        help="Record changes",
    )

    # Using lambda factory
    push_cmd: SubcommandSpec[DynamicPushArguments] = SubcommandSpec(
        name="push",
        argument_class_factory=lambda: DynamicPushArguments,
        help="Update remote",
    )

    # Using direct class (should still work)
    status_cmd: SubcommandSpec[DynamicCommitArguments] = SubcommandSpec(
        name="status",
        argument_class=DynamicCommitArguments,  # Reusing for simplicity
        help="Show status",
    )


class TestDynamicSubcommands(unittest.TestCase):
    def test_factory_function_commit(self):
        """Test subcommand with factory function."""
        # commit requires -m
        with self.assertRaises(SystemExit):
            DynamicGitArguments(["commit"])

        git_args = DynamicGitArguments(["commit", "-m", "fix"])
        commit = git_args.last_subcommand
        assert isinstance(commit, DynamicCommitArguments), (
            "commit should be an instance of DynamicCommitArguments"
        )
        self.assertEqual(commit.message.unwrap(), "fix")
        self.assertFalse(commit.amend.unwrap())

    def test_lambda_factory_push(self):
        """Test subcommand with lambda factory."""
        git_args = DynamicGitArguments(["push"])
        push = git_args.last_subcommand
        assert isinstance(push, DynamicPushArguments), (
            "push should be an instance of DynamicPushArguments"
        )
        self.assertEqual(push.remote.unwrap(), "origin")
        self.assertFalse(push.force.unwrap())

    def test_direct_class_status(self):
        """Test subcommand with direct class (should still work)."""
        git_args = DynamicGitArguments(["status", "-m", "test"])
        status = git_args.last_subcommand
        assert isinstance(status, DynamicCommitArguments), (
            "status should be an instance of DynamicCommitArguments"
        )
        self.assertEqual(status.message.unwrap(), "test")

    def test_factory_called_on_demand(self):
        """Test that factory is called on demand, not at class definition time."""
        calls: List[str] = []

        def counting_factory() -> Type[DynamicCommitArguments]:
            calls.append("called")
            return DynamicCommitArguments

        class TestArgs(BaseArguments):
            test_cmd: SubcommandSpec[DynamicCommitArguments] = SubcommandSpec(
                name="test",
                argument_class_factory=counting_factory,
                help="Test command",
            )

        # Factory should not be called yet
        self.assertEqual(len(calls), 0)

        # Factory should be called when getting argument class
        TestArgs(["test", "-m", "message"])
        self.assertEqual(len(calls), 1)


class TestSubcommandSpecValidation(unittest.TestCase):
    def test_no_class_or_factory_raises_error(self):
        """Test that providing neither argument_class nor argument_class_factory raises an error."""
        with self.assertRaises(ValueError) as cm:
            SubcommandSpec(name="test")
        self.assertIn(
            "Either argument_class or argument_class_factory must be provided",
            str(cm.exception),
        )

    def test_both_class_and_factory_raises_error(self):
        """Test that providing both argument_class and argument_class_factory raises an error."""
        with self.assertRaises(ValueError) as cm:
            SubcommandSpec(
                name="test",
                argument_class=DynamicCommitArguments,
                argument_class_factory=create_commit_class,
            )
        self.assertIn(
            "Only one of argument_class or argument_class_factory should be provided",
            str(cm.exception),
        )

    def test_get_argument_class_with_class(self):
        """Test get_argument_class with direct class."""
        spec = SubcommandSpec(name="test", argument_class=DynamicCommitArguments)
        self.assertEqual(spec.get_argument_class(), DynamicCommitArguments)

    def test_get_argument_class_with_factory(self):
        """Test get_argument_class with factory function."""
        spec = SubcommandSpec(name="test", argument_class_factory=create_commit_class)
        self.assertEqual(spec.get_argument_class(), DynamicCommitArguments)


if __name__ == "__main__":
    unittest.main()
