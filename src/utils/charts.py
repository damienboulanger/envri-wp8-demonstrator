import toolz
import numpy as np
import pandas as pd
import xarray as xr
from plotly import express as px, graph_objects as go


# Color codes
ACTRIS_COLOR_HEX = '#00adb7'
IAGOS_COLOR_HEX = '#456096'
ICOS_COLOR_HEX = '#ec165c'


def plotly_scatter(x, y, *args, **kwargs):
    """
    This is a thin wrapper around plotly.graph_objects.Scatter. It workaround plotly bug:
    Artifacts on line scatter plot when the first item is None #3959
    https://github.com/plotly/plotly.py/issues/3959
    """
    x = np.asanyarray(x)
    y = np.asanyarray(y)
    y_isnan = np.isnan(y).astype('i4')
    isolated_notnans = np.diff(y_isnan, n=2, prepend=1, append=1) == 2
    return go.Scatter(
        x=x,
        y=np.where(~isolated_notnans, y, np.nan),
        *args,
        **kwargs
    )


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
        df, x_start='time_period_start', x_end='time_period_end', y='station_fullname', color='RI',
        hover_name='var_codes',
        hover_data={'station_fullname': True, 'platform_id_RI': True, 'datasets': True, 'RI': False},
        custom_data=['indices'],
        category_orders={'RI': ['ACTRIS', 'IAGOS', 'ICOS']},
        color_discrete_sequence=[ACTRIS_COLOR_HEX, IAGOS_COLOR_HEX, ICOS_COLOR_HEX],
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


def get_avail_data_by_var_gantt(ds):
    dfs = []
    for v, da in ds.data_vars.items():
        *v_label, ri = v.split('_')
        v_label = '_'.join(v_label)
        notnull_diff = da.notnull().astype('i2').diff('time')

        s = da['time'].where(notnull_diff == 1, drop=True).values
        if da.isel({'time': 0}).notnull():
            s = np.concatenate((da['time'].values[:1], s))
        e = da['time'].where(notnull_diff == -1, drop=True).values
        if da.isel({'time': -1}).notnull():
            e = np.concatenate((e, da['time'].values[-1:]))

        df = _contiguous_periods(s, e)[['time_period_start', 'time_period_end']]
        df['var_label'] = v_label
        df['RI'] = ri
        df['variable (RI)'] = f'{v_label} ({ri})'
        dfs.append(df)

    df = pd.concat(dfs, ignore_index=True)
    # df = df.sort_values('platform_id_RI')
    height = 200 + max(80, 30 + 10 * len(ds.data_vars))
    gantt = px.timeline(
        df, x_start='time_period_start', x_end='time_period_end', y='variable (RI)', color='RI',
        hover_name='variable (RI)',
        hover_data={'var_label': True, 'RI': False},
        # custom_data=['indices'],
        category_orders={'RI': ['ACTRIS', 'IAGOS', 'ICOS']},
        color_discrete_sequence=[ACTRIS_COLOR_HEX, IAGOS_COLOR_HEX, ICOS_COLOR_HEX],
        height=height
    )
    gantt.update_layout(
        clickmode='event',
        selectdirection='h',
        legend={'orientation': 'h', 'yanchor': 'bottom', 'y': 1.04, 'xanchor': 'left', 'x': 0},
    )
    return gantt


def colors():
    import plotly.colors
    list_of_rgb_triples = [plotly.colors.hex_to_rgb(hex_color) for hex_color in px.colors.qualitative.Dark24]
    return list_of_rgb_triples


def get_color_mapping(variables):
    return dict(zip(variables, colors()))


