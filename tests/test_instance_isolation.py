import unittest
from typing import cast

from spargear import ArgumentSpec, BaseArguments, SubcommandSpec


class SharedSubCommand(BaseArguments):
    """공유되는 서브커맨드 클래스 - 여러 부모에서 사용됨"""

    shared_arg: ArgumentSpec[str] = ArgumentSpec(["--shared"], default="default", help="Shared argument")
    value: ArgumentSpec[int] = ArgumentSpec(["--value"], type=int, default=0, help="Value argument")


class ParentA(BaseArguments):
    """첫 번째 부모 클래스"""

    parent_a_arg: ArgumentSpec[str] = ArgumentSpec(["--parent-a"], default="a", help="Parent A argument")
    shared_sub = SubcommandSpec("shared", help="Shared subcommand", argument_class=SharedSubCommand)


class ParentB(BaseArguments):
    """두 번째 부모 클래스"""

    parent_b_arg: ArgumentSpec[str] = ArgumentSpec(["--parent-b"], default="b", help="Parent B argument")
    shared_sub = SubcommandSpec("shared", help="Shared subcommand", argument_class=SharedSubCommand)


class TestInstanceIsolation(unittest.TestCase):
    """인스턴스 격리 테스트"""

    def test_shared_subcommand_class_isolation(self):
        """동일한 서브커맨드 클래스가 여러 부모에서 사용될 때 격리되는지 테스트"""

        # 첫 번째 부모에서 서브커맨드 사용
        parent_a = ParentA(["shared", "--shared", "value_a", "--value", "100"])
        sub_a = parent_a.last_subcommand

        # 두 번째 부모에서 서브커맨드 사용
        parent_b = ParentB(["shared", "--shared", "value_b", "--value", "200"])
        sub_b = parent_b.last_subcommand

        # 타입 확인
        self.assertIsInstance(sub_a, SharedSubCommand)
        self.assertIsInstance(sub_b, SharedSubCommand)
        self.assertIsNotNone(sub_a)
        self.assertIsNotNone(sub_b)

        # 타입 캐스팅으로 타입 체커 오류 해결
        sub_a_typed = cast(SharedSubCommand, sub_a)
        sub_b_typed = cast(SharedSubCommand, sub_b)

        # 값 격리 확인
        self.assertEqual(sub_a_typed.shared_arg.unwrap(), "value_a")
        self.assertEqual(sub_a_typed.value.unwrap(), 100)

        self.assertEqual(sub_b_typed.shared_arg.unwrap(), "value_b")
        self.assertEqual(sub_b_typed.value.unwrap(), 200)

        # 인스턴스가 독립적인지 확인
        self.assertNotEqual(sub_a_typed.shared_arg.unwrap(), sub_b_typed.shared_arg.unwrap())
        self.assertNotEqual(sub_a_typed.value.unwrap(), sub_b_typed.value.unwrap())

    def test_multiple_instances_same_class(self):
        """같은 클래스의 여러 인스턴스가 서로 독립적인지 테스트"""

        # 같은 클래스로 여러 인스턴스 생성
        instance1 = ParentA(["shared", "--shared", "inst1", "--value", "10"])
        instance2 = ParentA(["shared", "--shared", "inst2", "--value", "20"])
        instance3 = ParentA(["shared", "--shared", "inst3", "--value", "30"])

        sub1 = instance1.last_subcommand
        sub2 = instance2.last_subcommand
        sub3 = instance3.last_subcommand

        # 타입 확인
        self.assertIsInstance(sub1, SharedSubCommand)
        self.assertIsInstance(sub2, SharedSubCommand)
        self.assertIsInstance(sub3, SharedSubCommand)

        # 타입 캐스팅
        sub1_typed = cast(SharedSubCommand, sub1)
        sub2_typed = cast(SharedSubCommand, sub2)
        sub3_typed = cast(SharedSubCommand, sub3)

        # 각 인스턴스가 독립적인 값을 가지는지 확인
        self.assertEqual(sub1_typed.shared_arg.unwrap(), "inst1")
        self.assertEqual(sub1_typed.value.unwrap(), 10)

        self.assertEqual(sub2_typed.shared_arg.unwrap(), "inst2")
        self.assertEqual(sub2_typed.value.unwrap(), 20)

        self.assertEqual(sub3_typed.shared_arg.unwrap(), "inst3")
        self.assertEqual(sub3_typed.value.unwrap(), 30)

        # 서로 다른 인스턴스인지 확인
        self.assertIsNot(sub1, sub2)
        self.assertIsNot(sub2, sub3)
        self.assertIsNot(sub1, sub3)

    def test_argumentspec_instance_isolation(self):
        """ArgumentSpec 인스턴스가 격리되는지 테스트"""

        parent1 = ParentA(["--parent-a", "custom1"])
        parent2 = ParentA(["--parent-a", "custom2"])

        # ArgumentSpec 인스턴스가 독립적인지 확인
        self.assertEqual(parent1.parent_a_arg.unwrap(), "custom1")
        self.assertEqual(parent2.parent_a_arg.unwrap(), "custom2")

        # spec 객체 자체는 다른 인스턴스여야 함
        self.assertIsNot(parent1.parent_a_arg, parent2.parent_a_arg)

        # 값 변경이 다른 인스턴스에 영향을 주지 않는지 확인
        parent1.parent_a_arg.value = "modified1"
        parent2.parent_a_arg.value = "modified2"

        self.assertEqual(parent1.parent_a_arg.value, "modified1")
        self.assertEqual(parent2.parent_a_arg.value, "modified2")

    def test_default_values_isolation(self):
        """기본값이 독립적으로 관리되는지 테스트"""

        # 기본값 사용
        parent1 = ParentA([])
        parent2 = ParentA([])

        # 기본값이 같은지 확인
        self.assertEqual(parent1.parent_a_arg.unwrap(), "a")
        self.assertEqual(parent2.parent_a_arg.unwrap(), "a")

        # 하나의 값을 변경
        parent1.parent_a_arg.value = "changed"

        # 다른 인스턴스에 영향을 주지 않는지 확인
        self.assertEqual(parent1.parent_a_arg.value, "changed")
        self.assertEqual(parent2.parent_a_arg.unwrap(), "a")

    def test_class_attribute_preservation(self):
        """클래스 수준 속성이 보존되는지 테스트 - 회귀 테스트"""

        # 원래 클래스 속성 저장
        original_subcommands_a = ParentA.__subcommands__.copy()
        original_subcommands_b = ParentB.__subcommands__.copy()
        original_shared_subcommands = SharedSubCommand.__subcommands__.copy()

        # 여러 인스턴스 생성
        for i in range(5):
            ParentA(["shared", "--shared", f"test_{i}"])
            ParentB(["shared", "--shared", f"test_{i}"])

        # 클래스 속성이 변경되지 않았는지 확인
        # (이전에는 __parent__ 설정으로 인해 문제가 있었음)
        self.assertEqual(ParentA.__subcommands__, original_subcommands_a)
        self.assertEqual(ParentB.__subcommands__, original_subcommands_b)
        self.assertEqual(SharedSubCommand.__subcommands__, original_shared_subcommands)


if __name__ == "__main__":
    unittest.main()
