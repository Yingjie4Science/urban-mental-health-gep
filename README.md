# Global GEP Urban Mental Health Service

This repository estimates additional depression-related cases under a built-up-like, zero-positive-NDVI counterfactual relative to estimated observed 2019 cases. It uses 2019 country-specific, all-age GBD depressive-disorders prevalence with 2019 all-age WorldPop. The resulting cases and costs are conditional model estimates, not observed avoided diagnoses or validated societal savings.

## Status and evidence boundary

The country-prevalence workflow and observed-case formula are implemented, with conditional 95% effect-size bounds and a run manifest. The public repository does not include the rasters, lookup table, effect-size workbook, urban polygons, cost workbook, or completed outputs. The numerical results, spatial joins, cost basis and full geospatial run are therefore unvalidated. The default `p0 = 0.115` remains a transported assumption.

## Workflow

1. Nearest-neighbor warp 2019 GLC_FCS30D land cover (approximately 30 m) to the 2019 WorldPop population grid (approximately 100 m).
2. Assign NDVI to each land-cover code from `glc_fcs30d_attribute_table_processed.csv`. This code does not calculate Landsat NDVI or a residential buffer average.
3. Set every positive mapped NDVI value to zero for a built-up-like exposure counterfactual. Zero and negative values remain unchanged; land-cover codes do not change.
4. Calculate `delta_NDVI = baseline_NDVI - counterfactual_NDVI`.
5. Convert the Liu et al. (2023) depression odds ratio per +0.1 NDVI to an approximate risk ratio using `RR = OR / (1 - p0 + p0 * OR)`. Compute a pixel **case factor at prevalence 1** as `population × (RR^(-10 × delta_NDVI) - 1)`. This treats 2019 prevalence-derived cases as the observed reference state.
6. Sum case factors within urban polygons and multiply each polygon by its matched country 2019 GBD depressive-disorders prevalence. Sum regional cases by country and apply matched 2019 USD non-PPP cost-per-case rates. Unmatched prevalence or cost countries stop the run.

The agreed primary workflow requires `--country-prevalence-table` pointing to the validated 204-location CSV documented in the local `gep-global/depression_prevalence_review` folder. The table must have `location_id`, `country_as_gbd`, `year = 2019`, `prevalence_fraction`, and `gbd_release = GBD 2023`. Exact polygon-country/GBD-name matches are used by default. A reviewed crosswalk CSV (`polygon_country,gbd_location_id`) can resolve differences; missing matches fail. The historical 0.05 WHO adult proxy is available only via explicit `--baseline-prevalence 0.05` sensitivity run, not the primary default.

The separate default `p0 = 0.115` is the health-record diagnosis proportion for the lowest residential-NDVI quartile in Table 1 of [Hystad et al. (2019)](https://pubmed.ncbi.nlm.nih.gov/33778335/), a Quebec adult cohort. It is not a GBD country prevalence or measured zero-NDVI risk. [Zhang and Yu (1998)](https://doi.org/10.1001/jama.280.19.1690) give the approximate OR-to-RR conversion. The model's cost and case interpretations still depend on outcome/effect compatibility and data validation.

## Reproduce a run

Create the environment from `environment.yml` and provide the six external spatial, effect and cost inputs at the paths below, relative to `--base-data-dir`:

| Input | Expected path |
| --- | --- |
| 2019 WorldPop mosaic | `worldpop/100m_2019_global-mosaic.tif` |
| Land-cover NDVI lookup | `glc_fcs30d_attribute_table_processed.csv` |
| Effect sizes | `effect_size.xlsx` |
| Urban polygons | `urban_boundaries_2019.gpkg` |
| Cost per case | `treatment_cost.xlsx` |
| 2019 GLC_FCS30D land cover | `../../lulc/glc_fcs30d/lulc_glc_fcs30d_2019.tif` |

The effect-size workbook must have exactly one `health_indicator = depression` row with numeric `effect_size`, `ci_lower`, and `ci_upper` columns. These must be an OR and its 95% confidence limits per +0.1 NDVI. The published Liu et al. (2023) example is 0.931 (0.887–0.977).

The cost workbook must have one row per country with `country`, nonnegative `cost_per_case`, `currency = USD`, `price_year = 2019`, and `ppp_adjusted = FALSE` (an Excel boolean). The script stops if any row lacks this declaration and labels its output `cost_savings_2019_usd`. **These declarations are not proof of the rates' basis.** For each source rate, retain a citation and its original currency and price year. If conversion is needed, document the market exchange rate and inflation index used to express it in 2019 USD; do not use PPP conversion factors. The public repository lacks `treatment_cost.xlsx`, so its current rates and conversion history remain unverified.

Run from this directory with a fresh output directory:

```bash
python run_urban_mental_health.py \
  --base-data-dir /path/to/urban_mental_health_inputs \
  --country-prevalence-table /path/to/gbd_2023_2019_depressive_disorders_country_prevalence.csv \
  --project-dir /path/to/new_run
```

Omit `--country-crosswalk` only if every polygon country label exactly matches the GBD table. Use `--baseline-prevalence` for an explicitly labelled scalar sensitivity run **instead of** the country table; use `--p0` for a reference-risk sensitivity run. `p0` should correspond to the least-green reference group for the OR. The default output directory is timestamped. Earlier land-cover and NDVI tasks still skip existing files, so a fresh directory is needed when inputs change.

After successful execution, `run_manifest.json` records parameter values and provenance notes, the Git commit when available, Python version, and SHA-256 checksums of inputs, source files, and key outputs. Hashing large rasters adds I/O time. The manifest is local output and should be reviewed for machine paths before any publication.

## Conditional 95% effect-size limits

The pipeline writes point and effect-limit **case-factor** rasters (each at prevalence 1) and matching urban-region case and country-cost CSVs. It propagates the two reported OR limits through the same OR-to-RR conversion and model formula. For this code's nonnegative exposure change, a lower OR produces a larger case-equivalent estimate. Therefore, the lower output limit uses the **upper OR limit**, and the upper output limit uses the **lower OR limit**. Direct endpoint transformation gives the conditional bounds for one shared monotone effect parameter; sampling that parameter by Monte Carlo would converge to the same result.

The interval holds p0, baseline prevalence, land-cover-derived NDVI, population, and cost rates fixed. It does not cover their uncertainty, the substantial heterogeneity of the source literature, or the assumptions needed for a causal interpretation. Fractional region estimates are retained through country aggregation; values are rounded only in final country CSV presentation.

## Review gates

Before reporting case or monetary values, verify the GBD-country/polygon join and outcome match, transportability and sensitivity of the Quebec p0 proxy, land-cover-to-NDVI lookup provenance, polygon feature-ID mapping, cost scope, each rate's 2019 USD non-PPP provenance, and the observed-case reference-state assumption. These checks require the unpublished input files and a completed run.
