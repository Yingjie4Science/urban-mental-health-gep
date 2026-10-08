# Liu et al. (2023) NDVI depression extraction and `p0` synthesis audit

8 October 2026. This audit uses Liu's main article, the author-supplied supplementary Word file, and original study reports. The row-level extraction is in [`liu_2023_ndvi_study_extraction.csv`](liu_2023_ndvi_study_extraction.csv). It is an evidence review; it does not change the model or rerun outputs.

## What the two Liu files establish

Liu et al. state that **nine studies** with **267,744 participants** were included in the NDVI/depression meta-analysis and report a pooled OR of **0.931 (95% CI 0.887–0.977)** per 0.1 NDVI, with **I²=94.4%**. Figure 4 contains **13 estimates**, because Hystad contributes three depression outcomes, Abraham Cottagiri contributes two, and Gonzales-Inca contributes two.

The supplementary file adds the covariate audit, leave-one-out analysis, subgroup results, and funnel plot. Its Table S4 rows are **the pooled OR after removing each listed estimate**, not the omitted study's individual effect. The study-specific standardized effects must therefore be transcribed from Figure 4, as done in the CSV.

## Reconciliation problems that affect use in this project

1. **Non-independent rows.** Thirteen forest rows come from nine named studies, with repeated outcomes from the same participants. Treating all rows as independent gives cohorts with multiple outcomes extra influence and understates dependence.
2. **Outcome mixing.** The forest combines symptom screens, claims or clinical diagnosis, self-reported past diagnosis, lifetime probable MDD, and incident symptoms. Those outcomes have different case probabilities and time windows, so a single common `p0` is not identifiable from the synthesis.
3. **Exposure mixing.** Most effects are standardized to 0.1 NDVI, but Song begins with a quartile contrast. One Gonzales row is described in Liu Table 1 as a contrast in total residential green-space percentage, yet appears in the NDVI forest.
4. **Study-label error.** Liu calls the Canadian CARTaGENE study “Perry 2019”; the source is Hystad et al. (2019).
5. **Sample-size errors.** Liu prints Brown's sample as 24,905; the original study contains 249,405 Medicare beneficiaries. The nine sample sizes printed in Liu Table 1 sum to 275,745, not 267,744. Excluding Gonzales yields 267,774, only 30 above Liu's stated total, suggesting that the stated total may omit Gonzales and also contain a small arithmetic or transcription error.
6. **Gonzales mapping is unresolved.** The original paper selected 14,424 urban participants and reports different analytic samples after exclusions. Liu lists 7,971 and labels two rows as BDI, while the original paper distinguishes BDI and doctor-diagnosed depression. Exact row-to-model mapping should be confirmed before reuse.
7. **High heterogeneity and publication bias.** Liu reports I² above 94% and an asymmetric funnel plot. A pooled point estimate should not be treated as a universally transportable causal effect.

## What was recoverable for `p0`

`p0` must be the outcome probability in the reference exposure group for the same effect estimate. The extraction found no fully paired low-exposure `p0` for any of the 13 rows.

- **Hystad:** 9.6% in the least-green 250 m quartile for self-reported doctor-diagnosed depression matches the outcome of the 0.85 OR but not its 500 m exposure buffer. The 11.5% value matches the 500 m least-green quartile but is a health-record diagnosis rather than the self-reported outcome.
- **Brown/Perrino:** Brown's cohort has 9.25% depression overall. A later analysis of the same Medicare cohort reports 12.44% in the lowest NDVI tertile, but that tertile spans −0.40 to −0.06 and does not match Brown's continuous per-0.1 effect or the model's NDVI=0 counterfactual.
- **Abraham Cottagiri:** overall prevalence is 15.96% for CES-D-10 screen-positive symptoms and 16.40% for past clinical diagnosis, but exposure-specific risks were not reported.
- **Sarkar:** 25.66% is the whole-sample lifetime probable-MDD prevalence, not a low-NDVI risk.
- **Bezold:** 11.06% is the whole-sample adolescent high-symptom proportion, driven by an approximately top-decile case definition.
- **Tomita:** 15.9% and 20.8% are incident symptom proportions at waves 2 and 3 in a baseline-free cohort. They are not low-NDVI probabilities, and the original effect is modified by income.
- **Gonzales-Inca:** roughly 4% BDI prevalence and 12% doctor-diagnosed prevalence demonstrate outcome sensitivity but are whole-sample values.
- **Song and Niu:** no low-exposure binary cases and denominators were recovered from the accessible article and supplement material.

