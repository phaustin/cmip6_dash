import json
import os

import intake
import pooch
from case_utils import get_case_data
from case_utils import write_case_definition

case_file_path = "cases/"

if not os.path.isdir(case_file_path):
    os.mkdir(case_file_path)


odie = pooch.create(
    path="./.cache",
    base_url="https://storage.googleapis.com/cmip6/",
    registry={"pangeo-cmip6.csv": None},
)

file_path = odie.fetch("pangeo-cmip6.csv")
col = intake.open_esm_datastore(file_path)


write_case_definition(
    "bc_case_2",
    "tas",
    "CanESM5",
    "historical",
    10,
    "1950-01",
    "1955-02",
    (60, -139.05),
    (49, -114.068333),
    (case_file_path + "bc_tas_2.json"),
)

with open((case_file_path + "bc_tas_2.json")) as f:
    data = json.load(f)

get_case_data(col, data, write_path=(case_file_path + "bc_tas_2.nc"))
