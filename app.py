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
from cmpi_6_dash.src.a448_lib import data_read
from cmpi_6_dash.src.plot_fcns import *
import fsspec
import cmocean as cm
import cartopy.feature as cfeature
import numpy as np
from io import BytesIO
import base64

# Code from jupyter notebook
csv_filename = "pangeo-cmip6.csv"
root = "https://storage.googleapis.com/cmip6"
if Path(csv_filename).is_file():
    print(f"found {csv_filename}")
else:
    print(f"downloading {csv_filename}")
    data_read.download(csv_filename,root=root)
    
json_filename="https://storage.googleapis.com/cmip6/pangeo-cmip6.json"

catalog_df=pd.read_csv(csv_filename)

col = intake.open_esm_datastore(json_filename)

# Creating variable key dict constant
var_key = {
    'tas' : 
        {'fullname' : 'Near-Surface Air Temperature',
         'monthly_table' : 'Amon',
         'units' : '[K]'},
    'ta' :
        {'fullname' : 'Air Temperature',
         'monthly_table' : 'Amon',
         'units' : '[K]'},
    'pr' : 
        {'fullname' : 'Precipitation',
         'monthly_table' : 'Amon',
         'units' : '[kg m-2 s-1]'},
    'hus' : 
        {'fullname' : 'Specific Humidity',
         'monthly_table' : 'Amon' ,
         'units' : '[1]'}, 
    'cl' : 
        {'fullname' : 'Percentage Cloud Cover',
         'monthly_table' : 'Amon',
         'units' : '[%]'},
    'sisnthick' :
        {'fullname' : 'Snow Thickness',
         'monthly_table' : 'SImon',
         'units' : '[m]'},
    'sithick' :  
        {'fullname' : 'Sea Ice Thickness',
         'monthly_table' : 'SImon',
         'units' : '[m]'},
    'mrro' : 
        {'fullname' : 'Total Runoff', 
         'monthly_table' : 'Lmon',
         'units' : '[kg m-2 s-1]'},
    'lai' : 
        {'fullname' : 'Leaf Area Index',
         'monthly_table' : 'Lmon',
         'units' : '[1]'}, 
    'mrso' : {'fullname' : 'Total Soil Moisture Content' ,
              'monthly_table' : 'Lmon',
              'units' : '[kg m-2]'}
}

# Creating object
full_name_key = []
for var in var_key:
    full_name_key.append({'label' : var_key[var]['fullname'], 'value' : var})

# Helper functions
def get_monthly_table_for_var(var_id):
    '''Returns appropriate X-mon for a given variable id from
       the var key'''
    return var_key[var_id]['monthly_table']



def get_models_with_var(data_store, var_id, table_id):
    '''Takes a variable id and a corresponding table id and and returns all the model labels 
       with the combination '''
    query_variable_id = dict(
        experiment_id=['historical'],
        table_id = [table_id],
        variable_id=[var_id])

    data_sets = data_store.search(**query_variable_id)
    return(data_sets.df.source_id.unique())

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
                            html.Img(
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
    Output('histogram', "src"),
    Input('var_drop', "value"))
def update_map(var_drop):
    var_id = var_drop
    mod_id = 'GFDL-CM4'
    dset = get_cmpi6_model_run(data_store = col, var_id = var_id,
     mod_id = mod_id)
    return plot_year(dset, var_id = var_id, month = '01', year = '1875', layer = 4)

if __name__ == '__main__':
    app.run_server(debug=True)