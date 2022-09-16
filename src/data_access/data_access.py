"""
This module provides a unified API for access to metadata and datasets from ACTRIS, IAGOS, SIOS and ICOS RI's.
"""

import pkg_resources
import numpy as np
import pandas as pd
import logging
import pathlib
import json
import datetime
from datetime import date
import itertools
import xarray as xr
from mmappickle.dict import mmapdict
import re

from . import helper
from . import query_actris
from . import query_iagos
from . import query_icos
from . import query_sios


LON_LAT_BBOX_EPS = 0.05  # epsil
CACHE_DIR = pathlib.PurePath(pkg_resources.resource_filename('data_access', 'cache'))
logger = logging.getLogger(__name__)


# for caching purposes
# TODO: do it properly
_stations = None
_variables = None

_RIS = ['actris', 'iagos', 'icos', 'sios']
_GET_DATASETS_BY_RI = dict()

# mapping from standard ECV names to short variable names (used for time-line graphs)
# must be updated on adding new RI's!
VARIABLES_MAPPING = {
    'Aerosol Optical Properties': 'AOP',
    'Aerosol Chemical Properties': 'ACP',
    'Aerosol Physical Properties': 'APP',
    'Pressure (surface)': 'AP',
    'Surface Wind Speed and direction': 'WSD',
    'Temperature (near surface)': 'AT',
    'Water Vapour (surface)': 'RH',
    'Carbon Dioxide': 'CO2',
    'Carbon Monoxide': 'CO',
    'Methane': 'CH4',
    'Nitrous Oxide': 'N2O',
    'NO2': 'NO2',
    'Ozone': 'O3',
    'Cloud Properties': 'ClP',
    'Surface Radiation Budget': 'SRB',
}

_var_codes_by_ECV = pd.Series(VARIABLES_MAPPING, name='code')
_ECV_by_var_codes = pd.Series({v: k for k, v in VARIABLES_MAPPING.items()}, name='ECV')


def _get_ri_query_module_by_ri(ris=None):
    if ris is None:
        ris = _RIS
    else:
        ris = sorted(ri.lower() for ri in ris)
    ri_query_module_by_ri = {}
    for ri in ris:
        if ri == 'actris':
            ri_query_module_by_ri[ri] = query_actris
        elif ri == 'iagos':
            ri_query_module_by_ri[ri] = query_iagos
        elif ri == 'icos':
            ri_query_module_by_ri[ri] = query_icos
        elif ri == 'sios':
            ri_query_module_by_ri[ri] = query_sios
        else:
            raise ValueError(f'ri={ri}')
    return ri_query_module_by_ri


_ri_query_module_by_ri = _get_ri_query_module_by_ri()


def _get_stations(ris=None):
    ri_query_module_by_ri = _get_ri_query_module_by_ri(ris)
    stations_dfs = []
    for ri, ri_query_module in ri_query_module_by_ri.items():
        cache_path = CACHE_DIR / f'stations_{ri}.pkl'
        try:
            try:
                stations_df = pd.read_pickle(cache_path)
            except FileNotFoundError:
                stations = ri_query_module.get_list_platforms()
                stations_df = pd.DataFrame.from_dict(stations)
                stations_df.to_pickle(cache_path)
                
            if ri == 'actris':
                stations_df = stations_df.rename(columns={'URI': 'uri', 'altitude': 'ground_elevation'})
                stations_df['RI'] = 'ACTRIS'
                stations_df['country'] = np.nan
                stations_df['theme'] = np.nan
                stations_dfs.append(stations_df)
            elif ri == 'iagos':
                stations_df = stations_df.rename(columns={'altitude': 'ground_elevation'})
                stations_df['RI'] = 'IAGOS'
                stations_df['uri'] = np.nan
                stations_df['country'] = np.nan
                stations_df['theme'] = np.nan
                stations_dfs.append(stations_df)
            elif ri == 'icos':
                for col in ['latitude', 'longitude', 'ground_elevation']:
                    stations_df[col] = pd.to_numeric(stations_df[col])
                stations_dfs.append(stations_df)
            # elif ri == 'sios':
            #     stations_df = stations_df.rename(columns={'URI': 'uri'})
            #     stations_df['RI'] = 'SIOS'
            #     stations_df['country'] = np.nan
            #     stations_df['theme'] = np.nan
            #     stations_dfs.append(stations_df)                
            else:
                raise ValueError(f'ri={ri}')
        except Exception as e:
            logger.exception(f'getting {ri.upper()} stations failed', exc_info=e)

    all_stations_df = pd.concat(stations_dfs, ignore_index=True)
    all_stations_df['short_name_RI'] = all_stations_df['short_name'] + ' (' + all_stations_df['RI'] + ')'
    all_stations_df['idx'] = all_stations_df.index
    all_stations_df['marker_size'] = 7

    return all_stations_df


