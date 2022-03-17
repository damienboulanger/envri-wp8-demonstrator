"""
ATMO-ACCESS time series service
"""

import os
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime

# Dash imports; for documentation (including tutorial), see: https://dash.plotly.com/
import dash
from dash import dcc
from dash import html
from dash import dash_table
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc

# Provides a version of Dash application which can be run in Jupyter notebook/lab
# See: https://github.com/plotly/jupyter-dash
from jupyter_dash import JupyterDash

# Local imports
import data_access


# Configuration of the app
# See: https://dash.plotly.com/devtools#configuring-with-run_server
# for the usual Dash app, and:
# https://github.com/plotly/jupyter-dash/blob/master/notebooks/getting_started.ipynb
# for a JupyterDash app version.
app_conf = {'mode': 'external', 'debug': True}  # for running inside a Jupyter notebook change 'mode' to 'inline'
RUNNING_IN_BINDER = os.environ.get('BINDER_SERVICE_HOST') is not None
if RUNNING_IN_BINDER:
    JupyterDash.infer_jupyter_proxy_config()
else:
    app_conf.update({'host': 'localhost', 'port': 9235})


# Below there are id's of Dash JS components.
# The components themselves are declared in the dashboard layout (see the function get_dashboard_layout).
# Essential properties of each component are explained in the comments below.
APP_TABS_ID = 'app-tabs'    # see: https://dash.plotly.com/dash-core-components/tabs; method 1 (content as callback)
    # value contains an id of the active tab
    # children contains a list of layouts of each tab
SEARCH_DATASETS_TAB_VALUE = 'search-datasets-tab'
SELECT_DATASETS_TAB_VALUE = 'select-datasets-tab'

STATIONS_MAP_ID = 'stations-map'
    # 'selectedData' contains a dictionary
    # {
    #   'point' ->
    #       list of dicionaries {'pointIndex' -> index of a station in the global dataframe stations, 'lon' -> float, 'lat' -> float, ...},
    #   'range' (present only if a box was selected on the map) ->
    #       {'mapbox' -> [[lon_min, lat_max], [lon_max, lat_min]]}
    # }
VARIABLES_CHECKLIST_ALL_NONE_SWITCH_ID = 'variables-checklist-all-none-switch'
VARIABLES_CHECKLIST_ID = 'variables-checklist'
SELECTED_STATIONS_DROPDOWN_ID = 'selected-stations-dropdown'
    # 'options' contains a list of dictionaries {'label' -> station label, 'value' -> index of the station in the global dataframe stations (see below)}
    # 'value' contains a list of indices of stations selected using the dropdown
SEARCH_DATASETS_BUTTON_ID = 'search-datasets-button'
    # 'n_click' contains a number of click at the button
LAT_MAX_ID = 'lat-max'
LAT_MIN_ID = 'lat-min'
LON_MAX_ID = 'lon-max'
LON_MIN_ID = 'lon-min'
    # 'value' contains a number (or None)
GANTT_VIEW_RADIO_ID = 'gantt-view-radio'
    # 'value' contains 'compact' or 'detailed'
GANTT_GRAPH_ID = 'gantt-graph'
    # 'figure' contains a Plotly figure object
DATASETS_STORE_ID = 'datasets-store'
    # 'data' stores datasets metadata in JSON, as provided by the method pd.DataFrame.to_json(orient='split', date_format='iso')
DATASETS_TABLE_CHECKLIST_ALL_NONE_SWITCH_ID = 'datasets-table-checklist-all-none-switch'
DATASETS_TABLE_ID = 'datasets-table'
    # 'columns' contains list of dictionaries {'name' -> column name, 'id' -> column id}
    # 'data' contains a list of records as provided by the method pd.DataFrame.to_dict(orient='records')
QUICKLOOK_POPUP_ID = 'quicklook-popup'
    # 'children' contains a layout of the popup

# Atmo-Access logo url
ATMO_ACCESS_LOGO_URL = \
    'https://www7.obs-mip.fr/wp-content-aeris/uploads/sites/82/2021/03/ATMO-ACCESS-Logo-final_horizontal-payoff-grey-blue.png'

# Color codes
ACTRIS_COLOR_HEX = '#00adb7'
IAGOS_COLOR_HEX = '#456096'
ICOS_COLOR_HEX = '#ec165c'
SIOS_COLOR_HEX ='#e7b059'


