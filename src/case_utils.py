import json
import os

import xarray as xr

from .wrangling_utils import get_cmpi6_model_run
from .wrangling_utils import get_model_key
from .wrangling_utils import get_var_key
from .wrangling_utils import is_date_valid_for_exp


def scenario_data_dict_to_netcdf(
    scenario_name, xarray_dict, write_path, write_over=False
):
    """Takes a dict of model, vars, and xarray dsets concatted along member axis,
    Creates a folder with the name of the scenario, and saves each xarray as a netcdf
    with a name of the form model_variable
     the file
    dict should be of the form
    {'modelx' {'var1' : xarray_dataset,
               'var2' : xarray_dataset},
     ...
     'modely' {'var1' : xarray_dataset,
               'var2' : xarray_dataset},"""
    file_path = write_path + "/" + scenario_name
    if os.path.isdir(file_path) & (not write_over):
        print("Scenario folder exists and write_over set to false!")
        raise OSError
    os.mkdir(file_path)
    for mod in xarray_dict.keys():
        for var in xarray_dict[mod].keys():
            xarray_dict[mod][var].to_netcdf(f"{file_path}/{mod}_{var}.nc")


def get_case_data(data_store, case_definition, write_path="None"):

    """Queries a given data store for the specification and returns and writes the data

    Wraps a query for the data_store to get the xarray. Variable id must be supported
    by get_monthly_table_for_var(). Data is written in the netCDF format.

    Parameters
    ----------
    data_store : esm_datastore
        The data store to query

    case_definition : dict
        This dict specifies the region, variable time period, scenario, and number of
        ensemble members. Write_case_definitions will generate and validate an
        appropriate dict.

    write_path : str
        Ignored if xarr_write_path is set to none. Path where the netCDF file with
        case data will be written.


    Returns
    -------
    xarr_file : xarrary Dataset
        The experiment for the given query in a list
    """
    # Grabbing through the corners of our case
    bottom_lat_bnd = case_definition["bottom_right"][0]
    top_lat_bnd = case_definition["top_left"][0]
    right_lon_bnd = case_definition["bottom_right"][1]
    left_lon_bnd = case_definition["top_left"][1]

    return_dict = {}
    # Iterating through all the models, creating a dictionary with a variable var_dict
    # and fetching the xarray set for the first n members in that variable/model
    # combo and joining all the members into the same xarray set
    for mod in case_definition["mod_id_list"]:
        var_dict = {}
        # The fetching step
        for var in case_definition["var_id_list"]:
            dsets = get_cmpi6_model_run(
                data_store,
                var,
                mod,
                case_definition["exp_id"],
                case_definition["members"],
            )
            # Here we deal with the piControl edge case. Since the dates are not
            # Consistent between models for piControl, we get the last year available
            # And save that as the data for each model.
            if case_definition["exp_id"] == "piControl":
                year = (
                    dsets[0]["time"]  # From the time index
                    .isel(time=slice(-2, -1))  # Get the last year
                    .dt.year.values[0]  # Change format to year and grab it
                )
                start_date = str(year - 1)
                end_date = str(year)
            else:
                start_date = case_definition["start_date"]
                end_date = case_definition["end_date"]
            # The clipping to geographic area and time step
            dsets_clipped = [
                clip_xarray(
                    dset,
                    top_lat_bnd,
                    bottom_lat_bnd,
                    right_lon_bnd,
                    left_lon_bnd,
                    lons_360=False,
                ).sel(time=slice(start_date, end_date))
                for dset in dsets
            ]
            # The joining on member axis step
            var_dict[var] = join_members(dsets_clipped)
        return_dict[mod] = var_dict

    if write_path != "None":
        scenario_data_dict_to_netcdf(
            case_definition["case_name"], return_dict, write_path
        )
    else:
        return return_dict


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


