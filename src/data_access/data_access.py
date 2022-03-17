"""
This module provides a unified API for access to metadata and datasets from ACTRIS, IAGOS, SIOS and ICOS RI's.
At the moment, the access to ICOS RI is implemented here.
"""

import numpy as np
import pandas as pd
import logging
import pathlib
import datetime
from datetime import date

from . import query_actris
from . import query_iagos
from . import query_icos
from . import query_sios


CACHE_DIR = pathlib.Path('cache')

logger = logging.getLogger(__name__)


# for caching purposes
# TODO: do it properly
_stations = None
_variables = None


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
}


_var_codes_by_ECV = pd.Series(VARIABLES_MAPPING, name='code')
_ECV_by_var_codes = pd.Series({v: k for k, v in VARIABLES_MAPPING.items()}, name='ECV')


def _get_ri_query_module_by_ri(ris=None):
    if ris is None:
        ris = ['actris', 'iagos', 'icos', 'sios']
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
        cache_path = pathlib.PurePath(CACHE_DIR, f'stations_{ri}.pkl')
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
            elif ri == 'sios':
                stations_df = stations_df.rename(columns={'URI': 'uri'})
                stations_df['RI'] = 'SIOS'
                stations_df['country'] = np.nan
                stations_df['theme'] = np.nan
                stations_dfs.append(stations_df)                
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
            cache_path = pathlib.PurePath(CACHE_DIR, f'variables_{ri}.pkl')
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


def get_datasets(variables, lon_min=None, lon_max=None, lat_min=None, lat_max=None, start=None, end=None):
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
    if None in [lon_min, lon_max, lat_min, lat_max]:
        bbox = []
    else:
        bbox = [lon_min, lat_min, lon_max, lat_max]
    if None in [start, end]:
        period = []
    else:
        period = [start, end]

    datasets_dfs = []
    for get_ri_datasets in (_get_actris_datasets, _get_icos_datasets, _get_sios_datasets):
        df = get_ri_datasets(variables, bbox, period)
        if df is not None:
            datasets_dfs.append(df)

    if not datasets_dfs:
        return None
    datasets_df = pd.concat(datasets_dfs, ignore_index=True)

    vars_long = get_vars_long()
    def var_names_to_var_codes(var_names):
        # TODO: performance issues
        var_names = np.unique(var_names)
        codes1 = vars_long[['ECV_name', 'code']].join(pd.DataFrame(index=var_names), on='ECV_name', how='inner')
        codes1 = codes1['code'].unique()
        codes2 = vars_long[['variable_name', 'code']].join(pd.DataFrame(index=var_names), on='variable_name', how='inner')
        codes2 = codes2['code'].unique()
        codes = np.concatenate([codes1, codes2])
        return np.sort(np.unique(codes)).tolist()
    def var_names_to_std_ecv_by_var_name(var_names):
        # TODO: performance issues
        var_names = np.unique(var_names)
        std_ECV_names1 = vars_long[['ECV_name', 'std_ECV_name']].join(pd.DataFrame(index=var_names), on='ECV_name', how='inner')
        std_ECV_names1 = std_ECV_names1.rename(columns={'ECV_name': 'name'}).drop_duplicates(ignore_index=True)
        std_ECV_names2 = vars_long[['variable_name', 'std_ECV_name']].join(pd.DataFrame(index=var_names), on='variable_name', how='inner')
        std_ECV_names2 = std_ECV_names2.rename(columns={'variable_name': 'name'}).drop_duplicates(ignore_index=True)
        std_ECV_names = pd.concat([std_ECV_names1, std_ECV_names2], ignore_index=True).drop_duplicates(ignore_index=True)
        return std_ECV_names
    datasets_df['var_codes'] = datasets_df['ecv_variables'].apply(lambda var_names: var_names_to_var_codes(var_names))
    datasets_df['ecv_variables_filtered'] = datasets_df['ecv_variables'].apply(lambda var_names:
                                                                               var_names_to_std_ecv_by_var_name(var_names)\
                                                                               .join(pd.DataFrame(index=variables), on='std_ECV_name', how='inner')['name']\
                                                                               .tolist())
    datasets_df['std_ecv_variables_filtered'] = datasets_df['ecv_variables'].apply(lambda var_names:
                                                                                   [v for v in var_names_to_std_ecv_by_var_name(var_names)['std_ECV_name'].tolist() if v in variables])
    req_var_codes = set(VARIABLES_MAPPING[v] for v in variables if v in VARIABLES_MAPPING)
    datasets_df['var_codes_filtered'] = datasets_df['var_codes']\
        .apply(lambda var_codes: ', '.join([vc for vc in var_codes if vc in req_var_codes]))

    # datasets_df['url'] = datasets_df['urls'].apply(lambda x: x[-1]['url'])  # now we take the last proposed url; TODO: see what should be a proper rule (first non-empty url?)
    datasets_df['time_period_start'] = datasets_df['time_period'].apply(lambda x: pd.Timestamp(x[0]))
    datasets_df['time_period_end'] = datasets_df['time_period'].apply(lambda x: pd.Timestamp(x[1]))
    datasets_df['platform_id_RI'] = datasets_df['platform_id'] + ' (' + datasets_df['RI'] + ')'

    # return datasets_df.drop(columns=['urls', 'time_period'])
    return datasets_df.drop(columns=['time_period']).rename(columns={'urls': 'url'})