def _get_station_by_shortnameRI(stations):
    df = stations.set_index('short_name_RI')[['long_name', 'RI']]
    df['station_fullname'] = df['long_name'] + ' (' + df['RI'] + ')'
    return df


def _get_std_variables(variables):
    std_vars = variables[['std_ECV_name', 'code']].drop_duplicates()
    # TODO: temporary
    try:
        std_vars = std_vars[std_vars['std_ECV_name'] != 'Aerosol Optical Properties']
    except ValueError:
        pass
    std_vars['label'] = std_vars['code'] + ' - ' + std_vars['std_ECV_name']
    return std_vars.rename(columns={'std_ECV_name': 'value'}).drop(columns='code')


# Initialization of global objects
app = JupyterDash(__name__, external_stylesheets=[
    dbc.themes.BOOTSTRAP,
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css',
])
stations = data_access.get_stations()
station_by_shortnameRI = _get_station_by_shortnameRI(stations)
variables = data_access.get_vars()
std_variables = _get_std_variables(variables)


# Begin of definition of routines which constructs components of the dashboard

def get_variables_checklist():
    """
    Provide variables checklist Dash component
    See: https://dash.plotly.com/dash-core-components/checklist
    :return: dash.dcc.Checklist
    """
    variables_options = std_variables.to_dict(orient='records')
    variables_values = std_variables['value'].tolist()
    variables_checklist = dbc.Checklist(
        id=VARIABLES_CHECKLIST_ID,
        options=variables_options,
        value=variables_values,
        labelStyle={'display': 'flex'},  # display in column rather than in a row; not sure if it is the right way to do
    )
    return variables_checklist


def get_stations_map():
    """
    Provide a Dash component containing a map with stations
    See: https://dash.plotly.com/dash-core-components/graph
    :return: dash.dcc.Graph object
    """
    fig = px.scatter_mapbox(
        stations,
        lat="latitude", lon="longitude", color='RI',
        hover_name="long_name", hover_data={'ground_elevation': True, 'marker_size': False},
        custom_data=['idx'],
        size=stations['marker_size'],
        size_max=7,
        category_orders={'RI': ['ACTRIS', 'IAGOS', 'ICOS', 'SIOS']},
        color_discrete_sequence=[ACTRIS_COLOR_HEX, IAGOS_COLOR_HEX, ICOS_COLOR_HEX, SIOS_COLOR_HEX],
        center={'lat': 54, 'lon':12},
        zoom=3, height=600,
        title='Stations map',
    )
    fig.update_layout(
        mapbox_style="open-street-map",
        margin={'r': 0, 't': 40, 'l': 0, 'b': 0},
        clickmode='event+select',
        hoverdistance=1, hovermode='closest',  # hoverlabel=None,
    )
    # TODO: synchronize box selection on the map with max/min lon/lat input fields
    # TODO: as explained in https://dash.plotly.com/interactive-graphing (Generic Crossfilter Recipe)
    stations_map = dcc.Graph(
        id=STATIONS_MAP_ID,
        figure=fig,
    )
    return stations_map


def get_bbox_selection_div():
    """
    Provide a composed Dash component with input/ouput text fields which allow to provide coordinates of a bounding box
    See: https://dash.plotly.com/dash-core-components/input
    :return: dash.html.Div object
    """
    bbox_selection_div = html.Div(id='bbox-selection-div', style={'margin-top': '15px'}, children=[
        html.Div(className='row', children=[
            html.Div(className='three columns, offset-by-six columns', children=[
                dcc.Input(id=LAT_MAX_ID, style={'width': '100%'}, placeholder='lat max', type='number', min=-90, max=90),  # , step=0.01),
            ]),
        ]),
        html.Div(className='row', children=[
            html.Div(className='three columns',
                     children=html.P(children='Bounding box:', style={'width': '100%', 'font-weight': 'bold'})),
            html.Div(className='three columns',
                     children=dcc.Input(style={'width': '100%'}, id=LON_MIN_ID, placeholder='lon min', type='number',
                                        min=-180, max=180),  # , step=0.01),
                     ),
            html.Div(className='offset-by-three columns, three columns',
                     children=dcc.Input(style={'width': '100%'}, id=LON_MAX_ID, placeholder='lon max', type='number',
                                        min=-180, max=180),  # , step=0.01),
                     ),
        ]),
        html.Div(className='row', children=[
            html.Div(className='offset-by-six columns, three columns',
                     children=dcc.Input(style={'width': '100%'}, id=LAT_MIN_ID, placeholder='lat min', type='number',
                                        min=-90, max=90),  # , step=0.01),
                     ),
        ]),
    ])
    return bbox_selection_div


