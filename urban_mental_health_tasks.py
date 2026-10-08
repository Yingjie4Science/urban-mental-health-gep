import os
import numpy as np
import rasterio
import urban_mental_health_functions
import effect_size_uncertainty


def task_warp_lulc_to_population(p):
    """
    #Downsample ESA CCI LULC 300m data to match WorldPop 1km grid.
    Downsample ESA CCI LULC 30m data to match WorldPop 100m grid.
    """
    
    #print(f"Reference reprojected population raster path for input: {p.population_2019_path}")
    p.lulc_reprojected_and_resampled_baseline_path = os.path.join(p.project_dir, "lulc_2019_reprojected_and_resampled.tif")

    # Resample baseline LULC
    urban_mental_health_functions.warp_raster_to_reference(
        input_path=p.base_year_lulc_path,
        reference_path=p.population_2019_path,
        out_path=p.lulc_reprojected_and_resampled_baseline_path,
        resampling_method='near',  # to preserve categorical values
        compress="lzw"
    )
    print(f"Finished resampling baseline LULC to population grid: {p.lulc_reprojected_and_resampled_baseline_path}")

    return p.lulc_reprojected_and_resampled_baseline_path


def task_convert_lulc_to_ndvi_baseline(p):
    """
    Task to convert baseline LULC (2019) to NDVI using processed attribute table.
    """

    p.ndvi_baseline_path = os.path.join(p.project_dir, 'ndvi_2019.tif')

    # Use resampled LULC
    #lulc_path = getattr(p, 'lulc_reprojected_and_resampled_baseline_path', p.base_year_lulc_path)
    lulc_path = os.path.join(p.project_dir, "lulc_2019_reprojected_and_resampled.tif")
    print(f"Reprojected and resampled LULC baseline path for input: {lulc_path}")

    urban_mental_health_functions.map_lulc_to_ndvi_dask(
        lulc_path=lulc_path,
        attr_table_path=p.lulc_attribute_table_path,
        ndvi_col='lc_ndvi',  # from attribute table
        out_path=p.ndvi_baseline_path,
        #compress="lzw"
        compress="deflate"
    )
    print(f"NDVI baseline raster saved to {p.ndvi_baseline_path}")

    return p.ndvi_baseline_path


def task_create_no_vegetation_scenario(p):
    """
    Task to create a no-vegetation NDVI scenario.
    """

    p.ndvi_no_vegetation_path = os.path.join(p.project_dir, 'ndvi_no_vegetation.tif')
    urban_mental_health_functions.create_no_vegetation_ndvi_scenario(
        baseline_ndvi_path=p.ndvi_baseline_path,
        out_path=p.ndvi_no_vegetation_path,
        #compress="lzw"
        compress="deflate"
    )
    
    print(f"No-vegetation NDVI scenario saved to {p.ndvi_no_vegetation_path}")
    return p.ndvi_no_vegetation_path


def task_calculate_delta_nature_exposure(p):
    """
    Task to calculate delta nature exposure (NDVI_2019 - NDVI_no_vegetation).
    """

    p.ndvi_baseline_path = os.path.join(p.project_dir, 'ndvi_2019.tif')
    p.ndvi_no_vegetation_path = os.path.join(p.project_dir, 'ndvi_no_vegetation.tif')
    p.delta_ne_path = os.path.join(p.project_dir, 'delta_ne_2019_vs_no_veg.tif')
    
    urban_mental_health_functions.calculate_delta_raster(
        raster1_path=p.ndvi_baseline_path,
        raster2_path=p.ndvi_no_vegetation_path,
        #raster2_path=p.ndvi_baseline_path,
        out_path=p.delta_ne_path,
        operation=lambda a, b: a - b,  # NDVI_2019 - NDVI_no_vegetation
        fill_value=np.nan,
        #compress="lzw"
        compress="deflate"
    )
    
    print(f"Delta NDVI raster (current vs no-vegetation) saved to {p.delta_ne_path}")
    return p.delta_ne_path


