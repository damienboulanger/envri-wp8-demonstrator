from subprocess import list2cmdline
from pandas import concat
import requests
import xarray as xr 
import numpy as np
from requests.exceptions import HTTPError
import os

dir_path = os.path.dirname(os.path.realpath(__file__))

#provide the list of platforms for the demonstrator
def get_list_platforms():
    cnr_platforms = get_list_platforms_cnr()
    metno_platforms = get_list_platforms_metno()
    
    return cnr_platforms + metno_platforms

#provide the mapping between locally used variables CF standard names and ECV
def get_list_variables():
    cnr_list_variables = get_list_variables_cnr()
    metno_list_variables = get_list_variables_metno()

    list_variables = cnr_list_variables

    for x in metno_list_variables:
        if x['variable_name'] not in list(map(lambda i: i['variable_name'], list_variables)):
            list_variables.append(x)

    return list_variables

def query_datasets(variables_list=[], temporal_extent=[None,None], spatial_extent=[None,None,None,None]):
    cnr_datasets = query_datasets_cnr(variables_list, temporal_extent, spatial_extent)
    metno_datasets = query_datasets_metno(variables_list, temporal_extent, spatial_extent)

    datasets = cnr_datasets + metno_datasets

    return datasets

# we will use the opendap url as the dataset_id to distinguish between cnr and metno datasets
def read_dataset(dataset_id,variables_list=[], temporal_extent=[None,None], spatial_extent=[None,None,None,None]):
  # Variable alias, just for convenience
  dataset_opendap_url = dataset_id
  dataset = None

  if ("met.no" in dataset_opendap_url):
    dataset = read_dataset_metno(dataset_id, variables_list, temporal_extent, spatial_extent)
  
  if ("iadc.cnr.it" in dataset_opendap_url):
    dataset = read_dataset_cnr(dataset_id, variables_list, temporal_extent, spatial_extent)
  
  # swap dimension from row to time.
  if "row" in dataset.dims:
      return dataset.swap_dims({"row":"time"})
  else:
      return dataset



''' ********** MET.NO ************ '''



#mapping between cf standard names and ECV variables
MAPPING_ECV_VARIABLES_METNO = {'surface_air_pressure':'Pressure (surface)',
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
                          #'keywords' : [element.strip() for element in data['keywords_keyword'].split(',') if element.strip() in MAPPING_ECV_VARIABLES_METNO.keys()],
                          'keywords' : [element.strip() for element in data['keywords_keyword'].split(',') if element.strip() in MAPPING_ECV_VARIABLES_METNO.keys()] if data['keywords_keyword'] != '' else ['surface_air_pressure', 'air_temperature', 'wind_from_direction', 'wind_speed', 'relative_humidity'],
                          'urls': [{'url' : 'https://sios-svalbard.org/metsis/metadata/'+data['metadata_identifier'].replace('no.met.adc:','no-met-adc-'), 'type': 'landing_page'},
                                   {'url' : data['data_access_url_opendap'], 'type' : 'opendap'},
                                   {'url' : data['data_access_url_http'], 'type' : 'data_file'}]
                         })
    return(sios_info)

#provide the list of platforms for the demonstrator
def get_list_platforms_metno():
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
def get_list_variables_metno():
    variables = []
    mapping = MAPPING_ECV_VARIABLES_METNO
    for k,v in mapping.items():
        variables.append({'variable_name' : k, 'ECV_name' : [v]})

    return(variables)

def query_datasets_metno(variables_list=[], temporal_extent=[None,None], spatial_extent=[None,None,None,None]):
    filtered_dataset_info = []
    resources = get_sios_info()
    for resource in resources:
        if ((not temporal_extent[1] or resource['date_start'] <= temporal_extent[1])
                and (not temporal_extent[0] or not resource['date_end'] or resource['date_end'] >= temporal_extent[0])
                and (not spatial_extent[0] or resource['longitude'] >= spatial_extent[0])
                and (not spatial_extent[2] or resource['longitude'] <= spatial_extent[2])
                and (not spatial_extent[1] or resource['latitude'] >= spatial_extent[1])
                and (not spatial_extent[3] or resource['latitude'] <= spatial_extent[3])
                and (len(variables_list) == 0 or [k for k in resource['keywords'] if MAPPING_ECV_VARIABLES_METNO[k] in variables_list])):
            filtered_dataset_info.append({'title' : resource['title'],
                                          'urls' : resource['urls'],
                                          'ecv_variables': list(set([MAPPING_ECV_VARIABLES_METNO[k] for k in resource['keywords']])),
                                          'time_period': [resource['date_start'], resource['date_end']],
                                          'platform_id': resource['platform_short_name']})
    return(filtered_dataset_info)