def get_dashboard_layout():
    # these are special Dash components used for transferring data from one callback to other callback(s)
    # without displaying the data
    stores = [
        dcc.Store(id=DATASETS_STORE_ID),
    ]

    # logo and application title
    title_and_logo_bar = html.Div(style={'display': 'flex', 'justify-content': 'space-between',
                                         'margin-bottom': '20px'},
                                  children=[
        html.Div(children=[
            html.H2('FAIR ENVRI atmospheric data demonstrator', style={'font-weight': 'bold'}),
        ]),
        html.Div(children=[
            html.A(
                html.Img(
                            src=app.get_asset_url('envrifair-logo-transp.png'),
                            style={'float': 'right', 'height': '140px', 'margin-top': '10px'}
                ),
                        href="https://envri.eu/home-envri-fair/"
            ),
        ]),
    ])

    stations_vars_tab = dcc.Tab(label='Search datasets', value=SEARCH_DATASETS_TAB_VALUE,
                                children=html.Div(style={'margin': '20px'}, children=[
        html.Div(id='search-datasets-left-panel-div', className='four columns', children=[
            html.Div(id='variables-selection-div', className='nine columns', children=[
                html.P('Select variable(s):', style={'font-weight': 'bold'}),
                dbc.Switch(
                    id=VARIABLES_CHECKLIST_ALL_NONE_SWITCH_ID,
                    label='Select all / none',
                    style={'margin-top': '10px'},
                    value=True,
                ),
                get_variables_checklist(),
            ]),

            html.Div(id='search-datasets-button-div', className='three columns',
                     children=dbc.Button(id=SEARCH_DATASETS_BUTTON_ID, n_clicks=0,
                                         color='primary',
                                         type='submit',
                                         style={'font-weight': 'bold'},
                                         children='Search datasets')),

            html.Div(id='search-datasets-left-panel-cont-div', className='twelve columns',
                     style={'margin-top': '20px'},
                     children=[
                         html.Div(children=[
                             html.P('Date range:', style={'display': 'inline', 'font-weight': 'bold', 'margin-right': '20px'}),
                             dcc.DatePickerRange(
                                 id='my-date-picker-range',
                                 min_date_allowed=data_access.get_start_date(),
                                 max_date_allowed=data_access.get_end_date(),
                                 initial_visible_month=data_access.get_start_date(),
                                 start_date=data_access.get_start_date(),
                                 end_date=data_access.get_end_date()
                             ),
                         ]),
                         get_bbox_selection_div(),
                         html.Div(id='selected-stations-div',
                                  style={'margin-top': '20px'},
                                  children=[
                                      html.P('Selected stations (you can refine your selection)', style={'font-weight': 'bold'}),
                                      dcc.Dropdown(id=SELECTED_STATIONS_DROPDOWN_ID, multi=True, clearable=False),
                                  ]),
                     ]),
        ]),

        html.Div(id='search-datasets-right-panel-div', className='eight columns', children=[
            get_stations_map(),
        ]),
    ]))

    select_datasets_tab = dcc.Tab(label='Select datasets', value=SELECT_DATASETS_TAB_VALUE,
                                  children=html.Div(style={'margin': '20px'}, children=[
        html.Div(id='select-datasets-left-panel-div', className='four columns', children=[
            html.Div(id='select-datasets-left-left-subpanel-div', className='nine columns', children=
                dbc.RadioItems(
                    id=GANTT_VIEW_RADIO_ID,
                    options=[
                        {'label': 'compact view', 'value': 'compact'},
                        {'label': 'detailed view', 'value': 'detailed'},
                    ],
                    value='compact',
                    inline=True)),
            html.Div(id='select-datasets-left-right-subpanel-div', className='three columns', children=
                dbc.Button(id='foo', n_clicks=0,
                       color='primary', type='submit',
                       style={'font-weight': 'bold'},
                       children='Select datasets'))
        ]),
        html.Div(id='select-datasets-right-panel-div', className='eight columns', children=None),
        html.Div(id='select-datasets-main-panel-div', className='twelve columns', children=[
            dcc.Graph(
                id=GANTT_GRAPH_ID,
            ),
            dbc.Switch(
                id=DATASETS_TABLE_CHECKLIST_ALL_NONE_SWITCH_ID,
                label='Select all / none',
                style={'margin-top': '10px'},
                value=False,
            ),
            dash_table.DataTable(
                id=DATASETS_TABLE_ID,
                css=[dict(selector="p", rule="margin: 0px;")],
                # see: https://dash.plotly.com/datatable/interactivity
                row_selectable="multi",
                selected_rows=[],
                selected_row_ids=[],
                sort_action='native',
                # filter_action='native',
                page_action="native", page_current=0, page_size=20,
                # see: https://dash.plotly.com/datatable/width
                # hidden_columns=['url', 'ecv_variables', 'ecv_variables_filtered', 'std_ecv_variables_filtered', 'var_codes', 'platform_id_RI'],
                style_data={
                    'whiteSpace': 'normal',
                    'height': 'auto',
                    'lineHeight': '15px'
                },
                style_cell={'textAlign': 'left'},
                markdown_options={'html': True},
            ),
            html.Div(id=QUICKLOOK_POPUP_ID),
        ]),
    ]))

    mockup_remaining_tabs = _get_mockup_remaining_tabs()

    app_tabs = dcc.Tabs(id=APP_TABS_ID, value=SEARCH_DATASETS_TAB_VALUE,
                        children=[
                            stations_vars_tab,
                            select_datasets_tab,
                            *mockup_remaining_tabs
                        ])

    layout = html.Div(id='app-container-div', style={'margin': '30px', 'padding-bottom': '50px'}, children=stores + [
        html.Div(id='heading-div', className='twelve columns', children=[
            title_and_logo_bar,
            app_tabs,
        ])
    ])

    return layout


