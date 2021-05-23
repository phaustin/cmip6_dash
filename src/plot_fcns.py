import json

import cartopy.feature as cf
import fsspec
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import xarray as xr


# Creating dictionary to map names of model variables to full names,
# associated tables, and units
def get_var_key():
    var_key = {
        "tas": {
            "fullname": "Near-Surface Air Temperature",
            "monthly_table": "Amon",
            "units": "[K]",
        },
        "ta": {
            "fullname": "Air Temperature",
            "monthly_table": "Amon",
            "units": "[K]",
        },
        "pr": {
            "fullname": "Precipitation",
            "monthly_table": "Amon",
            "units": "[kg m-2 s-1]",
        },
        "hus": {
            "fullname": "Specific Humidity",
            "monthly_table": "Amon",
            "units": "[1]",
        },
        "sisnthick": {
            "fullname": "Snow Thickness",
            "monthly_table": "SImon",
            "units": "[m]",
        },
        "sithick": {
            "fullname": "Sea Ice Thickness",
            "monthly_table": "SImon",
            "units": "[m]",
        },
        "mrro": {
            "fullname": "Total Runoff",
            "monthly_table": "Lmon",
            "units": "[kg m-2 s-1]",
        },
        "lai": {
            "fullname": "Leaf Area Index",
            "monthly_table": "Lmon",
            "units": "[1]",
        },
        "mrso": {
            "fullname": "Total Soil Moisture Content",
            "monthly_table": "Lmon",
            "units": "[kg m-2]",
        },
    }
    return var_key


def get_models_with_var(data_store, var_id, table_id):
    """Takes a variable id and a corresponding table id and and returns all the model labels
    with the combination"""
    query_variable_id = dict(
        experiment_id=["historical"], table_id=[table_id], variable_id=[var_id]
    )

    data_sets = data_store.search(**query_variable_id)
    return data_sets.df.source_id.unique()


def get_monthly_table_for_var(var_id):
    """Returns appropriate X-mon for a given variable id from
    the var key"""
    var_key = get_var_key()
    return var_key[var_id]["monthly_table"]


def get_outline(fig):
    """Takes a figure and adds cartopy's coastline geometries on it"""
    x_coords = []
    y_coords = []
    for coord_seq in cf.COASTLINE.geometries():
        x_coords.extend([k[0] for k in coord_seq.coords] + [np.nan])
        y_coords.extend([k[1] for k in coord_seq.coords] + [np.nan])
    fig.add_trace(
        go.Scatter(x=x_coords, y=y_coords, mode="lines", line=dict(color="#FFFFFF"))
    )

    return fig


def get_cmpi6_model_run(data_store, var_id, mod_id, exp_id="historical", members=1):
    """Queries a given data store for historical model runs for the given variable id

    Wraps a query for the data_store using variable and model id
    from the associated monthly table. Takes the first model run from the historical
    experiments. Variable id must be supported by get_monthly_table_for_var().

    Parameters
    ----------
    data_store : esm_datastore
        The data store to extract the variable and model id's from
    var_id : string
        String to search for. Table id will be fetched with
        get_monthly_table_for_var(var_id)
    mod_id : string
        The climate model string to use in query. If the model does not provide
        var function will fail mysteriously and inelegantly- get_models_with_var()
        may help.

    Returns
    -------
    dsets : list
       A list of the xarray datasets matching the query
    """

    # Querying datastore to get xarr file
    query_variable_id = dict(
        experiment_id=[exp_id],
        source_id=mod_id,
        table_id=[get_monthly_table_for_var(var_id)],
        variable_id=[var_id],
    )

    datasets = data_store.search(**query_variable_id)

    dsets = []
    # Getting the member number for the first experiment
    for member_num in range(members):
        member_ids = datasets.df["member_id"][member_num]
        dstore_filename = datasets.df.query("member_id==@member_ids")["zstore"].iloc[0]
        dsets.append(
            xr.open_zarr(fsspec.get_mapper(dstore_filename), consolidated=True)
        )

    return dsets


def get_month_and_year(dset, var_id, month, year, exp_id="historical", layer=1):
    """
    This function filters an xarray dset for a given month, year and layer from
    the cmpi6 historical runs and returns it. It assumes montly data where
    the day is specified between the 14th and the 17th.

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
        Year to plot. Must be between '1850' and '2100'
    piControl : 'str'
        The exp_id. Required here because year should be ignored for
        piControl model runs.
    layer : int
        Must be between 0 and 18- only used for plotting humidity and temp

    Returns
    -------
    var_data : xarray.Dataset
        The xarray.Dataset filtered for the given, month, year, and layer
    """
    # If out experiment ID is piControl, we ignore year and instead use the first
    #  year in the dset
    if exp_id == "piControl":
        year = (
            dset["time"]  # From the time index
            .isel(time=slice(0, 1))  # Get the first year
            .dt.year.values[0]  # Change format to year and grab it
        )
        year = str(year)

    # Specifying a year and month to select by with xarray
    start_date = year + "-" + month + "-" + "14"
    end_date = year + "-" + month + "-" + "17"

    # Slicing model output on the given times two ways depending on whether or not
    # the model has layers
    layer_vars = ["hus", "ta"]
    if var_id in layer_vars:
        var_data = dset[var_id].sel(time=slice(start_date, end_date))[0, layer, :, :]
    else:
        var_data = dset[var_id].sel(time=slice(start_date, end_date))[0, :, :]

    return var_data