Whole-sample prevalence is useful for plausibility checks but cannot be substituted for `p0` in the OR-to-RR conversion.

## Decision and feasible synthesis path

### Current model

Keep `p0=0.115` as a **legacy Hystad health-record scenario**, not as a validated global parameter. Keep `p0=0.096` as a separate Hystad self-report scenario. Retain the broader 0.03–0.20 structural sensitivity range. Do not use the Liu pooled OR with an average of the whole-sample prevalences above, and do not describe the resulting interval as a 95% confidence interval.

The expanded evidence does not justify replacing 0.115 with another single globally valid value. It does strengthen the explanation that values around 0.10–0.12 are empirically anchored in one low-exposure adult cohort and are numerically consistent with several whole-sample symptom or claims estimates, while still being endpoint-specific and geographically limited.

### Stronger reanalysis

1. Choose one outcome per independent cohort before pooling. Prespecify outcome strata: current symptom screen, clinical or claims diagnosis, lifetime diagnosis, and incident symptoms.
2. Retain only effects with a clear 0.1 NDVI contrast and a compatible population. Resolve the Gonzales row and exclude any percent-green-space effect from an NDVI synthesis.
3. Obtain the low-exposure cases and denominators, exposure bounds, or covariate-standardized probabilities for the same model row. Convert each study's OR using its own `p0`; propagate uncertainty in both quantities.
4. Pool comparable log RRs with a random-effects model and robust variance or a multilevel structure for multiple outcomes from a cohort. Report a prediction interval and leave-one-cohort-out analysis.
5. Keep country GBD prevalence for baseline cases separate. Country marginal prevalence does not identify the low-NDVI reference risk, though it can calibrate or check model-wide marginal predictions.

## Files or data still useful

No additional Liu file is needed. The highest-value missing information is narrow:

1. Abraham Cottagiri study supplement or author-provided counts by NDVI category for the two depression outcomes.
2. Song study counts and denominators for CES-D≥16 in each NDVI quartile.
3. Niu study's dichotomous PHQ-2 supplementary model, including case definition and low-exposure counts.
4. Gonzales-Inca Appendix Table A2 or author clarification that maps Liu's two forest rows to outcome, exposure metric, follow-up, and analytic sample.
5. If feasible, author-supplied marginal standardized risks at NDVI 0 and observed reference values for Hystad, Brown, Abraham Cottagiri, Sarkar, Song, and Niu.

These are author or restricted-data requests rather than prerequisites for keeping the current scenario analysis transparent.

## Source links

- Liu et al. 2023: <https://pubmed.ncbi.nlm.nih.gov/37268208/>
- Hystad et al. 2019: <https://pmc.ncbi.nlm.nih.gov/articles/PMC7952103/>
- Brown et al. 2018: <https://pmc.ncbi.nlm.nih.gov/articles/PMC5876975/>
- Abraham Cottagiri et al. 2022: <https://pubmed.ncbi.nlm.nih.gov/34951990/>
- Sarkar et al. 2018: <https://pubmed.ncbi.nlm.nih.gov/29615217/>
- Bezold et al. 2018: <https://pubmed.ncbi.nlm.nih.gov/29273301/>
- Tomita et al. 2017: <https://pubmed.ncbi.nlm.nih.gov/28890948/>
- Gonzales-Inca et al. 2022: <https://pubmed.ncbi.nlm.nih.gov/35134742/>
- Di et al. 2020: <https://pmc.ncbi.nlm.nih.gov/articles/PMC8454668/>
- Song et al. 2019: <https://pmc.ncbi.nlm.nih.gov/articles/PMC6352234/>