def _get_mockup_remaining_tabs():
    plot_data_tab = dcc.Tab(label='Visualize datasets', value='plot-data-tab')
    colocation_tab = dcc.Tab(label='Colocation satellite data', value='colocation-tab')
    download_tab = dcc.Tab(label='Download datasets', value='download-tab')
    return [plot_data_tab, colocation_tab, download_tab]

# End of definition of routines which constructs components of the dashboard


# Assign a dashboard layout to app Dash object
app.layout = get_dashboard_layout()


# Begin of callback definitions and their helper routines.
# See: https://dash.plotly.com/basic-callbacks
# for a basic tutorial and
# https://dash.plotly.com/  -->  Dash Callback in left menu
# for more detailed documentation

@app.callback(
    Output(VARIABLES_CHECKLIST_ID, 'value'),
    Input(VARIABLES_CHECKLIST_ALL_NONE_SWITCH_ID, 'value')
)
def toogle_variable_checklist(variables_checklist_all_none_switch):
    if variables_checklist_all_none_switch:
        return std_variables['value'].tolist()
    else:
        return []


@app.callback(
    Output(DATASETS_STORE_ID, 'data'),
    Output(APP_TABS_ID, 'value'),
    Input(SEARCH_DATASETS_BUTTON_ID, 'n_clicks'),
    State(VARIABLES_CHECKLIST_ID, 'value'),
    State(LON_MIN_ID, 'value'),
    State(LON_MAX_ID, 'value'),
    State(LAT_MIN_ID, 'value'),
    State(LAT_MAX_ID, 'value'),
    State('my-date-picker-range', 'start_date'),
    State('my-date-picker-range', 'end_date'),
    State(SELECTED_STATIONS_DROPDOWN_ID, 'value'),
    State(DATASETS_STORE_ID, 'data'),  # TODO: if no station or variable selected, do not launch Search datasets action; instead, return an old data
)
def search_datasets(
        n_clicks, selected_variables, lon_min, lon_max, lat_min, lat_max, start, end,
        selected_stations_idx, previous_datasets_json
    ):
    
    start = start + "T00:00:00"
    
    if selected_stations_idx is None:
        selected_stations_idx = []

    empty_datasets_df = pd.DataFrame(
        columns=['title', 'url', 'ecv_variables', 'platform_id', 'RI', 'var_codes', 'ecv_variables_filtered',
                 'std_ecv_variables_filtered', 'var_codes_filtered', 'time_period_start', 'time_period_end',
                 'platform_id_RI', 'id']
    )   # TODO: do it cleanly

    if not selected_variables or None in [lon_min, lon_max, lat_min, lat_max]:
        if previous_datasets_json is not None:
            datasets_json = previous_datasets_json
        else:
            datasets_json = empty_datasets_df.to_json(orient='split', date_format='iso')
        return datasets_json, SEARCH_DATASETS_TAB_VALUE

    datasets_df = data_access.get_datasets(selected_variables, lon_min, lon_max, lat_min, lat_max, start, end)
    if datasets_df is None:
        datasets_df = empty_datasets_df

    selected_stations = stations.iloc[selected_stations_idx]
    datasets_df_filtered = datasets_df[
        datasets_df['platform_id'].isin(selected_stations['short_name']) &
        datasets_df['RI'].isin(selected_stations['RI'])     # short_name of the station might not be unique among RI's
    ]

    datasets_df_filtered = datasets_df_filtered.reset_index(drop=True)
    datasets_df_filtered['id'] = datasets_df_filtered.index

    new_active_tab = SELECT_DATASETS_TAB_VALUE if n_clicks > 0 else SEARCH_DATASETS_TAB_VALUE  # TODO: is it a right way?

    return datasets_df_filtered.to_json(orient='split', date_format='iso'), new_active_tab


