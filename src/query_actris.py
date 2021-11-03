import requests
import xarray as xr

# Use this mapping for the mapping, to reduce the size
MAPPING_ECV2ACTRIS = {
    #'Cloud Properties': ['cloud.aerosol.target.classification', 'cloud.fraction', 'cloud.mask'],
    'Aerosol Optical Properties': ['aerosol.absorption.coefficient','aerosol.backscatter.coefficient','aerosol.backscatter.coefficient.hemispheric','aerosol.backscatter.ratio','aerosol.depolarisation.coefficient','aerosol.depolarisation.ratio','aerosol.extinction.coefficient','aerosol.extinction.ratio','aerosol.extinction.to.backscatter.ratio','aerosol.optical.depth','aerosol.optical.depth.550','aerosol.rayleigh.backscatter','aerosol.scattering.coefficient'],
    'Aerosol Chemical Properties': ['elemental.carbon','organic.carbon.concentration','organic.mass.concentration','total.carbon.concentration'],
    'Aerosol Physical Properties': ['particle.number.concentration','particle.number.size.distribution','pm10.concentration','pm1.concentration','pm2.5.concentration','pm2.5-&gt;pm10.concentration'],
    #'Precursors': ['ethane', 'acetonitrile', 'benzene', 'butanales', 'butanone', 'butenes', 'cis-2-butene', 'cis-2-pentene', 'cyclo-hexane', 'cyclo-pentene', 'C9-alkylbenzenes', 'ethanal', 'NO2.concentration', 'NOx.concentration', 'ethanedial', 'ethene', 'ethylbenzene', 'ethyne', 'hexanal', 'isoheptanes', 'isohexanes', 'isoprene', 'methanal', 'methanol', 'methyl-cyclohexane', 'methyl-cyclopentane', 'monoterpenes', 'm-p-xylene', 'MVK_MACR_crotonaldehyde', 'n-butane', 'n-heptane', 'n-hexanal', 'n-hexane', 'n-nonane', 'NO.concentration', 'n-octane', 'n-pentane', 'o-xylene', 'pentanal', 'pentenes', 'propanal', 'propane', 'propanone', 'propene', 'propyne', 'toluene', 'trans-2-butene', 'trans-2-pentene', 'valeraldehyde.o-tolualdehyde', '1-butene', '1-butyne', '1-hexene', '1-pentene', '1-2-3-trimethylbenzene', '1-2-4-trimethylbenzene', '1-3-butadiene', '1-3-5-trimethylbenzene', '2-methylbutane', '2-methylhexane', '2-methylpentane', '2-methylpropane', '2-methylpropenal', '2-methylpropene', '2-oxopropanal', '2-propenal', '2-2-dimethylbutane', '2-2-dimethylpentane', '2-2-dimethylpropane', '2-2-3-trimethylbutane', '2-2-4-trimethylpentane', '2-3-dimethylbutane', '2-3-dimethylpentane', '2-4-dimethylpentane', '3-buten-2-one', '3-methylheptane', '3-methylpentane', '3-methyl-1-butene', '3-3-dimethylpentane']
}


def get_list_platforms():

    response = requests.get('https://prod-actris-md.nilu.no/Stations')

    stations_demonstrator = []

    for station in response.json():

        stations_demonstrator.append(
            {
                'short_name': station['identifier'],
                'latitude': station['lat'],
                'longitude': station['lon'],
                'long_name': station['name'],
                'altitude': station['alt']})

    return stations_demonstrator


def get_list_variables():

    response = requests.get(
        'https://prod-actris-md.nilu.no/ContentInformation/attributes')

    variables_demonstrator = []

    for v in response.json():
        for k, var_list in MAPPING_ECV2ACTRIS.items():
            if k == 'Cloud Properties' and v['attribute_type'] in var_list:
                variables_demonstrator.append(
                    {'variable_name': v['attribute_type'], 'ECV_name': ['Cloud Properties']})
            elif k == 'Aerosol Optical Properties' and v['attribute_type'] in var_list:
                variables_demonstrator.append(
                    {'variable_name': v['attribute_type'], 'ECV_name': ['Aerosol Optical Properties']})
            elif k == 'Aerosol Chemical Properties' and v['attribute_type'] in var_list:
                variables_demonstrator.append(
                    {'variable_name': v['attribute_type'], 'ECV_name': ['Aerosol Chemical Properties']})
            elif k == 'Aerosol Physical Properties' and v['attribute_type'] in var_list:
                variables_demonstrator.append(
                    {'variable_name': v['attribute_type'], 'ECV_name': ['Aerosol Physical Properties']})
            elif k == 'Precursors' and v['attribute_type'] in var_list:
                variables_demonstrator.append(
                    {'variable_name': v['attribute_type'], 'ECV_name': ['Precursors']})
            else:
                pass

    return variables_demonstrator


