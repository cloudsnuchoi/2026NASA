"""Regression checks for missing output and incompatible validation data."""
import importlib.util
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
spec = importlib.util.spec_from_file_location('matlab_validate', Path(__file__).resolve().parents[1] / 'matlab_validate.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ValidationTests(unittest.TestCase):
    def test_missing_and_nonfinite_are_not_validated(self):
        for value in ('', 'NaN', 'inf', None):
            self.assertIsNone(module.finite(value))
        self.assertIn('not validated', module.paired([], {('a',): 1}, 'value', ('id',)))

    def test_missing_duplicate_and_unknown_keys_do_not_pass(self):
        rows = [{'id': 'a', 'value': '3'}, {'id': 'a', 'value': '9'}, {'id': 'b', 'value': '0'}]
        result = module.paired(rows, {('a',): 1, ('c',): 4}, 'value', ('id',))
        self.assertIn('1/2', result)
        self.assertIn('MAE 2.000', result)
        self.assertIn('제외 2건', result)


if __name__ == '__main__':
    unittest.main()
