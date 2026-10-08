"""Pure calculations for effect-size uncertainty propagation."""

import math


def odds_ratio_to_risk_ratio(odds_ratio, p0):
    """Zhang-Yu OR-to-RR conversion using least-green reference prevalence p0.

    For the default global run p0=0.115 comes from Hystad et al. (2019),
    Table 1, Quebec health-record depression diagnosis in the lowest NDVI
    quartile. It is distinct from country-wide baseline prevalence for cases.
    """
    if not math.isfinite(odds_ratio) or odds_ratio <= 0:
        raise ValueError("Odds ratio must be finite and positive")
    if not math.isfinite(p0) or not 0 <= p0 < 1:
        raise ValueError("p0 must be a probability in [0, 1)")
    return odds_ratio / (1 - p0 + p0 * odds_ratio)


def additional_cases_from_observed(observed_cases, risk_ratio, delta_ndvi):
    """No-vegetation cases minus observed cases for an observed-case baseline.

    delta_ndvi is observed minus counterfactual NDVI; RR is per +0.1 NDVI.
    This expression also supports NumPy arrays at the raster calculation site.
    """
    if not math.isfinite(risk_ratio) or risk_ratio <= 0:
        raise ValueError('Risk ratio must be finite and positive')
    return observed_cases * (risk_ratio ** (-10 * delta_ndvi) - 1)


def odds_ratios_for_case_interval(effect_size, ci_lower, ci_upper):
    """Map an OR interval to point/lower/upper case outputs for ΔNDVI >= 0."""
    values = (effect_size, ci_lower, ci_upper)
    if not all(math.isfinite(v) and v > 0 for v in values):
        raise ValueError("OR and confidence limits must be finite and positive")
    if not ci_lower <= effect_size <= ci_upper:
        raise ValueError("OR must lie within its confidence interval")
    return {'point': effect_size, 'lower': ci_upper, 'upper': ci_lower}
