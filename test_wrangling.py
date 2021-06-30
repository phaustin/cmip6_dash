import pytest

from src.wrangling_utils import dict_to_dash_opts
from src.wrangling_utils import get_cmpi6_model_run
from src.wrangling_utils import get_esm_datastore
from src.wrangling_utils import get_experiment_key
from src.wrangling_utils import get_model_key
from src.wrangling_utils import is_date_valid_for_exp


@pytest.fixture
def esm_datastore():
    return get_esm_datastore()


@pytest.fixture
def mod_exp_tuple():
    """Generates a tuple of model string and a list of
    associated scenarios"""
    model_dict = get_model_key()

    model = list(model_dict.keys())[0]
    first_sub_dict = model_dict[model]
    scenarios = []
    for lab in first_sub_dict.keys():
        for exp_id in first_sub_dict[lab]:
            scenarios.append(exp_id)

    mod_and_exp_id = (model, scenarios)
    return mod_and_exp_id


@pytest.fixture
def drop_down_opts():
    mod_options = [
        {"label": "CanESM5", "value": "CanESM5"},
        {"label": "HadGEM3-GC31-MM", "value": "HadGEM3-GC31-MM"},
        {"label": "CESM2", "value": "CESM2"},
    ]

    exp_options = [
        {"label": "Historical Runs", "value": "historical"},
        {"label": "Pre-industrial Control", "value": "piControl"},
        {"label": "ssp585", "value": "ssp585"},
        {"label": "ssp245", "value": "ssp245"},
    ]
    return mod_options, exp_options


def test_get_cmip6_model_run(esm_datastore, mod_exp_tuple):
    model = mod_exp_tuple[0]
    exp = mod_exp_tuple[1][0]
    model_list = get_cmpi6_model_run(
        esm_datastore, "tas", mod_exp_tuple[0], exp_id=exp, members=3
    )
    # Testing that three memebers get pulled down
    assert len(model_list) == 3


def test_model_opts(drop_down_opts):
    # Testing conversion between model_key functions and dash_dropdowns
    assert drop_down_opts[0] == dict_to_dash_opts(get_model_key())
    assert drop_down_opts[1] == dict_to_dash_opts(get_experiment_key())


def test_exp_date_validation():
    assert is_date_valid_for_exp("historical", "1950/01")
    assert not is_date_valid_for_exp("historical", "1600/01")
    assert is_date_valid_for_exp("ssp585", "2015/01")
    assert not is_date_valid_for_exp("ssp585", "2000/06")
    assert is_date_valid_for_exp("piControl", "2000/01")
