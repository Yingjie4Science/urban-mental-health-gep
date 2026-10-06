import unittest

from cost_basis import validate_2019_usd_non_ppp


class CostBasisTests(unittest.TestCase):
    def test_accepts_explicit_2019_usd_without_ppp(self):
        validate_2019_usd_non_ppp([{
            'country': 'Example', 'currency': 'USD',
            'price_year': 2019, 'ppp_adjusted': False,
        }])

    def test_rejects_other_bases(self):
        base = {'country': 'Example', 'currency': 'USD',
                'price_year': 2019, 'ppp_adjusted': False}
        for change in ({'currency': 'EUR'}, {'price_year': 2020},
                       {'ppp_adjusted': True}, {'ppp_adjusted': 'FALSE'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_2019_usd_non_ppp([{**base, **change}])


if __name__ == '__main__':
    unittest.main()