def get_avail_data_by_var_heatmap(ds, granularity, adjust_color_intensity_to_max=True, color_mapping=None):
    """

    :param ds: xarray.Dataset or dictionary {var_label: xarray.DataArray};
    :param granularity: str; one of ['year', 'season', 'month']
    :param adjust_color_intensity_to_max: bool, optional, default=True
    :param color_mapping: dict, optional; {var_label: tuple(r, g, b)}, where r, b, g are int's
    :return:
    """
    if color_mapping is None:
        color_mapping = get_color_mapping(ds)

    def get_data_avail_with_freq(ds, granularity):
        if granularity == 'year':
            freq = 'YS'
        elif granularity == 'season':
            freq = 'QS-DEC'
        elif granularity == 'month':
            freq = 'MS'
        else:
            raise ValueError(f'unknown granularity={granularity}')
        if isinstance(ds, xr.Dataset):
            ds_avail = ds.notnull().resample({'time': freq}).mean()
        else:
            # ds is a dictionary {var_label: xr.DataArray}
            ds_avail = xr.merge(
                [
                    da.reset_coords(drop=True).notnull().resample({'time': freq}).mean().rename(v)
                    for v, da in ds.items()
                ],
                join='outer',
                # compat='override',
            )
        t = ds_avail['time']
        if granularity == 'year':
            t2 = t.dt.year
        elif granularity == 'season':
            season = t.dt.month.to_series().map({12: 'DJF', 3: 'MAM', 6: 'JJA', 9: 'SON'})
            t2 = t.dt.year.astype(str).str.cat('-', xr.DataArray(season))
        elif granularity == 'month':
            month = t.dt.month.to_series().map({m: str(m).zfill(2) for m in range(1, 13)})
            t2 = t.dt.year.astype(str).str.cat('-', xr.DataArray(month))
        else:
            raise ValueError(f'unknown granularity={granularity}')
        ds_avail['time_period'] = t2
        return ds_avail.set_coords('time_period')

    def get_heatmap(ds_avail, adjust_color_intensity_to_max, color_mapping):
        vs = list(reversed(list(ds_avail.data_vars)))
        n_vars = len(vs)
        availability_data = np.stack([ds_avail[v].values for v in vs])

        if not adjust_color_intensity_to_max:
            z_data = availability_data
        else:
            max_availability = np.nanmax(availability_data, axis=1, keepdims=True) if len(availability_data) > 0 else np.nan
            z_data = availability_data / max_availability
            z_data = np.nan_to_num(z_data)
        # this hook is because we want apply different color scale to each row of availability_data:
        z_data += 2 * np.arange(n_vars).reshape((n_vars, 1))
        # and here come the color scales:
        colorscale = [
            [[2*i / (2*n_vars), f'rgba{color_mapping[v] + (0,)}'], [(2*i+1) / (2*n_vars), f'rgba{color_mapping[v] + (255,)}']]
            for i, v in enumerate(vs)
        ]
        colorscale = sum(colorscale, start=[])
        colorscale.append([1., 'rgba(255, 255, 255, 255)'])  # must define whatever color for z / zmax = 1.
        xperiod0 = None
        if granularity == 'year':
            xperiod = 'M12'
        elif granularity == 'season':
            xperiod = 'M3'
            xperiod0 = ds_avail['time'].values[0]
        elif granularity == 'month':
            xperiod = 'M1'
        else:
            raise ValueError(granularity)
        heatmap = go.Heatmap(
            z=z_data,
            #x=ds_avail['time_period'],
            x=ds_avail['time'].values,
            xperiod=xperiod,
            xperiod0=xperiod0,
            #xperiodalignment='end',
            y=vs,
            colorscale=colorscale,
            customdata=100 * availability_data,   # availability in %
            hovertemplate='%{x}: %{customdata:.0f}%',
            name='',
            showscale=False,
            xgap=1,
            ygap=5,
            zmin=0,
            zmax=2*n_vars,
        )
        return heatmap

    ds_avail = get_data_avail_with_freq(ds, granularity)

    n_vars = max(len(ds_avail.data_vars), 1)
    layout_dict = {
        'autosize': True,
        'height': 80 + 30 * n_vars,
        'margin': {'b': 25, 't': 35},
    }

    fig = go.Figure(data=get_heatmap(ds_avail, adjust_color_intensity_to_max, color_mapping), layout=layout_dict)
    if granularity == 'year':
        dtick = 'M12'
        tickformat = '%Y'
    else:
        dtick = 'M3'
        tickformat = '%b %Y'
    fig.update_xaxes(
        type='date',
        dtick=dtick,
        tickformat=tickformat,
        ticklabelmode='period',
        title='time',
    )
    return fig


