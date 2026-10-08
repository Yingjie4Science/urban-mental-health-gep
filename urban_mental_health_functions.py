import os
import rasterio
from rasterstats import zonal_stats
from rasterio.enums import Resampling
import rasterio.warp
import numpy as np
from tqdm import tqdm
import gc
import pandas as pd
import geopandas as gpd
from osgeo import gdal
import shapely
from shapely.geometry import MultiPolygon
import pygeoprocessing as pgp
import effect_size_uncertainty
from hazelbean.spatial_utils import warp_raster_to_match
import rioxarray
import xarray as xr
import dask
from dask.distributed import Client, LocalCluster, Lock
from dask.diagnostics import ProgressBar
from dask.utils import SerializableLock


def warp_raster_to_reference(
    input_path,
    reference_path,
    out_path,
    resampling_method='near',
    compress="lzw"
    ):
    """
    Reproject and resample a raster to match the resolution and grid of a reference raster.
    """

    if os.path.exists(out_path):
        print(f"Raster already exists at {out_path}. Skipping reprojection and resampling.")
        return out_path

    # result = warp_raster_to_match(
    #     input_path=input_path,
    #     output_path=out_path,
    #     match_path=reference_path,
    #     resample_method=resampling_method
    # )  # reconstructs output width & height from bounding_box/pixel_size
        
    # Forcing the output width,height to exactly equal the reference raster's
    # own RasterXSize/RasterYSize (read directly from its header) rather than
    # reconstruction

    with rasterio.open(reference_path) as ref:
        ref_width = ref.width
        ref_height = ref.height
        ref_bounds = ref.bounds
        ref_crs_wkt = ref.crs.to_wkt()

    with rasterio.open(input_path) as src:
        src_nodata = src.nodata

    warp_options = gdal.WarpOptions(
        format='GTiff',
        dstSRS=ref_crs_wkt,
        outputBounds=(ref_bounds.left, ref_bounds.bottom, ref_bounds.right, ref_bounds.top),
        width=ref_width,
        height=ref_height,
        resampleAlg=resampling_method,
        srcNodata=src_nodata,
        dstNodata=src_nodata,
        creationOptions=['TILED=YES', 'BIGTIFF=YES', f'COMPRESS={compress.upper()}'],
    )

    result = gdal.Warp(out_path, input_path, options=warp_options)
    result.FlushCache()
    result = None

    print(f"Reprojected and resampled raster saved to: {out_path}")
    return out_path


# This version of map_lulc_to_ndvi() is a disguised for loop: for each pixel, lc_to_ndvi.get() is called.
# This is millions of slow python function calls.
# def map_lulc_to_ndvi(lulc_path, attr_table_path, ndvi_col, out_path, compress="lzw"):
#     """
#     Map LULC raster codes to NDVI values using attribute table.
#     """

#     # Read attribute table
#     df = pd.read_csv(attr_table_path)

#     # Create lookup dictionary with NaN handling for unmapped codes
#     lc_to_ndvi = dict(zip(df['lc_code'], df[ndvi_col]))

#     with rasterio.open(lulc_path) as src:
#         profile = src.profile.copy()
#         profile.update(dtype='float32', BIGTIFF='YES', nodata=np.nan, compress=compress)

#         with rasterio.open(out_path, 'w', **profile) as dst:
#             windows = list(src.block_windows(1))
#             for idx, window in tqdm(windows, desc="Converting LULC to NDVI"):
#             #for idx, window in windows:
#                 arr = src.read(1, window=window)

#                 # Map LULC codes to NDVI values, handling unmapped codes as NaN
#                 ndvi_arr = np.vectorize(lambda x: lc_to_ndvi.get(x, np.nan), otypes=[float])(arr)  # np.vectorize for better performance with large arrays thus avoiding the need for a loop over each pixel

#                 dst.write(ndvi_arr.astype('float32'), 1, window=window)

#     #print(f"NDVI raster saved to: {out_path}")

# This version of map_lulc_to_ndvi() is better than the one above because pgp library
# is fundamentally a set of Python wrappers around GDAL's core C++ functions.
# def map_lulc_to_ndvi(lulc_path, attr_table_path, ndvi_col, out_path, compress="lzw"):
#     """
#     Map LULC raster codes to NDVI values using attribute table.
#     """

