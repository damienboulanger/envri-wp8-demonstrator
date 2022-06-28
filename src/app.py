"""
ATMO-ACCESS time series service
"""

import os
import pandas as pd

# Local imports
import data_access
import gui

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

# Configuration of the app
# For the usual Dash app, see: https://dash.plotly.com/devtools#configuring-with-run_server
# For a JupyterDash app version, see: https://github.com/plotly/jupyter-dash/blob/master/notebooks/getting_started.ipynb
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
PLOT_DATASETS_TAB_VALUE = 'plot-datasets-tab'

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
SELECT_DATASETS_BUTTON_ID = 'select-datasets-button'
    # 'n_click' contains a number of click at the button
LAT_MAX_ID = 'lat-max'
LAT_MIN_ID = 'lat-min'
LON_MAX_ID = 'lon-max'
LON_MIN_ID = 'lon-min'
    # 'value' contains a number (or None)
GANTT_VIEW_RADIO_ID = 'gantt-view-radio'
    # 'value' contains 'compact' or 'detailed'
GANTT_GRAPH_ID = 'gantt-graph'
TIMESERIES_GRAPH_ID = 'timeseries-graph'
    # 'figure' contains a Plotly figure object
DATASETS_STORE_ID = 'datasets-store'
DATASETS_STORE_VISU_ID = 'datasets-store-visu'
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

# Initialization of global objects
app = JupyterDash(__name__, external_stylesheets=[
    dbc.themes.BOOTSTRAP,
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css',
])
stations = data_access.get_stations()
station_by_shortnameRI = gui.get_station_by_shortnameRI(stations)
variables = data_access.get_vars()
std_variables = gui.get_std_variables(variables)


