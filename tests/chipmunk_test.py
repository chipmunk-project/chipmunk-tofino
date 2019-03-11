"""Simple unit tests for chipmunk."""

from os import path, listdir
from pathlib import Path
import unittest

from chipmunk import Compiler
from optverify import optverify
from utils import get_hole_dicts


class ChipmunkCodegenTest(unittest.TestCase):
    """Tests codegen method from chipmunk.Compiler."""

    def setUp(self):
        self.base_path = path.abspath(path.dirname(__file__))
        self.data_dir = path.join(self.base_path, "data/")
        self.alu_dir = path.join(self.base_path, "../example_alus/")
        self.spec_dir = path.join(self.base_path, "../example_specs/")

    def test_codegen_with_simple_sketch_for_all_alus(self):
        alus = [
            f for f in listdir(self.alu_dir)
            if path.isfile(path.join(self.alu_dir, f))
        ]

        for alu in alus:
            # TODO(taegyunkim): Instead of writing to the same success and
            # failure files, use different files for each ALU.
            compiler = Compiler(
                path.join(self.base_path, "../example_specs/simple.sk"),
                path.join(self.alu_dir, alu), 2, 2, "simple", "serial")
            self.assertEqual(compiler.codegen()[0], 0,
                             "Compiling simple.sk failed for " + alu)
            # TODO(taegyunkim): When all tests pass, clean up intermediary files
            # or at least have an option to keep intermediary files, with
            # default deleting them.

    def test_raise_assertion_for_grid_size(self):
        spec_filename = "simple.sk"
        alu_filename = "raw.stateful_alu"

        with self.assertRaises(AssertionError):
            Compiler(
                path.join(self.spec_dir, spec_filename),
                path.join(self.alu_dir, alu_filename), 1, 0, "simple_raw_1_2",
                "serial")

    def test_simple_raw_succeeds_with_two_two_grid(self):
        spec_filename = "simple.sk"
        alu_filename = "raw.stateful_alu"

        compiler = Compiler(
            path.join(self.spec_dir, spec_filename),
            path.join(self.alu_dir, alu_filename), 2, 2, "simple_raw_2_2",
            "serial")
        (ret_code, output) = compiler.codegen()
        self.assertEqual(
            ret_code, 0,
            "Compiling " + spec_filename + " failed for " + alu_filename)

        expected_holes = get_hole_dicts(
            Path(path.join(self.data_dir,
                           "simple_raw_2_2_codegen.sk")).read_text())

        output_holes = get_hole_dicts(
            Path(path.join(self.base_path,
                           "../simple_raw_2_2_codegen.sk")).read_text())

        self.assertEqual(sorted(expected_holes), sorted(output_holes))


class OptverifyTest(unittest.TestCase):
    def setUp(self):
        self.base_path = path.abspath(path.dirname(__file__))
        self.alu_dir = path.join(self.base_path, "../example_alus/")
        self.spec_dir = path.join(self.base_path, "../example_specs/")
        self.transform_dir = path.join(self.base_path,
                                       "../example_transforms/")

    def test_simple_sketch_same_config(self):
        spec_filename = "simple.sk"
        alu_filename = "raw.stateful_alu"

        compiler = Compiler(
            path.join(self.spec_dir, spec_filename),
            path.join(self.alu_dir, alu_filename), 1, 1, "sample1", "serial")

        compiler.optverify()

        compiler = Compiler(
            path.join(self.spec_dir, spec_filename),
            path.join(self.alu_dir, alu_filename), 1, 1, "sample2", "serial")

        compiler.optverify()

        self.assertEqual(
            0,
            optverify("sample1", "sample2",
                      path.join(self.transform_dir, "very_simple.transform")))


if __name__ == '__main__':
    unittest.main()
