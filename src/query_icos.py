'''
Provide Atmospheric stations, variables and datasets
for EnvriFair Task 8.5
API description: https://docs.google.com/document/d/1_YjLJQqO4ZPoIkPgvSKkhJzlUPptIEm0F1X7uDrKRiA/edit

The corresponding Essential Climate Variables for ICOS are:
    
https://gcos.wmo.int/en/essential-climate-variables/surface-vapour/ecv-requirements
https://gcos.wmo.int/en/essential-climate-variables/surface-temperature/ecv-requirements
https://gcos.wmo.int/en/essential-climate-variables/surface-wind/ecv-requirements
https://gcos.wmo.int/en/essential-climate-variables/pressure/ecv-requirements
https://gcos.wmo.int/en/essential-climate-variables/ghg/ecv-requirements

'''

import pandas as pd

from icoscp.station import station
from icoscp.cpb.dobj import Dobj
from icoscp.sparql.runsparql import RunSparql


# all stations info
def get_list_platforms():
    '''
    Query ICOS for a list of atmosperic stations
    Returns
    -------
    stations : LIST[dicts]
    '''

    stations = station.getIdList()

    # remove ecosystem and ocean for this demonstrator
    # but, stations would contain ALL stations from ICOS
    stations = stations[stations['theme']=='AS']

    # rename columns to conform
    stations.rename(columns=__colname(), inplace=True)

    # transform to desired output format
    stations = list(stations.T.to_dict().values())

    return stations

def __colname():
    # rename columns for compatibility
    colname = {'id': 'short_name',
               'name': 'long_name',
               'lat': 'latitude',
               'lon': 'longitude',
               'elevation': 'ground_elevation',
               'project': 'RI'
               }
    return colname


def get_list_variables():
    """
    Return a list of Variables from ICOS for the moment this is a
    fixed dictionary, but could / should be dynamically queried

    Returns
    -------
    variables : LIST[dicts]
    """

    variables = [{'variable_name':'AP', 'ECV_name': ['Pressure (surface)', 'Pressure', 'ap']},
                 {'variable_name':'WD', 'ECV_name': ['Surface Wind Speed and direction', 'wd']},
                 {'variable_name':'WS', 'ECV_name': ['Surface Wind Speed and direction', 'ws']},
                 {'variable_name':'AT', 'ECV_name': ['Temperature (near surface)', 'Temperature', 'at']},
                 {'variable_name':'RH', 'ECV_name': ['Water Vapour (surface)','Water Vapour (Relative Humidity)','rh']},
                 {'variable_name':'co2','ECV_name': ['Carbon Dioxide, Methane and other Greenhouse gases','Tropospheric CO2', 'co2']},
                 {'variable_name':'co', 'ECV_name': ['Carbon Dioxide, Methane and other Greenhouse gases','co']},
                 {'variable_name':'ch4','ECV_name': ['Carbon Dioxide, Methane and other Greenhouse gases','Tropospheric CH4','ch4']},
                 {'variable_name':'n2o','ECV_name': ['Carbon Dioxide, Methane and other Greenhouse gases','n2o']}
                 ]
    return variables


def ecv_icos_map():
    reverse = []    
    for var in get_list_variables():
        reverse.append({v[0]: k for k, v in var.items()})
    
    return reverse
    
def __get_spec(variable_name):
    """
    Return a list of Variables from ICOS for the moment this is a
    fixed dictionary, but could / should be dynamically queried

    Returns
    -------
    variables : LIST[dicts]
    """
   
    # make sure variable_name is lower case
    variable_name = variable_name.lower()
    specs = {'ap':  'http://meta.icos-cp.eu/resources/cpmeta/atcMtoL2DataObject',
             'wd':  'http://meta.icos-cp.eu/resources/cpmeta/atcMtoL2DataObject',
             'ws':  'http://meta.icos-cp.eu/resources/cpmeta/atcMtoL2DataObject',
             'at':  'http://meta.icos-cp.eu/resources/cpmeta/atcMtoL2DataObject',
             'rh':  'http://meta.icos-cp.eu/resources/cpmeta/atcMtoL2DataObject',
             'co2': 'http://meta.icos-cp.eu/resources/cpmeta/atcCo2L2DataObject',
             'co':  'http://meta.icos-cp.eu/resources/cpmeta/atcCoL2DataObject',
             'ch4': 'http://meta.icos-cp.eu/resources/cpmeta/atcCh4L2DataObject',
             'n2o': 'http://meta.icos-cp.eu/resources/cpmeta/atcN2oL2DataObject'
             }
    if variable_name in specs.keys():
        return specs[variable_name]
    else:
        return ''

