import unittest
from os import path

from chipc import iterative_solver

BASE_PATH = path.abspath(path.dirname(__file__))

STATELESS_ALU_DIR = path.join(BASE_PATH, '../example_alus/stateless_alus/')
STATEFUL_ALU_DIR = path.join(BASE_PATH, '../example_alus/stateful_alus/')
SPEC_DIR = path.join(BASE_PATH, '../example_specs/')


class TofinoIterativeSolverTest(unittest.TestCase):
    def test_learn_filter_modified_for_test_1_3_tofino_alu_cex_mode(self):
        self.assertEqual(
            0,
            iterative_solver.main([
                'iterative_solver',
                path.join(SPEC_DIR, 'learn_filter_modified_for_test.sk'),
                path.join(STATEFUL_ALU_DIR, 'tofino.alu'),
                path.join(STATELESS_ALU_DIR, 'stateless_alu_for_tofino.alu'),
                '1', '3', '0,1,2,3', '10']),
        )

    def test_learn_filter_modified_for_test_2_2_tofino_alu_cex_mode(self):
        self.assertEqual(
            0,
            iterative_solver.main([
                'iterative_solver',
                path.join(SPEC_DIR, 'learn_filter_modified_for_test.sk'),
                path.join(STATEFUL_ALU_DIR, 'tofino.alu'),
                path.join(STATELESS_ALU_DIR, 'stateless_alu_for_tofino.alu'),
                '2', '2', '0,1,2,3', '10']),
        )

    def test_simple_2_2_tofino_alu_cex_mode(self):
        self.assertEqual(
            0,
            iterative_solver.main([
                'iterative_solver',
                path.join(SPEC_DIR, 'simple.sk'),
                path.join(STATEFUL_ALU_DIR, 'tofino.alu'),
                path.join(STATELESS_ALU_DIR, 'stateless_alu_for_tofino.alu'),
                '2', '2', '0,1,2,3', '10']),
        )

    def test_simple2_2_2_tofino_alu_cex_mode(self):
        self.assertEqual(
            0,
            iterative_solver.main([
                'iterative_solver',
                path.join(SPEC_DIR, 'simple2.sk'),
                path.join(STATEFUL_ALU_DIR, 'tofino.alu'),
                path.join(STATELESS_ALU_DIR, 'stateless_alu_for_tofino.alu'),
                '2', '2', '0,1,2,3', '10']),
        )

    def test_snap_heavy_hitter_2_2_tofino_alu_cex_mode(self):
        self.assertEqual(
            0,
            iterative_solver.main([
                'iterative_solver',
                path.join(SPEC_DIR, 'snap_heavy_hitter.sk'),
                path.join(STATEFUL_ALU_DIR, 'tofino.alu'),
                path.join(STATELESS_ALU_DIR, 'stateless_alu_for_tofino.alu'),
                '1', '1', '0,1,2,3', '10']),
        )


if __name__ == '__main__':
    unittest.main()
