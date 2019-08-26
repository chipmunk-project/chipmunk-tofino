import unittest
from pathlib import Path
from unittest.mock import patch

import z3

from chipc import z3_utils


class ParseSmt2FileTest(unittest.TestCase):
    @patch('z3.parse_smt2_file', return_value=['1'])
    def test_success(self, mock_z3_parse_smt2_file):
        self.assertEqual('1', z3_utils.parse_smt2_file('foo'))

    def test_raise_assert_for_unexpected_inputs(self):
        with patch('z3.parse_smt2_file', return_value=[]):
            with self.assertRaisesRegex(AssertionError,
                                        '0 or more than 1 asserts'):
                z3_utils.parse_smt2_file('bar')
        with patch('z3.parse_smt2_file', return_value=['1', '2']):
            with self.assertRaises(AssertionError):
                z3_utils.parse_smt2_file('baz')


class NegatedBodyTest(unittest.TestCase):
    def test_forall(self):
        a, b = z3.Ints('a b')
        formula = z3.ForAll([a, b], a > b)

        self.assertEqual(z3.Not(a > b),
                         z3_utils.negated_body(formula))

    def test_variable_order(self):
        # Little more complex case, to see whether ordering of variables are
        # kept right.
        a, b, c = z3.Ints('a b c')
        formula = z3.ForAll([c, a, b], z3.And(b > a, a > c))

        self.assertEqual(z3.Not(z3.And(b > a, a > c)),
                         z3_utils.negated_body(formula))

    def test_raise_assert_non_quantifiers(self):
        a, b = z3.Bools('a b')
        formula = z3.Implies(a, b)
        with self.assertRaisesRegex(AssertionError, 'not a quantifier'):
            z3_utils.negated_body(formula)


class GenerateCounterexamplesTest(unittest.TestCase):
    def test_successs_with_mock(self):
        x = z3.Int('pkt_0_0_0_0')
        simple_formula = z3.ForAll([x], z3.And(x > 3, x < 2))
        pkt_fields, _ = z3_utils.generate_counterexamples(
            simple_formula)
        self.assertDictEqual(pkt_fields, {'pkt_0': 0})

    def test_unsat_formula(self):
        x = z3.Int('x')
        equality = z3.ForAll([x], x == x)
        pkt_fields, state_vars = z3_utils.generate_counterexamples(equality)
        self.assertDictEqual(pkt_fields, {})
        self.assertDictEqual(state_vars, {})

    def test_state_group_with_alphabets(self):
        x = z3.Int('state_group_1_state_0_b_b_0')
        simple_formula = z3.ForAll([x], z3.And(x > 3, x < 2))
        _, state_vars = z3_utils.generate_counterexamples(
            simple_formula)
        self.assertDictEqual(state_vars, {'state_group_1_state_0': 0})


class GetZ3FormulaTest(unittest.TestCase):
    def test_hello(self):
        base_path = Path(__file__).parent
        sketch_ir = Path(base_path / './data/hello.dag').resolve().read_text()
        formula_from_ir = z3_utils.get_z3_formula(sketch_ir, input_bits=2)
        ir_pkt_fields, ir_state_vars = z3_utils.generate_counterexamples(
            formula_from_ir)

        formula_from_smt = z3_utils.parse_smt2_file(
            str(Path(base_path / './data/hello.smt').resolve()))
        smt_pkt_fields, smt_state_vars = z3_utils.generate_counterexamples(
            formula_from_smt)

        self.assertDictEqual(ir_pkt_fields, smt_pkt_fields)
        self.assertDictEqual(ir_state_vars, smt_state_vars)

    def test_sampling(self):
        base_path = Path(__file__).parent
        sketch_ir = Path(
            base_path / './data/sampling.dag').resolve().read_text()
        formula_from_ir = z3_utils.get_z3_formula(sketch_ir, input_bits=2)
        ir_pkt_fields, ir_state_vars = z3_utils.generate_counterexamples(
            formula_from_ir)

        formula_from_smt = z3_utils.parse_smt2_file(
            str(Path(base_path / './data/sampling.smt').resolve()))
        smt_pkt_fields, smt_state_vars = z3_utils.generate_counterexamples(
            formula_from_smt)

        self.assertDictEqual(ir_pkt_fields, smt_pkt_fields)
        self.assertDictEqual(ir_state_vars, smt_state_vars)


class SimpleCheckTest(unittest.TestCase):
    def test_success(self):
        a = z3.Int('a')
        input_formula = z3.ForAll([a], z3.Implies(a > 0, a + 1 > a))
        with patch('z3.parse_smt2_file', return_value=[input_formula]):
            self.assertTrue(z3_utils.simple_check('foobar'))


if __name__ == '__main__':
    unittest.main()
