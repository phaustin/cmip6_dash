import dash
import dash_table
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Output, Input
import pandas as pd
import warnings
import intake
import xarray as xr 
import matplotlib.pyplot as plt 
import pandas as pd 
import cftime
import gcsfs
import cartopy.crs as ccrs
from pathlib import Path
import pandas as pd
from src.a448_lib import data_read
from src.plot_fcns import *
import fsspec
import cmocean as cm
import cartopy.feature as cfeature
import numpy as np
from io import BytesIO
import base64

# Checking to see if the data is already downloaded
csv_filename = "pangeo-cmip6.csv"
root = "https://storage.googleapis.com/cmip6"
if Path(csv_filename).is_file():
    print(f"found {csv_filename}")
else:
    print(f"downloading {csv_filename}")
    data_read.download(csv_filename,root=root)
    
json_filename="https://storage.googleapis.com/cmip6/pangeo-cmip6.json"

# Getting the esm data store
catalog_df=pd.read_csv(csv_filename)

col = intake.open_esm_datastore(json_filename)

var_key = get_var_key()

# Creating object with all variable full names
full_name_key = []
for var in var_key:
    full_name_key.append({'label' : var_key[var]['fullname'], 'value' : var})

# Creating object with all models for given variables
models = get_models_with_var(data_store = col, var_id = 'tas', table_id = get_monthly_table_for_var('tas'))
model_list = []
for mod in models:
    model_list.append({'value' : mod, 'label' : mod})

# Layout for the app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H1('My splashboard demo',
                style={
                    'color': 'white',
                    'text-align': 'left',
                    'font-size': '48px',
                    }) #, 'width': 300}),

        ], style={'backgroundColor': 'steelblue',
                    'border-radius': 3,
                    'padding': 15,
                    'margin-top': 20,
                    'margin-bottom': 20,
                    'margin-right': 15
        })

    ]),
    dbc.Row([
        dbc.Col([
            html.H6('Model Variable'),
            dcc.Dropdown(id = 'var_drop',
                        value = 'tas',
                        options = full_name_key),
            html.Br(),
            html.H6('Model'),
            dcc.Dropdown(id = 'mod_drop',
                        value = 'CanESM5',
                        options = model_list),
            html.Br(),
            html.H6('Year'),
            dcc.Dropdown(),
            html.Br(),
            html.H6('Month'),
            dcc.Dropdown(),
            html.Br(),
            html.H6('Mean'),
            dbc.Card(dbc.CardBody(id='mean_card')),
            html.Br(),
            html.H6('Std. Dev'),
            dbc.Card(dbc.CardBody(id='var_card'))

            ],
            md=2,
            style={
                'background-color': '#e6e6e6',
                'padding': 15,
                'border-radius': 3}), 
        dbc.Col([
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader('Climate Plot', style={'fontWeight': 'bold'}),
                        dbc.CardBody(
                            dcc.Graph(
                                id='histogram',
                                style={'border-width': '0', 'width': '100%', 'height': '100%'}
                                ))
                                ])])
            ])
        ])
    ]),
    html.Hr(),
    html.P('')
])

# Callbacks
@app.callback(
    Output('histogram', "figure"),
    Input('var_drop', "value"),
    Input('mod_drop', 'value'))
def update_map(var_drop, mod_drop):
    """
    Updates the graph when the a different variable is selected
    """
    fig = plotly_wrapper(col, var_drop, mod_drop, month = '01', year = '1950', layer = 1)
    return fig

@app.callback(
    Output('mean_card', 'children'),
    Input('histogram', 'selectedData'))
def update_mean(selection):
    """
    Updates the mean card depending on the selected data in the graph
    """
    if selection is None:
        return 0
    var_vals = []
    for dict in selection['points']:
        val = dict['marker.color']
        var_vals.append(val)
        mean = np.mean(np.array(var_vals))
    return mean #round(mean, 2)

@app.callback(
    Output('var_card', 'children'),
    Input('histogram', 'selectedData'))
def update_variance(selection):
    """
    Updates the variance card depending on the selected data in the graph
    """
    if selection is None:
        return 0
    var_vals = []
    for dict in selection['points']:
        val = dict['marker.color']
        var_vals.append(val)
        std = np.std(np.array(var_vals))
    return std #round(std, 2)

# Callbacks
@app.callback(
    Output('mod_drop', "options"),
    Input('var_drop', "value"))
def update_mod_drop(var_drop):
    """
    returns the appropriate set of models for the selected figure
    """
    # Creating object with all models for given variables
    models = get_models_with_var(data_store = col, var_id = var_drop, table_id = get_monthly_table_for_var(var_drop))
    model_list = []
    for mod in models:
        model_list.append({'value' : mod, 'label' : mod})
    return model_list


if __name__ == '__main__':
    app.run_server(debug=True)