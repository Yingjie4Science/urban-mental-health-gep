# Global GEP — Urban Mental Health Service

Estimates preventable depression cases (and their avoided societal cost) attributable
to urban nature exposure, following the InVEST-style Urban Mental Health design doc
(v0.3.0, Yingjie Li). Compares 2019 land-use NDVI-based nature exposure against a
counterfactual no-vegetation scenario, applies a dose-response relative-risk model,
and aggregates results by urban region and country.

## Pipeline
1. Resample/warp LULC (GLC_FCS30D 30m) onto the population (WorldPop 100m) grid.
2. Convert LULC to NDVI via a land-cover attribute table.
3. Build a no-vegetation counterfactual NDVI scenario.
4. Compute Δ nature exposure (baseline − no-vegetation).
5. Compute preventable depression cases per pixel (population, prevalence, effect size).
6. Aggregate preventable cases by urban region (zonal statistics).
7. Apply country-specific cost-per-case rates for avoided-cost estimates.

## Data (not tracked in this repo — see `.gitignore`)
- WorldPop 100m population raster.
- GLC_FCS30D land-cover raster + `glc_fcs30d_attribute_table_processed.csv`.
- GUPPD urban boundary polygons.
- `effect_size.xlsx` (dose-response effect sizes, Liu et al. 2023).
- Country-level treatment cost table.