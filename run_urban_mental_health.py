"""Run the 2019 global urban mental-health GEP scenario.

Use 2019 country GBD depressive-disorders prevalence matched to all-age
WorldPop. An explicit scalar is available only for sensitivity comparisons.
"""

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path

import hazelbean as hb

import run_provenance
import urban_mental_health_tasks
from prevalence_inputs import load_country_prevalence


def build_task_tree(project):
    project.task_reproject_and_resample_lulc_to_population_grid = project.add_task(
        urban_mental_health_tasks.task_warp_lulc_to_population)
    project.task_convert_lulc_to_ndvi_baseline = project.add_task(
        urban_mental_health_tasks.task_convert_lulc_to_ndvi_baseline)
    project.task_create_no_vegetation_scenario = project.add_task(
        urban_mental_health_tasks.task_create_no_vegetation_scenario)
    project.task_calculate_delta_nature_exposure = project.add_task(
        urban_mental_health_tasks.task_calculate_delta_nature_exposure)
    project.task_calculate_preventable_cases = project.add_task(
        urban_mental_health_tasks.task_calculate_preventable_cases)
    project.task_aggregate_preventable_cases_by_region = project.add_task(
        urban_mental_health_tasks.task_aggregate_preventable_cases_by_region)
    project.task_calculate_country_costs = project.add_task(
        urban_mental_health_tasks.task_calculate_country_costs)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    default_base = Path.home() / 'Files' / 'base_data' / 'submissions' / 'urban_mental_health'
    parser.add_argument('--base-data-dir', type=Path, default=default_base,
                        help='Directory holding the tabular and WorldPop inputs')
    parser.add_argument('--project-dir', type=Path,
                        help='Output directory; defaults to a timestamped project under ~/Files/global_invest/projects')
    parser.add_argument('--country-prevalence-table', type=Path,
                        help='Validated GBD 2023 release, 2019 all-age depressive-disorders country CSV')
    parser.add_argument('--country-crosswalk', type=Path,
                        help='Optional CSV with polygon_country,gbd_location_id for reviewed name mismatches')
    parser.add_argument('--baseline-prevalence', type=float,
                        help='Explicit scalar sensitivity rate; overrides the country table (e.g. historical 0.05)')
    parser.add_argument('--p0', type=float,
                        help='Least-green reference prevalence for OR-to-RR conversion; default 0.115')
    return parser.parse_args()