def query_datasets(variables, temporal_extent, spatial_extent):

    try:

        actris_variable_list = []

        for v in variables:

            actris_variable_list.extend(MAPPING_ECV2ACTRIS[v])


        start_time,end_time = temporal_extent[0],temporal_extent[1]
        #temporal_extent = [start_time, end_time]
        lon0, lat0, lon1, lat1 = spatial_extent[0],spatial_extent[1],spatial_extent[2],spatial_extent[3],
        #spatial_extent = [lon0, lat0, lon1, lat1]

        dataset_endpoints = []

        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json',
        }

        data = '{"where":{"argument":{"type":"content","sub-type":"attribute_type","value":' + \
            str(actris_variable_list) + \
            ',"case-sensitive":false,"and":{"argument":{"type":"temporal_extent","comparison-operator":"overlap","value":["' + \
            temporal_extent[0] + '","' + temporal_extent[1] + '"]}}}}}'

        response = requests.post(
            'https://prod-actris-md.nilu.no/Metadata/query',
            headers=headers,
            data=data)

        for ds in response.json():

            lat_point, lon_point = ds['md_data_identification']['station']['lat'], ds['md_data_identification']['station']['lon']

            if (lon0 < lon_point < lon1) and (lat0 < lat_point < lat1) == True:
                local_filename = ds['md_distribution_information']['dataset_url'].split(
                    '/')[-1]
                opendap_url = 'http://thredds.nilu.no/thredds/dodsC/ebas/{0}'.format(
                    local_filename)
                dataset_endpoints.append(opendap_url)
            else:
                pass

        return dataset_endpoints

    except BaseException:
        return "Variables must be one of the following: 'Aerosol Optical Properties','Aerosol Chemical Properties','Aerosol Physical Properties'"


