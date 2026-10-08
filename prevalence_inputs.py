"""Validated, explicit country-to-GBD prevalence mapping for the 2019 model."""

import csv
import math
from pathlib import Path


def load_country_prevalence(table_path, crosswalk_path=None):
    """Return (GBD rates by location ID, polygon-country-to-ID crosswalk).

    The crosswalk is optional only when polygon country names exactly match GBD
    names. Never guess a missing match or replace it with a global rate.
    """
    with Path(table_path).open(newline='', encoding='utf-8-sig') as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError('Country prevalence table is empty')
    expected = {'location_id', 'country_as_gbd', 'year', 'prevalence_fraction',
                'gbd_release'}
    if not expected.issubset(rows[0]):
        raise ValueError(f'Country prevalence table lacks {sorted(expected - rows[0].keys())}')
    by_id = {}
    name_to_id = {}
    for row in rows:
        if row['year'] != '2019' or row['gbd_release'] != 'GBD 2023':
            raise ValueError('Expected GBD 2023 release estimates for year 2019')
        location_id = row['location_id'].strip()
        name = row['country_as_gbd'].strip()
        rate = float(row['prevalence_fraction'])
        if not location_id or not name or not math.isfinite(rate) or not 0 <= rate <= 1:
            raise ValueError(f'Invalid GBD location or prevalence: {row}')
        if location_id in by_id or name in name_to_id:
            raise ValueError(f'Duplicate GBD location: {location_id} / {name}')
        by_id[location_id] = {'name': name, 'rate': rate}
        name_to_id[name] = location_id
    crosswalk = {}
    if crosswalk_path:
        with Path(crosswalk_path).open(newline='', encoding='utf-8-sig') as stream:
            mapping_rows = list(csv.DictReader(stream))
        if mapping_rows and not {'polygon_country', 'gbd_location_id'}.issubset(mapping_rows[0]):
            raise ValueError('Crosswalk requires polygon_country,gbd_location_id')
        for row in mapping_rows:
            polygon_name = row['polygon_country'].strip()
            location_id = row['gbd_location_id'].strip()
            if not polygon_name or location_id not in by_id or polygon_name in crosswalk:
                raise ValueError(f'Invalid or duplicate country crosswalk row: {row}')
            crosswalk[polygon_name] = location_id
    return by_id, name_to_id, crosswalk


def resolve_country_rates(countries, table_path, crosswalk_path=None):
    """Map all polygon countries to rates, raising on every unmatched label."""
    by_id, name_to_id, crosswalk = load_country_prevalence(table_path, crosswalk_path)
    resolved = {}
    missing = []
    for country in countries:
        if not isinstance(country, str) or not country.strip():
            missing.append(str(country))
            continue
        name = country.strip()
        location_id = crosswalk.get(name, name_to_id.get(name))
        if location_id is None:
            missing.append(name)
        else:
            resolved[country] = by_id[location_id]['rate']
    if missing:
        raise ValueError('Unmatched polygon countries in GBD prevalence table: '
                         + ', '.join(sorted(set(missing))))
    return resolved
