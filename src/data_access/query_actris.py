import requests
import xarray as xr
import netCDF4
from netCDF4 import num2date
import plotly.graph_objects as go
from math import pi
import numpy as np


MAPPING_ECV2ACTRIS = {
    'Aerosol Optical Properties': ['aerosol.absorption.coefficient', 'aerosol.backscatter.coefficient', 'aerosol.backscatter.coefficient.hemispheric', 'aerosol.backscatter.ratio', 'aerosol.depolarisation.coefficient', 'aerosol.depolarisation.ratio', 'aerosol.extinction.coefficient', 'aerosol.extinction.ratio', 'aerosol.extinction.to.backscatter.ratio', 'aerosol.optical.depth', 'aerosol.optical.depth.550', 'aerosol.rayleigh.backscatter', 'aerosol.scattering.coefficient', 'volume.depolarization.ratio', 'cloud.condensation.nuclei.number.concentration'],
    'Aerosol Chemical Properties': ['elemental.carbon', 'organic.carbon.concentration', 'organic.mass.concentration', 'total.carbon.concentration'],
    'Aerosol Physical Properties': ['particle.number.concentration', 'particle.number.size.distribution', 'pm10.concentration', 'pm1.concentration', 'pm2.5.concentration', 'pm2.5-&gt;pm10.concentration'],
    'NO2' : ['nitrogen.dioxide'],
}


def get_list_platforms():

    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json',
    }

    actris_variable_list = ['elemental.carbon', 'organic.carbon.concentration', 'organic.mass.concentration', 'total.carbon.concentration', 'aerosol.absorption.coefficient', 'aerosol.backscatter.coefficient.hemispheric',
                            'aerosol.scattering.coefficient', 'particle.number.concentration', 'particle.number.size.distribution', 'pm10.concentration', 'pm1.concentration', 'pm2.5.concentration', 'pm2.5-&gt;pm10.concentration']

    data = '{"where":{"argument":{"type":"content","sub-type":"attribute_type","value":' + \
        str(actris_variable_list) + \
        ',"case-sensitive":false,"and":{"argument":{"type":"temporal_extent","comparison-operator":"overlap","value":["1970-01-01T00:00:00","2020-01-01T00:00:00"]}}}}}'

    response = requests.post(
        'https://prod-actris-md.nilu.no/Metadata/query',
        headers=headers,
        data=data)

    stations_demonstrator = []
    unique_identifiers = []

    for ds in response.json():

        if ds['md_data_identification']['station']['wmo_region'] == 'Europe':

            if ds['md_data_identification']['station']['identifier'] in unique_identifiers:
                pass
            else:
                unique_identifiers.append(
                    ds['md_data_identification']['station']['identifier'])

                stations_demonstrator.append(
                    {
                        'short_name': ds['md_data_identification']['station']['identifier'],
                        'latitude': ds['md_data_identification']['station']['lat'],
                        'longitude': ds['md_data_identification']['station']['lon'],
                        'long_name': ds['md_data_identification']['station']['name'],
                        'URI': 'https://prod-actris-md.nilu.no/Stations/{0}'.format(ds['md_data_identification']['station']['identifier']),
                        'altitude': ds['md_data_identification']['station']['alt']})
        else:
            pass

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

    # try:

    actris_variable_list = []

    for v in variables:
        if v in MAPPING_ECV2ACTRIS:
            actris_variable_list.extend(MAPPING_ECV2ACTRIS[v])

    start_time, end_time = temporal_extent[0], temporal_extent[1]
    #temporal_extent = [start_time, end_time]
    lon0, lat0, lon1, lat1 = spatial_extent[0], spatial_extent[1], spatial_extent[2], spatial_extent[3],
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

        # filter urls by data provider.


        lat_point, lon_point = ds['md_data_identification']['station']['lat'], ds['md_data_identification']['station']['lon']

        if (lon0 < lon_point < lon1) and (lat0 < lat_point < lat1) == True:
            
            local_filename = ds['md_distribution_information'][0]['dataset_url'].split('/')[-1]

            if ds['md_metadata']['provider_id'] == 14:
                opendap_url = 'http://thredds.nilu.no/thredds/dodsC/ebas/{0}'.format(
                    local_filename)
            else:
                opendap_url = None

            attribute_descriptions = ds['md_content_information']['attribute_descriptions']

            ecv_vars = []

            if any(x in MAPPING_ECV2ACTRIS['Aerosol Optical Properties'] for x in attribute_descriptions):
                ecv_vars.append('Aerosol Optical Properties')
            else:
                pass

            if any(x in MAPPING_ECV2ACTRIS['Aerosol Chemical Properties'] for x in attribute_descriptions):
                ecv_vars.append('Aerosol Chemical Properties')
            else:
                pass

            if any(x in MAPPING_ECV2ACTRIS['Aerosol Physical Properties'] for x in attribute_descriptions):
                ecv_vars.append('Aerosol Physical Properties')
            else:
                pass

            # generate dataset_metadata dict

            ds_title = 'Ground based observations of {0} (matrix: {1}) using {2} at {3}: {4} -> {5}'.format(','.join(ds['md_content_information']['attribute_descriptions']), ds['md_actris_specific']['matrix'], ','.join(
                ds['md_actris_specific']['instrument_type']), ds['md_data_identification']['station']['name'], ds['ex_temporal_extent']['time_period_begin'], ds['ex_temporal_extent']['time_period_end'])
            dataset_metadata = {'title': ds_title, 'urls': [{'url': opendap_url, 'type': 'opendap'}, {'url': ds['md_distribution_information'][0]['dataset_url'], 'type':'data_file'}], 'ecv_variables': ecv_vars, 'time_period': [
                ds['ex_temporal_extent']['time_period_begin'], ds['ex_temporal_extent']['time_period_end']], 'platform_id': ds['md_data_identification']['station']['identifier']}
            dataset_endpoints.append(dataset_metadata)

        else:
            pass

    return dataset_endpoints

    # except BaseException:
    #    return "Variables must be one of the following: 'Aerosol Optical Properties','Aerosol Chemical Properties','Aerosol Physical Properties'"