#     # Read attribute table
#     df = pd.read_csv(attr_table_path)

#     # Create lookup dictionary with NaN handling for unmapped codes
#     lc_to_ndvi = dict(zip(df['lc_code'], df[ndvi_col]))

#     # Pre-scan the LULC raster to find ALL unique values
#     unique_raster_values = set()
#     with rasterio.open(lulc_path) as src:
#         src_nodata = src.nodata
#         for idx, window in src.block_windows(1):
#             block = src.read(1, window=window)
#             unique_raster_values.update(np.unique(block))

#     # Add any value from the raster that is not in our table
#     # to map these unmapped codes to np.nan
#     # in order to complete the dictionary
#     for val in unique_raster_values:
#         if val not in lc_to_ndvi:
#             lc_to_ndvi[int(val)] = np.nan # Add the missing key

#     # Run the optimized reclassification
#     pgp.reclassify_raster(
#         (lulc_path, 1),      # (path, band_index) for base raster
#         lc_to_ndvi,          # The lookup dictionary
#         out_path,            # Output path
#         gdal.GDT_Float32,    # Output data type
#         np.nan               # Output nodata value
#     )

#     print(f"NDVI raster saved to: {out_path}")

# This version of map_lulc_to_ndvi() has multhreaded implementation.
def map_lulc_to_ndvi_dask(lulc_path, attr_table_path, ndvi_col, out_path, compress='deflate'):
    """
    Map LULC raster codes to NDVI values using attribute table.
    """

    if os.path.exists(out_path):
        print(f"Raster already exists at {out_path}. Skipping LULC to NDVI conversion.")
        return out_path

    with rasterio.open(lulc_path) as src:
        src_nodata = src.nodata
    
    # Setup Dask cluster.
    with LocalCluster(
        #n_workers=os.cpu_count()//4 or 1,
        n_workers=8,
        threads_per_worker=1,
        memory_limit='45GB',
        death_timeout='2400s'
        ) as cluster, \
         Client(cluster) as client:
        
        print(f"Dask Dashboard link: {client.dashboard_link}")

        # Create the lookup array.
        df = pd.read_csv(attr_table_path)
        lc_codes = df['lc_code'].values.astype(int)
        ndvi_values = df[ndvi_col].values.astype(np.float32)
        max_code = np.max(lc_codes)
        lookup_array = np.full(int(max_code) + 1, np.nan, dtype=np.float32)
        lookup_array[lc_codes] = ndvi_values
        
        # Define the function to apply to each block.
        def lookup(block):
            max_lookup_index = len(lookup_array) - 1
            
            # This is the fast, C-optimized NumPy lookup
            ndvi_arr = np.full(block.shape, np.nan, dtype=np.float32)
            
            if block.size > 0: 
                mask = (block <= max_lookup_index) & (block >= 0)
                if src_nodata is not None:
                    mask = mask & (block != src_nodata)  # exclude the nodata value
                valid_codes = block[mask]
                ndvi_arr[mask] = lookup_array[valid_codes]
            
            return ndvi_arr

        src_raster = rioxarray.open_rasterio(
            lulc_path, 
            chunks={'x': 2048, 'y': 2048}, # Tell Dask how to chunk it
            lock=False
        )  # open_rasterio opens the GeoTIFF
            # and returns a Dask-backed XARRAY DataArray
        
        # Apply lookup() to src_raster.
        ndvi_result = xr.apply_ufunc(
            lookup,
            src_raster,
            dask="parallelized",
            output_dtypes=[np.float32]
        )
        
        # Copy the spatial metadata from the source to the result.
        ndvi_result = ndvi_result.rio.write_crs(src_raster.rio.crs)
        ndvi_result = ndvi_result.rio.write_transform(src_raster.rio.transform())
        ndvi_result.rio.update_encoding(dict(dtype='float32', _FillValue=np.nan, nodata=np.nan, compress=compress, BIGTIFF='YES'), inplace=True)

        # Execute the job and save to disk.
        print("Starting parallel LULC to NDVI conversion...")
        with rasterio.Env(
            CHECK_DISK_FREE_SPACE=False,
            GDAL_CACHEMAX=512,
            GDAL_NUM_THREADS=1
            ):
            with ProgressBar():
                ndvi_result.rio.to_raster(
                    out_path,
                    tiled=True,
                    #lock=dask.utils.SerializableLock(),
                    lock=Lock("rio-lock", client=client),
                    compress=compress,
                    compute=True
                    )
        src_raster.close()
        print(f"NDVI raster saved to: {out_path}")


