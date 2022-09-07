import dash
from dash import dcc
from dash import html
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import dash_bootstrap_components as dbc

# Local imports
import data_access

# Color codes
ACTRIS_COLOR_HEX = '#00adb7'
IAGOS_COLOR_HEX = '#456096'
ICOS_COLOR_HEX = '#ec165c'
SIOS_COLOR_HEX ='#e7b059'

def get_variables_checklist(list_id, std_variables):
    """
    Provide variables checklist Dash component
    See: https://dash.plotly.com/dash-core-components/checklist
    :return: dash.dcc.Checklist
    """
    variables_options = std_variables.to_dict(orient='records')
    sorted_variables_options = sorted(variables_options, key=lambda d: d['label']) 
    variables_values = std_variables['value'].tolist()
    variables_checklist = dbc.Checklist(
        id=list_id,
        options=sorted_variables_options,
        value=variables_values,
        labelStyle={'display': 'flex'},  # display in column rather than in a row; not sure if it is the right way to do
    )
    return variables_checklist

def get_stations_map(map_id, stations):
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
        center={'lat': 67, 'lon':12},
        zoom=2.3,
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
        id=map_id,
        figure=fig,
        style={'height':800}
    )
    return stations_map

def get_bbox_selection_div(lamax, lamin, lonmax, lonmin):
    """
    Provide a composed Dash component with input/ouput text fields which allow to provide coordinates of a bounding box
    See: https://dash.plotly.com/dash-core-components/input
    :return: dash.html.Div object
    """
    bbox_selection_div = html.Div(id='bbox-selection-div', style={'margin-top': '15px'}, children=[
        html.Div(className='row', children=[
            html.Div(className='three columns, offset-by-six columns', children=[
                dcc.Input(id=lamax, style={'width': '100%'}, placeholder='lat max', type='number', min=-90, max=90),  # , step=0.01),
            ]),
        ]),
        html.Div(className='row', children=[
            html.Div(className='three columns',
                     children=html.P(children='Bounding box:', style={'width': '100%', 'font-weight': 'bold'})),
            html.Div(className='three columns',
                     children=dcc.Input(style={'width': '100%'}, id=lonmin, placeholder='lon min', type='number',
                                        min=-180, max=180),  # , step=0.01),
                     ),
            html.Div(className='offset-by-three columns, three columns',
                     children=dcc.Input(style={'width': '100%'}, id=lonmax, placeholder='lon max', type='number',
                                        min=-180, max=180),  # , step=0.01),
                     ),
        ]),
        html.Div(className='row', children=[
            html.Div(className='offset-by-six columns, three columns',
                     children=dcc.Input(style={'width': '100%'}, id=lamin, placeholder='lat min', type='number',
                                        min=-90, max=90),  # , step=0.01),
                     ),
        ]),
    ])
    return bbox_selection_div

def get_timeline_by_station(datasets_df):
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

def get_timeline_by_station_and_vars(datasets_df):
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

def plot_vars(ds, v1, v2=None):
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

def add_trace(fig, ds, ri, vs, axes, legend):
    vars_long = data_access.get_vars_long()
    v_names = []
    axes=axes
    tempaxes={}
    for i, v in enumerate(vs):
        da = ds[v]
        units=da.attrs['units'] if 'units' in da.attrs else "no units"
        name=da.attrs['standard_name'] if 'standard_name' in da.attrs else v
        tempaxes[name + " (" + units + ")"]=units
        if units not in axes:
            axes.append(units)
        fig.add_trace(
            go.Scatter(
                x=da['time'].values,
                y=da.values,
                name=name + " (" + units + ") (" + legend + ")",
                legendgroup=ri,  # this can be any string, not just "group"
                legendgrouptitle_text=ri,
                yaxis=f"y{axes.index(units) + 1}",
            )
        )
    
    fig.update_layout(
        xaxis=dict(
            domain=[0.0, 0.95]
        ),
        yaxis1=dict(
            title=axes[0],
            anchor='x',
            side='left',
        ),
    )
    
    fig.update_layout(
    {
        t.yaxis.replace("y", "yaxis"): {
            "title": tempaxes[t.name],
            "overlaying": "y",
            "side": f"{'right' if (i % 2) != 0 else 'left'}",
            "position":1-(i/15)
        }
        for i, t in enumerate(fig.data)
        if t.yaxis != "y"
    }
    ).update_layout(
        #title_text="You have selected the following datasets: ...",
        legend_title_text='Variables',
        showlegend=True,
        legend=dict(groupclick="toggleitem"),
        xaxis={"domain":[0,1-((len(axes)-1)*.07)]},
    )
    fig.update_xaxes(title_text="Time") 
    
    return fig, axes 

