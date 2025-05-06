import os
import sys
import unittest
from typing import Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from spargear import ArgumentSpec, BaseArguments, SubcommandSpec


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
        commit = GitArguments(["commit", "-m", "fix"]).last_subcommand
        assert isinstance(commit, GitCommitArguments), "commit should be an instance of GitCommitArguments"
        self.assertEqual(commit.message.unwrap(), "fix")
        self.assertFalse(commit.amend.unwrap())

    def test_commit_with_amend(self):
        commit = GitArguments(["commit", "-m", "msg", "--amend"]).last_subcommand
        assert isinstance(commit, GitCommitArguments), "commit should be an instance of GitCommitArguments"
        self.assertTrue(commit.amend.unwrap())

    def test_push_subcommand_defaults(self):
        push = GitArguments(["push"]).last_subcommand
        assert isinstance(push, GitPushArguments), "push should be an instance of GitPushArguments"
        self.assertEqual(push.remote.unwrap(), "origin")
        self.assertIsNone(push.branch.value)
        self.assertFalse(push.force.unwrap())

    def test_push_with_overrides(self):
        push = GitArguments(["push", "upstream", "dev", "--force"]).last_subcommand
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
        baz = RootArgs(["FOO_VAL", "bar", "baz", "--qux", "QUX_VAL"]).last_subcommand
        assert isinstance(baz, BazArgs), f"baz should be an instance of BarArgs: {type(baz)}"
        self.assertEqual(baz.qux.unwrap(), "QUX_VAL")

    def test_error_on_missing(self):
        with self.assertRaises(SystemExit):
            RootArgs([])  # missing foo positional
        with self.assertRaises(SystemExit):
            RootArgs(["FOO_VAL", "VAL", "bar"])  # missing baz sub-subcommand


if __name__ == "__main__":
    unittest.main()
