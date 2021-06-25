import json
import os

from src.case_utils import get_case_data
from src.case_utils import write_case_definition
from src.wrangling_utils import get_esm_datastore

case_file_path = "cases/"

if not os.path.isdir(case_file_path):
    os.mkdir(case_file_path)

col = get_esm_datastore()


def write_bc_case():
    write_case_definition(
        "bc_case_2",
        ["tas"],
        ["CanESM5"],
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

    get_case_data(col, data, write_path=(case_file_path))


def main():
    write_bc_case()


if __name__ == "__main__":
    main()