def _get_actris_datasets(variables, bbox, period):
    datasets = query_actris.query_datasets(variables=variables, temporal_extent=period, spatial_extent=bbox)
    if not datasets:
        return None
    datasets_df = pd.DataFrame.from_dict(datasets)

    # fix title for ACTRIS datasets: remove time span
    datasets_df['title'] = datasets_df['title'].str.slice(stop=-62)

    datasets_df['RI'] = 'ACTRIS'
    return datasets_df


def _get_icos_datasets(variables, bbox, period):
    datasets = query_icos.query_datasets(variables=variables, temporal=period, spatial=bbox)
    if not datasets:
        return None
    datasets_df = pd.DataFrame.from_dict(datasets)
    datasets_df['RI'] = 'ICOS'
    return datasets_df

def _get_sios_datasets(variables, bbox, period):
    bbox2 = bbox
    if len(bbox) == 0:
        bbox2 = [None,None,None,None]
    datasets = query_sios.query_datasets(variables_list=variables, temporal_extent=period, spatial_extent=bbox2)
    if not datasets:
        return None
    for ds in datasets:
        ds['time_period'][1] = datetime.datetime.today().strftime('%Y-%m-%dT%H:%M:%S') #'2021-01-31T23:00:00Z'
    datasets_df = pd.DataFrame.from_dict(datasets)
    datasets_df['RI'] = 'SIOS'
    return datasets_df

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


# def _to_hashable(x):
#     """
#     Convert a structure to a hashable one.
#     :param x: list of dicts of list of ...
#     :return: a hashable structure
#     """
#     try:
#         hash(x)
#         return x
#     except TypeError:
#         if isinstance(x, (tuple, list)):
#             return tuple(_to_hashable(i) for i in x)
#         elif isinstance(x, dict):
#             return frozendict({k: _to_hashable(v) for k, v in x.items()})
#         else:
#             raise TypeError(type(x))


# def _read_dataset(ri, url):
#     _ri_query_module[ri].
#     path = str(CACHE_DS_DIR / url.split('/')[-1])
#     res = requests.get(url)
#     with open(path, 'wb') as f:
#         f.write(res.content)
#     _cache_ds_dict[url] = path


def read_dataset(ri, url, ds_metadata):
    if isinstance(url, (list, tuple)):
        ds = None
        for single_url in url:
            ds = read_dataset(ri, single_url, ds_metadata)
            if ds is not None:
                break
        return ds

    if isinstance(url, dict):
        return read_dataset(ri, url['url'], ds_metadata)

    if not isinstance(url, str):
        raise ValueError(f'url must be str; got: {url} of type={type(url)}')

    ri = ri.lower()
    # path = _ri_cache_ds_dict[ri].get(url)
    # if path is None:
    #     ds, path = _read_dataset(ri, url)
    #     if ds is not None:
    #         _ri_cache_ds_dict[ri][url] = path
    #         with open(RI_CACHE_DS_DICT_FILE[ri], 'a') as f:
    #             yaml.safe_dump({url: str(path)}, f)
    #     return ds
    # else:
    #     return xr.load_dataset(path)
    if ri == 'actris':
        return _ri_query_module_by_ri[ri].read_dataset(url, ds_metadata['ecv_variables_filtered'])
    elif ri == 'icos':
        ds = _ri_query_module_by_ri[ri].read_dataset(url)
        vars_long = get_vars_long()
        variables_names_filtered = list(vars_long.join(
            pd.DataFrame(index=ds_metadata['std_ecv_variables_filtered']),
            on='std_ECV_name',
            how='inner')['variable_name'].unique())
        variables_names_filtered = [v for v in ds if v in variables_names_filtered]
        ds_filtered = ds[['TIMESTAMP'] + variables_names_filtered].compute()
        return ds_filtered.assign_coords({'index': ds['TIMESTAMP']}).rename({'index': 'time'}).drop_vars('TIMESTAMP')