def query_datasets(variables=[], temporal=[], spatial=[]):
    """
    return identifiers for datasets constraint by input parameters.
    if a parameter is empty, it will be ignored. if no parameter is 
    provided...ALL datasets are returned.
    
    
    Parameters
    ----------
    variables : LIST[STR]
        Provide a list of strings to query for variables. Entries\
        matching the variables returned from get_list_variables().
    
    temporal_extent : LIST[STR,STR] start, end , string at format yyyyMMddTHHmmss
                or more general str must be convertible with a pandas.
                date = pandas.to_datetime(date).date()
    
    spatial_extent : LIST[min_lon, min_lat, max_lon, max_lat] 
        lat lon must be convertible to float. The bounding box is of format
        bottom left, top right corner.
        
    Returns
    -------
    LIST[URI], where URI is an ICOS specific assembly inlcuding the PID
    The URI is persistent landing page for the dataset. If no results
    an empty list is returned
    """
    stn = station.getIdList()
    stn = stn[stn['theme']=='AS']
    dtypes = ['str','str','str','str','float','float','float','str', 'str']
    dtype=dict(zip(stn.columns.tolist(), dtypes))
    stn.astype(dtype)   
    

    # get all datasets and convert dtype    
    dataset = __sparql_data()
    dtypes = ['str','str','str','str','int','datetime64','datetime64','datetime64']
    dtype=dict(zip(dataset.columns.tolist(), dtypes))
    dataset.astype(dtype)
    
    # start filtering according to parameters
    selected_var=[]    
    for vv in get_list_variables():        
        for v in variables:
            if v in vv['ECV_name']:
                selected_var.append(vv['variable_name'])

    # make sure there are no duplicates
    selected_var = list(set(selected_var))
    
    df = pd.DataFrame()
    # get variables
    for v in selected_var:
        data = dataset['spec'] == __get_spec(v)
        df = df.append(dataset[data])
    if df.empty:
        return []
    
    # filter temporal
    if len(temporal) == 2:
        df = df[(df.timeStart >= temporal[0]) | (df.timeEnd <= temporal[1])]
    
    # filter spatial
    if len(spatial) == 4:
        stlist = []
        for s in df.station.unique().tolist():
            #find stations within bounding box              
            a = stn.loc[stn['uri'] == s]
            if float(a.lon) >= spatial[0] and \
               float(a.lon) <= spatial[2] and \
               float(a.lat) >= spatial[1] and \
               float(a.lat) <= spatial[3]:
                  stlist.append(a.uri.values[0])
        if stlist:
            df = df[df.station.isin(stlist)]
            
    return df['dobj'].tolist()
    

def __sparql_data():    
    
    q =  """	   prefix cpmeta: <http://meta.icos-cp.eu/ontologies/cpmeta/>
     prefix prov: <http://www.w3.org/ns/prov#>
    	select ?station ?dobj ?spec ?fileName ?size ?submTime ?timeStart ?timeEnd
    	where {
        		VALUES ?spec {
        			<http://meta.icos-cp.eu/resources/cpmeta/atcCh4L2DataObject> 
        			<http://meta.icos-cp.eu/resources/cpmeta/atcCoL2DataObject>
        			<http://meta.icos-cp.eu/resources/cpmeta/atcCo2L2DataObject>
        			<http://meta.icos-cp.eu/resources/cpmeta/atcMtoL2DataObject>
        			<http://meta.icos-cp.eu/resources/cpmeta/atcN2oL2DataObject>}
        	?dobj cpmeta:hasObjectSpec ?spec .
        	?dobj cpmeta:hasSizeInBytes ?size .
        	?dobj cpmeta:hasName ?fileName .
        	?dobj cpmeta:wasAcquiredBy/prov:wasAssociatedWith ?station .
        	?dobj cpmeta:wasSubmittedBy/prov:endedAtTime ?submTime .
        	?dobj cpmeta:hasStartTime | (cpmeta:wasAcquiredBy / prov:startedAtTime) ?timeStart .
        	?dobj cpmeta:hasEndTime | (cpmeta:wasAcquiredBy / prov:endedAtTime) ?timeEnd .
        	FILTER NOT EXISTS {[] cpmeta:isNextVersionOf ?dobj}
        	{
        		{FILTER NOT EXISTS {?dobj cpmeta:hasVariableName ?varName}}
        		UNION
        		{
        			?dobj cpmeta:hasVariableName ?varName
        			FILTER (?varName = "co2" || ?varName = "ch4" || ?varName = "co" || ?varName = "n2o" || ?varName = "RH" || ?varName = "WD" || ?varName = "WS")
        		}
        	}
        }
    """
    sparql = RunSparql(q, output_format='pandas').run()
    
    return sparql

def read_dataset(pid):
    data = Dobj(pid).data
    return data.to_xarray()
    
    
if __name__ == "__main__":
    
    #print(get_list_platforms())
    #print(get_list_variables())
    #print(query_datasets(variables=['co2','Pressure (surface)'],temporal=['2018-01-01','2018-12-31']))
    #print(query_datasets(['Pressure (surface)'], ['2018-01-01T03:00:00','2021-12-31T24:00:00'],[10, 40, 23, 60]))
    pids = query_datasets(variables=['co2', 'ws','Carbon Dioxide, Methane and other Greenhouse gases'], temporal= ['2018-01-01T03:00:00','2021-12-31T24:00:00'], spatial = [10, 40, 23, 60])
    print(pids)
    data = read_dataset(pids[0])
    print(data.head())
    