import unittest
from os import path

from chipc import iterative_solver
from chipc.iterative_solver import generate_hole_elimination_assert

BASE_PATH = path.abspath(path.dirname(__file__))

STATELESS_ALU_DIR = path.join(BASE_PATH, '../example_alus/stateless_alus/')
STATEFUL_ALU_DIR = path.join(BASE_PATH, '../example_alus/stateful_alus/')
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
                path.join(STATEFUL_ALU_DIR, 'if_else_raw.alu'),
                path.join(STATELESS_ALU_DIR, 'stateless_alu.alu'),
                '2', '1', '{0,1,2,3}', '10']),
        )

    def test_sampling_2_1_if_else_raw_cex_mode_synthesized_alloc(self):
        self.assertEqual(
            0,
            iterative_solver.main([
                'iterative_solver',
                path.join(SPEC_DIR, 'sampling.sk'),
                path.join(STATEFUL_ALU_DIR, 'if_else_raw.alu'),
                path.join(STATELESS_ALU_DIR, 'stateless_alu.alu'),
                '2', '1', '{0,1,2,3}', '10',
                '--synthesized-allocation']),
        )

    def test_rcp_3_2_if_else_raw_cex_mode(self):
        self.assertEqual(
            0,
            iterative_solver.main([
                'iterative_solver',
                path.join(SPEC_DIR, 'rcp.sk'),
                path.join(STATEFUL_ALU_DIR, 'if_else_raw.alu'),
                path.join(STATELESS_ALU_DIR, 'stateless_alu.alu'),
                '3', '2', '{0,1,2,3}', '10']),
        )

    def test_rcp_3_2_if_else_raw_cex_mode_synthesized_alloc(self):
        self.assertEqual(
            0,
            iterative_solver.main([
                'iterative_solver',
                path.join(SPEC_DIR, 'rcp.sk'),
                path.join(STATEFUL_ALU_DIR, 'if_else_raw.alu'),
                path.join(STATELESS_ALU_DIR, 'stateless_alu.alu'),
                '3', '2', '{0,1,2,3}', '10',
                '--synthesized-allocation']),
        )

    def test_blue_increase_4_2_pred_raw_cex_mode(self):
        self.assertEqual(
            0,
            iterative_solver.main([
                'iterative_solver',
                path.join(SPEC_DIR, 'blue_increase.sk'),
                path.join(STATEFUL_ALU_DIR, 'pred_raw.alu'),
                path.join(STATELESS_ALU_DIR, 'stateless_alu.alu'),
                '4', '2', '{0,1,2,3}', '10']),
        )

    def test_blue_increase_4_2_pred_raw_cex_mode_synthesized_alloc(self):
        self.assertEqual(
            0,
            iterative_solver.main([
                'iterative_solver',
                path.join(SPEC_DIR, 'blue_increase.sk'),
                path.join(STATEFUL_ALU_DIR, 'pred_raw.alu'),
                path.join(STATELESS_ALU_DIR, 'stateless_alu.alu'),
                '4', '2', '{0,1,2,3}', '10',
                '--synthesized-allocation']),
        )

    def test_learn_filter_1_3_raw_cex_mode(self):
        self.assertEqual(
            0,
            iterative_solver.main([
                'iterative_solver',
                path.join(SPEC_DIR, 'learn_filter.sk'),
                path.join(STATEFUL_ALU_DIR, 'raw.alu'),
                path.join(STATELESS_ALU_DIR, 'stateless_alu.alu'),
                '1', '3', '{0,1,2,3}', '10']),
        )

    def test_learn_filter_1_3_raw_cex_mode_synthesized_alloc(self):
        self.assertEqual(
            0,
            iterative_solver.main([
                'iterative_solver',
                path.join(SPEC_DIR, 'learn_filter.sk'),
                path.join(STATEFUL_ALU_DIR, 'raw.alu'),
                path.join(STATELESS_ALU_DIR, 'stateless_alu.alu'),
                '1', '3', '{0,1,2,3}', '10',
                '--synthesized-allocation']),
        )

    def test_learn_filter_2_2_raw_cex_mode(self):
        self.assertEqual(
            0,
            iterative_solver.main([
                'iterative_solver',
                path.join(SPEC_DIR, 'learn_filter.sk'),
                path.join(STATEFUL_ALU_DIR, 'raw.alu'),
                path.join(STATELESS_ALU_DIR, 'stateless_alu.alu'),
                '2', '2', '{0,1,2,3}', '10']),
        )

    def test_learn_filter_2_2_raw_cex_mode_synthesized_alloc(self):
        self.assertEqual(
            0,
            iterative_solver.main([
                'iterative_solver',
                path.join(SPEC_DIR, 'learn_filter.sk'),
                path.join(STATEFUL_ALU_DIR, 'raw.alu'),
                path.join(STATELESS_ALU_DIR, 'stateless_alu.alu'),
                '2', '2', '{0,1,2,3}', '10',
                '--synthesized-allocation']),
        )

    def test_blue_decrease_4_2_sub_cex_mode(self):
        self.assertEqual(
            0,
            iterative_solver.main([
                'iterative_solver',
                path.join(SPEC_DIR, 'blue_decrease.sk'),
                path.join(STATEFUL_ALU_DIR, 'sub.alu'),
                path.join(STATELESS_ALU_DIR, 'stateless_alu.alu'),
                '4', '2', '{0,1,2,3}', '10']),
        )

    def test_blue_decrease_4_2_sub_cex_mode_synthesized_alloc(self):
        self.assertEqual(
            0,
            iterative_solver.main([
                'iterative_solver',
                path.join(SPEC_DIR, 'blue_decrease.sk'),
                path.join(STATEFUL_ALU_DIR, 'sub.alu'),
                path.join(STATELESS_ALU_DIR, 'stateless_alu.alu'),
                '4', '2', '{0,1,2,3}', '10',
                '--synthesized-allocation']),
        )

    def test_marple_tcp_nmo_3_2_pred_raw_cex_mode(self):
        self.assertEqual(
            0,
            iterative_solver.main([
                'iterative_solver',
                path.join(SPEC_DIR, 'marple_tcp_nmo.sk'),
                path.join(STATEFUL_ALU_DIR, 'pred_raw.alu'),
                path.join(STATELESS_ALU_DIR, 'stateless_alu.alu'),
                '3', '2', '{0,1,2,3}', '10']),
        )

    def test_marple_tcp_nmo_3_2_pred_raw_cex_mode_synthesized_alloc(self):
        self.assertEqual(
            0,
            iterative_solver.main([
                'iterative_solver',
                path.join(SPEC_DIR, 'marple_tcp_nmo.sk'),
                path.join(STATEFUL_ALU_DIR, 'pred_raw.alu'),
                path.join(STATELESS_ALU_DIR, 'stateless_alu.alu'),
                '3', '2', '{0,1,2,3}', '10',
                '--synthesized-allocation']),
        )

    def test_marple_new_flow_2_2_pred_raw_cex_mode(self):
        self.assertEqual(
            0,
            iterative_solver.main([
                'iterative_solver',
                path.join(SPEC_DIR, 'marple_new_flow.sk'),
                path.join(STATEFUL_ALU_DIR, 'pred_raw.alu'),
                path.join(STATELESS_ALU_DIR, 'stateless_alu.alu'),
                '2', '2', '{0,1,2,3}', '10']),
        )

    def test_marple_new_flow_2_2_pred_raw_cex_mode_synthesized_alloc(self):
        self.assertEqual(
            0,
            iterative_solver.main([
                'iterative_solver',
                path.join(SPEC_DIR, 'marple_new_flow.sk'),
                path.join(STATEFUL_ALU_DIR, 'pred_raw.alu'),
                path.join(STATELESS_ALU_DIR, 'stateless_alu.alu'),
                '2', '2', '{0,1,2,3}', '10',
                '--synthesized-allocation']),
        )

    def test_simple_2_2_raw_cex_mode(self):
        self.assertEqual(
            0,
            iterative_solver.main([
                'iterative_solver',
                path.join(SPEC_DIR, 'simple.sk'),
                path.join(STATEFUL_ALU_DIR, 'raw.alu'),
                path.join(STATELESS_ALU_DIR, 'stateless_alu.alu'),
                '2', '2', '{0,1,2,3}', '10']),
        )

    def test_simple_2_2_raw_cex_mode_synthesized_alloc(self):
        self.assertEqual(
            0,
            iterative_solver.main([
                'iterative_solver',
                path.join(SPEC_DIR, 'simple.sk'),
                path.join(STATEFUL_ALU_DIR, 'raw.alu'),
                path.join(STATELESS_ALU_DIR, 'stateless_alu.alu'),
                '2', '2', '{0,1,2,3}', '10',
                '--synthesized-allocation']),
        )

    def test_sampling_revised_2_2_raw_cex_mode(self):
        self.assertEqual(
            1,
            iterative_solver.main([
                'iterative_solver',
                path.join(SPEC_DIR, 'sampling_revised.sk'),
                path.join(STATEFUL_ALU_DIR, 'raw.alu'),
                path.join(STATELESS_ALU_DIR, 'stateless_alu.alu'),
                '2', '2', '{0,1,2,3}', '10']),
        )

    def test_sampling_revised_2_2_raw_cex_mode_synthesized_alloc(self):
        self.assertEqual(
            1,
            iterative_solver.main([
                'iterative_solver',
                path.join(SPEC_DIR, 'sampling_revised.sk'),
                path.join(STATEFUL_ALU_DIR, 'raw.alu'),
                path.join(STATELESS_ALU_DIR, 'stateless_alu.alu'),
                '2', '2', '{0,1,2,3}', '10',
                '--synthesized-allocation']),
        )

    # NOTE(taegyunkim): As long as we synthesize initially with 2 bits, and try
    # to verify with a larger input bits, times_two.sk will always trigger the
    # code paths to add counterexamples and additional asserts for hole value
    # assignments.
    def test_times_two(self):
        self.assertEqual(
            0,
            iterative_solver.main([
                'iterative_solver',
                path.join(SPEC_DIR, 'times_two.sk'),
                path.join(STATEFUL_ALU_DIR, 'if_else_raw.alu'),
                path.join(STATELESS_ALU_DIR, 'stateless_alu.alu'),
                '3', '3', '{0,1,2,3}', '10']),
        )
    '''
    def test_times_two_hole_elimination(self):
        self.assertEqual(
            0,
            iterative_solver.main([
                'iterative_solver',
                path.join(SPEC_DIR, 'times_two.sk'),
                path.join(STATEFUL_ALU_DIR, 'if_else_raw.alu'),
                path.join(STATELESS_ALU_DIR, 'stateless_alu.alu'),
                '3', '3', '10', '--hole-elimination']),
        )
    '''

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