def _get_selected_points(selected_stations):
    if selected_stations is not None:
        points = selected_stations['points']
        for point in points:
            point['idx'] = round(point['customdata'][0])
    else:
        points = []
    return pd.DataFrame.from_records(points, index='idx', columns=['idx', 'lon', 'lat'])


def _get_bounding_box(selected_points_df, selected_stations):
    # decimal precision for bounding box coordinates (lon/lat)
    decimal_precision = 2

    # find selection box, if there is one
    try:
        (lon_min, lat_max), (lon_max, lat_min) = selected_stations['range']['mapbox']
    except:
        lon_min, lon_max, lat_min, lat_max = np.inf, -np.inf, np.inf, -np.inf

    if len(selected_points_df) > 0:
        # find bouding box for selected points
        epsilon = 0.001  # precision margin for filtering on lon/lat of stations later on
        lon_min2, lon_max2 = selected_points_df['lon'].min() - epsilon, selected_points_df['lon'].max() + epsilon
        lat_min2, lat_max2 = selected_points_df['lat'].min() - epsilon, selected_points_df['lat'].max() + epsilon

        # find a common bounding box for the both bboxes found above
        lon_min, lon_max = np.min((lon_min, lon_min2)), np.max((lon_max, lon_max2))
        lat_min, lat_max = np.min((lat_min, lat_min2)), np.max((lat_max, lat_max2))

    if not np.all(np.isfinite([lon_min, lon_max, lat_min, lat_max])):
        return [None] * 4
    return [round(coord, decimal_precision) for coord in (lon_min, lon_max, lat_min, lat_max)]


def _get_selected_stations_dropdown(selected_stations_df):
    idx = selected_stations_df.index
    df = stations.iloc[idx]
    labels = df['short_name'] + ' (' + df['long_name'] + ', ' + df['RI'] + ')'
    options = labels.rename('label').reset_index().rename(columns={'index': 'value'})
    return options.to_dict(orient='records'), list(options['value'])


@app.callback(
    Output(LON_MIN_ID, 'value'),
    Output(LON_MAX_ID, 'value'),
    Output(LAT_MIN_ID, 'value'),
    Output(LAT_MAX_ID, 'value'),
    Output(SELECTED_STATIONS_DROPDOWN_ID, 'options'),
    Output(SELECTED_STATIONS_DROPDOWN_ID, 'value'),
    Input(STATIONS_MAP_ID, 'selectedData'))
def get_selected_stations_bbox_and_dropdown(selected_stations):
    selected_stations_df = _get_selected_points(selected_stations)
    bbox = _get_bounding_box(selected_stations_df, selected_stations)
    selected_stations_dropdown_options, selected_stations_dropdown_value = _get_selected_stations_dropdown(selected_stations_df)
    return bbox + [selected_stations_dropdown_options, selected_stations_dropdown_value]