def get_stations():
    """
    For each ACTRIS, IAGOS and ICOS station (for the moment it is ICOS only).
    :return: pandas Dataframe with stations data; it has the following columns:
    'uri', 'short_name', 'long_name', 'country', 'latitude', 'longitude', 'ground_elevation', 'RI', 'short_name_RI',
    'theme', 'idx'
    A sample record is:
        'uri': 'http://meta.icos-cp.eu/resources/stations/AS_BIR',
        'short_name': 'BIR',
        'long_name': 'Birkenes',
        'country': 'NO',
        'latitude': 58.3886,
        'longitude': 8.2519,
        'ground_elevation': 219.0,
        'RI': 'ICOS',
        'short_name_RI': 'BIR (ICOS)',
        'theme': 'AS'
        'idx': 2
    """
    global _stations
    if _stations is None:
        _stations = _get_stations()
    return _stations

def get_start_date():
    return date(1800, 1, 1)

def get_end_date():
    return datetime.datetime.today()

def get_vars_long():
    """
    Provide a listing of RI's variables. For the same variable code there might be many records with different ECV names
    :return: pandas.DataFrame with columns: 'variable_name', 'ECV_name', 'std_ECV_name', 'code'; sample records are:
        'variable_name': 'co', 'ECV_name': 'Carbon Monoxide', 'std_ECV_name': 'Carbon Monoxide', 'code': 'CO';
        'variable_name': 'co', 'ECV_name': 'Carbon Dioxide, Methane and other Greenhouse gases', 'std_ECV_name': 'Carbon Monoxide', 'code': 'CO';
        'variable_name': 'co', 'ECV_name': 'co', 'std_ECV_name': 'Carbon Monoxide', 'code': 'CO';
    """
    global _variables
    if _variables is None:
        variables_dfs = []
        for ri, ri_query_module in _ri_query_module_by_ri.items():
            cache_path = CACHE_DIR / f'variables_{ri}.pkl'
            try:
                try:
                    variables_df = pd.read_pickle(cache_path)
                except FileNotFoundError:
                    variables = ri_query_module.get_list_variables()
                    variables_df = pd.DataFrame.from_dict(variables)
                    variables_df.to_pickle(cache_path)
                variables_dfs.append(variables_df)
            except Exception as e:
                logger.exception(f'getting {ri.upper()} variables failed', exc_info=e)
        df = pd.concat(variables_dfs, ignore_index=True)
        df['std_ECV_name'] = df['ECV_name'].apply(lambda l: l[0])
        df = df.join(_var_codes_by_ECV, on='std_ECV_name')
        _variables = df.explode('ECV_name', ignore_index=True).drop_duplicates(keep='first', ignore_index=True)
    return _variables


def get_vars():
    """
    Provide a listing of RI's variables.
    :return: pandas.DataFrame with columns: 'ECV_name', 'std_ECV_name', 'code'; a sample record is:
        'ECV_name': 'Carbon Dioxide, Methane and other Greenhouse gases',
        'std_ECV_name': 'Carbon Monoxide',
        'code': 'CO'
    """
    variables_df = get_vars_long().drop(columns=['variable_name'])
    return variables_df.drop_duplicates(subset=['std_ECV_name', 'ECV_name'], keep='first', ignore_index=True)