def get_histogram(da, x_label, bins=50, color=None, x_min=None, x_max=None, log_x=False, log_y=False):
    color = f'rgb{color}' if isinstance(color, tuple) and len(color) == 3 else color

    ar = da.where(da.notnull(), drop=True).values

    if len(ar) == 0:
        ar_ = np.array([np.nan])
    else:
        ar_ = ar
    qs = np.quantile(ar_, q=[0.25, 0.5, 0.75])
    boxplot_data = {
        'q1': qs[0], 'median': qs[1], 'q3': qs[2],
        'lowerfence': np.amin(ar_), 'upperfence': np.amax(ar_),
        'mean': np.mean(ar_), 'sd': np.std(ar_),
    }
    boxplot_data = {k: [v] for k, v in boxplot_data.items()}
    boxplot_trace = go.Box(
        line={'color': color},
        y=[x_label],
        orientation='h',
        xaxis='x',
        yaxis='y2',
        **boxplot_data
    )

    if log_x:
        ar = np.log(ar[ar > 0])
        x_min = np.log(x_min) if x_min is not None and x_min > 0 else None
        x_max = np.log(x_max) if x_max is not None and x_max > 0 else None

    rng = [x_min, x_max] if x_min is not None and x_max is not None else None
    h, edges = np.histogram(ar, bins=bins, range=rng)

    if log_x:
        edges = np.exp(edges)

    rng = edges[-1] - edges[0]
    precision = int(np.ceil(np.log10(50 * bins / rng)))
    if precision < 0:
        precision = 0

    histogram_trace = go.Bar(
        name=x_label,
        y=h,
        x=edges[:-1],
        width=np.diff(edges),
        offset=0,
        customdata=np.transpose([edges[:-1], edges[1:], h]),
        hovertemplate='<br>'.join([
            'obs: %{customdata[2]}',
            'range: [%{customdata[0]:.' + str(precision) + 'f}, %{customdata[1]:.' + str(precision) + 'f}]',
        ]),
        marker={'color': color}
    )

    xaxis_title = da.attrs.get('long_name', da.attrs.get('label', '???'))
    xaxis_units = da.attrs.get('units', '???')
    fig_layout = {
        'xaxis': {
            'title': f'{xaxis_title} ({xaxis_units})',
        },
        'yaxis': {
            'title': '# observations',
            'domain': [0, 0.775],
        },
        'yaxis2': {
            'domain': [0.825, 1],
        }
    }

    fig = go.Figure(data=[histogram_trace, boxplot_trace], layout=fig_layout)

    fig.update_layout({
        'autosize': True,
        'height': 320,
        'margin': {'b': 0, 't': 35},
        'showlegend': False,
    })

    if log_x:
        fig.update_xaxes(type='log')
    if log_y:
        fig.update_layout({'yaxis': {'type': 'log'}})
    return fig


def align_range(rng, nticks, log_coeffs=(2, 2.5, 5)):
    if nticks < 3:
        ValueError(f'no_ticks must be an integer >= 3; got no_ticks={nticks}')
    nticks = int(nticks)

    log_coeffs = log_coeffs + (10,)
    low, high = rng
    if np.isnan(low) or np.isnan(high):
        return (0, 1), 0, 1 / (nticks - 1)

    dtick = (high - low) / (nticks - 2)
    dtick_base = np.power(10, np.floor(np.log10(dtick)))
    dlog_dtick = dtick / dtick_base
    for log_coeff in log_coeffs:
        if dlog_dtick <= log_coeff:
            break
    dtick = dtick_base * log_coeff
    delta_aligned = dtick * (nticks - 1)
    low_aligned = np.floor(low / dtick) * dtick
    high_aligned = np.ceil(high / dtick) * dtick
    while high_aligned - low_aligned < delta_aligned - dtick / 2:
        high_aligned += dtick
        if high_aligned - low_aligned < delta_aligned - dtick / 2:
            low_aligned -= dtick
    return (low_aligned, high_aligned), low_aligned, dtick


