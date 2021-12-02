# <h1>Weather station (land fixed) from The Norwegian Meteorologial Institue included in the SIOS catalogue</h1>

import requests
import xarray as xr 

#query csw
def call_sios_csw():
    csw_info = []
    answer = False 
    while not answer: 
        response = requests.get('https://sios.csw.met.no/collections/metadata:main/items?q=Norwegian%20weather%20station&f=json')
        #print('response', response.status_code)
        if response.status_code != 500:
            answer = True
        else: 
            pass
    tot_records = response.json()['numberMatched']
    n_records = response.json()['numberReturned']
    pages = round(tot_records/n_records)
    #print(tot_records, n_records, pages)
    resources = []
    for index in range(0, pages*n_records,n_records):
        response = requests.get('https://sios.csw.met.no/collections/metadata:main/items?q=Norwegian%20weather%20station&startindex='+str(index)+'&f=json')
        for element in response.json()['features']:
            urls = element['associations']
            opendap = next(item for item in urls if item['type'] == 'OPENDAP:OPENDAP')
            download = next(item for item in urls if item['type'] == 'download')
            csw_info.append({'title' : element['properties']['title'], 
                             'id': element['id'], 
                             'urls' : {'landing page' : 'https://sios-svalbard.org/metsis/metadata/'+element['id'], 
                                       'opendap' : opendap['href'],
                                       'download' : download['href']}})

    return(csw_info)


def sios_dataset_info(url):
    #cf standard name to ECV mapping
    mapping = {'surface_air_pressure':'Pressure (surface)',
               'wind_speed':'Surface Wind Speed and direction', 
               'wind_from_direction':'Surface Wind Speed and direction', 
               'air_temperature':'Temperature (near surface)', 
               'relative_humidity':'Water Vapour (surface)'}   
    try:
        ds = xr.open_dataset(url)
    except: 
        return
    try:
        #get station name
        station_name = ds.attrs['station_name']
        wmo_id = ds.attrs['wmo_identifier']
        platform_url = 'https://oscar.wmo.int/surface/#/search/station/stationReportDetails/0-20000-0-'+wmo_id
        request_response = requests.head("https://oscar.wmo.int/surface/rest/api/stations/station?wmoIndex=0-20000-0-"+wmo_id)        
        if request_response.status_code != 200:
            platform_url = 'None'
        #get temporal extent
        start = ds.attrs['time_coverage_start']
        end = ds.attrs['time_coverage_end']
        temporal_extent = [start, end]        
        #get spatial extent
        lat0 = float(ds.attrs['geospatial_lat_min'])
        lat1 = float(ds.attrs['geospatial_lat_max'])
        lon0 = float(ds.attrs['geospatial_lon_min'])
        lon1 = float(ds.attrs['geospatial_lon_max'])
        station_info = {'short_name':station_name, 'latitude':lat0,'longitude':lon0, 'URI':platform_url}
        spatial_extent = [lon0, lat0, lon1, lat1]
        variables = []
        for varname, da in ds.data_vars.items():
            if 'standard_name' in da.attrs and da.attrs['standard_name'] in mapping:
                variables.append({'variable_name': varname, 'ECV_name': [mapping[da.attrs['standard_name']]]})
        return dict(url=url, station_info=station_info, variables=variables, temporal_extent=temporal_extent, spatial_extent=spatial_extent)
    except:
        #print("no dataset global attributes found for: ", url)
        return

# all stations info
def get_list_platforms():
    platform_info = []
    resources = call_sios_csw()
    for i in resources:
        if i['urls']['opendap']:
            dsinfo = sios_dataset_info(i['urls']['opendap'])
            if dsinfo != None:
                platform_info.append(dsinfo['station_info'])
    return (platform_info)


