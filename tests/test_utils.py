import unittest

from chipc.utils import get_hole_value_assignments
from chipc.utils import get_state_group_info


class GetHoleValueAssignmentsTest(unittest.TestCase):
    def test_success(self):
        with self.assertRaises(AssertionError):
            get_hole_value_assignments(['a'], 'a__one = 3; a__two = 4')

        holes_to_values = get_hole_value_assignments(
            ['a', 'b', 'c'], 'a__one = 3; b__two = 4 c__three = 5')

        self.assertEqual(holes_to_values, {'a': '3', 'b': '4', 'c': '5'})


class GetStateGroupInfoTest(unittest.TestCase):
    def test_multiple_groups(self):
        state_group_info = get_state_group_info(
            """state_and_packet.state_group_0_state_0,
            state_and_packet.state_group_0_state_1,
            state_and_packet.state_group_1_state_0,
            state_and_packet.state_group_1_state_1""")

        expected_info = {
            '0': set(['0', '1']),
            '1': set(['0', '1']),
        }

        self.assertDictEqual(state_group_info, expected_info)

    def test_ignore_duplicates(self):
        state_group_info = get_state_group_info(
            """state_and_packet.state_group_0_state_0 = 1;
            state_and_packet.state_group_0_state_0 += 1;"""
        )

        self.assertDictEqual(state_group_info, {'0': set('0')})


if __name__ == '__main__':
    unittest.main()
