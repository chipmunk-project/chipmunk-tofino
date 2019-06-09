import unittest
from os import path

from chipc import iterative_solver
from chipc.iterative_solver import generate_hole_elimination_assert

BASE_PATH = path.abspath(path.dirname(__file__))
STATEFUL_ALU_DIR = path.join(BASE_PATH, '../example_alus/')
STATELESS_ALU_DIR = path.join(BASE_PATH, '../chipc/templates/')
SPEC_DIR = path.join(BASE_PATH, '../example_specs/')


class GenerateHoleEliminationTest(unittest.TestCase):
    def test_success(self):
        hole_assignments = {'c': '3', 'a': '1', 'b': '2'}
        self.assertListEqual(
            generate_hole_elimination_assert(hole_assignments),
            ['!((a == 1) && (b == 2) && (c == 3))']
        )

    def test_handle_empty_assignments(self):
        self.assertListEqual(
            generate_hole_elimination_assert({}), []
        )


class IterativeSolverTest(unittest.TestCase):
    def test_sampling_2_1_if_else_raw_cex_mode(self):
        self.assertEqual(
            0,
            iterative_solver.main([
                'iterative_solver',
                path.join(SPEC_DIR, 'sampling.sk'),
                path.join(STATEFUL_ALU_DIR, 'if_else_raw.stateful_alu'),
                path.join(STATELESS_ALU_DIR, 'stateless_alu.j2'),
                '2', '1', '10']),
        )

    def test_rcp_3_2_if_else_raw_cex_mode(self):
        self.assertEqual(
            0,
            iterative_solver.main([
                'iterative_solver',
                path.join(SPEC_DIR, 'rcp.sk'),
                path.join(STATEFUL_ALU_DIR, 'if_else_raw.stateful_alu'),
                path.join(STATELESS_ALU_DIR, 'stateless_alu.j2'),
                '3', '2', '10']),
        )

    def test_blue_increase_4_3_pred_raw_cex_mode(self):
        self.assertEqual(
            0,
            iterative_solver.main([
                'iterative_solver',
                path.join(SPEC_DIR, 'blue_increase.sk'),
                path.join(STATEFUL_ALU_DIR, 'pred_raw.stateful_alu'),
                path.join(STATELESS_ALU_DIR, 'stateless_alu.j2'),
                '4', '3', '10']),
        )

    def test_blue_decrease_4_3_sub_cex_mode(self):
        self.assertEqual(
            0,
            iterative_solver.main([
                'iterative_solver',
                path.join(SPEC_DIR, 'blue_decrease.sk'),
                path.join(STATEFUL_ALU_DIR, 'sub.stateful_alu'),
                path.join(STATELESS_ALU_DIR, 'stateless_alu.j2'),
                '4', '3', '10']),
        )

    def test_marple_tcp_nmo_3_2_pred_raw_cex_mode(self):
        self.assertEqual(
            0,
            iterative_solver.main([
                'iterative_solver',
                path.join(SPEC_DIR, 'marple_tcp_nmo.sk'),
                path.join(STATEFUL_ALU_DIR, 'pred_raw.stateful_alu'),
                path.join(STATELESS_ALU_DIR, 'stateless_alu.j2'),
                '3', '2', '10']),
        )

    def test_marple_new_flow_2_2_pred_raw_cex_mode(self):
        self.assertEqual(
            0,
            iterative_solver.main([
                'iterative_solver',
                path.join(SPEC_DIR, 'marple_new_flow.sk'),
                path.join(STATEFUL_ALU_DIR, 'pred_raw.stateful_alu'),
                path.join(STATELESS_ALU_DIR, 'stateless_alu.j2'),
                '2', '2', '10']),
        )

    def test_simple_2_2_raw_cex_mode(self):
        self.assertEqual(
            0,
            iterative_solver.main([
                'iterative_solver',
                path.join(SPEC_DIR, 'simple.sk'),
                path.join(STATEFUL_ALU_DIR, 'raw.stateful_alu'),
                path.join(STATELESS_ALU_DIR, 'stateless_alu.j2'),
                '2', '2', '10']),
        )

    def test_simple_2_2_raw_hole_elimination_mode(self):
        self.assertEqual(
            0,
            iterative_solver.main([
                'iterative_solver', path.join(SPEC_DIR, 'simple.sk'),
                path.join(STATEFUL_ALU_DIR, 'raw.stateful_alu'),
                path.join(STATELESS_ALU_DIR, 'stateless_alu.j2'),
                '2', '2', '10',
                '--hole-elimination']),
        )

    def test_sampling_revised_2_2_raw_cex_mode(self):
        self.assertEqual(
            1,
            iterative_solver.main([
                'iterative_solver',
                path.join(SPEC_DIR, 'sampling_revised.sk'),
                path.join(STATEFUL_ALU_DIR, 'raw.stateful_alu'),
                path.join(STATELESS_ALU_DIR, 'stateless_alu.j2'),
                '2', '2', '10']),
        )

    def test_times_two(self):
        self.assertEqual(
            0,
            iterative_solver.main([
                'iterative_solver',
                path.join(SPEC_DIR, 'times_two.sk'),
                path.join(STATEFUL_ALU_DIR, 'if_else_raw.stateful_alu'),
                path.join(STATELESS_ALU_DIR, 'stateless_alu.j2'),
                '3', '3', '10']),
        )

    def test_set_default_values(self):
        num_fields_in_prog = 2
        state_group_info = {
            '0': set(['0', '1'])
        }

        pkt_fields = {'pkt_1': 1}
        state_vars = {'state_group_0_state_0': 2}

        pkt_fields, state_vars = iterative_solver.set_default_values(
            pkt_fields, state_vars, num_fields_in_prog, state_group_info)

        self.assertDictEqual(pkt_fields, {'pkt_0': 0, 'pkt_1': 1})
        self.assertDictEqual(state_vars, {'state_group_0_state_0': 2,
                                          'state_group_0_state_1': 0})


if __name__ == '__main__':
    unittest.main()