def join_members(list_of_dsets):
    """Joins a list of members together in one dataset

    Parameters
    ----------
    list_of_dsets : list
        List of xarray datasets. Should be repeats of the same model run
        with identical parameters. New dimension is called "member_num" assigned
        based on order in list passed to function.

    Returns
    -------
    xarray datasetc
        list of xarray datasets
    """
    # Creating the new index to join data sets on
    for index in range(len(list_of_dsets)):
        list_of_dsets[index] = list_of_dsets[index].assign_coords(member_num=index)

    # Joining the datasets on the new axis and returning
    concat_sets = xr.concat(list_of_dsets, dim="member_num")
    return concat_sets


def write_case_definition(
    case_name,
    var_id_list,
    mod_id_list,
    exp_id,
    members,
    start_date,
    end_date,
    top_left,
    bottom_right,
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

    var_id_list : list of str
         The variable id to use in the query. Must be a member of dict supplied by
         get_var_key()

    mod_id_list : list of str
         The model id to query results for. Must be a valid cimp6 model id

    exp_id : str
         The experiment id. Must be valid for each mod in the mod_id_list and str in the
         var_id list

    members : int
        Number of model runs to include in case xarr dataset.

    start_date : str '1950-01'
        Of the form YYYY-MM e.g '1955-02'. Start of the date range- check these dates
        are contained in the given runs of the given experiment. Ignored for piControl.

    end_date : str '1955-02'
        Of the form YYYY-MM e.g '1955-02'. End of the date range check these dates are
        contained in the given runs of the given experiment. Ignored for piControl.

    top_left : tuple (float, float)
        Top left lat-lon coord for regional subselection. Should be decimal of the form
        Lat -90-90, Lon -180-180

    bottom_right : tuple (float, float)
        Bottom right lat-lon coord for regional subselection. Should be decimal of the
        form lat -90-90, Lon -180-180

    padding : int
        Amount of space to include in plotting

    write_path : str
        The file path + file name for writing the json

    Returns
    -------
    case_definition : dict
        A dictionary with all the requests validated

    """
    # Var id should be in var_keys
    mod_key = get_model_key()
    try:
        for var in var_id_list:
            var_key = get_var_key()
            var_key[var]
    except KeyError:
        print(f"var id should be one of {get_var_key().keys()}")
        raise KeyError
    # Mod id should be one in the model key dict
    try:
        for mod in mod_id_list:
            mod_key[mod]
    except KeyError:
        print(f"mod id should be one of {mod_key.keys()}")
        raise KeyError
    # The exp id must be one of the scenarios or controls for the model
    model_opts = (
        mod_key[mod_id_list[0]]["scenarios"] + mod_key[mod_id_list[0]]["controls"]
    )
    if exp_id not in model_opts:
        print(f"experiment id should be one of {model_opts} for {mod_id_list}")
        raise AssertionError

    # Checking that the start and end dates are valid for experiment
    if not is_date_valid_for_exp(exp_id, start_date):
        print(f"{start_date} not valid for {exp_id}!")
        raise AssertionError

    if not is_date_valid_for_exp(exp_id, end_date):
        print(f"{end_date} not valid for {exp_id}!")
        raise AssertionError

    # Members should be less than 40
    if members > 40:
        print(f"{members} is too many members")
        raise AssertionError
    # Checking lats and lons are in the right range
    lats = [top_left[0], bottom_right[0]]
    for lat in lats:
        if abs(lat) > 90:
            print(f"{lat} is not between -90 and 90!")
            raise AssertionError
    lons = [top_left[1], bottom_right[1]]
    for lon in lons:
        if abs(lon) > 180:
            print(f"{lon} is not between -180 and 180!")
            raise AssertionError

    # The lats should correspond to Amon gridding (see above)
    case_definition = {
        "case_name": case_name,
        "var_id_list": var_id_list,
        "mod_id_list": mod_id_list,
        "exp_id": exp_id,
        "members": members,
        "start_date": start_date,
        "end_date": end_date,
        "top_left": top_left,
        "bottom_right": bottom_right,
    }

    if write_path != "None":
        with open(write_path, "w") as write_file:
            json.dump(case_definition, write_file, indent=4)
    else:
        return case_definition
