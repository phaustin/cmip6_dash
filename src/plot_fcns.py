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
import fsspec
import cmocean as cm
import cartopy.feature as cfeature
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import cartopy.feature as cf

# Creating dictionary to map names of model variables to full names, associated tables, and units
def get_var_key():
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
    return var_key

def get_models_with_var(data_store, var_id, table_id):
    '''Takes a variable id and a corresponding table id and and returns all the model labels 
       with the combination '''
    query_variable_id = dict(
        experiment_id=['historical'],
        table_id = [table_id],
        variable_id=[var_id])

    data_sets = data_store.search(**query_variable_id)
    return(data_sets.df.source_id.unique())

def get_monthly_table_for_var(var_id):
    '''Returns appropriate X-mon for a given variable id from
       the var key'''
    var_key = get_var_key()
    return var_key[var_id]['monthly_table']

def get_outline(fig):
    """Takes a figure and adds cartopy's coastline geometries on it"""
    x_coords = []
    y_coords = []
    for coord_seq in cf.COASTLINE.geometries():
        x_coords.extend([k[0] for k in coord_seq.coords] + [np.nan])
        y_coords.extend([k[1] for k in coord_seq.coords] + [np.nan])
    fig.add_trace(
        go.Scatter(
            x = x_coords,
            y = y_coords,
            mode = 'lines',
            line=dict(color="#FFFFFF")))
            
    return fig

def get_cmpi6_model_run(data_store, var_id, mod_id):
    """ Queries a given data store for historical model runs for the given variable id

    Wraps a query for the data_store using variable and model id from the associated monthly
    table. Takes the first model run from the historical experiments. Variable id must be supported by
    get_monthly_table_for_var(). 

    Parameters
    ----------
    data_store : esm_datastore
        The data store to extract the variable and model id's from
    var_id : string
        String to search for. Table id will be fetched with get_monthly_table_for_var(var_id)
    mod_id : string
        The climate model string to use in query. If the model does not provide var function
        will fail mysteriously and inelegantly- get_models_with_var() may help.

    Returns
    -------
    dset_opened : xarray.Datasfet
        The xarray object matching the query
    """
    
    # Querying datastore to get xarr file
    query_variable_id = dict(
        experiment_id=['historical'],
        source_id = mod_id,
        table_id = [get_monthly_table_for_var(var_id)],
        variable_id=[var_id])

    datasets = data_store.search(**query_variable_id)

    # Getting the member number for the first experiment
    first_member_id = datasets.df['member_id'][0]

    dstore_filename = datasets.df.query("member_id==@first_member_id")['zstore'].iloc[0]

    dset_opened = xr.open_zarr(fsspec.get_mapper(dstore_filename), consolidated=True)

    return dset_opened

def get_month_and_year(dset, var_id, month, year, layer = 1):
    """ 
    This function filters an xarray dset for a given month, year and layer from the cmpi6 historical runs and returns it. It 
    assumes montly data where the day is specified between the 14th and the 17th.

    Parameters
    ----------
    dset : xarray.Dataset
        The xarray.Dataset to plot
    var_id : 'str'
        The variable to be plotted.
    month : 'str'
        String specifying which month to plot.
        Must be between '01'-'12'. 0 required for single digit months.
    year : 'str'
        Year to plot. Must be between '1850' and '2014'
    layer : int
        Must be between 0 and 18- only used for plotting humidity and temp
        
    Returns
    -------
    fig : plotly figure object
    """
    # Specifying a year and month to select by with xarray
    start_date = year + '-' + month + '-' + '14'
    end_date = year + '-' + month + '-' + '17'
   
    # Slicing model output on the given times two ways depending on whether or not the model has layers
    layer_vars = ['hus', 'ta']
    if var_id in layer_vars:
        var_data = dset[var_id].sel(time=slice(start_date, end_date))[0, layer,:,:]
    else:
        var_data = dset[var_id].sel(time=slice(start_date, end_date))[0,:,:]

    return var_data

def plot_year_plotly(dset, var_id, month, year, layer = 1):
    
    """ This function plots results for a given month and year for a variable given by var_id in the dset 

    Wraps plotly plotting code for a one month, year slice of cmpi-6 climate model output for the given variable

    Parameters
    ----------
    dset : xarray.Dataset
        The xarray.Dataset to plot
    var_id : 'str'
        The variable to be plotted.
    month : 'str'
        String specifying which month to plot.
        Must be between '01'-'12'. 0 required for single digit months.
    year : 'str'
        Year to plot. Must be between '1850' and '2014'
    layer : int
        Must be between 0 and 18- only used for plotting humidity and temp
        
    Returns
    -------
    fig : plotly figure object
    """

    var_data = get_month_and_year(dset, var_id, month, year, layer)

    var_key = get_var_key()
    
    # Converting to a df so we can use plotly
    var_df = var_data.to_dataframe().reset_index()
    
    # Converting from a 0-360 longitudinal system to a -180-180 longitudinal system
    var_df['lon_adj'] = var_df['lon'].apply(lambda x: x - 360 if x > 180 else x)
    
    fig = px.scatter(var_df, x = 'lon_adj', y = 'lat', color = var_id, opacity = 0)

    # Plotting
    fig = get_outline(fig)
   
    fig.add_trace(
        go.Contour(
               x = var_df['lon_adj'],
               y = var_df['lat'],
               z = var_df[var_id],
               contours_coloring='heatmap',
               colorbar= {
               "borderwidth": 0, 
                "outlinewidth": 0, 
                "thickness": 15, 
                "tickfont": {"size": 14}, 
                "title": var_key[var_id]['units']}, #gives your legend some units                                                                     #

                contours= {
                #"end": 4, 
                "showlines": False, 
               # "size": 0.5, #this is your contour interval
               # "start": -4 
                }))

    fig.update_layout(margin={"r":1,"t":4,"l":1,"b":1},
                     title = var_key[var_id]['fullname'] + ' ' + year + '-' + month)

    return fig

def plotly_wrapper(data_store, var_id = 'tas', mod_id = 'GFDL-CM4', month = '01', year = '1950', layer = 1):
    '''Wraps model request and plotting code for ease of use'''
    dset = get_cmpi6_model_run(data_store, var_id, mod_id)
    fig = plot_year_plotly(dset, var_id, month, year, layer)
    return fig