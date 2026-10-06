"""Check the declared monetary basis before country cost calculations.

Labels in the input workbook are a reproducibility gate, not independent
verification of the source rates or their currency-conversion history.
"""


def validate_2019_usd_non_ppp(rows):
    """Require every cost row to declare USD, 2019 prices, and no PPP adjustment.

    The workbook needs one row per country with `currency`, `price_year`, and
    `ppp_adjusted` columns. Use Excel boolean FALSE for `ppp_adjusted`.
    Original rates in another currency or year must be converted upstream,
    using a documented market exchange rate and price index, before the run.
    """
    rows = list(rows)
    if not rows:
        raise ValueError('Cost workbook has no country rows')
    required = {'country', 'currency', 'price_year', 'ppp_adjusted'}
    for index, row in enumerate(rows, start=2):
        missing = required.difference(row)
        if missing:
            raise ValueError(f'Cost workbook row {index} lacks {sorted(missing)}')
        if not isinstance(row['currency'], str) or row['currency'].strip().upper() != 'USD':
            raise ValueError(f'Cost workbook row {index} is not declared in USD')
        year = row['price_year']
        if isinstance(year, bool) or year != 2019:
            raise ValueError(f'Cost workbook row {index} is not declared in 2019 prices')
        if row['ppp_adjusted'] is not False:
            raise ValueError(f'Cost workbook row {index} must declare ppp_adjusted as Excel FALSE')
