import requests
from requests.exceptions import HTTPError
import xarray as xr   

REST_URL_STATIONS="https://services.iagos-data.fr/prod/v2.0/airports/public?active=true"
REST_URL_VARIABLES="https://services.iagos-data.fr/prod/v2.0/parameters/public"
REST_URL_SEARCH="http://iagos-data.fr/services/rest/tracks/list?level=2"
REST_URL_DOWNLOAD="http://iagos-data.fr/services/rest/download/timeseries"
REST_URL_KEY="http://iagos-data.fr/services/rest/auth"
STATIC_PARAMETERS=["latitude", "longitude", "air_pressure", "barometric_altitude"]
MAPPING_ECV_IAGOS={
    "Temperature (near surface)" : [ "air_temperature" ],
    "Water Vapour (surface)" : [ "mole_fraction_of_water_vapor_in_air", "relative_humidity" ],
    "Temperature (upper-air)" : [ "air_temperature" ],
    "Water Vapour (upper air)" : [ "mole_fraction_of_water_vapor_in_air, relative_humidity" ],
    "Cloud Properties" : [ "number_concentration_of_cloud_liquid_water_particles_in_air" ],
    "Wind speed and direction (upper-air)" : [ "wind_speed, wind_from_direction" ],
    "Carbon Dioxide" : [ "mole_fraction_of_carbon_dioxide_in_air" ],
    "Methane" : [ "mole_fraction_of_methane_in_air" ],
    "Ozone" : [ "mole_fraction_of_ozone_in_air" ],
    "Carbon Monoxide" : [ "mole_fraction_of_carbon_monoxide_in_air" ],
    "NO2" : [ "mole_fraction_of_nitrogen_dioxide_in_air" ]
}
MAPPING_CF_IAGOS={
    "air_temperature" : "air_temp",
    "mole_fraction_of_water_vapor_in_air" : "H2O_gas",
    "relative_humidity" : "RHL",
    "mole_fraction_of_methane_in_air" : "CH4",
    "number_concentration_of_cloud_liquid_water_particles_in_air" : "cloud",
    "mole_fraction_of_carbon_monoxide_in_air" : "CO",
    "mole_fraction_of_carbon_dioxide_in_air" : "CO2",
    "mole_fraction_of_nitrogen_dioxide_in_air" : "NO2",
    "mole_fraction_of_ozone_in_air" : "O3"
}

def reverse_mapping(mapping):
    ret={}
    for key, values in mapping.items():
        for value in values:
            if value not in ret:
                ret[value] = []
            ret[value].append(key)
    return ret
MAPPING_IAGOS_ECV=reverse_mapping(MAPPING_ECV_IAGOS)

def get_list_platforms():
    try:
        response = requests.get(REST_URL_STATIONS)
        response.raise_for_status()
        jsonResponse = response.json()
        ret = []
        for item in jsonResponse:
            if int(item['nb_profiles'] > 100) and item['latitude'] < 71 and item['latitude'] > 27 and item['longitude'] < 62 and item['longitude'] > -26:
                station={ 'short_name': item['iata_code'], 'long_name': item['city'], 'longitude': item['longitude'], 'latitude': item['latitude'], 'altitude': item['altitude']  }
                ret.append(station)
        return ret    
    except HTTPError as http_err:
        print(f'HTTP error occurred: {http_err}')
    except Exception as err:
        print(f'Other error occurred: {err}')

def get_list_variables():
    try:
        response = requests.get(REST_URL_VARIABLES)
        response.raise_for_status()
        jsonResponse = response.json()
        ret = []
        done = []
        for item in jsonResponse:
            if(item['cf_standard_name'] in MAPPING_IAGOS_ECV and item['cf_standard_name'] not in done):
                variable={ 'variable_name': item['cf_standard_name'], 'ECV_name': MAPPING_IAGOS_ECV[item['cf_standard_name']] }
                done.append(item['cf_standard_name'])
                ret.append(variable)
        return ret    
    except HTTPError as http_err:
        print(f'HTTP error occurred: {http_err}')
    except Exception as err:
        print(f'Other error occurred: {err}')
        
def query_datasets(variables_list, temporal_extent, spatial_extent): #TODO : setup THREDDS server
    parameters = []
    for param in variables_list:
        if param in MAPPING_ECV_IAGOS:
            for p in MAPPING_ECV_IAGOS[param]:
                    parameters.append(MAPPING_CF_IAGOS[p])
    fromm=temporal_extent[0]
    to=temporal_extent[1]
    bbox=','.join(map(str, spatial_extent))
    try:
        url = REST_URL_SEARCH + "&from=" + fromm + "&to=" + to + "&bbox=" + bbox + "&parameters=" + ','.join(parameters)
        response = requests.get(url)
        response.raise_for_status()
        jsonResponse = response.json()
        ret = []
        for item in jsonResponse['features']:
            flight=item['properties']['flight']
            ret.append(REST_URL_DOWNLOAD + "/" + flight)
        return ret    
    except HTTPError as http_err:
        print(f'HTTP error occurred: {http_err}')
    except Exception as err:
        print(f'Other error occurred: {err}')

def read_dataset(dataset_id, variables_list, temporal_extent, spatial_extent):
    response = requests.get(REST_URL_KEY + "/tech@envri-fair.eu") # setup ENVRI account
    key=response.text
    results = requests.get(dataset_id + "?api_key=" + key + "&format=nc")
    with open('/tmp/fic.nc', 'wb') as f:
        f.write(results.content)
    ds = xr.open_dataset('/tmp/fic.nc')
    varlist = []
    for varname, da in ds.data_vars.items():
        if 'standard_name' in da.attrs and (da.attrs['standard_name'] in variables_list or da.attrs['standard_name'] in STATIC_PARAMETERS):
            varlist.append(varname)
    ds = ds[varlist] 
    return ds
    
if __name__ == "__main__":
    print(get_list_platforms())