def multi_line(df, width=1800, height=500, scatter_mode='lines', nticks=None, color_mapping=None, range_tick0_dtick_by_var=None):
    """
    :param df: pandas DataFrame or dict of pandas Series (in that case each series might have a different index)
    :param width:
    :param height:
    :param scatter_mode:
    :param nticks:
    :param color_mapping:
    :param range_tick0_dtick_by_var:
    :return:
    """
    nvars = len(list(df))
    if not (nvars >= 1):
        return None
    if nticks is None:
        nticks = max(height // 50, 3)
    if color_mapping is None:
        color_mapping = get_color_mapping(list(df))
    if range_tick0_dtick_by_var is None:
        range_by_var = {v: (df[v].min(), df[v].max()) for v in df}
        range_tick0_dtick_by_var = toolz.valmap(lambda rng: align_range(rng, nticks=nticks), range_by_var)

    fig = go.Figure()

    for i, (variable_label, variable_values) in enumerate(df.items()):
        if i > 0:
            yaxis = {'yaxis': f'y{i+1}'}
        else:
            yaxis = {}

        scatter = plotly_scatter(
            x=variable_values.index.values,
            y=variable_values.values,
            name=variable_label,
            mode=scatter_mode,
            marker_color=f'rgb{color_mapping[variable_label]}',
            **yaxis,
        )
        fig.add_trace(scatter)

    delta_domain = min(75 / width, 0.5 / nvars)
    domain = [delta_domain * ((nvars - 1) // 2), min(1 - delta_domain * ((nvars - 2) // 2), 1)]
    fig.update_layout(xaxis={'domain': domain})

    for i, (variable_label, (rng, tick0, dtick)) in enumerate(range_tick0_dtick_by_var.items()):
        yaxis_props = {
            #'gridcolor': 'black',
            #'gridwidth': 1,
            'range': rng,
            'tick0': tick0,
            'dtick': dtick,
            'tickcolor': f'rgb{color_mapping[variable_label]}',
            'ticklabelposition': 'outside',
            'tickfont_color': f'rgb{color_mapping[variable_label]}',
            #'minor_showgrid': False,
            'title': {
                'font_color': f'rgb{color_mapping[variable_label]}',
                'standoff': 0,
                'text': variable_label,
            },
            'showline': True,
            'linewidth': 2,
            'linecolor': f'rgb{color_mapping[variable_label]}',
            'zeroline': True,
            'zerolinewidth': 1,
            #'zerolinecolor': 'black',
            'fixedrange': True,
        }
        if i > 0:
            yaxis_props.update({'overlaying': 'y'})

        idx_of_last_variable_on_left_side = (nvars + 1) // 2 - 1
        idx_of_first_variable_on_right_side = (nvars + 1) // 2
        if i == idx_of_last_variable_on_left_side:
            yaxis_props.update({
                'side': 'left',
                #'ticks': 'inside',
            })
        elif i == idx_of_first_variable_on_right_side:
            yaxis_props.update({
                'anchor': 'x',
                'side': 'right',
                #'ticks': 'inside',
            })
        else:
            if i < idx_of_last_variable_on_left_side:
                position = delta_domain * i
                side = 'left'
            else:
                position = 1 - delta_domain * (nvars - 1 - i)
                side = 'right'
            yaxis_props.update({
                'anchor': 'free',
                'position': position,
                'side': side,
            })

        yaxis_id = 'yaxis' if i == 0 else f'yaxis{i+1}'
        fig.update_layout({yaxis_id: yaxis_props})

    fig_size = {}
    if height:
        #fig_size['minreducedheight'] = height
        fig_size['height'] = height
    if width:
        fig_size['minreducedwidth'] = width
        #fig_size['width'] = width
    if fig_size:
        fig.update_layout(fig_size)

    return fig


def empty_figure():
    return go.Figure()


def _get_watermark_size(fig):
    if not isinstance(fig, dict):
        fig = fig.to_dict()

    default_size = 75
    ref_height = 500
    ref_width = 1000

    layout = fig.get('layout')
    if layout is None:
        return default_size
    height = layout.get('height')
    if height is not None:
        return default_size * height / ref_height
    width = layout.get('width', ref_width)
    return default_size * width / ref_width


def _get_fig_center(fig):
    if not isinstance(fig, dict):
        fig = fig.to_dict()

    default_center_by_axis = {
        'xaxis': .5,
        'yaxis': .5,
    }
    def_center = (default_center_by_axis['xaxis'], default_center_by_axis['yaxis'])

    layout = fig.get('layout')
    if layout is None:
        return def_center

    def get_axis_domain_center(axis):
        axis = layout.get(axis)
        if axis is None:
            return default_center_by_axis[axis]
        return sum(axis.get('domain', (0, 1))) / 2

    x = get_axis_domain_center('xaxis')
    y = get_axis_domain_center('yaxis')
    return x, y


def add_watermark(fig, size=None):
    if size is None:
        size = _get_watermark_size(fig)
    x, y = _get_fig_center(fig)

    annotations = [dict(
        name="watermark",
        text="ENVRI-FAIR",
        textangle=-30,
        opacity=0.1,
        font=dict(color="black", size=size),
        xref="paper",
        yref="paper",
        x=x,
        y=y,
        showarrow=False,
    )]
    fig.update_layout(annotations=annotations)
    return fig