def plot_year_plotly(dset, var_id, month, year, exp_id, layer=1):

    """This function plots the var for a given month and year

    Wraps plotly plotting code for a one month, year slice of cmpi-6 climate model
     output for the given variable

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
    exp_id : 'str'

    layer : int
        Must be between 0 and 18- only used for plotting humidity and temp

    Returns
    -------
    fig : plotly figure object
    """
    var_data = get_month_and_year(dset, var_id, month, year, exp_id, layer)

    var_key = get_var_key()

    # Converting to a df so we can use plotly
    var_df = var_data.to_dataframe().reset_index()

    # Converting from a 0-360 longitudinal system to a -180-180 longitudinal system
    var_df["lon_adj"] = var_df["lon"].apply(lambda x: x - 360 if x > 180 else x)

    # Invisible plotly express scatter of var values at lons and lats. Added
    # this here to get the box and lasso select to do the mean/ variance.
    # A bit of a hack but seems to be the best option currently.
    fig = px.scatter(var_df, x="lon_adj", y="lat", color=var_id, opacity=0)
    # Removing the color bar generated by plotly express
    fig.update_layout(coloraxis_showscale=False)

    # Adding cartopy features to our plot
    fig = get_outline(fig)

    fig.add_trace(
        go.Contour(
            x=var_df["lon_adj"],
            y=var_df["lat"],
            z=var_df[var_id],
            contours_coloring="heatmap",
            colorbar={
                "borderwidth": 0,
                "outlinewidth": 0,
                "thickness": 15,
                "tickfont": {"size": 14},
                "title": var_key[var_id]["units"],
            },  # specifies units here
            # Sizing and spacing of contours can be changed by editing these
            # commented out iptions
            contours={
                # "end": 4,
                "showlines": False,
                # "size": 0.5, #this is your contour interval
                # "start": -4
            },
        )
    )
    fig.update_xaxes(
        range=[var_df["lon_adj"].min(), var_df["lon_adj"].max()],
        showticklabels=False,
        visible=False,
    )
    fig.update_yaxes(
        range=[var_df["lat"].min(), var_df["lat"].max()],
        showticklabels=False,
        visible=False,
    )

    fig.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        title=var_key[var_id]["fullname"] + " " + year + "-" + month,
    )

    return fig


def plot_model_comparisons(
    dset, var_id, mod_id, exp_id, month, year, layer, mod_comp_id="CanESM5"
):
    # Get a df with the corresponding var_id etc. for the first model
    filt_dset = get_cmpi6_model_run(dset, var_id, mod_id, exp_id)
    filt_dset = get_month_and_year(filt_dset, var_id, month, year, exp_id, layer)
    df = filt_dset.to_dataframe().reset_index()

    # Get a df with the corresponding var_id etc. for the second model
    dset_comp = get_cmpi6_model_run(dset, var_id, mod_comp_id, exp_id)
    dset_comp = get_month_and_year(dset_comp, var_id, month, year, exp_id, layer)
    df_comp = dset_comp.to_dataframe().reset_index()

    # Changing the column labels on the var_ids to be the model ids so we can melt
    df_comp = df_comp.rename({var_id: mod_comp_id}, axis=1)[[mod_comp_id]]
    df = df.rename({var_id: mod_id}, axis=1)[[mod_id]]
    uni_df = pd.concat([df, df_comp], axis=1)
    uni_df = uni_df.melt(var_name="model")

    # Plotting counts of different values against each ohter
    fig = px.histogram(uni_df, x="value", color="model", opacity=0.5)
    return fig


def plotly_wrapper(
    data_store,
    var_id="tas",
    mod_id="CanESM5",
    exp_id="historical",
    month="01",
    year="1950",
    layer=1,
):
    """Wraps model request and plotting code for ease of use"""
    dset = get_cmpi6_model_run(data_store, var_id, mod_id, exp_id)[0]
    fig = plot_year_plotly(dset, var_id, month, year, exp_id, layer)
    return fig


