Author: Damien Boulanger

# FAIR ENVRI atmospheric data demonstrator

This demonstrator has been implemented in the frame of the ENVRI-FAIR project (https://envri.eu/) in order to demonstrate the interoperability between the data of the European Research Infrastructures of the Atmosphere domain: ACTRIS, IAGOS, ICOS and SIOS.

The work is part of the Work Package WP8 and the Task 8.5.

## Installation

This demonstrator has been develop in Python using Dash and Plotly APIs.

You can install the demonstrator by following this procedure:

```sh
git clone https://github.com/iagos-dc/envri-fair-atmospheric-demonstrator
cd envri-wp8-demonstrator
conda env create -f environment.yml
conda activate envri-wp8-env
```

## Deployment

Deployment in the stand-alone mode:

```sh
python app.py
```

Open the address: http://localhost:9235/

Deployment in a Jupyter Notebook:

```sh
jupyter notebook
```
then open `app.ipynb` in the notebook and run all cells (can use >> button to that end).

If you need to change the application configuration, modify this part of the code (somewhere at the beginning of the script):

```python
RUNNING_IN_BINDER = False   # for running in Binder change it to True
app_conf = {'mode': 'external', 'debug': True}  # for running inside a Jupyter notebook change 'mode' to 'inline'
if RUNNING_IN_BINDER:
    JupyterDash.infer_jupyter_proxy_config()
else:
    app_conf.update({'host': 'localhost', 'port': 9235})
```

## License

All data used in this demonstrator all following data usage license of each relevant Research Infrastructure:
- ACTRIS data are licensed under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
- IAGOS data are licensed under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
- ICOS data are licensed under the Creative Commons Attribution 4.0 International licence (CC BY 4.0).
- Data tagged as SIOS for this demonstrator are quality controlled timeseries from Norwegian weather stations, as provided by the Norwegian Meteorological Institute, and other stations in Svalbard region, as provided by the Norwegian Institute for Air Research, the Norwegian Polar Institute and the Italian Institute of Polar Sciences. Data from the Norwegian Meteorological Institute are licensed under the Creative Commons 4.0 BY (CC-BY-4.0). Data from Italian Institute of Polar Sciences and EXAODEP-2020 participants are licensed under Non-commercial Creative Commons 4.0 (CC-BY-NC-4.0).


## Credits

This demonstrator has been developed by CNRS by Damien Boulanger (Manager of the IAGOS Data Centre, Observatoire Midi-Pyrénées, SEDOO).

The library for data access has been developed jointly by all the Research Infrastructures:
- ACTRIS
- ICOS
- CNRS (Damien Boulanger - Manager of the IAGOS Data Centre, Observatoire Midi-Pyrénées, SEDOO) for access to IAGOS data
- SIOS