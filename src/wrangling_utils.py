from pathlib import Path

import fsspec
import intake
import xarray as xr

from .a448_lib import data_read


def get_esm_datastore():
    """Wrapper function for code to grab the pangeo datastore using the
    a448_lib package"""
    csv_filename = "pangeo-cmip6.csv"
    root = "https://storage.googleapis.com/cmip6"
    if Path(csv_filename).is_file():
        print(f"found {csv_filename}")
    else:
        print(f"downloading {csv_filename}")
        data_read.download(csv_filename, root=root)

    json_filename = "https://storage.googleapis.com/cmip6/pangeo-cmip6.json"

    col = intake.open_esm_datastore(json_filename)
    return col


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
        #        "sisnthick": {
        #            "fullname": "Snow Thickness",
        #            "monthly_table": "SImon",
        #            "units": "[m]",
        #        },
        #        "sithick": {
        #            "fullname": "Sea Ice Thickness",
        #            "monthly_table": "SImon",
        #            "units": "[m]",
        #        },
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


def get_model_key():
    model_keys = {
        "CanESM5": {
            "scenarios": ["ssp585", "ssp245"],
            "controls": ["historical", "piControl"],
        },
        "HadGEM3-GC31-MM": {
            "scenarios": ["ssp585"],
            "controls": ["historical", "piControl"],
        },
        "CESM2": {
            "scenarios": ["ssp585", "ssp245"],
            "controls": ["historical", "piControl"],
        },
    }
    return model_keys


def get_experiment_key():
    exp_key = {
        "historical": {
            "start_year": 1850,
            "end_year": 2014,
            "full_name": "Historical Runs",
        },
        "piControl": {
            "start_year": "None",
            "end_year": "None",
            "full_name": "Pre-industrial Control",
        },
        "ssp585": {
            "start_year": 2015,
            "end_year": 2100,
            "full_name": "ssp585",
        },
        "ssp245": {
            "start_year": 2015,
            "end_year": 2100,
            "full_name": "ssp245",
        },
    }
    return exp_key


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
    the cmpi6 historical runs and returns it. It assumes monthly data where
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
