# <h1>Weather station (land fixed) from The Norwegian Meteorologial Institue included in the SIOS catalogue</h1>

import requests
import xarray as xr 
from requests.exceptions import HTTPError

#mapping between cf standard names and ECV variables
MAPPING_ECV_VARIABLES = {'surface_air_pressure':'Pressure (surface)',
                         'wind_speed':'Surface Wind Speed and direction',
                         'wind_from_direction':'Surface Wind Speed and direction',
                         'air_temperature':'Temperature (near surface)',
                         'relative_humidity':'Water Vapour (surface)',
                         #'precipitation_amount':'Precipitation'
                        }

#query the REST endpoint to extract Norwegian weather stations indexed in the sios-svalbard.org data portal
def get_sios_info():
    sios_info = []
    endpoint = 'https://sios-svalbard.org/rest/stations/data.json'
    query = endpoint + '?fulltext="Norwegian weather station"'
    n_pages = (requests.get(query)).json()['pager']['total_pages']
    for p in range(0, n_pages):
        response = requests.get(query+'&page='+str(p))
        for data in response.json()['rows']:
            sios_info.append({'title': data['title'],
                          'id': data['metadata_identifier'],
                          'latitude': float(data['geographic_extent_rectangle_south']),
                          'longitude': float(data['geographic_extent_rectangle_west']),
                          'platform_short_name': data['platform_short_name'],
                          'platform_long_name': data['platform_long_name'],
                          'platform_resource': data['platform_resource'],
                          'date_start': data['temporal_extent_start_date'],
                          'date_end': data['temporal_extent_end_date'],
                          #'keywords' : [element.strip() for element in data['keywords_keyword'].split(',') if element.strip() in MAPPING_ECV_VARIABLES.keys()],
                          'keywords' : [element.strip() for element in data['keywords_keyword'].split(',') if element.strip() in MAPPING_ECV_VARIABLES.keys()] if data['keywords_keyword'] != '' else ['surface_air_pressure', 'air_temperature', 'wind_from_direction', 'wind_speed', 'relative_humidity'],
                          'urls': [{'url' : 'https://sios-svalbard.org/metsis/metadata/'+data['metadata_identifier'], 'type': 'landing_page'},
                                   {'url' : data['data_access_url_opendap'], 'type' : 'opendap'},
                                   {'url' : data['data_access_url_http'], 'type' : 'data_file'}]
                         })
    return(sios_info)

#provide the list of platforms for the demonstrator
def get_list_platforms():
    platform_info = []
    resources = get_sios_info()
    for resource in resources:
        if not any(rec['short_name'] == resource['platform_short_name'] for rec in platform_info):
            platform_info.append({'short_name' : resource['platform_short_name'],
                                  'long_name' : resource['platform_long_name'],
                                  'short_name' : resource['platform_short_name'],
                                  'latitude' : resource['latitude'],
                                  'longitude' : resource['longitude'],
                                  'URI' : resource['platform_resource']})
    return(platform_info)

#provide the mapping between locally used variables CF standard names and ECV
def get_list_variables():
    variables = []
    mapping = MAPPING_ECV_VARIABLES
    for k,v in mapping.items():
        variables.append({'variable_name' : k, 'ECV_name' : [v]})

    return(variables)

#return the urls of data which have at least one variable in the input list and are within the temporal and spatial extent
#if input is left empty all datasets will be returned
def query_datasets(variables_list=[], temporal_extent=[None,None], spatial_extent=[None,None,None,None]):
    filtered_dataset_info = []
    resources = get_sios_info()
    for resource in resources:
        if ((not temporal_extent[1] or resource['date_start'] <= temporal_extent[1])
                and (not temporal_extent[0] or not resource['date_end'] or resource['date_end'] >= temporal_extent[0])
                and (not spatial_extent[0] or resource['longitude'] >= spatial_extent[0])
                and (not spatial_extent[2] or resource['longitude'] <= spatial_extent[2])
                and (not spatial_extent[1] or resource['latitude'] >= spatial_extent[1])
                and (not spatial_extent[3] or resource['latitude'] <= spatial_extent[3])
                and (len(variables_list) == 0 or [k for k in resource['keywords'] if MAPPING_ECV_VARIABLES[k] in variables_list])):
            filtered_dataset_info.append({'title' : resource['title'],
                                          'urls' : resource['urls'],
                                          'ecv_variables': list(set([MAPPING_ECV_VARIABLES[k] for k in resource['keywords']])),
                                          'time_period': [resource['date_start'], resource['date_end']],
                                          'platform_id': resource['platform_short_name']})
    return(filtered_dataset_info)


#return an xarray for a specific opendap url with the requested variables
#if input is empty the whole dataset is returned
def read_dataset(dataset_id,variables_list=[], temporal_extent=[None,None], spatial_extent=[None,None,None,None]):
    try:
        ds = xr.open_dataset(dataset_id)

        cf_var = [k for k,v in MAPPING_ECV_VARIABLES.items() if v in variables_list]
        varlist = []
        for varname, da in ds.data_vars.items():
            if 'standard_name' in da.attrs and (da.attrs['standard_name'] in cf_var or da.attrs['standard_name'] == 'latitude' or da.attrs['standard_name'] == 'longitude'):
                varlist.append(da.attrs['standard_name'])
        standard_name = lambda v: v in varlist
        ds = ds.filter_by_attrs(standard_name=standard_name)
        return(ds)
    except HTTPError as http_err:
        print(f'HTTP error occurred: {http_err}')
    except Exception as err:
        print(f'Other error occurred: {err}')


if __name__ == "__main__":
    # <h1>Get platform info</h1>
    print(get_list_platforms())
    # <h1>Get stations variables</h1>
    print(get_list_variables())
    # <h2>Get list of datasets (example)</h2>
    print(query_datasets(['Pressure (surface)'], ['1810-03-01T03:00:00','1960-10-01T03:00:00'], [10, 70, 23, 80]))