def read_dataset(url, variables):

    # For InSitu specific variables
    actris2insitu = {'particle_number_size_distribution': 'particle.number.size.distribution',
                     'aerosol_absorption_coefficient': 'aerosol.absorption.coefficient',
                     'aerosol_light_backscattering_coefficient': 'aerosol.backscatter.coefficient.hemispheric',
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
                     'nitrogen_dioxide': 'nitrogen.dioxide'
                     }

    # For ARES specific variables
    actris2ares = {'backscatter': 'aerosol.backscatter.coefficient',
                   'particledepolarization': 'aerosol.depolarisation.ratio',
                   'extinction': 'aerosol.extinction.coefficient',
                   'lidarratio': 'aerosol.extinction.to.backscatter.ratio',
                   'volumedepolarization': 'volume.depolarization.ratio'
                   }

    varlist_tmp = []
    for k, v in MAPPING_ECV2ACTRIS.items():
        if k in variables:
            varlist_tmp.extend(v)

    actris_varlist = []
    for k, v in actris2insitu.items():
        if v in varlist_tmp:
            actris_varlist.append(k)

    for k, v in actris2ares.items():
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
    
def test_particle_number_size_distribution(dataset):
    if 'particle_number_size_distribution_pm10_amean' in dataset.variables.keys() or 'particle_number_size_distribution_amean' in dataset.variables.keys()or  'particle_number_size_distribution' in dataset.variables.keys():
        return True
    else:
        return False

def gen_log_legend(z):
    no_log=[]
    z_step=(z.max() - z.min())/4
    z_leg=np.arange(z.min(),z.max(),z_step)
    z_leg=np.append(z_leg,z.max())
    for t in z_leg:
        n_log=10**t
        if n_log < 10:
            no_log.append(float('%.1g' % n_log)) #trick to make a nice legend
        else:
            no_log.append(float('%.2g' % n_log))
    return z_leg,no_log

