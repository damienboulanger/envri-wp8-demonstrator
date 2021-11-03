import query_actris
import query_iagos
import query_icos
import query_sios

def load_platforms():
    platforms = {}
    platforms['actris'] = query_actris.get_list_platforms()
    platforms['iagos'] = query_iagos.get_list_platforms()
    platforms['icos'] = query_icos.get_list_platforms()
    #platforms['sios'] = query_sios.get_list_platforms()
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

def load_variables():
    variables = {}
    variables['actris'] = query_actris.get_list_variables()
    variables['iagos'] = query_iagos.get_list_variables()
    variables['icos'] = load_variables_icos()
    variables['sios'] = query_sios.get_list_variables()
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
    
    datasets = []
    #datasets.append(query_actris.query_datasets(variables=variables,temporal_extent=[start,end], spatial_extent=bbox))
    datasets.append(query_icos.query_datasets(variables=variables_icos,temporal=[start,end], spatial=bbox))
    #datasets.append(query_sios.query_datasets(variables_list=variables,temporal_extent=[start,end], spatial_extent=bbox))
    datasets.append(query_iagos.query_datasets(variables_list=variables,temporal_extent=[start,end], spatial_extent=bbox))
    return datasets