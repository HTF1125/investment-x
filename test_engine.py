
import unittest
import pandas as pd
from ix.engine import execute_source_code

class TestEngine(unittest.TestCase):

    def test_execute_source_code(self):
        # Test a simple case
        source_code = "Series('SPY US EQUITY:PX_LAST')"
        result = execute_source_code(source_code)
        self.assertIsInstance(result, pd.Series)

        # Test a more complex case
        source_code = "MovingAverage(Series('SPY US EQUITY:PX_LAST'), window=10)"
        result = execute_source_code(source_code)
        self.assertIsInstance(result, pd.Series)

        # Test an invalid function
        source_code = "some_invalid_function()"
        result = execute_source_code(source_code)
        self.assertIsNone(result)

if __name__ == '__main__':
    unittest.main()
