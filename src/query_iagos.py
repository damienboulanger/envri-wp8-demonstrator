import requests
from requests.exceptions import HTTPError

REST_URL_STATIONS="http://iagos-data.fr/services/rest/airports/list?format=json&level=2"
REST_URL_VARIABLES="http://iagos-data.fr/services/rest/parameters/list?format=json"

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
    "Carbon monoxide" : [ "mole_fraction_of_carbon_monoxide_in_air" ],
    "NO2" : [ "mole_fraction_of_nitrogen_dioxide_in_air" ]
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
            if int(item['profiles_number'] > 100):
                station={ 'short_name': item['iata_code'], 'long_name': item['name'], 'longitude': item['longitude'], 'latitude': item['latitude'], 'altitude': item['altitude']  }
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
        for item in jsonResponse:
            if(item['CF_name'] in MAPPING_IAGOS_ECV):
                variable={ 'variable_name': item['CF_name'], 'ECV_name': MAPPING_IAGOS_ECV[item['CF_name']] }
                ret.append(variable)
        return ret    
    except HTTPError as http_err:
        print(f'HTTP error occurred: {http_err}')
    except Exception as err:
        print(f'Other error occurred: {err}')
        
def query_datasets(variables_list, temporal_extent, spatial_extent):
    return

def read_dataset(dataset_id, variables_list, temporal_extent, spatial_extent):
    return
    
if __name__ == "__main__":
    print(get_list_platforms())
    print(get_list_variables())

