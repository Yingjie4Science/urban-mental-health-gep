"""Check the country join and observed-case reference calculation."""

import csv
from pathlib import Path
import tempfile
import unittest

from effect_size_uncertainty import additional_cases_from_observed, odds_ratio_to_risk_ratio
from prevalence_inputs import resolve_country_rates


class CountryPrevalenceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.table = Path(self.tmp.name) / 'gbd.csv'
        with self.table.open('w', newline='') as stream:
            writer = csv.writer(stream)
            writer.writerow(['location_id', 'country_as_gbd', 'year',
                             'prevalence_fraction', 'gbd_release'])
            writer.writerow(['160', 'Afghanistan', '2019', '0.0324', 'GBD 2023'])
            writer.writerow(['139', 'Algeria', '2019', '0.0388', 'GBD 2023'])

    def test_exact_match_and_explicit_crosswalk(self):
        crosswalk = Path(self.tmp.name) / 'crosswalk.csv'
        crosswalk.write_text('polygon_country,gbd_location_id\nAlgerian Republic,139\n')
        rates = resolve_country_rates(['Afghanistan', 'Algerian Republic'],
                                      self.table, crosswalk)
        self.assertEqual(rates, {'Afghanistan': 0.0324, 'Algerian Republic': 0.0388})

    def test_unmatched_country_fails(self):
        with self.assertRaisesRegex(ValueError, 'Unmatched polygon countries'):
            resolve_country_rates(['Unknown'], self.table)

    def test_wrong_estimate_year_fails(self):
        self.table.write_text(self.table.read_text().replace('2019', '2020'))
        with self.assertRaisesRegex(ValueError, 'year 2019'):
            resolve_country_rates(['Afghanistan'], self.table)


class ObservedCaseReferenceTest(unittest.TestCase):
    def test_counterfactual_difference(self):
        rr = odds_ratio_to_risk_ratio(0.931, 0.115)
        observed_cases = 100.0
        added = additional_cases_from_observed(observed_cases, rr, 0.1)
        self.assertAlmostEqual(added, observed_cases / rr - observed_cases)
        self.assertGreater(added, 0)
        self.assertEqual(additional_cases_from_observed(observed_cases, rr, 0), 0)

    def test_effect_interval_direction(self):
        lower_or = odds_ratio_to_risk_ratio(0.887, 0.115)
        upper_or = odds_ratio_to_risk_ratio(0.977, 0.115)
        self.assertGreater(additional_cases_from_observed(100, lower_or, 0.1),
                           additional_cases_from_observed(100, upper_or, 0.1))


if __name__ == '__main__':
    unittest.main()
