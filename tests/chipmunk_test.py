"""Simple unit tests for chipmunk."""

import unittest
import glob
from os import path, listdir

from chipmunk import Compiler


class ChipmunkCodegenTest(unittest.TestCase):
    """Tests codegen method from chipmunk.Compiler."""

    def setUp(self):
        self.base_path = path.abspath(path.dirname(__file__))
        self.data_dir = path.join(self.base_path, "data/")
        self.alu_dir = path.join(self.base_path, "../example_alus/")
        self.spec_dir = path.join(self.base_path, "../example_specs/")

    def test_codegen_with_simple_sketch_for_all_alus(self):
        base_path = path.abspath(path.dirname(__file__))
        alu_dir = path.join(base_path, "../example_alus/")
        alus = [
            f for f in listdir(alu_dir) if path.isfile(path.join(alu_dir, f))
        ]

        for alu in alus:
            # TODO(taegyunkim): Instead of writing to the same success and
            # failure files, use different files for each ALU.
            compiler = Compiler(
                path.join(base_path, "../example_specs/simple.sk"),
                path.join(alu_dir, alu), 2, 2, "simple", "serial")
            self.assertEqual(compiler.codegen()[
                             0], 0, "Compiling simple.sk failed for " + alu)
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


if __name__ == '__main__':
    unittest.main()