def _contiguous_periods(start, end, var_codes=None, dt=pd.Timedelta('1D')):
    """
    Merge together periods which overlap, are adjacent or nearly adjacent (up to dt). The merged periods are returned
    with:
    - start and end time ('time_period_start', 'time_period_end'),
    - list of indices of datasets which enters into a given period ('indices'),
    - number of the datasets (the length of the above list) ('datasets'),
    - codes of variables available within a given period, if the parameter var_codes is provided.
    :param start: pandas.Series of Timestamps with periods' start
    :param end: pandas.Series of Timestamps with periods' end
    :param var_codes: pandas.Series of strings or None, optional; if given, must contain variable codes separated by comma
    :param dt: pandas.Timedelta
    :return: pandas.DataFrame with columns 'time_period_start', 'time_period_end', 'indices', 'datasets' and 'var_codes'
    """
    s, e, idx = [], [], []
    df_dict = {'s': start, 'e': end}
    if var_codes is not None:
        dat = []
        df_dict['var_codes'] = var_codes
    df = pd.DataFrame(df_dict).sort_values(by='s', ignore_index=False)
    df['e'] = df['e'].cummax()
    if len(df) > 0:
        delims, = np.nonzero((df['e'] + dt).values[:-1] < df['s'].values[1:])
        delims = np.concatenate(([0], delims + 1, [len(df)]))
        for i, j in zip(delims[:-1], delims[1:]):
            s.append(df['s'].iloc[i])
            e.append(df['e'].iloc[j - 1])
            idx.append(df.index[i:j])
            if var_codes is not None:
                # concatenate all var_codes; [:-1] is to suppress the last comma
                all_var_codes = (df['var_codes'].iloc[i:j] + ', ').sum()[:-2]
                # remove duplicates from all_var_codes...
                all_var_codes = np.sort(np.unique(all_var_codes.split(', ')))
                # ...and form a single string with codes separated by comma
                all_var_codes = ', '.join(all_var_codes)
                dat.append(all_var_codes)
    res_dict = {'time_period_start': s, 'time_period_end': e, 'indices': idx, 'datasets': [len(i) for i in idx]}
    if var_codes is not None:
        res_dict['var_codes'] = dat
    return pd.DataFrame(res_dict)


def _get_timeline_by_station(datasets_df):
    df = datasets_df\
        .groupby(['platform_id_RI', 'station_fullname', 'RI'])\
        .apply(lambda x: _contiguous_periods(x['time_period_start'], x['time_period_end'], x['var_codes_filtered']))\
        .reset_index()
    df = df.sort_values('platform_id_RI')
    no_platforms = len(df['platform_id_RI'].unique())
    height = 100 + max(100, 50 + 30 * no_platforms)
    gantt = px.timeline(
        df, x_start='time_period_start', x_end='time_period_end', y='platform_id_RI', color='RI',
        hover_name='var_codes',
        hover_data={'station_fullname': True, 'platform_id_RI': True, 'datasets': True, 'RI': False},
        custom_data=['indices'],
        category_orders={'RI': ['ACTRIS', 'IAGOS', 'ICOS', 'SIOS']},
        color_discrete_sequence=[ACTRIS_COLOR_HEX, IAGOS_COLOR_HEX, ICOS_COLOR_HEX, SIOS_COLOR_HEX],
        height=height
    )
    gantt.update_layout(
        clickmode='event+select',
        selectdirection='h',
        legend={'orientation': 'h', 'yanchor': 'bottom', 'y': 1.04, 'xanchor': 'left', 'x': 0},
    )
    return gantt


def _get_timeline_by_station_and_vars(datasets_df):
    df = datasets_df\
        .groupby(['platform_id_RI', 'station_fullname', 'var_codes_filtered'])\
        .apply(lambda x: _contiguous_periods(x['time_period_start'], x['time_period_end']))\
        .reset_index()
    df = df.sort_values('platform_id_RI')
    facet_col_wrap = 4
    no_platforms = len(df['platform_id_RI'].unique())
    no_var_codes_filtered = len(df['var_codes_filtered'].unique())
    no_facet_rows = (no_var_codes_filtered + facet_col_wrap - 1) // facet_col_wrap
    height = 100 + max(100, 50 + 25 * no_platforms) * no_facet_rows
    gantt = px.timeline(
        df, x_start='time_period_start', x_end='time_period_end', y='platform_id_RI', color='var_codes_filtered',
        hover_name='station_fullname',
        hover_data={'station_fullname': True, 'platform_id_RI': True, 'var_codes_filtered': True, 'datasets': True},
        custom_data=['indices'],
        height=height, facet_col='var_codes_filtered', facet_col_wrap=facet_col_wrap,
    )
    gantt.update_layout(
        clickmode='event+select',
        selectdirection='h',
        legend={'orientation': 'h', 'yanchor': 'bottom', 'y': 1.06, 'xanchor': 'left', 'x': 0},
    )
    return gantt