def get_datasets(variables, lon_min=None, lon_max=None, lat_min=None, lat_max=None, start=None, end=None, selected_RIs=None):
    """
    Provide metadata of datasets selected according to the provided criteria.
    :param variables: list of str or None; list of variable standard ECV names (as in the column 'std_ECV_name' of the dataframe returned by get_vars function)
    :param lon_min: float or None
    :param lon_max: float or None
    :param lat_min: float or None
    :param lat_max: float or None
    :return: pandas.DataFrame with columns: 'title', 'url', 'ecv_variables', 'platform_id', 'RI', 'var_codes',
     'ecv_variables_filtered', 'std_ecv_variables_filtered', 'var_codes_filtered',
     'time_period_start', 'time_period_end', 'platform_id_RI';
    e.g. for the call get_datasets(['Pressure (surface)', 'Temperature (near surface)'] one gets a dataframe with an example row like:
         'title': 'ICOS_ATC_L2_L2-2021.1_GAT_2.5_CTS_MTO.zip',
         'url': [{'url': 'https://meta.icos-cp.eu/objects/0HxLXMXolAVqfcuqpysYz8jK', 'type': 'landing_page'}],
         'ecv_variables': ['Pressure (surface)', 'Surface Wind Speed and direction', 'Temperature (near surface)', 'Water Vapour (surface)'],
         'platform_id': 'GAT',
         'RI': 'ICOS',
         'var_codes': ['AP', 'AT', 'RH', 'WSD'],
         'ecv_variables_filtered': ['Pressure (surface)', 'Temperature (near surface)'],
         'std_ecv_variables_filtered': ['Pressure (surface)', 'Temperature (near surface)'],
         'var_codes_filtered': 'AP, AT',
         'time_period_start': Timestamp('2016-05-10 00:00:00+0000', tz='UTC'),
         'time_period_end': Timestamp('2021-01-31 23:00:00+0000', tz='UTC'),
         'platform_id_RI': 'GAT (ICOS)'
    """
    if variables is None:
        variables = []
    else:
        variables = list(variables)
    if None in [lon_min, lon_max, lat_min, lat_max]:
        bbox = []
    else:
        bbox = [lon_min, lat_min, lon_max, lat_max]
    if None in [start, end]:
        period = []
    else:
        period = [start, end]

    datasets_dfs = []
    for ri, get_ri_datasets in _GET_DATASETS_BY_RI.items():
        if ri.upper() in selected_RIs:
            cache_path = CACHE_DIR / f'datasets_{ri}.pkl'
            try:
                try:
                    df = pd.read_pickle(cache_path)
                except FileNotFoundError:
                    df = get_ri_datasets(variables, bbox, period)
                    df.to_pickle(cache_path)
            except Exception as e:
                logger.exception(f'getting datasets for {ri.upper()} failed', exc_info=e)
            if df is not None:
                datasets_dfs.append(df)
    
    if not datasets_dfs:
        return None
    datasets_df = pd.concat(datasets_dfs, ignore_index=True)#.reset_index()

    vars_long = get_vars_long()

    codes_by_ECV_name = helper.many2many_to_dictOfList(
        zip(vars_long['ECV_name'].to_list(), vars_long['code'].to_list())
    )
    codes_by_variable_name = helper.many2many_to_dictOfList(
        zip(vars_long['variable_name'].to_list(), vars_long['code'].to_list())
    )
    codes_by_name = helper.many2manyLists_to_dictOfList(
        itertools.chain(codes_by_ECV_name.items(), codes_by_variable_name.items())
    )
    datasets_df['var_codes'] = [
        sorted(helper.image_of_dictOfLists(vs, codes_by_name))
        for vs in datasets_df['ecv_variables'].to_list()
    ]

    std_ECV_names_by_ECV_name = helper.many2many_to_dictOfList(
        zip(vars_long['ECV_name'].to_list(), vars_long['std_ECV_name'].to_list()), keep_set=True
    )
    std_ECV_names_by_variable_name = helper.many2many_to_dictOfList(
        zip(vars_long['variable_name'].to_list(), vars_long['std_ECV_name'].to_list()), keep_set=True
    )
    std_ECV_names_by_name = helper.many2manyLists_to_dictOfList(
        itertools.chain(std_ECV_names_by_ECV_name.items(), std_ECV_names_by_variable_name.items()), keep_set=True
    )
    datasets_df['ecv_variables_filtered'] = [
        sorted(
            v for v in vs if std_ECV_names_by_name[v].intersection(variables)
        )
        for vs in datasets_df['ecv_variables'].to_list()
    ]
    datasets_df['std_ecv_variables_filtered'] = [
        sorted(
            helper.image_of_dictOfLists(vs, std_ECV_names_by_name).intersection(variables)
        )
        for vs in datasets_df['ecv_variables'].to_list()
    ]
    req_var_codes = helper.image_of_dict(variables, VARIABLES_MAPPING)
    datasets_df['var_codes_filtered'] = [
        ', '.join(sorted(vc for vc in var_codes if vc in req_var_codes))
        for var_codes in datasets_df['var_codes'].to_list()
    ]
    datasets_df['time_period_start'] = datasets_df['time_period'].apply(lambda x: pd.Timestamp(x[0]))
    datasets_df['time_period_end'] = datasets_df['time_period'].apply(lambda x: pd.Timestamp(x[1]))
    datasets_df['platform_id_RI'] = datasets_df['platform_id'] + ' (' + datasets_df['RI'] + ')'

    return datasets_df.drop(columns=['time_period']).rename(columns={'urls': 'url'})

