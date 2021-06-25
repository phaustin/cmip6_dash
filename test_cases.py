import json

import pytest
import xarray as xr

from src.case_utils import get_case_data
from src.case_utils import write_case_definition
from src.wrangling_utils import get_esm_datastore


@pytest.fixture
def bc_tas_data():
    nc_path = "cases/bc_tas_2.nc"
    return xr.open_dataset(nc_path)


@pytest.fixture
def bc_tas_def_json():
    nc_path = "cases/bc_tas_2.json"
    with open(nc_path) as f:
        data = json.load(f)
    return data


@pytest.fixture
def bc_tas_double_json():
    nc_path = "cases/bc_tas_double.json"
    with open(nc_path) as f:
        data = json.load(f)
    return data


@pytest.fixture
def bc_tas_def_fresh():
    bc_tas_case_def = write_case_definition(
        "bc_case_2",
        ["tas"],
        ["CanESM5"],
        "historical",
        10,
        "1950-01",
        "1955-02",
        (60, -139.05),
        (49, -114.068333),
    )
    return bc_tas_case_def


@pytest.fixture
def bc_tas_lai_2mod_def():
    bc_tas_lai_def = write_case_definition(
        "bc_case_2",
        ["tas", "lai"],
        ["CanESM5", "CESM2"],
        "historical",
        10,
        "1950-01",
        "1955-02",
        (60, -139.05),
        (49, -114.068333),
    )
    return bc_tas_lai_def


def test_single_case_def(bc_tas_def_json, bc_tas_def_fresh):
    """ """
    # Checking that they have the same keys
    # Would be lovely to do more validation here time permitting
    assert bc_tas_def_json.keys() == bc_tas_def_fresh.keys()


def test_single_case_data(bc_tas_data, bc_tas_def_fresh):
    # Fetching the datastore and pulling down the case specified above
    col = get_esm_datastore()
    test_fetch = get_case_data(col, bc_tas_def_fresh)
    assert test_fetch.equals(bc_tas_data)


def test_doble_case_def(bc_tas_double_json, bc_tas_lai_2mod_def):
    """ """
    # Checking that they have the same keys
    # Would be lovely to do more validation here time permitting
    assert bc_tas_double_json.keys() == bc_tas_lai_2mod_def.keys()