def main():
    args = parse_args()
    baseline_prevalence = args.baseline_prevalence
    p0 = 0.115 if args.p0 is None else args.p0
    if baseline_prevalence is not None and not 0 <= baseline_prevalence <= 1:
        raise ValueError('Scalar sensitivity prevalence must be in [0, 1]')
    if not 0 <= p0 < 1:
        raise ValueError('p0 must be in [0, 1)')
    if baseline_prevalence is None and args.country_prevalence_table is None:
        raise ValueError('Specify --country-prevalence-table for the agreed primary run')
    if baseline_prevalence is not None and args.country_prevalence_table is not None:
        raise ValueError('Choose the country table or scalar sensitivity, not both')
    if args.country_crosswalk and not args.country_prevalence_table:
        raise ValueError('Country crosswalk requires --country-prevalence-table')
    if args.country_prevalence_table:
        load_country_prevalence(args.country_prevalence_table, args.country_crosswalk)

    p = hb.ProjectFlow()
    p.user_dir = os.path.expanduser('~')
    p.extra_dirs = ['Files', 'global_invest', 'projects']
    if args.project_dir is None:
        stamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_UTC')
        project_dir = Path.home() / 'Files' / 'global_invest' / 'projects' / f'urban_mental_health_{stamp}'
    else:
        project_dir = args.project_dir.expanduser().resolve()
    p.project_name = project_dir.name
    p.project_dir = str(project_dir)
    p.set_project_dir(p.project_dir)

    p.base_data_dir = str(args.base_data_dir.expanduser().resolve())
    p.aoi = 'global'
    # The 30 m land-cover raster is nearest-neighbor warped to the 100 m
    # population grid. NDVI is assigned by land-cover code, not read from Landsat.
    p.base_year_lulc_path = p.get_path(os.path.join(
        p.base_data_dir, '../../lulc/glc_fcs30d/lulc_glc_fcs30d_2019.tif'))
    p.population_2019_path = p.get_path(os.path.join(
        p.base_data_dir, 'worldpop/100m_2019_global-mosaic.tif'))
    p.lulc_attribute_table_path = p.get_path(os.path.join(
        p.base_data_dir, 'glc_fcs30d_attribute_table_processed.csv'))
    p.effect_size_table_path = p.get_path(os.path.join(p.base_data_dir, 'effect_size.xlsx'))
    p.urban_boundary_path = p.get_path(os.path.join(p.base_data_dir, 'urban_boundaries_2019.gpkg'))
    p.health_cost_rate_path = p.get_path(os.path.join(p.base_data_dir, 'treatment_cost.xlsx'))

    p.scalar_prevalence = baseline_prevalence
    p.country_prevalence_table_path = (str(args.country_prevalence_table.expanduser().resolve())
                                       if args.country_prevalence_table else None)
    p.country_crosswalk_path = (str(args.country_crosswalk.expanduser().resolve())
                                if args.country_crosswalk else None)
    # Hystad et al. (2019), Table 1: 234 (11.5%) health-record diagnoses in
    # the lowest residential-NDVI quartile of a Quebec adult cohort. This is a
    # proxy for p0, not measured global unexposed prevalence. Perry is the
    # first author's given name. DOI: 10.1097/EE9.0000000000000040.
    p.prevalence_nonexposed = p0

    build_task_tree(p)
    p.execute()

    output_names = (
        'case_factor_at_prevalence_1.tif',
        'case_factor_at_prevalence_1_effect_ci_lower.tif',
        'case_factor_at_prevalence_1_effect_ci_upper.tif',
        'preventable_cases_by_region.csv',
        'preventable_cases_by_region_effect_ci_lower.csv',
        'preventable_cases_by_region_effect_ci_upper.csv',
        'preventable_cost_by_country.csv',
        'preventable_cost_by_country_effect_ci_lower.csv',
        'preventable_cost_by_country_effect_ci_upper.csv',
    )
    run_provenance.write_manifest(
        project_dir=project_dir,
        inputs={
            'land_cover_2019': p.base_year_lulc_path,
            'population_2019': p.population_2019_path,
            'land_cover_ndvi_lookup': p.lulc_attribute_table_path,
            'effect_size': p.effect_size_table_path,
            'urban_boundaries': p.urban_boundary_path,
            'country_costs': p.health_cost_rate_path,
            'country_prevalence': p.country_prevalence_table_path,
            'country_crosswalk': p.country_crosswalk_path,
        },
        source_dir=Path(__file__).resolve().parent,
        outputs={name: project_dir / name for name in output_names},
        parameters={
            'baseline_prevalence': baseline_prevalence,
            'baseline_prevalence_source': (
                'explicit scalar sensitivity; verify outcome, age group and year'
                if baseline_prevalence is not None else
                'GBD 2023 release; 2019 all-age both-sex crude depressive-disorders '
                'country rates, applied to 2019 all-age WorldPop'),
            'p0': p0,
            'p0_source': (
                'user supplied; verify least-green reference group'
                if args.p0 is not None else
                'Hystad et al. 2019 Table 1 health-record depression diagnosis, '
                'lowest NDVI quartile, Quebec adult cohort'),
            'scenario': 'positive land-cover-derived NDVI set to zero',
            'effect_interval': '95% OR CI only; p0, prevalence, exposure, population and costs fixed',
            'cost_basis': 'cost workbook rows must declare 2019 USD and ppp_adjusted=False; source conversion must be audited',
            'case_estimand': 'additional no-vegetation cases relative to estimated observed 2019 cases; '
                             'conditional on model assumptions',
        },
    )
    print('URBAN MENTAL HEALTH MODEL COMPLETED')


if __name__ == '__main__':
    main()
