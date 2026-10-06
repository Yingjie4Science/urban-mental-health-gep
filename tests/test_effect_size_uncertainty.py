import unittest

from effect_size_uncertainty import (
    odds_ratio_to_risk_ratio,
    odds_ratios_for_case_interval,
)


class EffectSizeIntervalTests(unittest.TestCase):
    def test_depression_interval_reverses_for_case_outputs(self):
        ors = odds_ratios_for_case_interval(0.931, 0.887, 0.977)
        p0 = 0.115
        delta_ndvi = 0.2
        case_fractions = {
            name: 1 - odds_ratio_to_risk_ratio(or_value, p0) ** (10 * delta_ndvi)
            for name, or_value in ors.items()
        }
        self.assertLess(case_fractions['lower'], case_fractions['point'])
        self.assertLess(case_fractions['point'], case_fractions['upper'])

    def test_invalid_interval_is_rejected(self):
        with self.assertRaises(ValueError):
            odds_ratios_for_case_interval(0.931, 0.977, 0.887)


if __name__ == '__main__':
    unittest.main()