def get_dataset(particle_number_size_distribution_data):
    return netCDF4.Dataset(particle_number_size_distribution_data)

def get_contour_plot(dataset):
    if 'particle_number_size_distribution_pm10_amean' in dataset.variables.keys():
        values = dataset['particle_number_size_distribution_pm10_amean']
    elif 'particle_number_size_distribution_amean' in dataset.variables.keys():
        values = dataset['particle_number_size_distribution_amean']
    elif 'particle_number_size_distribution' in dataset.variables.keys():
        values = dataset['particle_number_size_distribution']
    else:
        return {}
    zz=[]
    for arr in values:
        for ver in arr:
            if ver >0:
                zz.append(np.log10(ver))
            else:
                zz.append(0)
    z=np.reshape(zz,values.shape)
    x = num2date(dataset.variables['time'][:],units='days since 1900-01-01 00:00:00',calendar='gregorian')
    particle_diameter = dataset.variables['D'][:]

    try:
        title=dataset.ebas_instrument_type + " - " + dataset.ebas_component + " - {} - {}".format(dataset.ebas_matrix, dataset.ebas_station_name)
    except:
        try:
            title=dataset.ebas_instrument_type + " - " + dataset.ebas_component + " - {}".format(dataset.ebas_station_name)
        except:
            try:
                title=dataset.ebas_instrument_type + " - {}".format(dataset.ebas_station_name)
            except:
                try:
                    title=dataset.title
                except:
                    title='Title not available'

    #generate non-log legend:
    z_leg,no_log = gen_log_legend(z)
    fig = go.Figure(data=
        go.Heatmap(
            z=z,x=x,y=particle_diameter,
            colorscale='jet',
            zsmooth='best',
            colorbar=dict(
                title='dn/dlogDp (1/cm3)',
                titleside='right',
                tickvals=z_leg,
                ticktext=no_log
            )
        )
    )
    fig.update_yaxes(type="log")
    fig.update_layout(
    title=title,
    xaxis_title="Time",
    yaxis_title="Particle Diameter /nm"
)
    #fig.show()
    return fig

if __name__ == "__main__":
    #b = query_datasets(variables=['Aerosol Physical Properties'],temporal_extent=['2000-01-01T00:00:00', '2022-01-10T00:00:00'],spatial_extent=[0, 0, 180, 90])
    #print(b)
    
    #ret = read_dataset("http://thredds.nilu.no/thredds/dodsC/ebas/NO0042G.20160506060000.20170505102504.dmps.particle_number_size_distribution.pm10.1y.1h.NO01L_DMPS_ZEP1_NRT.NO01L_dmps_DMPS_ZEP01..nc", ['Aerosol Physical Properties'])
    ret = get_contour_plot(get_dataset("http://thredds.nilu.no/thredds/dodsC/ebas/NO0042G.20160506060000.20170505102504.dmps.particle_number_size_distribution.pm10.1y.1h.NO01L_DMPS_ZEP1_NRT.NO01L_dmps_DMPS_ZEP01..nc"))
    ret.show()
    #print(ret)
    # ret = read_dataset("http://thredds.nilu.no/thredds/dodsC/ebas/DE0007R.20131231230000.20211123085808.high_vol_sampler.pm25_mass.pm25.7y.1d.DE03L_UBA_Ng_HVS_0002.DE28L_UBA_Sm_FWg_0001.lev2.nc", ['Aerosol Physical Properties'])
    # print(ret)
    # ret = read_dataset("https://thredds.nilu.no/thredds/fileServer/ebas/FR0022R.20120101090000.20210714000000.TEOM.pm10_mass.pm10.9y.1d.FR11L_OPE_teom_1405DF_pm10.FR11L_teom.lev2.nc", ['Aerosol Physical Properties'])
    # print(ret)
    
    
