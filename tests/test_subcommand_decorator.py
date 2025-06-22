import unittest
from typing import Optional

from spargear import ArgumentSpec, BaseArguments, subcommand


class GitCommitArguments(BaseArguments):
    """Git commit command arguments."""

    message: ArgumentSpec[str] = ArgumentSpec(["-m", "--message"], required=True, help="Commit message")
    amend: ArgumentSpec[bool] = ArgumentSpec(["--amend"], action="store_true", help="Amend previous commit")


class GitPushArguments(BaseArguments):
    """Git push command arguments."""

    remote: ArgumentSpec[str] = ArgumentSpec(["remote"], nargs="?", default="origin", help="Remote name")
    branch: ArgumentSpec[Optional[str]] = ArgumentSpec(["branch"], nargs="?", help="Branch name")
    force: ArgumentSpec[bool] = ArgumentSpec(["-f", "--force"], action="store_true", help="Force push")


class GitStatusArguments(BaseArguments):
    """Git status command arguments."""

    short: ArgumentSpec[bool] = ArgumentSpec(["-s", "--short"], action="store_true", help="Show short format")


class GitArgumentsWithDecorator(BaseArguments):
    """Git command line interface using @subcommand decorator."""

    verbose: ArgumentSpec[bool] = ArgumentSpec(["-v", "--verbose"], action="store_true", help="Increase verbosity")

    @subcommand(help="Record changes to the repository")
    def commit():
        """Record changes to the repository.

        This command records the changes in the repository.
        """
        return GitCommitArguments

    @subcommand(name="push", help="Update remote refs")
    def push_cmd():
        return GitPushArguments

    @subcommand()
    def status():
        """Show the working tree status.

        Displays paths that have differences between the index file
        and the current HEAD commit.
        """
        return GitStatusArguments


class TestSubcommandDecorator(unittest.TestCase):
    def test_decorator_with_help(self):
        """Test that @subcommand with help parameter works."""
        args = GitArgumentsWithDecorator(["commit", "-m", "test commit"])
        commit = args.last_subcommand
        assert isinstance(commit, GitCommitArguments), "commit should be a GitCommitArguments instance"
        self.assertEqual(commit.message.unwrap(), "test commit")
        self.assertFalse(commit.amend.unwrap())

    def test_decorator_with_name_override(self):
        """Test that @subcommand with custom name works."""
        args = GitArgumentsWithDecorator(["push", "upstream", "main", "--force"])
        push = args.last_subcommand
        assert isinstance(push, GitPushArguments), "push should be a GitPushArguments instance"
        self.assertEqual(push.remote.unwrap(), "upstream")
        self.assertEqual(push.branch.unwrap(), "main")
        self.assertTrue(push.force.unwrap())

    def test_decorator_with_docstring(self):
        """Test that @subcommand extracts help from docstring."""
        args = GitArgumentsWithDecorator(["status", "--short"])
        status = args.last_subcommand
        assert isinstance(status, GitStatusArguments), "status should be a GitStatusArguments instance"
        self.assertTrue(status.short.unwrap())

    def test_subcommand_specs_created(self):
        """Test that SubcommandSpec instances are properly created."""
        cls = GitArgumentsWithDecorator

        # Check that subcommands are registered
        self.assertIn("commit", cls.__subcommands__)
        self.assertIn("push", cls.__subcommands__)
        self.assertIn("status", cls.__subcommands__)

        # Check commit subcommand spec
        commit_spec = cls.__subcommands__["commit"]
        self.assertEqual(commit_spec.name, "commit")
        self.assertEqual(commit_spec.help, "Record changes to the repository")
        self.assertIsNotNone(commit_spec.argument_class_factory)
        self.assertIsNone(commit_spec.argument_class)
        self.assertEqual(commit_spec.get_argument_class(), GitCommitArguments)

        # Check push subcommand spec (with custom name)
        push_spec = cls.__subcommands__["push"]
        self.assertEqual(push_spec.name, "push")
        self.assertEqual(push_spec.help, "Update remote refs")

        # Check status subcommand spec (with docstring)
        status_spec = cls.__subcommands__["status"]
        self.assertEqual(status_spec.name, "status")
        self.assertEqual(status_spec.help, "Show the working tree status.")
        self.assertIsNotNone(status_spec.description)
        self.assertIn("Displays paths", status_spec.description or "")


class GitArgumentsWithDirectClass(BaseArguments):
    """Test using argument_class parameter directly."""

    @subcommand(argument_class=GitCommitArguments, help="Commit changes")  # pyright: ignore[reportArgumentType]
    def commit(self):
        pass  # This function won't be called since argument_class is provided


class TestDirectArgumentClass(unittest.TestCase):
    def test_direct_argument_class(self):
        """Test using argument_class parameter directly."""
        args = GitArgumentsWithDirectClass(["commit", "-m", "direct test"])
        commit = args.last_subcommand
        assert isinstance(commit, GitCommitArguments), "commit should be a GitCommitArguments instance"
        self.assertEqual(commit.message.unwrap(), "direct test")


if __name__ == "__main__":
    unittest.main()