def get_case_data(data_store, case_definition, xarr_write_path="None"):

    """Queries a given data store for the specification and returns and writes the data

    Wraps a query for the data_store to get the xarray. Variable id must be supported
    by get_monthly_table_for_var(). Data is written in the xarr format

    Parameters
    ----------
    data_store : esm_datastore
        The data store to query

    case_definition : dict
        This dict specifies the region, variable time period, scenario, and number of
        ensemble members. Write_case_definitions will generate and validate an
        appropriate dict.

    definition_path : str
        Ignored if a case_definition is provided or if set to none. The name of a case
        saved as a json to fetch to use as the case definition

    xarr_write_path : str
        Ignored if xarr_write_path is set to none. The location the file will be
        written.


    Returns
    -------
    xarr_file : list of xarrary dsets
        The experiment for the given query in a list
    """
    dsets = get_cmpi6_model_run(
        data_store,
        case_definition["var_id"],
        case_definition["mod_id"],
        case_definition["exp_id"],
        case_definition["members"],
    )

    bottom_lat_bnd = case_definition["bottom_right"][0]
    top_lat_bnd = case_definition["top_left"][0]
    right_lon_bnd = case_definition["bottom_right"][1]
    left_lon_bnd = case_definition["top_left"][1]

    # TODO: Filter on dates

    dsets_clipped = [
        clip_xarray(
            dset, top_lat_bnd, bottom_lat_bnd, right_lon_bnd, left_lon_bnd, lon_360=True
        ).sel(time=slice(case_definition["start_date"], case_definition["end_date"]))
        for dset in dsets
    ]


def clip_xarray(
    xarray_dset,
    top_lat_bnd,
    bottom_lat_bnd,
    right_lon_bnd,
    left_lon_bnd,
    lon_padding=3,
    lat_padding=3,
    lons_360=False,
):
    """Takes an xarray_dataset and clips values to a square defined by the lat lon
    values supplied"""
    if not lons_360:
        right_lon_bnd = lon_180_to_360(right_lon_bnd)
        left_lon_bnd = lon_180_to_360(left_lon_bnd)
    return (
        xarray_dset.where(xarray_dset.lat > bottom_lat_bnd - lat_padding, drop=True)
        .where(xarray_dset.lat < top_lat_bnd + lat_padding, drop=True)
        .where(xarray_dset.lon < right_lon_bnd + lon_padding, drop=True)
        .where(xarray_dset.lon > left_lon_bnd - lon_padding, drop=True)
    )


def lon_180_to_360(lon):
    """Converts longitudes on the -180-180 scale to 0-365"""
    lon = lon + 360 if lon < 0 else lon
    return lon


def write_case_definition(
    var_id,
    mod_id,
    exp_id,
    members,
    start_date,
    end_date,
    top_left,
    bottom_right,
    padding=3,
    write_path="None",
):
    """
    This function creates and validates a dictionary to use with get_case and writes
    the definition to a json if a write path is supplied

    Parameters
    ----------
    write_path : str
         The path to write a json of the case definition for. This will overwrite case
         definitions with the same name. If 'None' specified, the case definition will
         not be saved as a json

    var_id : str
         The variable id to use in the query. Must be a member of dict supplied by
         get_var_key()

    mod_id : str
         The model id to query results for. Must be a valid cimp6 model id

    exp_id : str
         The experiment id. Must be valid for the mod_id and var_id

    members : int
        Number of model runs to include in case xarr dataset. Should be between 0 and 39

    start_date : str '1950-01'
        Of the form YYYY-MM e.g '1955-02'. Start of the date range- check these dates
        are contained in the given runs of the given experiment. Ignored for piControl.

    end_date : str '1955-02'
        Of the form YYYY-MM e.g '1955-02'. End of the date range check these dates are
        contained in the given runs of the given experiment. Ignored for piControl.

    top_left : tuple (float, float)
        Top left lat-lon coord for regional subselection. Should be decimal of the form
        Lat -90-90, Lon 0-360

    bottom_right : tuple (float, float)
        Bottom right lat-lon coord for regional subselection. Should be decimal of the
        form lat -90-90, Lon 0-360

    write_path : str
        The file path + file name for writing the json

    Returns
    -------
    case_definition : dict
        A dictionary with all the requests validated

    """
    # TODO: Write script to validate input
    # Var id should be in var_keys
    # Mod id should be in [CanESM5 etc]
    # The exp id must be one of ['historical', 'piControl', other opts]
    # Members should be less than 40
    # The start date must be compatible with the exp id (1850-2014 for historical),
    # 2014 on for pi
    # Same with end date
    # The lats should correspond to Amon gridding (see above)
    case_definition = {
        "var_id": var_id,
        "mod_id": mod_id,
        "exp_id": exp_id,
        "members": members,
        "start_date": start_date,
        "end_date": end_date,
        "top_left": top_left,
        "bottom_right": bottom_right,
        "padding": padding,
    }

    case_definition["data"] = get_case_data(case_definition)
    if write_path != "None":
        with open(write_path, "w") as write_file:
            json.dump(case_definition, write_file, sort_keys=True, indent=4)
    else:
        return case_definition
