import unittest
from os import path

from chipc import iterative_solver

BASE_PATH = path.abspath(path.dirname(__file__))
STATEFUL_ALU_DIR = path.join(BASE_PATH, "../example_alus/")
STATELESS_ALU_DIR = path.join(BASE_PATH, "../chipc/templates/")
SPEC_DIR = path.join(BASE_PATH, "../example_specs/")


class IterativeSolverTest(unittest.TestCase):
    def test_simple_2_2_raw_cex_mode(self):
        self.assertEqual(
            0,
            iterative_solver.main([
                "iterative_solver",
                path.join(SPEC_DIR, "simple.sk"),
                path.join(STATEFUL_ALU_DIR, "raw.stateful_alu"),
                path.join(STATELESS_ALU_DIR, "stateless_alu.j2"),
                "2", "2"]),
        )

    def test_simple_2_2_raw_hole_elimination_mode(self):
        self.assertEqual(
            0,
            iterative_solver.main([
                "iterative_solver", path.join(SPEC_DIR, "simple.sk"),
                path.join(STATEFUL_ALU_DIR, "raw.stateful_alu"),
                path.join(STATELESS_ALU_DIR, "stateless_alu.j2"),
                "2", "2",
                "--hole-elimination"]),
        )

    def test_sampling_revised_2_2_raw_cex_mode(self):
        self.assertEqual(
            1,
            iterative_solver.main([
                "iterative_solver",
                path.join(SPEC_DIR, "sampling_revised.sk"),
                path.join(STATEFUL_ALU_DIR, "raw.stateful_alu"),
                path.join(STATELESS_ALU_DIR, "stateless_alu.j2"),
                "2", "2"]),
        )

    def test_set_default_values(self):
        num_fields_in_prog = 2
        state_group_info = [['0', '0'], ['0', '1']]

        pkt_fields = {'pkt_1': 1}
        state_vars = {'state_group_0_state_0': 2}

        pkt_fields, state_vars = iterative_solver.set_default_values(
            pkt_fields, state_vars, num_fields_in_prog, state_group_info)

        self.assertDictEqual(pkt_fields, {'pkt_0': 0, 'pkt_1': 1})
        self.assertDictEqual(state_vars, {'state_group_0_state_0': 2,
                                          'state_group_0_state_1': 0})


if __name__ == '__main__':
    unittest.main()