def read_dataset_metno(dataset_id,variables_list=[], temporal_extent=[None,None], spatial_extent=[None,None,None,None]):
    try:
        ds = xr.open_dataset(dataset_id)
        cf_var = [k for k,v in MAPPING_ECV_VARIABLES_METNO.items() if v in variables_list]
        if len(cf_var) > 0:
            varlist = []
            for varname, da in ds.data_vars.items():
                if 'standard_name' in da.attrs and (da.attrs['standard_name'] in cf_var or da.attrs['standard_name'] == 'latitude' or da.attrs['standard_name'] == 'longitude'):
                    varlist.append(da.attrs['standard_name'])
            standard_name = lambda v: v in varlist
            ds = ds.filter_by_attrs(standard_name=standard_name)
        if (temporal_extent[0] or temporal_extent[1]):
            if temporal_extent[0]:
                start = temporal_extent[0]
                s = np.datetime64(start[:-1], 'ns')
                mask_start = (ds.time >= s)
                ds = ds.where(mask_start, drop=True)
            if temporal_extent[1]:
                end = temporal_extent[1]
                e = np.datetime64(end[:-1], 'ns')
                mask_end = (ds.time <= e)
                ds = ds.where(mask_end, drop=True)
        ds = ds.where(ds != 9.96921e+36)
        return ds
    except HTTPError as http_err:
        print(f'HTTP error occurred: {http_err}')
    except Exception as err:
        print(f'Other error occurred: {err}')




''' **************** CNR ***************** '''




MAPPING_ECV_VARIABLES_CNR = {'air_pressure':'Pressure (surface)',
                         'wind_speed':'Surface Wind Speed and direction',
                         'wind_from_direction':'Surface Wind Speed and direction', 
                         'air_temperature':'Temperature (near surface)',
                         'relative_humidity':'Water Vapour (surface)', 
                         'equivalent_thickness_at_stp_of_atmosphere_ozone_content':'Ozone',
                         'surface_net_downward_radiative_flux':'Surface Radiation Budget'}

def get_iadc_datasets():
    datasets = []
    endpoint = 'https://data.iadc.cnr.it/erddap/search/advanced.json'
    query = endpoint + '?searchFor=ENVRI'
    response = requests.get(query)

    table = response.json()['table']
    index = table['columnNames'].index('Dataset ID') # Perché il JSON è formattato così
    for row in table['rows']:
      datasets.append(row[index])
    
    return(datasets)

def get_list_platforms_cnr():
  platforms = []
  datasets = get_iadc_datasets()

  for datasetID in datasets:
    metadata = get_metadata_from_dataset(datasetID)
    platform = { 'short_name': metadata['ENVRI_platform_short_name'],
                'latitude':  metadata['geospatial_lat_max'],
                'longitude':  metadata['geospatial_lon_max'],
                'long_name':  metadata['ENVRI_platform_long_name'],
                'URI':  metadata['ENVRI_platform_URI'],
                'ground_elevation':  None }

    platforms.append(platform)

  return platforms

def get_list_variables_cnr():
    variables = []
    mapping = MAPPING_ECV_VARIABLES_CNR
    for k,v in mapping.items():
        variables.append({'variable_name' : k, 'ECV_name' : [v] })

    return(variables)

def query_datasets_cnr(variables_list=[], temporal_extent=[None,None], spatial_extent=[None,None,None,None]):
  # This works but needs to be optimized
  datasets = []

  endpoint = 'https://data.iadc.cnr.it/erddap/search/advanced.json'
  query = endpoint + f'?searchFor=ENVRI&minLon={spatial_extent[0]}&minLat={spatial_extent[1]}&maxLon={spatial_extent[2]}&maxLat={spatial_extent[3]}&minTime={temporal_extent[0]}&maxTime={temporal_extent[1]}'
  response = requests.get(query)

  # No datasets for the query
  if response.status_code == 404:
    return datasets
    
  table = response.json()['table']
  id = table['columnNames'].index('Dataset ID')
  tabledap = table['columnNames'].index('tabledap')

  for row in table['rows']:
    metadata = get_metadata_from_dataset(row[id])
    standard_names = get_standard_names_from_dataset(row[id])

    ecvs = []
    for sn in standard_names:
      if sn in MAPPING_ECV_VARIABLES_CNR.keys():
        ecvs.append(MAPPING_ECV_VARIABLES_CNR[sn])

    datasets.append({
      'title': metadata['title'],
      'urls' : [{'url': metadata['infoUrl'] , 'type':'landing_page'}, {'url': row[tabledap] , 'type':'opendap'}, {'url': row[tabledap]+'.nc' , 'type':'data_file'}],
      'ecv_variables' : list(dict.fromkeys(ecvs)),
      'time_period': [metadata['time_coverage_start'], metadata['time_coverage_end']],
      'platform_id': metadata['ENVRI_platform_short_name']
    })

  filtered_datasets = list(filter(lambda x : set(variables_list) & set(x['ecv_variables']), datasets))
  
  return filtered_datasets

