#!/usr/bin/env python3

import sys, os
sys.path.insert(1, os.path.dirname(os.path.realpath(__file__)) + '/../task')

import unittest
import re
from RequestParser

class ExpressionTestCase(unittest.TestCase):
    """ Tests for 'Expression.py'. """
    
    def test_entire_module_for_syntax_errors_or_something(self):
        import Expression
    
    def test_init(self):
        # 1. Randomly generated expression
        result = Expression()
        pattern = re.compile(
            r"""^
                -?    # 0 or 1 negative signs
                (
                    # monomial (constant, variables, or coefficient/variables)
                    \d+    # constant
                    | ( \(? [a-zA-Z]+ (\^\d+)? \)? )+
                           # variables w/ no coefficient
                    | \d+ ( \(? [a-zA-Z]+ (\^\d+)? \)? )+
                           # coefficient and variables
                )
                (
                    # 0 or more instances of ( +/- monomial)
                    \s* ( \+ | - ) \s*    # plus or minus
                    (
                        \d+
                        | ( \(? [a-zA-Z]+ (\^\d+)? \)? )+
                        | \d+ ( \(? [a-zA-Z]+(\^\d+)? \)? )+
                    )
                )*
                $""",
            re.X)
        self.assertRegex(
            str(result), pattern,
            "\nThe output does not match the expected regex: " + str(result))
        
        # 2. User-generated expression 1
        result = Expression("3x + 1 - y")
        self.assertEqual(str(result), "3x - y + 1")
        
        # 3. User-generated expression 2
        # TODO: Make 6wx turn into 6xw
        result = Expression("-5(y^2)(x^3) + -6wx")
        self.assertEqual(str(result), "-5(x^3)(y^2) - 6wx")
        
        # 4. User-generated expression 2
        result = Expression("5x + 6x + 2y")
        self.assertEqual(str(result), "11x + 2y")
    
    def test_multiplication(self):
        # 1. Positive integer; positive, degree 1 variable
        result = Expression("3x - 6y + 1") * 5
        self.assertEqual(str(result), "15x - 30y + 5")
        
        # 2. Negative integer; positive, degree 2 variable
        result = -1 * Expression("-6x + -5(y^2)x")
        self.assertEqual(str(result), "5x(y^2) + 6x")
        
        # 3. Fraction; negative, degree 1 variable
        result = Expression("-4x + 6") / 2
        self.assertEqual(str(result), "-2x + 3")
        
        # 4. Monomial
        result = Expression("4x + 1") * Monomial("-5y")
        self.assertEqual(str(result), "-20xy - 5y")
        self.assertIsInstance(result, Expression)
        
        # 5. Expression
        result = Expression("4x + 1") * Expression("-5x - 2")
        self.assertEqual(str(result), "-20x^2 - 13x - 2")
        self.assertIsInstance(result, Expression)
        
        # 4. Flooring division
        result = Expression("y - 10") / "2"
        self.assertEqual(str(result), "(1/2)y - 5")
    
    def test_addition(self):
        # 1. Positive number
        result = 5 + Expression("3x - 6")
        self.assertEqual(str(result), "3x - 1")
        self.assertIsInstance(result, Expression)
        
        # 2. Negative number
        result = Expression("6y + x - 7") - 1
        self.assertEqual(str(result), "x + 6y - 8")
        self.assertIsInstance(result, Expression)
        
        # 3. Expression of same variable
        result = Expression("4x + 1") + Expression("-5x + 1")
        self.assertEqual(str(result), "-x + 2")
        self.assertIsInstance(result, Expression)
        
        # 4. Expression of different variable
        result = Expression("4x - 5w") - Expression("5y + 10z")
        self.assertEqual(str(result), "4x - 5y - 10z - 5w")
        self.assertIsInstance(result, Expression)
    
    def test_evaluation(self):
        # 1. Degree 1, two variables
        result = Expression("3x + y - 1").evaluate({'x': 2, 'y': 20})
        self.assertEqual(str(result), "25")
        
        # 2. Degree 2, one variable
        result = Expression("6y^2 - 2").evaluate({'y': 3})
        self.assertEqual(str(result), "52")
        
        # 3. Not enough inputs
        result = Expression("3x + y - 1").evaluate({'y': 3})
        self.assertEqual(str(result), "3x + 2")


if __name__ == '__main__':
    unittest.main()
