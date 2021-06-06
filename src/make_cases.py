import json
import os
from pathlib import Path

import intake
from case_utils import get_case_data
from case_utils import write_case_definition

from a448_lib import data_read

case_file_path = "cases/"

if not os.path.isdir(case_file_path):
    os.mkdir(case_file_path)


csv_filename = "pangeo-cmip6.csv"
root = "https://storage.googleapis.com/cmip6"


if Path(csv_filename).is_file():
    print(f"found {csv_filename}")
else:
    print(f"downloading {csv_filename}")
    data_read.download(csv_filename, root=root)

json_filename = "https://storage.googleapis.com/cmip6/pangeo-cmip6.json"

col = intake.open_esm_datastore(json_filename)


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
