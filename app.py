import dash
import dash_table
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Output, Input
import pandas as pd
import altair as alt
from vega_datasets import data
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
from a448_lib import data_read
import fsspec
import cmocean as cm
import cartopy.feature as cfeature
import numpy as np
from io import BytesIO
import base64

def fig_to_uri(in_fig, close_all=True, **save_args):
    # type: (plt.Figure) -> str
    """
    Save a figure as a URI
    :param in_fig:
    :return:
    """
    out_img = BytesIO()
    in_fig.savefig(out_img, format='png', **save_args)
    if close_all:
        in_fig.clf()
        plt.close('all')
    out_img.seek(0)  # rewind file
    encoded = base64.b64encode(out_img.read()).decode("ascii").replace("\n", "")
    return "data:image/png;base64,{}".format(encoded)

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

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

# Change source model by specifying it here
source = "GFDL-CM4"
# Querying to get Near Surface Air Temperature ('tas')
query_variable_id = dict(
    experiment_id=['historical'],
    #institution_id = "CCCma",
    source_id = source,
    table_id = ['Amon'],
    variable_id=['tas'])

col_var_subset = col.search(**query_variable_id)

# Getting the member number for the first experiment
tas_member = col_var_subset.df['member_id'][0]

tas_filename =col_var_subset.df.query("member_id==@tas_member")['zstore'].iloc[0]

dset_cccma_tas=xr.open_zarr(fsspec.get_mapper(tas_filename), consolidated=True)

# Specifying a year and month to select by with xarray
# TODO: Find more elegant solution, probably something with cftime\
Year = '2000'
Month = '07'
start_date = Year + '-' + Month + '-' + '01'
end_date = Year + '-' + Month + '-' + '30'

tas_lon = dset_cccma_tas.lon
tas_lat = dset_cccma_tas.lat
# Indexing for a particular month. Plotting code get upset if we don't index here.
tas_data = dset_cccma_tas['tas'].sel(time=slice(start_date, end_date))[0,:,:]


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
                        value = 'tas'),
            html.Br(),
            html.H6('Model'),
            dcc.Dropdown(),
            html.Br(),
            html.H6('Model'),
            dcc.Dropdown(),
            html.Br(),
            html.H6('Model'),
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
                        dbc.CardHeader('Variable distrbution', style={'fontWeight': 'bold'}),
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

@app.callback(
    Output('histogram', "src"),
    Input('var_drop', "value"))
def update_histogram(var_drop):
    f, ax = plt.subplots(1,1,figsize=(20,10),
                     subplot_kw=dict(projection=ccrs.PlateCarree()))

    p = ax.pcolormesh(tas_lon,
              tas_lat,
              tas_data,
              transform=ccrs.PlateCarree())

    f.colorbar(p, label='Temp (Kelvin)', shrink = .5)
    ax.set_title('Global Temperatures' )

    # Add land.
    ax.add_feature(cfeature.LAND, color='#a9a9a9', zorder=4)
    out_url = fig_to_uri(f)
    return out_url

if __name__ == '__main__':
    app.run_server(debug=True)