def read_dataset(url, variables):

    # For InSitu specific variables
    actris2insitu = {'particle_number_size_distribution': 'particle.number.size.distribution',
                     'aerosol_absorption_coefficient': 'aerosol.absorption.coefficient',
                     'aerosol_light_backscattering_coefficient': 'aerosol.backscatter.coefficient.hemispheric',
                     'aerosol_light_backscattering_coefficient': 'aerosol.backscatter.coefficient',
                     'aerosol_light_scattering_coefficient': 'aerosol.scattering.coefficient',
                     'cloud_condensation_nuclei_number_concentration': 'cloud.condensation.nuclei.number.concentration',
                     'particle_number_concentration': 'particle.number.concentration',
                     'elemental_carbon': 'elemental.carbon',
                     'organic_carbon': 'organic.carbon.concentration',
                     'organic_mass': 'organic.mass.concentration',
                     'particle_number_concentration': 'particle.number.concentration',
                     'pm1_mass': 'pm1.concentration',
                     'pm10_mass': 'pm10.concentration',
                     'pm25_mass': 'pm2.5.concentration',
                     'pm10_pm25_mass': 'pm2.5-&gt;pm10.concentration',
                     'total_carbon': 'total.carbon.concentration',
                     'aerosol_optical_depth': 'aerosol.optical.depth',
                     None: 'aerosol.backscatter.ratio',
                     None: 'aerosol.depolarisation.coefficient',
                     None: 'aerosol.depolarisation.ratio',
                     None: 'aerosol.extinction.coefficient',
                     None: 'aerosol.extinction.ratio',
                     None: 'aerosol.extinction.to.backscatter.ratio',
                     None: 'aerosol.optical.depth.550',
                     None: 'aerosol.rayleigh.backscatter',
                     None: 'cloud.aerosol.target.classification',
                     None: 'cloud.fraction',
                     None: 'cloud.mask',
                     'acetonitrile': 'acetonitrile',
                     'benzene': 'benzene',
                     'butanales': 'butanales',
                     'butanone': 'butanone',
                     'butenes': 'butenes',
                     'cis-2-butene': 'cis-2-butene',
                     'cis-2-pentene': 'cis-2-pentene',
                     'cyclo-hexane': 'cyclo-hexane',
                     'cyclo-pentene': 'cyclo-pentene',
                     'C9-alkylbenzenes': 'C9-alkylbenzenes',
                     'ethanal': 'ethanal',
                     'nitrogen_dioxide': 'NO2.concentration',
                     'NOx': 'NOx.concentration',
                     'ethane': 'ethane',
                     'ethanedial': 'ethanedial',
                     'ethene': 'ethene',
                     'ethylbenzene': 'ethylbenzene',
                     'ethyne': 'ethyne',
                     'hexanal': 'hexanal',
                     'isoheptanes': 'isoheptanes',
                     'isohexanes': 'isohexanes',
                     'isoprene': 'isoprene',
                     'methanal': 'methanal',
                     'methanol': 'methanol',
                     'methyl-cyclohexane': 'methyl-cyclohexane',
                     'methyl-cyclopentane': 'methyl-cyclopentane',
                     'monoterpenes': 'monoterpenes',
                     'm-p-xylene': 'm-p-xylene',
                     'MVK_MACR_crotonaldehyde': 'MVK_MACR_crotonaldehyde',
                     'n-butane': 'n-butane',
                     'n-heptane': 'n-heptane',
                     'n-hexanal': 'n-hexanal',
                     'n-hexane': 'n-hexane',
                     'n-nonane': 'n-nonane',
                     'nitrogen_monoxide': 'NO.concentration',
                     'n-octane': 'n-octane',
                     'n-pentane': 'n-pentane',
                     'o-xylene': 'o-xylene',
                     'pentanal': 'pentanal',
                     'pentenes': 'pentenes',
                     'propanal': 'propanal',
                     'propane': 'propane',
                     'propanone': 'propanone',
                     'propene': 'propene',
                     'propyne': 'propyne',
                     'toluene': 'toluene',
                     'trans-2-butene': 'trans-2-butene',
                     'trans-2-pentene': 'trans-2-pentene',
                     'valeraldehyde_o-tolualdehyde': 'valeraldehyde.o-tolualdehyde',
                     '1-butene': '1-butene',
                     '1-butyne': '1-butyne',
                     '1-hexene': '1-hexene',
                     '1-pentene': '1-pentene',
                     '1-2-3-trimethylbenzene': '1-2-3-trimethylbenzene',
                     '1-2-4-trimethylbenzene': '1-2-4-trimethylbenzene',
                     '1-3-butadiene': '1-3-butadiene',
                     '1-3-5-trimethylbenzene': '1-3-5-trimethylbenzene',
                     '2-methylbutane': '2-methylbutane',
                     '2-methylhexane': '2-methylhexane',
                     '2-methylpentane': '2-methylpentane',
                     '2-methylpropane': '2-methylpropane',
                     '2-methylpropenal': '2-methylpropenal',
                     '2-methylpropene': '2-methylpropene',
                     '2-oxopropanal': '2-oxopropanal',
                     '2-propenal': '2-propenal',
                     '2-2-dimethylbutane': '2-2-dimethylbutane',
                     '2-2-dimethylpentane': '2-2-dimethylpentane',
                     '2-2-dimethylpropane': '2-2-dimethylpropane',
                     '2-2-3-trimethylbutane': '2-2-3-trimethylbutane',
                     '2-2-4-trimethylpentane': '2-2-4-trimethylpentane',
                     '2-3-dimethylbutane': '2-3-dimethylbutane',
                     '2-3-dimethylpentane': '2-3-dimethylpentane',
                     '2-4-dimethylpentane': '2-4-dimethylpentane',
                     '3-buten-2-one': '3-buten-2-one',
                     '3-methylheptane': '3-methylheptane',
                     '3-methylpentane': '3-methylpentane',
                     '3-methyl-1-butene': '3-methyl-1-butene',
                     '3-3-dimethylpentane': '3-3-dimethylpentane'
                     }

    varlist_tmp = []
    for k, v in MAPPING_ECV2ACTRIS.items():
        if k in variables:
            varlist_tmp.extend(v)

    actris_varlist = []
    for k, v in actris2insitu.items():
        if v in varlist_tmp:
            actris_varlist.append(k)

    try:
        ds = xr.open_dataset(url)
        var_list = []
        for varname, da in ds.data_vars.items():
            if 'metadata' in varname or 'time' in varname or '_qc' in varname:
                pass
            elif any(var in varname for var in actris_varlist):
                var_list.append(varname)
            else:
                pass
        return ds[var_list]

    except BaseException:
        return None
