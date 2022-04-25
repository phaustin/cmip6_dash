import pytest

from .wrangling_utils import get_cmpi6_model_run
from .wrangling_utils import get_esm_datastore
from .wrangling_utils import get_model_key


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


def test_get_cmip6_model_run(esm_datastore, mod_exp_tuple):
    model = mod_exp_tuple[0]
    exp = mod_exp_tuple[1][0]
    model_list = get_cmpi6_model_run(
        esm_datastore, "tas", mod_exp_tuple[0], exp_id=exp, members=3
    )
    # Testing that three memebers get pulled down
    assert len(model_list) == 3