def create_no_vegetation_ndvi_scenario(
        baseline_ndvi_path,
        out_path,
        compress="deflate"
        ):
    """
    Create a no-vegetation scenario by setting all positive NDVI values to 0.
    Keeps built-up areas, water, etc. at their original NDVI values.
    """
    
    if os.path.exists(out_path):
        print(f"Raster already exists at {out_path}. Skipping creation of no vegetation NDVI scenario.")
        return out_path
    
    with rasterio.open(baseline_ndvi_path) as src:
        profile = src.profile.copy()
        profile.update(compress=compress, dtype='float32', BIGTIFF='YES')
        
        with rasterio.open(out_path, 'w', **profile) as dst:
            for _, window in tqdm(src.block_windows(1), desc="Creating no-vegetation NDVI scenario"):
                ndvi_data = src.read(1, window=window).astype('float32')
                
                # Set positive NDVI (vegetation) to 0, keep negative/zero values
                no_veg_data = np.where(ndvi_data > 0.0, 0.0, ndvi_data)
                
                dst.write(no_veg_data, 1, window=window)
    
    print(f"No-vegetation NDVI scenario saved to: {out_path}")


def calculate_delta_raster(
        raster1_path,
        raster2_path,
        out_path,
        operation,
        fill_value=np.nan,
        #compress="lzw"
        compress="deflate"
        ):
    """
    Calculate difference between two rasters.
    """

    if os.path.exists(out_path):
        print(f"Raster already exists at {out_path}. Skipping delta raster computation.")
        return out_path
    
    with rasterio.open(raster1_path) as src1, rasterio.open(raster2_path) as src2:
        if src1.shape != src2.shape:
            raise ValueError("Input rasters must have the same dimensions.")

        profile = src1.profile.copy()
        profile.update(dtype='float32', BIGTIFF='YES', nodata=fill_value, compress=compress)

        with rasterio.open(out_path, "w", **profile) as dst:
            windows = list(src1.block_windows(1))
            #for _, window in windows:
            for _, window in tqdm(windows, desc="Calculating delta raster"):
                arr1 = src1.read(1, window=window)
                arr2 = src2.read(1, window=window)

                # Handle NaN values properly
                result = operation(arr1, arr2)
                result = np.where(np.isnan(arr1) | np.isnan(arr2), fill_value, result)

                dst.write(result.astype("float32"), 1, window=window)

    #print(f"Delta raster saved to: {out_path}")


def load_depression_effect_sizes(effect_size_table_path):
    """Read the depression OR and its 95% CI per 0.1 NDVI increase."""
    df = pd.read_excel(effect_size_table_path)
    required = {'health_indicator', 'effect_size', 'ci_lower', 'ci_upper'}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Effect size table is missing columns: {sorted(missing)}")
    rows = df.loc[df['health_indicator'] == 'depression']
    if len(rows) != 1:
        raise ValueError("Effect size table must contain exactly one depression row")
    row = rows.iloc[0]
    values = {key: float(row[key]) for key in ('effect_size', 'ci_lower', 'ci_upper')}
    if not all(np.isfinite(value) and value > 0 for value in values.values()):
        raise ValueError("Depression OR and CI limits must be finite and positive")
    if not values['ci_lower'] <= values['effect_size'] <= values['ci_upper']:
        raise ValueError("Depression OR must lie within its 95% CI")
    return values


