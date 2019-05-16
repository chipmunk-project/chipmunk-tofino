"""Simple unit tests for chipmunk."""
import unittest
from os import getcwd
from os import listdir
from os import path
from pathlib import Path

from chipc.compiler import Compiler
from chipc.optverify import optverify
from chipc.utils import get_hole_dicts

BASE_PATH = path.abspath(path.dirname(__file__))
DATA_DIR = path.join(BASE_PATH, 'data/')
STATEFUL_ALU_DIR = path.join(BASE_PATH, '../example_alus/')
STATELESS_ALU_DIR = path.join(BASE_PATH, '../chipc/templates/')
SPEC_DIR = path.join(BASE_PATH, '../example_specs/')
TRANSFORM_DIR = path.join(BASE_PATH, '../example_transforms/')


class TestDirectSolver(unittest.TestCase):
    """Tests codegen method from chipmunk.Compiler."""

    def test_codegen_with_simple_sketch_for_all_alus(self):
        alus = [
            f for f in listdir(STATEFUL_ALU_DIR)
            if path.isfile(path.join(STATEFUL_ALU_DIR, f))
        ]

        for alu in alus:
            # TODO(taegyunkim): Instead of writing to the same success and
            # failure files, use different files for each ALU.
            compiler = Compiler(
                path.join(SPEC_DIR, 'simple.sk'), path.join(
                    STATEFUL_ALU_DIR, alu),
                path.join(STATELESS_ALU_DIR, 'stateless_alu.j2'), 2,
                2, 'simple', parallel_sketch=False)
            self.assertEqual(compiler.serial_codegen()[0], 0,
                             'Compiling simple.sk failed for ' + alu)
            # TODO(taegyunkim): When all tests pass, clean up intermediary
            # files or at least have an option to keep intermediary files, with
            # default deleting them.

    def test_raise_assertion_for_grid_size(self):
        spec_filename = 'simple.sk'
        alu_filename = 'raw.stateful_alu'

        with self.assertRaises(AssertionError):
            Compiler(
                path.join(SPEC_DIR, spec_filename),
                path.join(STATEFUL_ALU_DIR, alu_filename),
                path.join(STATELESS_ALU_DIR, 'stateless_alu.j2'),
                1, 0, 'simple_raw_1_2', 'serial')

    def test_simple_raw_succeeds_with_two_two_grid(self):
        spec_filename = 'simple.sk'
        alu_filename = 'raw.stateful_alu'

        compiler = Compiler(
            path.join(SPEC_DIR, spec_filename), path.join(
                STATEFUL_ALU_DIR, alu_filename),
            path.join(STATELESS_ALU_DIR, 'stateless_alu.j2'),
            2, 2, 'simple_raw_2_2', parallel_sketch=False)
        (ret_code, _, _) = compiler.serial_codegen()
        self.assertEqual(
            ret_code, 0,
            'Compiling ' + spec_filename + ' failed for ' + alu_filename)

        expected_holes = get_hole_dicts(
            Path(path.join(DATA_DIR, 'simple_raw_2_2_codegen_iteration_1.sk'
                           )).read_text())

        output_holes = get_hole_dicts(
            Path(path.join(getcwd(), 'simple_raw_2_2_codegen_iteration_1.sk'
                           )).read_text())

        self.assertEqual(sorted(expected_holes), sorted(output_holes))

    def test_simple_raw_fails_with_one_two_grid(self):
        spec_filename = 'simple.sk'
        alu_filename = 'raw.stateful_alu'

        compiler = Compiler(
            path.join(SPEC_DIR, spec_filename), path.join(
                STATEFUL_ALU_DIR, alu_filename),
            path.join(STATELESS_ALU_DIR, 'stateless_alu.j2'),
            1, 2, 'simple_raw_1_2', parallel_sketch=False)
        (ret_code, _, _) = compiler.serial_codegen()
        self.assertEqual(
            1, ret_code, 'Compiling ' + spec_filename + ' used to fail for ' +
            alu_filename + ', but it succeeded, please check and upate ' +
            'this test accordingly if this is expected.')

    def test_test_sketch(self):
        spec_filename = 'test.sk'
        alu_filename = 'raw.stateful_alu'
        # Running in parallel mode to minimize test run time.
        compiler = Compiler(
            path.join(SPEC_DIR, spec_filename), path.join(
                STATEFUL_ALU_DIR, alu_filename),
            path.join(STATELESS_ALU_DIR, 'stateless_alu.j2'),
            3, 3, 'test_raw_3_3', parallel_sketch=True)
        (ret_code, _, _) = compiler.serial_codegen()
        self.assertEqual(
            1, ret_code, 'Compiling ' + spec_filename + ' used to fail for ' +
            alu_filename + ', but it succeeded, please check and upate ' +
            'this test accordingly if this is expected.')

        compiler = Compiler(
            path.join(SPEC_DIR, spec_filename), path.join(
                STATEFUL_ALU_DIR, alu_filename),
            path.join(STATELESS_ALU_DIR, 'stateless_alu.j2'),
            4, 4, 'test_raw_4_4', parallel_sketch=True)
        (ret_code, _, _) = compiler.serial_codegen()
        self.assertEqual(
            ret_code, 0,
            'Compiling ' + spec_filename + ' failed for ' + alu_filename)


class OptverifyTest(unittest.TestCase):
    def test_simple_sketch_same_config(self):
        spec_filename = 'simple.sk'
        alu_filename = 'raw.stateful_alu'

        compiler = Compiler(
            path.join(SPEC_DIR, spec_filename), path.join(
                STATEFUL_ALU_DIR, alu_filename),
            path.join(STATELESS_ALU_DIR, 'stateless_alu.j2'),
            1, 1, 'sample1', parallel_sketch=False)

        compiler.optverify()

        compiler = Compiler(
            path.join(SPEC_DIR, spec_filename), path.join(
                STATEFUL_ALU_DIR, alu_filename),
            path.join(STATELESS_ALU_DIR, 'stateless_alu.j2'),
            1, 1, 'sample2', parallel_sketch=False)

        compiler.optverify()
        self.assertEqual(
            0,
            optverify('sample1', 'sample2',
                      path.join(TRANSFORM_DIR, 'very_simple.transform')))


if __name__ == '__main__':
    unittest.main()
