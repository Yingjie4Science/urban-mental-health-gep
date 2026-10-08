# Urban mental health model: decisions and open work

Updated 8 October 2026.

This record separates implemented behavior, accepted modelling decisions, evidence limitations, and work that still requires unpublished inputs. It should be read with the main [README](../README.md) and the [Liu NDVI evidence audit](evidence/liu_2023_ndvi_p0_review.md).

## Implemented and retained

1. **Baseline prevalence:** the primary workflow accepts country-specific 2019, both-sex, crude all-age prevalence of depressive disorders from the GBD 2023 release. This matches the all-age 2019 WorldPop denominator. The historical fixed 5% adult prevalence is retained only as an explicitly selected sensitivity value.
2. **Reference state for cases:** the model treats prevalence-derived 2019 cases as the observed state and estimates additional cases under the counterfactual exposure.
3. **Exposure counterfactual:** positive land-cover-assigned NDVI values are set to zero. Zero and negative values remain unchanged. This approximates a built-up-like exposure state; it does not relabel land-cover classes.
4. **Effect uncertainty:** the published OR confidence limits are propagated through the OR-to-RR conversion and case calculation. The resulting limits are conditional on fixed prevalence, `p0`, exposure, population, and costs.
5. **Cost metadata:** cost inputs must declare USD, price year 2019, and no PPP adjustment. These declarations are validation gates rather than proof of source provenance.

## `p0` decision

`p0` is the depression probability in the effect study's low-exposure reference group. It is used only to approximate an RR from an OR and must remain separate from country GBD prevalence used for baseline cases.

- Keep `p0 = 0.115` as the labelled legacy scenario. It comes from health-record depression diagnoses in Hystad et al.'s least-green 500 m quartile.
- Keep `p0 = 0.096` as a separate Hystad self-reported doctor-diagnosis scenario. It matches the outcome more closely but was reported for a 250 m exposure grouping rather than the 500 m effect.
- Retain `0.03–0.20` as a structural sensitivity range. It is not a 95% confidence interval.
- Do not replace `p0` with a country prevalence, a whole-sample study prevalence, or an average across incompatible outcomes.
- Do not pool study `p0` values and then apply that pooled value to Liu's pooled OR.

The current evidence does not identify a single globally valid reference risk. Values around 0.10–0.12 are empirically anchored in one low-exposure adult cohort and are broadly plausible against several whole-sample studies, but they remain endpoint-specific and geographically limited.

## Liu et al. (2023) evidence decision

Liu reports a pooled OR of 0.931 (95% CI 0.887–0.977) per 0.1 NDVI with I² above 94%. The review names nine studies but Figure 4 contains 13 estimates because three cohorts contribute multiple outcomes.

The extraction identified mixed symptom, clinical, claims, lifetime, and incident outcomes; repeated cohorts; a Hystad/Perry label error; a Brown sample-size typo; a participant-total mismatch; and an unresolved Gonzales exposure/outcome mapping. The supplementary Table S4 gives leave-one-estimate-out pooled ORs, not individual study effects. These limitations preclude interpreting the pooled OR as a universally transportable causal effect.

For any stronger synthesis:

1. Select one compatible outcome per independent cohort or use a model that accounts for correlated outcomes.
2. Retain only clearly mapped NDVI contrasts and resolve the Gonzales rows.
3. Obtain cases and denominators in the matching low-exposure group, or author-provided marginal standardized risks.
4. Convert each study-specific OR with its own matched `p0`.
5. Pool comparable log RRs using random effects with robust variance or a multilevel model, and report heterogeneity and a prediction interval.

## Open work

### Can proceed when source information is obtained

- Obtain Abraham Cottagiri depression counts by NDVI category.
- Obtain Song CES-D cases and denominators by NDVI quartile.
- Obtain Niu's dichotomous PHQ-2 supplementary model and low-exposure counts.
- Resolve Gonzales-Inca Appendix Table A2/model-to-forest mapping.
- Seek marginal standardized risks near NDVI zero from study authors where feasible.
- Audit every cost rate's source, original currency, original price year, market exchange-rate conversion, and inflation conversion to 2019 USD without PPP.

### Requires unpublished model inputs

- Validate country and polygon joins, urban feature identifiers, raster alignment, water treatment, NDVI lookup coverage, and country totals.
- Run the complete pipeline in a fresh output directory and inspect the run manifest and rendered/tabular outputs.
- Compare reported results with the validated run before making case or monetary claims.

## Reporting language

Describe results as conditional model estimates of additional depression-related cases and associated 2019 USD costs under a zero-positive-NDVI counterfactual. Do not describe them as observed diagnoses, validated causal effects, comprehensive uncertainty intervals, or verified societal savings until the corresponding evidence and input checks are complete.