@app.callback(
    Output(GANTT_GRAPH_ID, 'figure'),
    Output(GANTT_GRAPH_ID, 'selectedData'),
    Input(GANTT_VIEW_RADIO_ID, 'value'),
    Input(DATASETS_STORE_ID, 'data'),
)
def get_gantt_figure(gantt_view_type, datasets_json):
    selectedData = {'points': []}

    if datasets_json is None:
       return {}, selectedData   # empty figure; TODO: is it a right way?

    datasets_df = pd.read_json(datasets_json, orient='split', convert_dates=['time_period_start', 'time_period_end'])
    datasets_df = datasets_df.join(station_by_shortnameRI['station_fullname'], on='platform_id_RI')  # column 'station_fullname' joined to datasets_df

    if len(datasets_df) == 0:
       return {}, selectedData   # empty figure; TODO: is it a right way?

    if gantt_view_type == 'compact':
        fig = _get_timeline_by_station(datasets_df)
    else:
        fig = _get_timeline_by_station_and_vars(datasets_df)
    fig.update_traces(
        selectedpoints=[],
        #mode='markers+text', marker={'color': 'rgba(0, 116, 217, 0.7)', 'size': 20},
        unselected={'marker': {'opacity': 0.4}, }
    )
    return fig, selectedData


@app.callback(
    Output(DATASETS_TABLE_ID, 'columns'),
    Output(DATASETS_TABLE_ID, 'data'),
    Output(DATASETS_TABLE_ID, 'selected_rows'),
    Output(DATASETS_TABLE_ID, 'selected_row_ids'),
    Input(GANTT_GRAPH_ID, 'selectedData'),
    Input(DATASETS_TABLE_CHECKLIST_ALL_NONE_SWITCH_ID, 'value'),
    State(DATASETS_STORE_ID, 'data'),
    State(DATASETS_TABLE_ID, 'selected_row_ids'),
)
def datasets_as_table(gantt_figure_selectedData, datasets_table_checklist_all_none_switch,
                      datasets_json, previously_selected_row_ids):
    table_col_ids = ['eye', 'title', 'var_codes_filtered', 'RI', 'long_name', 'platform_id', 'time_period_start', 'time_period_end',
                     #_#'url', 'ecv_variables', 'ecv_variables_filtered', 'std_ecv_variables_filtered', 'var_codes', 'platform_id_RI'
                     ]
    table_col_names = ['', 'Title', 'Variables', 'RI', 'Station', 'Station code', 'Start', 'End',
                       #_#'url', 'ecv_variables', 'ecv_variables_filtered', 'std_ecv_variables_filtered', 'var_codes', 'platform_id_RI'
                       ]
    table_columns = [{'name': name, 'id': i} for name, i in zip(table_col_names, table_col_ids)]
    # on rendering HTML snipplets in DataTable cells:
    # https://github.com/plotly/dash-table/pull/916
    table_columns[0]['presentation'] = 'markdown'

    if datasets_json is None:
        return table_columns, [], [], []

    datasets_df = pd.read_json(datasets_json, orient='split', convert_dates=['time_period_start', 'time_period_end'])
    datasets_df = datasets_df.join(station_by_shortnameRI['long_name'], on='platform_id_RI')

    # filter on selected timeline bars on the Gantt figure
    if gantt_figure_selectedData and 'points' in gantt_figure_selectedData:
        datasets_indices = []
        for timeline_bar in gantt_figure_selectedData['points']:
            datasets_indices.extend(timeline_bar['customdata'][0])
        datasets_df = datasets_df.iloc[datasets_indices]

    # on rendering HTML snipplets in DataTable cells:
    # https://github.com/plotly/dash-table/pull/916
    datasets_df['eye'] = '<i class="fa fa-eye"></i>'

    table_data = datasets_df[['id'] + table_col_ids].to_dict(orient='records')

    # see here for explanation how dash.callback_context works
    # https://community.plotly.com/t/select-all-rows-in-dash-datatable/41466/2
    # TODO: this part needs to be checked and polished;
    # TODO: e.g. is the manual synchronization between selected_rows and selected_row_ids needed?
    trigger = dash.callback_context.triggered[0]['prop_id'].split('.')[0]
    if trigger == DATASETS_TABLE_CHECKLIST_ALL_NONE_SWITCH_ID:
        if datasets_table_checklist_all_none_switch:
            selected_rows = list(range(len(table_data)))
        else:
            selected_rows = []
        selected_row_ids = datasets_df['id'].iloc[selected_rows].to_list()
    else:
        if previously_selected_row_ids is None:
            previously_selected_row_ids = []
        selected_row_ids = sorted(set(previously_selected_row_ids) & set(datasets_df['id'].to_list()))
        idx = pd.DataFrame({'idx': datasets_df['id'], 'n': range(len(datasets_df['id']))}).set_index('idx')
        idx = idx.loc[selected_row_ids]
        selected_row_ids = idx.index.to_list()
        selected_rows = idx['n'].to_list()
    return table_columns, table_data, selected_rows, selected_row_ids