def _get_actris_datasets(variables, bbox, period):
    print("Search ACTRIS datasets...")
    datasets = query_actris.query_datasets(variables=variables, temporal_extent=period, spatial_extent=bbox)
    print("done")
    if not datasets:
        return None
    datasets_df = pd.DataFrame.from_dict(datasets)

    # fix title for ACTRIS datasets: remove time span
    datasets_df['title'] = datasets_df['title'].str.slice(stop=-62)

    datasets_df['RI'] = 'ACTRIS'
    return datasets_df

def _get_icos_datasets(variables, bbox, period):
    print("Search ICOS datasets...")
    datasets = query_icos.query_datasets(variables=variables, temporal=period, spatial=bbox)
    print("done")
    if not datasets:
        return None
    datasets_df = pd.DataFrame.from_dict(datasets)
    datasets_df['RI'] = 'ICOS'
    return datasets_df

def _get_sios_datasets(variables, bbox, period):
    print("Search SIOS datasets...")
    bbox2 = bbox
    if len(bbox) == 0:
        bbox2 = [None,None,None,None]
    datasets = query_sios.query_datasets(variables_list=variables, temporal_extent=period, spatial_extent=bbox2)
    print("done")
    if not datasets:
        return None
    for ds in datasets:
        ds['time_period'][1] = datetime.datetime.today().strftime('%Y-%m-%dT%H:%M:%S') #'2021-01-31T23:00:00Z'
    datasets_df = pd.DataFrame.from_dict(datasets)
    datasets_df['RI'] = 'SIOS'
    return datasets_df

# Temporary solution for IAGOS L3 data access until REST access is provided (using local files access).
_iagos_catalogue_df = None

def _get_iagos_datasets_catalogue():
    global _iagos_catalogue_df
    if _iagos_catalogue_df is None:
        url = pkg_resources.resource_filename('data_access', 'resources/catalogue.json')
        with open(url, 'r') as f:
            md = json.load(f)
        _iagos_catalogue_df = pd.DataFrame.from_records(md)
    return _iagos_catalogue_df

def _get_iagos_datasets(variables, bbox, period):
    print("Search IAGOS datasets...")
    variables = set(variables)
    df = _get_iagos_datasets_catalogue()
    print("done")
    variables_filter = df['ecv_variables'].map(lambda vs: bool(variables.intersection(vs)))
    lon_min, lat_min, lon_max, lat_max = bbox
    bbox_filter = (df['longitude'] >= lon_min - LON_LAT_BBOX_EPS) & (df['longitude'] <= lon_max + LON_LAT_BBOX_EPS) & \
                  (df['latitude'] >= lat_min - LON_LAT_BBOX_EPS) & (df['latitude'] <= lat_max + LON_LAT_BBOX_EPS)
    df = df[variables_filter & bbox_filter].explode('layer', ignore_index=True)
    df['title'] = df['title'] + ' in ' + df['layer']
    df['selector'] = 'layer:' + df['layer']
    df = df[['title', 'urls', 'ecv_variables', 'time_period', 'platform_id', 'RI', 'selector']]
    return df

def filter_datasets_on_stations(datasets_df, stations_short_name):
    """
    Filter datasets on stations by their short names.
    :param datasets_df: pandas.DataFrame with datasets metadata (in the format returned by get_datasets function)
    :param stations_short_name: list of str; short names of stations
    :return: pandas.DataFrame
    """
    return datasets_df[datasets_df['platform_id'].isin(stations_short_name)]

def filter_datasets_on_vars(datasets_df, var_codes):
    """
    Filter datasets which have at least one variables in common with var_codes.
    :param datasets_df: pandas.DataFrame with datasets metadata (in the format returned by get_datasets function)
    :param var_codes: list of str; variables codes
    :return: pandas.DataFrame
    """
    var_codes = set(var_codes)
    mask = datasets_df['var_codes'].apply(lambda vc: not var_codes.isdisjoint(vc))
    return datasets_df[mask]