def get_list_variables():    
    variables = []
    mapped_variables = []
    resources = call_sios_csw()
    for i in resources:
        dsinfo = sios_dataset_info(i['urls']['opendap'])
        if dsinfo != None:
            for vdict in dsinfo['variables']:
                if vdict['variable_name'] not in mapped_variables:
                    mapped_variables.append(vdict['variable_name'])
                    variables.append(vdict)
    return (variables)

# query datasets with filters
def query_datasets(variables_list, temporal_extent, spatial_extent):
    #info = [{uri:URI, variables: [variables], time:[time], bbox:[bbox]}]
    filtered_dataset_info = []
    resources = call_sios_csw()
    start = str(temporal_extent[0])
    stop = str(temporal_extent[1])
    for i in resources:
        dsinfo = sios_dataset_info(i['urls']['opendap'])
        if dsinfo != None:
            #start_ds < end and end_ds > start
            if temporal_extent[0] == None:
                start = dsinfo['temporal_extent'][0]
            if temporal_extent[1] == None:
                stop = dsinfo['temporal_extent'][1]
            #point location inclued in box
            if ((dsinfo['temporal_extent'][0] <= stop 
                    and dsinfo['temporal_extent'][1] >= start) 
                    and((spatial_extent[0] < dsinfo['spatial_extent'][0] < spatial_extent[2]) 
                    and (spatial_extent[1] < dsinfo['spatial_extent'][1] < spatial_extent[3]))):
                variables = []
                for ds_v in dsinfo['variables']:
                    variables.append(ds_v['ECV_name'][0])
                    if ds_v['ECV_name'][0] in variables_list:
                #        list_identifiers.append(dsinfo['url'])
                #        break
                        filtered_dataset_info.append({'title': i['title'], 
                                      'urls' : i['urls'], 
                                      'ecv_variables' : variables,
                                      'time_period' : [dsinfo['temporal_extent'][0],dsinfo['temporal_extent'][1]],
                                      'platform_id' : dsinfo['station_info']['short_name']})
    return(filtered_dataset_info)

#query_datasets(['ECV variable'], ['start date','end date'], ['lon0', 'lat0', 'lon1', 'lat1'])
#query_datasets(['Pressure (surface)','Surface Wind Speed and direction'], ['1800-03-01T03:00:00','2000-01-01T03:00:00'], [0, 78, 180, 90])

#read datasets
def read_dataset(url,variables_list, temporal_extent, spatial_extent):
    ds = xr.open_dataset(url)
    #cf standard name to ECV mapping
    mapping = {'surface_air_pressure':'Pressure (surface)',
               'wind_speed':'Surface Wind Speed and direction', 
               'wind_from_direction':'Surface Wind Speed and direction', 
               'air_temperature':'Temperature (near surface)', 
               'relative_humidity':'Water Vapour (surface)'}       
    
    varlist_tmp = []
    varlist = []
    # Map variables from ECV
    for k,v in mapping.items():
        if v in variables_list:
            varlist_tmp.append(k)
    # Choose variables
    for varname, da in ds.data_vars.items():
        if 'standard_name' in da.attrs and (da.attrs['standard_name'] in varlist_tmp or da.attrs['standard_name'] == 'latitude' or da.attrs['standard_name'] == 'longitude'):
            varlist.append(varname)
    ds = ds[varlist]         
    
    return(ds)

#read_dataset('https://thredds.met.no/thredds/dodsC/met.no/observations/stations/SN99752.nc', ['Pressure (surface)', 'Temperature (near surface)'], ['1908-09-01T06:00:00','1910-09-01T06:00:00'], [0, 0, 180, 90])


if __name__ == "__main__":
    # <h1>Get platform info</h1>
    print(get_list_platforms())
    # <h1>Get stations variables</h1>
    print(get_list_variables())
    # <h2>Get list of datasets (example)</h2>
    print(query_datasets(['Pressure (surface)'], ['1810-03-01T03:00:00','1960-10-01T03:00:00'], [10, 70, 23, 80]))