_tmp_dataset = None
_tmp_ds = None
_active_cell = None


def _plot_vars(ds, v1, v2=None):
    vars_long = data_access.get_vars_long()
    vs = [v1, v2] if v2 is not None else [v1]
    v_names = []
    for v in vs:
        try:
            v_name = vars_long.loc[vars_long['variable_name'] == v]['std_ECV_name'].iloc[0] + f' ({v})'
        except:
            v_name = v
        v_names.append(v_name)
    fig = go.Figure()
    for i, v in enumerate(vs):
        da = ds[v]
        fig.add_trace(go.Scatter(
            x=da['time'].values,
            y=da.values,
            name=v,
            yaxis=f'y{i + 1}'
        ))

    fig.update_layout(
        xaxis=dict(
            domain=[0.0, 0.95]
        ),
        yaxis1=dict(
            title=v_names[0],
            titlefont=dict(
                color="#1f77b4"
            ),
            tickfont=dict(
                color="#1f77b4"
            ),
            anchor='x',
            side='left',
        ),
    )
    if v2 is not None:
        fig.update_layout(
            yaxis2=dict(
                title=v_names[1],
                titlefont=dict(
                    color="#ff7f0e"
                ),
                tickfont=dict(
                    color="#ff7f0e"
                ),
                anchor="x",
                overlaying="y1",
                side="right",
                # position=0.15
            ),
        )

    return fig


@app.callback(
    Output(QUICKLOOK_POPUP_ID, 'children'),
    Input(DATASETS_TABLE_ID, 'active_cell'),
    State(DATASETS_STORE_ID, 'data'),
)
def popup_graphs(active_cell, datasets_json):
    global _tmp_dataset, _tmp_ds, _active_cell

    _active_cell = active_cell
    # print(f'active_cell={active_cell}')

    if datasets_json is None or active_cell is None:
        return None

    datasets_df = pd.read_json(datasets_json, orient='split', convert_dates=['time_period_start', 'time_period_end'])
    s = datasets_df.loc[active_cell['row_id']]
    _tmp_dataset = s

    try:
        ds = data_access.read_dataset(s['RI'], s['url'], s)
        ds_exc = None
    except Exception as e:
        ds = None
        ds_exc = e

    _tmp_ds = ds

    if ds is not None:
        ds_vars = [v for v in ds if ds[v].squeeze().ndim == 1]
        if len(ds_vars) > 0:
            ds_plot = dcc.Graph(
                id='quick-plot',
                figure=_plot_vars(ds, ds_vars[0], ds_vars[1] if len(ds_vars) > 1 else None)
            )
        else:
            ds_plot = None
    else:
        ds_plot = repr(ds_exc)

    return dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle(s['title'])),
            dbc.ModalBody(ds_plot),
        ],
        id="modal-xl",
        size="xl",
        is_open=True,
    )

# End of callback definitions


# Launch the Dash application.
# app_conf['debug'] = False
app.run_server(**app_conf)
