import json

import xarray as xr
from wrangling_utils import get_cmpi6_model_run
from wrangling_utils import get_model_key
from wrangling_utils import get_var_key
# The . here indicates current working directory


def get_case_data(data_store, case_definition, write_path="None"):

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

    write_path : str
        Ignored if xarr_write_path is set to none. Path where the netCDF file with
        case data will be written.


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

    dsets_clipped = [
        clip_xarray(
            dset,
            top_lat_bnd,
            bottom_lat_bnd,
            right_lon_bnd,
            left_lon_bnd,
            lons_360=False,
        ).sel(time=slice(case_definition["start_date"], case_definition["end_date"]))
        for dset in dsets
    ]

    for index in range(len(dsets_clipped)):
        dsets_clipped[index] = dsets_clipped[index].assign_coords(member_num=index)

    concat_sets = xr.concat(dsets_clipped, dim="member_num")

    if write_path != "None":
        concat_sets.to_netcdf(write_path)
    else:
        return case_definition


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
    case_name,
    var_id,
    mod_id,
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
        var_key = get_var_key()
        var_key[var_id]
    except KeyError:
        print(f"var id should be one of {get_var_key().keys()}")
        raise KeyError
    # Mod id should be one in the model key dict
    try:
        mod_key[mod_id]
    except KeyError:
        print(f"mod id should be one of {mod_key.keys()}")
        raise KeyError
    # The exp id must be one of the scenarios or controls for the model
    model_opts = mod_key[mod_id]["scenarios"] + mod_key[mod_id]["controls"]
    try:
        if exp_id not in model_opts:
            raise AssertionError
    except AssertionError:
        print(f"experiment id should be one of {model_opts} for {mod_id}")
        raise AssertionError

    # Members should be less than 40
    if members > 40:
        print(f"{members} is too many members")
        raise AssertionError
    # The start date must be compatible with the exp id (1850-2014 for historical),
    start_date_split = start_date.split("-")
    start_date_split = [int(date) for date in start_date_split]
    end_date_split = end_date.split("-")
    end_date_split = [int(date) for date in end_date_split]

    if exp_id == "historical":
        if not (start_date_split[0] >= 1850 and start_date_split[0] <= 2014):
            print("historical runs range from 1850 to 2014")
            raise AssertionError
        if not (end_date_split[0] >= 1850 and end_date_split[0] <= 2014):
            print("historical runs range from 1850 to 2014")
            raise AssertionError
    if exp_id in mod_key[mod_id]["scenarios"]:
        if not start_date_split[0] >= 2015 and start_date_split[0] <= 2100:
            print("historical runs range from 1850 to 2014")
            raise AssertionError
        if not end_date_split[0] >= 2015 and end_date_split[0] <= 2100:
            print("historical runs range from 1850 to 2014")
            raise AssertionError
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

    # 2014 on for pi
    # Same with end date
    # The lats should correspond to Amon gridding (see above)
    case_definition = {
        "case_name": case_name,
        "var_id": var_id,
        "mod_id": mod_id,
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