# Begin of definition of routines which constructs components of the dashboard (see gui.plot)
def get_dashboard_layout():
    # these are special Dash components used for transferring data from one callback to other callback(s)
    # without displaying the data
    stores = [
        dcc.Store(id=DATASETS_STORE_ID),
        dcc.Store(id=DATASETS_STORE_VISU_ID),
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
                gui.get_variables_checklist(VARIABLES_CHECKLIST_ID, std_variables),
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
                         gui.get_bbox_selection_div(LAT_MAX_ID, LAT_MIN_ID, LON_MAX_ID, LON_MIN_ID),
                         html.Div(id='selected-stations-div',
                                  style={'margin-top': '20px'},
                                  children=[
                                      html.P('Selected stations (you can refine your selection)', style={'font-weight': 'bold'}),
                                      dcc.Dropdown(id=SELECTED_STATIONS_DROPDOWN_ID, multi=True, clearable=False),
                                  ]),
                     ]),
        ]),

        html.Div(id='search-datasets-right-panel-div', className='eight columns', children=[
            gui.get_stations_map(STATIONS_MAP_ID, stations),
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
                dbc.Button(id=SELECT_DATASETS_BUTTON_ID, n_clicks=0,
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
    
    plot_data_tab =  dcc.Tab(label='Visualize datasets', value=PLOT_DATASETS_TAB_VALUE,
                                  children=html.Div(style={'margin': '20px'}, children=[
        html.Div(id='plot_datasets-div', children=
                dcc.Graph(
                id=TIMESERIES_GRAPH_ID,
            )
        ),
    ]))

    mockup_remaining_tabs = _get_mockup_remaining_tabs()

    app_tabs = dcc.Tabs(id=APP_TABS_ID, value=SEARCH_DATASETS_TAB_VALUE,
                        children=[
                            stations_vars_tab,
                            select_datasets_tab,
                            plot_data_tab,
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
    colocation_tab = dcc.Tab(label='Colocation satellite data', value='colocation-tab')
    download_tab = dcc.Tab(label='Download datasets', value='download-tab')
    #return [plot_data_tab, colocation_tab, download_tab]
    return []

# End of definition of routines which constructs components of the dashboard

# Assign a dashboard layout to app Dash object
app.layout = get_dashboard_layout()

# Begin of callback definitions and their helper routines.
# See: https://dash.plotly.com/basic-callbacks for a basic tutorial and
# https://dash.plotly.com/  -->  Dash Callback in left menu for more detailed documentation

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
    Output(LON_MIN_ID, 'value'),
    Output(LON_MAX_ID, 'value'),
    Output(LAT_MIN_ID, 'value'),
    Output(LAT_MAX_ID, 'value'),
    Output(SELECTED_STATIONS_DROPDOWN_ID, 'options'),
    Output(SELECTED_STATIONS_DROPDOWN_ID, 'value'),
    Input(STATIONS_MAP_ID, 'selectedData'))
def get_selected_stations_bbox_and_dropdown(selected_stations):
    selected_stations_df = gui.get_selected_points(selected_stations)
    bbox = gui.get_bounding_box(selected_stations_df, selected_stations)
    selected_stations_dropdown_options, selected_stations_dropdown_value = gui.get_selected_stations_dropdown(selected_stations_df, stations)
    return bbox + [selected_stations_dropdown_options, selected_stations_dropdown_value]

@app.callback(
    Output(DATASETS_STORE_ID, 'data'),
    Output(APP_TABS_ID, 'value'),
    Input(SEARCH_DATASETS_BUTTON_ID, 'n_clicks'),
    Input(SELECT_DATASETS_BUTTON_ID, 'n_clicks'),
    State(VARIABLES_CHECKLIST_ID, 'value'),
    State(LON_MIN_ID, 'value'),
    State(LON_MAX_ID, 'value'),
    State(LAT_MIN_ID, 'value'),
    State(LAT_MAX_ID, 'value'),
    State('my-date-picker-range', 'start_date'),
    State('my-date-picker-range', 'end_date'),
    State(SELECTED_STATIONS_DROPDOWN_ID, 'value'),
    State(DATASETS_STORE_ID, 'data'),  # TODO: if no station or variable selected, do not launch Search datasets action; instead, return an old data
    State(DATASETS_TABLE_ID, 'selected_row_ids'),
)
def change_tab(
        n_clicks_search, n_clicks_select, selected_variables, lon_min, lon_max, lat_min, lat_max, start, end,
        selected_stations_idx, previous_datasets_json, selected_row_ids
    ):
    
    from dash.exceptions import PreventUpdate
    if (n_clicks_search is None and n_clicks_select is None) or (n_clicks_search+n_clicks_select==0):
        raise PreventUpdate
    else: 
        ctx = dash.callback_context
        button_id = ctx.triggered[0]['prop_id'].split('.')[0] if not None else 'No clicks yet'
        
        if button_id == SEARCH_DATASETS_BUTTON_ID:
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
        
            new_active_tab = SELECT_DATASETS_TAB_VALUE if n_clicks_search > 0 else SEARCH_DATASETS_TAB_VALUE  # TODO: is it a right way?
            return datasets_df_filtered.to_json(orient='split', date_format='iso'), new_active_tab
        
        if button_id == SELECT_DATASETS_BUTTON_ID:
            new_active_tab = PLOT_DATASETS_TAB_VALUE if n_clicks_select > 0 else SELECT_DATASETS_TAB_VALUE
            return selected_row_ids, new_active_tab    

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
        fig = gui.get_timeline_by_station(datasets_df)
    else:
        fig = gui.get_timeline_by_station_and_vars(datasets_df)
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
    # on rendering HTML snipplets in DataTable cells: https://github.com/plotly/dash-table/pull/916
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

    # on rendering HTML snipplets in DataTable cells: https://github.com/plotly/dash-table/pull/916
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
@app.callback(
    Output(QUICKLOOK_POPUP_ID, 'children'),
    Input(DATASETS_TABLE_ID, 'active_cell'),
    State(DATASETS_STORE_ID, 'data'),
)
def popup_graphs(active_cell, datasets_json):
    global _tmp_dataset, _tmp_ds, _active_cell

    _active_cell = active_cell

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
                figure=gui.plot_vars(ds, ds_vars[0], ds_vars[1] if len(ds_vars) > 1 else None)
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

@app.callback(
    Output(TIMESERIES_GRAPH_ID, 'figure'),
    Output(TIMESERIES_GRAPH_ID, 'selectedData'),
    Input(DATASETS_STORE_VISU_ID, 'data'),
)
def get_timeseries_figure(datasets_json):
    selectedData = {'points': []}
    return {}, selectedData

# End of callback definitions


# Launch the Dash application.
# app_conf['debug'] = False
app.run_server(**app_conf)