def read_dataset_cnr(dataset_opendap_url, variables_list=[], temporal_extent=[None,None], spatial_extent=[None, None, None, None]):
  
  # get dataset id from opendap_url
  dataset_id = dataset_opendap_url.split('/')[-1]
  erddap_vars = get_erddap_variables_from_ecv_list(dataset_id, variables_list)

  # No datasets found with this variables
  if erddap_vars == []:
    return None
  
  endpoint = dataset_opendap_url + '.nc'
  #query = endpoint + f'?station_id,latitude,longitude,time,{",".join(erddap_vars)}&latitude>={spatial_extent[1]}&latitude<={spatial_extent[3]}&longitude>={spatial_extent[0]}&longitude<={spatial_extent[2]}&time>={temporal_extent[0]}&time<={temporal_extent[1]}'
  
  query = endpoint + f'?station_id,latitude,longitude,time,{",".join(erddap_vars)}'

  if temporal_extent is not None:
    if temporal_extent[0] is not None:
      query = query + f'&time>={temporal_extent[0]}'

    if temporal_extent[1] is not None:
      query = query + f'&time<={temporal_extent[1]}'
    
  if spatial_extent is not None:
    if spatial_extent[0] is not None:
      query = query + f'&longitude>={spatial_extent[0]}'

    if spatial_extent[1] is not None:
      query = query + f'&latitude>={spatial_extent[1]}'
      
    if spatial_extent[2] is not None:
      query = query + f'&longitude<={spatial_extent[2]}'

    if spatial_extent[3] is not None:
      query = query + f'&latitude<={spatial_extent[3]}'

  response = requests.get(query)
  # No datasets for the query
  if response.status_code == 404:
    return None

  ds_disk = xr.open_dataset(response.content)
  return ds_disk

### Utils ###        

def get_reverse_var_map():
  ecv_reverse = {}
  for k,v in MAPPING_ECV_VARIABLES_CNR.items():
    keys = []
    for k1,v1 in MAPPING_ECV_VARIABLES_CNR.items():
      if v == v1:
        keys.append(k1)
        ecv_reverse[v] = keys
  
  return ecv_reverse

def get_metadata_from_dataset(datasetID):
  query = f'https://data.iadc.cnr.it/erddap/info/{datasetID}/index.json'
  response = requests.get(query)

  table = response.json()['table']
    
  # Indexes for rows in json file
  variable_name = table['columnNames'].index('Variable Name') 
  attribute_name = table['columnNames'].index('Attribute Name') 
  value = table['columnNames'].index('Value')
  
  metadata = {}

  for row in table['rows']:
    if row[variable_name] == 'NC_GLOBAL':
      metadata[row[attribute_name]] = row[value]
    
  return metadata

def get_standard_names_from_dataset(datasetID):
  standard_names=[]
  query = f'https://data.iadc.cnr.it/erddap/info/{datasetID}/index.json'
  response = requests.get(query)

  table = response.json()['table']
    
  # Indexes for rows in json file
  attribute_name = table['columnNames'].index('Attribute Name') 
  value = table['columnNames'].index('Value')
  
  for row in table['rows']:
    if row[attribute_name] == 'standard_name':
      standard_names.append(row[value])
  
  # return list removing duplicates  
  return list(dict.fromkeys(standard_names))

def get_erddap_variables_from_ecv_list(datasetID, variable_list):
  erddap_variables = []
  query = f'https://data.iadc.cnr.it/erddap/info/{datasetID}/index.json'
  response = requests.get(query)

  if response.status_code == 404:
    return erddap_variables

  table = response.json()['table']
  
  reversed_map = get_reverse_var_map()
  
  # get standard names equivalent from variable_list
  sn_from_variable_list = []
  for k,v in reversed_map.items():
    if k in variable_list:
      sn_from_variable_list.extend(v)
  
  # Indexes for rows in json file
  variable_name = table['columnNames'].index('Variable Name') 
  attribute_name = table['columnNames'].index('Attribute Name') 
  value = table['columnNames'].index('Value')
  
  # get erddap variable names from selected standard names
  for row in table['rows']:
    if row[attribute_name] == 'standard_name' and row[value] in sn_from_variable_list:
      erddap_variables.append(row[variable_name])
  
  return erddap_variables



if __name__ == "__main__":
  #print(get_list_platforms())
  #print(get_list_variables())
  #print(query_datasets(['Ozone'], ['2009-09-20T00:00:00Z','2021-09-20T00:00:00Z'], [-22, 37, 52, 88]))
  print(read_dataset('https://data.iadc.cnr.it/erddap/tabledap/ozone-barentsburg', ['Ozone']))
  #print(read_dataset('https://data.iadc.cnr.it/erddap/tabledap/ozone-barentsburg.nc', ['Ozone']))
  #print(read_dataset('https://thredds.met.no/thredds/fileServer/met.no/observations/stations/SN99754.nc',['Temperature (near surface)', 'Water Vapour (surface)', 'Pressure (surface)', 'Surface Wind Speed and direction'],  [None,None], [None, None, None, None]))
  #print(read_dataset('https://thredds.met.no/thredds/dodsC/met.no/observations/stations/SN99938.nc', ['Pressure (surface)'],  ['2009-09-20T00:00:00Z','2021-09-20T00:00:00Z'], [None, None, None, None]))
  #print(get_iadc_datasets())