def calculate_preventable_cases(
        delta_ne_path,
        pop_path,
        effect_size_table_path,
        prevalence,
        p0,
        out_path,
        #compress="lzw"
        compress="deflate",
        odds_ratio=None,
        overwrite=False
        ):
    """
    Calculate preventable cases per pixel using delta nature exposure and population.
    """

    if os.path.exists(out_path) and not overwrite:
        print(f"Raster already exists at {out_path}. Skipping preventable cases raster computation.")
        return out_path
    
    if not 0 <= prevalence <= 1 or not 0 <= p0 < 1:
        raise ValueError("Prevalence and p0 must be probabilities in [0, 1]")
    if odds_ratio is None:
        odds_ratio = load_depression_effect_sizes(effect_size_table_path)['effect_size']
    odds_ratio = float(odds_ratio)
    if not np.isfinite(odds_ratio) or odds_ratio <= 0:
        raise ValueError("Odds ratio must be finite and positive")

    # Convert the meta-analysis OR to an approximate RR before applying NDVI.
    # p0 is prevalence in the least-green reference group, not the 0.05
    # population-wide baseline prevalence used below to calculate bc.
    # Default p0=0.115 comes from Hystad et al. (2019), Table 1, health-record
    # diagnosis in the lowest NDVI quartile of a Quebec adult cohort. This is
    # a transported proxy for the global run. Zhang & Yu (1998) conversion:
    # RR = OR / (1 - p0 + p0 * OR).
    risk_ratio = effect_size_uncertainty.odds_ratio_to_risk_ratio(odds_ratio, p0)

    with rasterio.open(delta_ne_path) as dsrc, rasterio.open(pop_path) as psrc:
        if dsrc.shape != psrc.shape:
            raise ValueError("Delta NE and population rasters must have the same dimensions.")

        pop_nodata = psrc.nodata
        
        profile = dsrc.profile.copy()
        profile.update(dtype='float32', BIGTIFF='YES', nodata=np.nan, compress=compress)

        with rasterio.open(out_path, 'w', **profile) as dst:
            windows = list(dsrc.block_windows(1))
            for _, window in tqdm(windows, desc="Calculating preventable cases"):
                delta_ne = dsrc.read(1, window=window)
                pop = psrc.read(1, window=window)

                if pop_nodata is not None:
                    pop = np.where(pop == pop_nodata, np.nan, pop)  # mask WorldPop's NoData sentinel before it enters arithmetic
                
                # The no-vegetation/observed risk ratio is 1 / RR**delta.
                # In the country-rate workflow prevalence=1 here; the actual
                # country rate is applied after urban-polygon aggregation.
                bc = prevalence * pop
                preventable_cases = effect_size_uncertainty.additional_cases_from_observed(
                    bc, risk_ratio, delta_ne)

                # Handle NaN values.
                preventable_cases = np.where(np.isnan(delta_ne) | np.isnan(pop), np.nan, preventable_cases)

                dst.write(preventable_cases.astype('float32'), 1, window=window)

    #print(f"Preventable cases raster saved to: {out_path}")


