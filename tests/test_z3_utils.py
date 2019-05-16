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


class GenerateCounterExampleTest(unittest.TestCase):
    def test_successs_with_mock(self):
        x = z3.Int('pkt_0_0_0_0')
        simple_formula = z3.ForAll([x], z3.And(x > 3, x < 2))
        with patch('z3.parse_smt2_file', return_value=[simple_formula]):
            pkt_fields, _ = z3_utils.generate_counter_examples(
                'foobar')
            self.assertDictEqual(pkt_fields, {'pkt_0': 0})

    def test_with_real_file(self):
        test_filepath = Path(__file__).parent.joinpath(
            './data/counterexample.smt2').resolve()
        pkt_fields, state_vars = z3_utils.generate_counter_examples(
            str(test_filepath))
        self.assertDictEqual(pkt_fields, {'pkt_0': 0})
        self.assertDictEqual(state_vars, {'state_group_0_state_0': 13})

    def test_unsat_formula(self):
        x = z3.Int('x')
        equality = z3.ForAll([x], x == x)
        with patch('z3.parse_smt2_file', return_value=[equality]):
            pkt_fields, state_vars = z3_utils.generate_counter_examples('foo')
            self.assertDictEqual(pkt_fields, {})
            self.assertDictEqual(state_vars, {})

    def test_state_group_with_alphabets(self):
        x = z3.Int('state_group_1_state_0_b_b_0')
        simple_formula = z3.ForAll([x], z3.And(x > 3, x < 2))
        with patch('z3.parse_smt2_file', return_value=[simple_formula]):
            _, state_vars = z3_utils.generate_counter_examples(
                'foobar')
            self.assertDictEqual(state_vars, {'state_group_1_state_0': 0})


class SimpleCheckTest(unittest.TestCase):
    def test_success(self):
        a = z3.Int('a')
        input_formula = z3.ForAll([a], z3.Implies(a > 0, a + 1 > a))
        with patch('z3.parse_smt2_file', return_value=[input_formula]):
            self.assertTrue(z3_utils.simple_check('foobar'))
