import query_actris
import query_iagos
import query_icos
import query_sios

ris = [ "actris", "iagos", "icos", "sios"]

ris_platforms = { "actris": query_actris.get_list_platforms(), 
                 "iagos": query_iagos.get_list_platforms(), 
                 "icos": query_icos.get_list_platforms(), 
                 "sios": query_sios.get_list_platforms()}

def load_platforms():
    platforms = {}
    for ri in ris:
        print("... loading " + ri + " platforms")
        try:
            platforms[ri] = ris_platforms[ri]
        except:
            print("problem during the loading of " + ri + " platforms")
    print("all the platforms are loaded")
    return platforms       
    
    platforms['actris'] = query_actris.get_list_platforms()
    platforms['iagos'] = query_iagos.get_list_platforms()
    platforms['icos'] = query_icos.get_list_platforms()
    platforms['sios'] = query_sios.get_list_platforms()
    return platforms

def mapping_ecv_icos():
    return {'Carbon Dioxide':'Carbon Dioxide, Methane and other Greenhouse gases',
        'Carbon monoxide':'Carbon Dioxide, Methane and other Greenhouse gases',
        'Methane':'Carbon Dioxide, Methane and other Greenhouse gases',
        'N2O':'Carbon Dioxide, Methane and other Greenhouse gases'}

def load_variables_icos():
    return [{'variable_name': 'AP', 'ECV_name': ['Pressure (surface)']},
                 {'variable_name': 'WD', 'ECV_name': ['Surface Wind Speed and direction']},
                 {'variable_name': 'WS', 'ECV_name': ['Surface Wind Speed and direction']},
                 {'variable_name': 'AT', 'ECV_name': ['Temperature (near surface)']},
                 {'variable_name': 'RH', 'ECV_name': ['Water Vapour (surface)', 'Water Vapour (Relative Humidity)']},
                 {'variable_name': 'co2', 'ECV_name': ['Carbon Dioxide']},
                 {'variable_name': 'co', 'ECV_name': ['Carbon monoxide']},
                 {'variable_name': 'ch4', 'ECV_name': ['Methane']},
                 {'variable_name': 'n2o', 'ECV_name': ['N2O']}
                ]

ris_variables = { "actris": query_actris.get_list_variables(), 
                 "iagos": query_iagos.get_list_variables(), 
                 "icos": load_variables_icos(), 
                 "sios": query_sios.get_list_variables()}

def load_variables():
    variables = {}
    for ri in ris:
        print("... loading " + ri + " variables")
        try:
            variables[ri] = ris_variables[ri]
        except:
            print("problem during the loading of " + ri + " variables")
    print("all the variables are loaded")
    return variables         
    
def get_ECV(variables):
    ecv=[]
    for ri in variables.keys():
        for val in variables[ri]:
            ecv = list(set(ecv+val['ECV_name']))
    return sorted(ecv)

def query_datasets(start, end, variables, bbox):
    ecv = mapping_ecv_icos()
    variables_icos = [ecv[val] if val in ecv.keys() else val for val in variables ]
    
    datasets = {}
    print("... searching datasets in actris")
    
    try:
        dts = query_actris.query_datasets(variables=variables,temporal_extent=[start,end], spatial_extent=bbox)
        datasets['actris'] = dts
        print(str(len(dts)) + " datasets found in actris")
    except:
            print("problem during the search of actris datasets")
    
    print("... searching datasets in icos")
    try:
        dts = query_icos.query_datasets(variables=variables_icos,temporal=[start,end], spatial=bbox)
        datasets['icos'] = dts
        print(str(len(dts)) + " datasets found in icos")
    except:
            print("problem during the search of icos datasets")
    
    print("... searching datasets in iagos")
    try:
        #dts = query_iagos.query_datasets(variables_list=variables,temporal_extent=[start,end], spatial_extent=bbox)
        dts = []
        datasets['iagos'] = dts
        print(str(len(dts)) + " datasets found in iagos")
    except:
            print("problem during the search of iagos datasets")
    
    print("... searching datasets in sios")
    try:
        dts = query_sios.query_datasets(variables_list=variables,temporal_extent=[start,end], spatial_extent=bbox)
        datasets['sios'] = dts
        print(str(len(dts)) + " datasets found in sios")
    except:
            print("problem during the search of sios datasets")

    print(datasets)
    return datasets

if __name__ == "__main__":
    query_datasets('2018-01-01T03:00:00','2021-12-31T24:00:00', ['Pressure (surface)'],[10, 40, 23, 60])
    
    