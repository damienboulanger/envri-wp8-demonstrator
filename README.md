Author: Damien Boulanger

# Demonstrator ENVRI-FAIR WP8 - Task 8.5

- version 1: extract variables names from CSW and REST endpoints

- version 2 : using ATMO-ACCESS developements

[![Binder](https://notebooks.gesis.org/binder/badge_logo.svg)](https://mybinder.org/v2/gh/damienboulanger/envri-wp8-demonstrator/HEAD?urlpath=/tree/app.ipynb)

## Installation
```sh
git clone https://github.com/damienboulanger/envri-wp8-demonstrator
cd envri-wp8-demonstrator
conda env create -f environment.yml
conda activate envri-wp8-env
```

## Deployment
Deployment in the stand-alone mode:
```sh
python app.py
```

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
