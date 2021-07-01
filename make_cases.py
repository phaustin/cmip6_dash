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
        (case_file_path + "bc_case_2.json"),
    )

    with open((case_file_path + "bc_case_2.json")) as f:
        data = json.load(f)

    get_case_data(col, data, write_path=(case_file_path))


def write_bc_case_mult():
    write_case_definition(
        "bc_case_mult",
        ["tas", "lai"],
        ["CanESM5", "HadGEM3-GC31-MM"],
        "historical",
        3,
        "1950-01",
        "1955-02",
        (60, -139.05),
        (49, -114.068333),
        (case_file_path + "bc_case_mult.json"),
    )

    with open((case_file_path + "bc_case_mult.json")) as f:
        data = json.load(f)

    get_case_data(col, data, write_path=(case_file_path))


def write_australia_case():
    write_case_definition(
        "aus_tas_case",
        ["tas"],
        ["CanESM5", "HadGEM3-GC31-MM"],
        "ssp585",
        3,
        "2025-01",
        "2050-02",
        (-10, 100),
        (-40, 170),
        (case_file_path + "aus_tas_case.json"),
    )

    with open((case_file_path + "aus_tas_case.json")) as f:
        data = json.load(f)

    get_case_data(col, data, write_path=(case_file_path))


def write_pi_bc_case():
    write_case_definition(
        "bc_pi",
        ["tas"],
        ["CanESM5"],
        "piControl",
        2,
        "1950-01",
        "1955-02",
        (60, -139.05),
        (49, -114.068333),
        (case_file_path + "bc_pi.json"),
    )

    with open((case_file_path + "bc_pi.json")) as f:
        data = json.load(f)

    get_case_data(col, data, write_path=(case_file_path))


def main():
    # write_bc_case()
    # write_bc_case_mult()
    # write_australia_case()
    write_pi_bc_case()


if __name__ == "__main__":
    main()