def aggregate_preventable_cases_by_region(
        preventable_cases_raster_path,
        urban_region_boundary_path,
        out_csv_path,
        country_prevalence_table_path=None,
        country_crosswalk_path=None,
        scalar_prevalence=None,
        ):
    """
    Aggregate preventable cases by urban regions using pygeoprocessing.
    """
    # Load urban boundaries to handle reprojection and attributes.
    urban_boundaries = gpd.read_file(urban_region_boundary_path)
    processing_boundary_path = urban_region_boundary_path

    with rasterio.open(preventable_cases_raster_path) as src:
        raster_crs = src.crs
        print(f"Raster CRS: {raster_crs}")

    # Reproject vector data and save to disk for pygeoprocessing.
    if urban_boundaries.crs != raster_crs:
        print(f"Reprojecting vector data from {urban_boundaries.crs} to match raster CRS {raster_crs}")
        urban_boundaries = urban_boundaries.to_crs(raster_crs)
        processing_boundary_path = out_csv_path.replace('.csv', '_reprojected.gpkg')
        urban_boundaries.to_file(processing_boundary_path, driver="GPKG")

    # Calculate zonal statistics for all polygons at block-level.
    print("Calculating zonal statistics using pygeoprocessing...")
    zs = pgp.geoprocessing.zonal_statistics(
        (preventable_cases_raster_path, 1),
        processing_boundary_path
    )

    results = []
    
    # Process results: pygeoprocessing returns a dict keyed by the vector's FID.
    # Geopandas loads FIDs into the dataframe index sequentially (or 0-indexed).
    urban_boundaries['fid'] = range(1, len(urban_boundaries) + 1)
    
    for fid, stats in tqdm(zs.items(), desc="Compiling zonal statistics"):
        if stats['count'] == 0 or stats['count'] is None:
            continue

        # Retrieve original row data based on FID.
        row = urban_boundaries[urban_boundaries['fid'] == fid].iloc[0]

        region_stats = {
            "region_id": row.get("id", fid),
            "country": row.get("country", None),
            "iso3_r250_label": row.get("iso3", None),
            "total_preventable_cases": stats['sum'] if stats['sum'] is not None else 0
        }
        results.append(region_stats)

    # The input raster is a case factor at prevalence = 1. Multiplying after
    # zonal aggregation is algebraically equivalent to a country-rate raster,
    # provided every urban polygon belongs to exactly one country. It avoids
    # rasterizing thousands of polygons across the global 100 m grid.
    df = pd.DataFrame(results)
    if df.empty:
        raise ValueError('No urban polygons had valid population/raster overlap')
    if country_prevalence_table_path is not None:
        from prevalence_inputs import resolve_country_rates
        rates = resolve_country_rates(df['country'].unique(),
                                      country_prevalence_table_path,
                                      country_crosswalk_path)
        df['baseline_prevalence'] = df['country'].map(rates)
    elif scalar_prevalence is not None:
        df['baseline_prevalence'] = scalar_prevalence
    else:
        raise ValueError('Provide a country prevalence table or an explicit scalar sensitivity rate')
    df['case_factor_at_prevalence_1'] = df.pop('total_preventable_cases')
    df['total_preventable_cases'] = df['case_factor_at_prevalence_1'] * df['baseline_prevalence']
    # Preserve fractional case-equivalent values through country aggregation.
    df.to_csv(out_csv_path, index=False)
    print(f"Regional preventable cases summary written to: {out_csv_path}")

    return out_csv_path


def apply_country_costs(
        regional_cases_csv_path,
        health_cost_rate_path,
        out_country_csv_path
        ):
    """
    Apply country-specific cost rates to aggregated preventable cases.
    """

    # Read input data.
    regional_df = pd.read_csv(regional_cases_csv_path)
    cost_df = pd.read_excel(health_cost_rate_path)
    from cost_basis import validate_2019_usd_non_ppp
    # The monetary basis must be explicit for every input rate. This validates
    # workbook declarations; source and conversion records still need review.
    validate_2019_usd_non_ppp(cost_df.to_dict('records'))
    if 'country' not in cost_df or 'cost_per_case' not in cost_df:
        raise ValueError("Cost table must contain country and cost_per_case columns")
    if cost_df['country'].isna().any() or cost_df['country'].duplicated().any():
        raise ValueError('Cost table country names must be nonmissing and unique')
    cost_df['cost_per_case'] = pd.to_numeric(cost_df['cost_per_case'], errors='coerce')
    if not np.isfinite(cost_df['cost_per_case']).all() or (cost_df['cost_per_case'] < 0).any():
        raise ValueError("Cost per case must be finite and nonnegative for interval propagation")

    # A missing country price must be reviewed, never silently omitted.
    unmatched = sorted(set(regional_df['country']) - set(cost_df['country']))
    if unmatched:
        raise ValueError(f"Urban-region countries missing from cost table: {unmatched}")
    filtered = regional_df

    # Sum preventable cases for each country.
    country_sums = filtered[['country', 'total_preventable_cases']].groupby('country').sum()

    # Merge summed cases with per-patient costs.
    merged = pd.merge(country_sums, cost_df, on='country')

    # Calculate cost savings.
    merged['cost_savings_2019_usd'] = merged['total_preventable_cases'] * merged['cost_per_case']

    # Write output CSV with desired columns.
    merged[['country', 'total_preventable_cases', 'cost_savings_2019_usd']].to_csv(out_country_csv_path, index=False, float_format='%.2f')
    print(f"Country-level cost savings saved to: {out_country_csv_path}")

    return out_country_csv_path
