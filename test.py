from spargear import ArgumentSpec, BaseArguments


class TestArgs(BaseArguments):
    name: ArgumentSpec[str] = ArgumentSpec(name_or_flags=["--name"], help="Name of the test", type=str)


if __name__ == "__main__":
    args = TestArgs()
    print(args.name)
    print(TestArgs.name)
