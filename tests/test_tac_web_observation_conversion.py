from __future__ import annotations
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import convert_tac_web_observations as converter


class DirectWebObservationConversionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.input_validator, cls.output_validator = converter.validators()

    def test_self_test_suite(self):
        converter.self_test(self.input_validator, self.output_validator)


if __name__ == "__main__":
    unittest.main()