def task_calculate_preventable_cases(p):
    """
    Task to calculate preventable cases per pixel
    using delta nature exposure and population.
    """

    p.delta_ne_path = os.path.join(p.project_dir, 'delta_ne_2019_vs_no_veg.tif')

    p.preventable_cases_path = os.path.join(p.project_dir, 'case_factor_at_prevalence_1.tif')
    p.preventable_cases_ci_lower_path = os.path.join(p.project_dir, 'case_factor_at_prevalence_1_effect_ci_lower.tif')
    p.preventable_cases_ci_upper_path = os.path.join(p.project_dir, 'case_factor_at_prevalence_1_effect_ci_upper.tif')

    effects = urban_mental_health_functions.load_depression_effect_sizes(p.effect_size_table_path)
    interval_ors = effect_size_uncertainty.odds_ratios_for_case_interval(
        effects['effect_size'], effects['ci_lower'], effects['ci_upper'])
    # A lower OR implies a larger positive case-equivalent estimate, so the
    # case interval uses the OR limits in reverse order.
    for out_path, odds_ratio in (
        (p.preventable_cases_path, interval_ors['point']),
        (p.preventable_cases_ci_lower_path, interval_ors['lower']),
        (p.preventable_cases_ci_upper_path, interval_ors['upper']),
    ):
        urban_mental_health_functions.calculate_preventable_cases(
            delta_ne_path=p.delta_ne_path,
            pop_path=p.population_2019_path,
            effect_size_table_path=p.effect_size_table_path,
            prevalence=1.0,
            p0=p.prevalence_nonexposed,
            out_path=out_path,
            compress="deflate",
            odds_ratio=odds_ratio,
            overwrite=True,
        )
        print(f"Case factor raster (prevalence=1) saved to: {out_path}")

    return p.preventable_cases_path


def task_aggregate_preventable_cases_by_region(p):
    """
    Task to aggregate preventable cases by urban regions.
    """

    #p.preventable_cases_path = p.get_path(os.path.join(p.project_dir, 'preventable_cases_2019.tif'))
    p.preventable_cases_path = os.path.join(p.project_dir, 'case_factor_at_prevalence_1.tif')
    p.preventable_cases_by_region_csv = os.path.join(p.project_dir, 'preventable_cases_by_region.csv')
    p.preventable_cases_by_region_ci_lower_csv = os.path.join(p.project_dir, 'preventable_cases_by_region_effect_ci_lower.csv')
    p.preventable_cases_by_region_ci_upper_csv = os.path.join(p.project_dir, 'preventable_cases_by_region_effect_ci_upper.csv')

    for raster_path, csv_path in (
        (p.preventable_cases_path, p.preventable_cases_by_region_csv),
        (p.preventable_cases_ci_lower_path, p.preventable_cases_by_region_ci_lower_csv),
        (p.preventable_cases_ci_upper_path, p.preventable_cases_by_region_ci_upper_csv),
    ):
        urban_mental_health_functions.aggregate_preventable_cases_by_region(
            preventable_cases_raster_path=raster_path,
            urban_region_boundary_path=p.urban_boundary_path,
            out_csv_path=csv_path,
            country_prevalence_table_path=p.country_prevalence_table_path,
            country_crosswalk_path=p.country_crosswalk_path,
            scalar_prevalence=p.scalar_prevalence,
        )

    # Return CSV path
    return p.preventable_cases_by_region_csv


def task_calculate_country_costs(p):
    """
    Task to apply country-specific cost rates to aggregated preventable cases.
    """
    #p.preventable_cases_by_region_csv = p.get_path(os.path.join(p.project_dir, 'preventable_cases_by_region.csv'))
    p.preventable_cases_by_region_csv = os.path.join(p.project_dir, 'preventable_cases_by_region.csv')
    p.preventable_cost_by_country_csv = os.path.join(p.project_dir, 'preventable_cost_by_country.csv')
    p.preventable_cost_by_country_ci_lower_csv = os.path.join(p.project_dir, 'preventable_cost_by_country_effect_ci_lower.csv')
    p.preventable_cost_by_country_ci_upper_csv = os.path.join(p.project_dir, 'preventable_cost_by_country_effect_ci_upper.csv')

    for cases_csv, costs_csv in (
        (p.preventable_cases_by_region_csv, p.preventable_cost_by_country_csv),
        (p.preventable_cases_by_region_ci_lower_csv, p.preventable_cost_by_country_ci_lower_csv),
        (p.preventable_cases_by_region_ci_upper_csv, p.preventable_cost_by_country_ci_upper_csv),
    ):
        urban_mental_health_functions.apply_country_costs(
            regional_cases_csv_path=cases_csv,
            health_cost_rate_path=p.health_cost_rate_path,
            out_country_csv_path=costs_csv,
        )

    # Return tuple of paths
    return p.preventable_cost_by_country_csv