def generate_id(url):
    return re.sub(r"[^a-z0-9]","",url.lower())

def get_dataset_from_cache(ri, id):
    cache_path = CACHE_DIR / f'data_{ri}.pkl'
    m = mmapdict(str(cache_path))
    return m[id]

def read_dataset(ri, url, ds_metadata):
    if isinstance(url, (list, tuple)):
        #print("list_urls=" + str(url))
        #if len(url) > 1:
        #    print("Multiple urls for this dataset")
        ds = None
        for single_url in url:
            ds = read_dataset(ri, single_url, ds_metadata)
            if ds is not None:
                break
        return ds

    if isinstance(url, dict):      
        print("dict_urls=" + str(url))
        if ri.lower() == "actris": # Only reading 'opendap' urls for ACTRIS.
            if url['type'] != None and url['type'] != "opendap":
                print('ACTRIS URL ignored, not opendap')
                return None          
        
        # if ri.lower() == "sios": # Only reading 'opendap' urls for SIOS.
        #     if url['type'] != None and url['type'] != "opendap":
        #         print('SIOS URL ignored, not opendap')
        #         return None          
        return read_dataset(ri, url['url'], ds_metadata)

    if not isinstance(url, str):
        raise ValueError(f'url must be str; got: {url} of type={type(url)}')

    print("single url=" + str(url))  
    ri = ri.lower()
    
    # generating unique identifier for the dataset from URL, lower and removing special characters.
    dataset_id = generate_id(url)
    cache_path = CACHE_DIR / f'data_{ri}.pkl'
    m = mmapdict(str(cache_path))
    print(ds_metadata['ecv_variables_filtered'])
    if ri == 'actris':
        if dataset_id not in m:
            ds = _ri_query_module_by_ri[ri].read_dataset(url, ds_metadata['ecv_variables_filtered'])  
            ds = ds.load().copy()
            if ds is None:
                print("ACTRIS dataset couldn't be loaded")
                return None        
            m[dataset_id] = ds
        else:
            ds = m[dataset_id]
    elif ri == 'icos':
        if dataset_id not in m:
            ds = _ri_query_module_by_ri[ri].read_dataset(url)
            m[dataset_id] = ds
        else:
            ds = m[dataset_id]
        vars_long = get_vars_long()
        variables_names_filtered = list(vars_long.join(
            pd.DataFrame(index=ds_metadata['std_ecv_variables_filtered']),
            on='std_ECV_name',
            how='inner')['variable_name'].unique())
        variables_names_filtered = [v for v in ds if v in variables_names_filtered]
        ds_filtered = ds[['TIMESTAMP'] + variables_names_filtered].compute()
        ds = ds_filtered.assign_coords({'index': ds['TIMESTAMP']}).rename({'index': 'time'}).drop_vars('TIMESTAMP')
    elif ri == 'sios':
        if dataset_id not in m:
            ds = _ri_query_module_by_ri[ri].read_dataset(url, ds_metadata['ecv_variables_filtered'],  [None,None], [None, None, None, None])
            m[dataset_id] = ds
        else:
            ds = m[dataset_id]
    elif ri == 'iagos':
        data_path = pathlib.Path(pkg_resources.resource_filename('data_access', 'resources/iagos_L3_postprocessed'))
        ds = xr.open_dataset(data_path / url)
        if 'selector' in ds_metadata and ds_metadata['selector'] is not np.nan and bool(ds_metadata['selector']):
            dim, *coord = ds_metadata['selector'].split(':')
            coord = ':'.join(coord)
            ds = ds.sel({dim: coord})
        std_ecv_to_vcode = {
            'Carbon Monoxide': 'CO_mean',
            'Ozone': 'O3_mean',
        }
        vs = [std_ecv_to_vcode[v] for v in ds_metadata['std_ecv_variables_filtered']]
        ds = ds[vs].load()
    else:
        raise ValueError(f'unknown RI={ri}')
        
    res = {}
    if ds is not None:
        for v, da in ds.items():
            res[v] = da
    return res, dataset_id
        
#! same order as in _RIs
_GET_DATASETS_BY_RI.update(zip(_RIS, (_get_actris_datasets, _get_iagos_datasets, _get_icos_datasets, _get_sios_datasets)))

if __name__ == "__main__":
    pass