# Global GEP Urban Mental Health Service

This repository estimates a depression-related, prevalence-based case-equivalent index associated with 2019 urban vegetation exposure and a built-up-like, zero-positive-NDVI counterfactual. It multiplies the index by country cost-per-case inputs for a cost-weighted output. The calculation follows an InVEST-style design but uses the Python pipeline in this repository. The current case-count interpretation, adult prevalence denominator, and cost scope require review before the output is presented as people with depression avoided or as avoided societal cost.

## Status and evidence boundary

This fork-ready update adds conditional 95% effect-size bounds and a run manifest. The public repository does not include the rasters, lookup table, effect-size workbook, urban polygons, cost workbook, or completed outputs. The numerical results and full geospatial run have therefore not been validated here. The fixed default prevalence parameters are documented assumptions rather than locally measured rates.

## Workflow

1. Nearest-neighbor warp 2019 GLC_FCS30D land cover (approximately 30 m) to the 2019 WorldPop population grid (approximately 100 m).
2. Assign NDVI to each land-cover code from `glc_fcs30d_attribute_table_processed.csv`. This code does not calculate Landsat NDVI or a residential buffer average.
3. Set every positive mapped NDVI value to zero for a built-up-like exposure counterfactual. Zero and negative values remain unchanged; land-cover codes do not change.
4. Calculate `delta_NDVI = baseline_NDVI - counterfactual_NDVI`.
5. Convert the Liu et al. (2023) depression odds ratio per +0.1 NDVI to a risk ratio using `RR = OR / (1 - p0 + p0 * OR)`; then calculate the current prevalence-based case-equivalent index per pixel.
6. Sum pixel outputs within supplied urban polygons, then apply matched country cost-per-case rates. Countries with no matching cost row are excluded.

The runner uses `baseline_prevalence = 0.05` and `p0 = 0.115` by default. **They have different roles.** The 0.05 value approximates a [WHO adult depression prevalence](https://www.who.int/key-messages), while the configured WorldPop raster includes all ages. This denominator mismatch must be resolved for interpretable case counts. The 0.115 value is the health-record depression diagnosis proportion for the lowest residential-NDVI quartile in Table 1 of [Hystad et al. (2019)](https://pubmed.ncbi.nlm.nih.gov/33778335/), a Quebec adult cohort. Perry is the first author's given name. This is a proxy for the least-green reference population in the OR-to-RR conversion, not global prevalence. The conversion follows [Zhang and Yu (1998)](https://doi.org/10.1001/jama.280.19.1690).

## Reproduce a run

Create the environment from `environment.yml` and provide the six external inputs at the paths below, relative to `--base-data-dir`:

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
  --project-dir /path/to/new_run
```

Use `--baseline-prevalence` and `--p0` to run documented alternatives. The first parameter should match the age range and outcome definition of the population raster; the second should represent the least-green reference group for the OR. The default output directory is timestamped. Earlier land-cover and NDVI tasks still skip existing files, so a fresh directory is needed when inputs change.

After successful execution, `run_manifest.json` records parameter values and provenance notes, the Git commit when available, Python version, and SHA-256 checksums of inputs, source files, and key outputs. Hashing large rasters adds I/O time. The manifest is local output and should be reviewed for machine paths before any publication.

## Conditional 95% effect-size limits

The pipeline writes the point raster plus `effect_ci_lower` and `effect_ci_upper` rasters and matching urban-region and country-cost CSVs. It propagates the two reported OR limits through the same OR-to-RR conversion and model formula. For this code's nonnegative exposure change, a lower OR produces a larger case-equivalent estimate. Therefore, the lower output limit uses the **upper OR limit**, and the upper output limit uses the **lower OR limit**. Direct endpoint transformation gives the conditional bounds for one shared monotone effect parameter; sampling that parameter by Monte Carlo would converge to the same result.

The interval holds p0, baseline prevalence, land-cover-derived NDVI, population, and cost rates fixed. It does not cover their uncertainty, the substantial heterogeneity of the source literature, or the assumptions needed for a causal interpretation. Fractional region estimates are retained through country aggregation; values are rounded only in final country CSV presentation.

## Review gates

Before reporting case or monetary values, verify the adult-versus-all-age prevalence denominator, the exact dated source for the 0.05 rate, transportability and sensitivity of the Quebec p0 proxy, land-cover-to-NDVI lookup provenance, polygon feature-ID mapping, cost scope, each rate's 2019 USD non-PPP provenance, and the reference-state meaning of the case formula. These checks require the unpublished input files and a completed run.
