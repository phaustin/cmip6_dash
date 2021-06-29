import json
import os
import re

import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import numpy as np
import xarray as xr
from dash.dependencies import Input
from dash.dependencies import Output
from dash.exceptions import PreventUpdate

from src.case_utils import join_members
from src.plot_utils import plot_member_line_comp
from src.plot_utils import plot_model_comparisons
from src.plot_utils import plot_year_plotly
from src.wrangling_utils import dict_to_dash_opts
from src.wrangling_utils import get_cmpi6_model_run
from src.wrangling_utils import get_esm_datastore
from src.wrangling_utils import get_experiment_key
from src.wrangling_utils import get_model_key
from src.wrangling_utils import get_month_and_year
from src.wrangling_utils import get_var_key


# Grabbing the ESM datastore
col = get_esm_datastore()

var_key = get_var_key()
mod_key = get_model_key()
exp_key = get_experiment_key()
# Getting the names of the cases for the dropdown
path = "cases/"
cases = os.listdir(path)
cases = [case for case in cases if re.search(r".json$", case)]
case_defs = [{"label": "Developer Mode", "value": "None"}]
for case in cases:
    case_defs.append({"label": case, "value": case})

# Plot displaying heatmap of selected run card
climate_heatmap_card = [
    dcc.Loading(
        dbc.Card(
            [
                dbc.CardHeader(
                    id="heatmap_title",
                    style={"fontWeight": "bold"},
                ),
                dbc.CardBody(
                    dcc.Graph(
                        id="histogram",
                        style={
                            "border-width": "0",
                            "width": "100%",
                            "height": "100%",
                        },
                    )
                ),
            ]
        )
    )
]

# Comparison tab-
comp_tab_contents = dbc.Col(
    [
        dcc.Loading(
            dbc.Card(
                [
                    dbc.CardHeader(  # The top comparison histogram
                        "Model Comparison",
                        style={"fontWeight": "bold"},
                    ),
                    dbc.CardBody(
                        dcc.Graph(
                            id="histogram_comparison",
                            style={
                                "border-width": "0",
                                "width": "100%",
                                "height": "100%",
                            },
                        )
                    ),
                ]
            )
        ),
        dcc.Loading(
            dbc.Card(
                [
                    dbc.CardHeader(  # Comapring models graph
                        "Model Run Comparison",
                        style={"fontWeight": "bold"},
                    ),
                    dbc.CardBody(
                        dcc.Graph(
                            id="mean_climatology",
                            style={
                                "border-width": "0",
                                "width": "100%",
                                "height": "100%",
                            },
                        )
                    ),
                ]
            )
        ),
    ]
)


# Dropdowns for specifying contents of the graphs
dashboard_controls = dbc.Col(
    [
        html.H6("Scenario"),
        dcc.Dropdown(id="scenario_drop", value="None", options=case_defs),
        html.Br(),
        html.H6("Model Variable"),
        dcc.Dropdown(id="var_drop", value="tas", options=dict_to_dash_opts(var_key)),
        html.Br(),
        html.H6("Model"),
        dcc.Dropdown(
            id="mod_drop", value="CanESM5", options=dict_to_dash_opts(mod_key)
        ),
        html.Br(),
        html.H6("Model Comparison"),
        dcc.Dropdown(
            id="mod_comp_drop", value="CESM2", options=dict_to_dash_opts(mod_key)
        ),
        html.Br(),
        html.H6("Date YYYY/MM"),
        dcc.Input(
            id="date_input",
            value="1975/02",
            style={"border-width": "0", "width": "100%"},
        ),
        html.Br(),
        html.Br(),
        html.H6("Experiment Label"),
        dcc.Dropdown(
            id="exp_drop",
            value="historical",
            options=dict_to_dash_opts(exp_key),
        ),
        html.Br(),
        html.H6("Mean"),
        dbc.Card(dbc.CardBody(id="mean_card")),
        html.Br(),
        html.H6("Std. Dev"),
        dbc.Card(dbc.CardBody(id="var_card")),
    ],
    md=2,
    style={
        "background-color": "#e6e6e6",
        "padding": 15,
        "border-radius": 3,
    },
)

# Actual layout for the app- all the defined pieces above get put together here
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
)

app.layout = dbc.Container(
    [
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H1(  # The big blue header
                            "CMIP-6 Dashboard",
                            style={
                                "color": "white",
                                "text-align": "left",
                                "font-size": "48px",
                            },
                        )
                    ],
                    style={
                        "backgroundColor": "steelblue",
                        "border-radius": 3,
                        "padding": 15,
                        "margin-top": 20,
                        "margin-bottom": 20,
                        "margin-right": 15,
                    },
                )
            ]
        ),
        dbc.Row(  # The tabs
            [
                dcc.Tabs(
                    id="tab_switch",
                    value="map_tab",
                    children=[
                        dcc.Tab(label="Climate Map", value="map_tab"),
                        dcc.Tab(label="Compare", value="comp_tab"),
                    ],
                )
            ]
        ),
        dbc.Row(  # The sidebar with controls
            [
                dashboard_controls,
                dbc.Col(id="tab_switch_content"),
            ]
        ),
        html.Hr(),
        html.P(""),
    ]
)


# Callbacks- these do all the dynamic updating and are where the calls to
# The various plotting and wrangling functions actually happen
@app.callback(
    [Output("histogram", "figure"), Output("heatmap_title", "children")],
    Input("scenario_drop", "value"),
    Input("var_drop", "value"),
    Input("mod_drop", "value"),
    Input("date_input", "value"),
    Input("exp_drop", "value"),
)
def update_map(scenario_drop, var_drop, mod_drop, date_input, exp_drop):
    """Updates the climate map graph when a different variable is selected


    Parameters
    ----------
    scenario_drop : str
        Output of string dropdown
    var_drop : str
        Var dropdown output
    mod_drop : str
        Mod dropdown selection
    date_input : str
        Input date selection
    exp_drop : str
        Experiment dropdown selection

    Returns
    -------
    Plotly figure
        Heatmap based on selections
    """
    date_list = date_input.split("/")
    if scenario_drop == "None":
        xarray_dset = get_cmpi6_model_run(col, var_drop, mod_drop, exp_drop)[0]
    else:
        folder_path = path + scenario_drop.split(".")[0]
        xarray_dset = xr.open_dataset(f"{folder_path}/{mod_drop}_{var_drop}.nc")

    fig = plot_year_plotly(
        xarray_dset,
        var_drop,
        mod_drop,
        month=date_list[1],
        year=date_list[0],
        exp_id=exp_drop,
    )
    full_var_name = var_key[var_drop]["fullname"]
    title = f"{full_var_name} {date_list[0]} {date_list[1]} {exp_drop} {mod_drop}"
    return fig, title


@app.callback(
    Output("mean_climatology", "figure"),
    Input("scenario_drop", "value"),
    Input("var_drop", "value"),
    Input("mod_drop", "value"),
    Input("date_input", "value"),
    Input("exp_drop", "value"),
)
def update_line_comp(scenario_drop, var_drop, mod_drop, date_input, exp_drop):
    """Updates the climate map graph when a different variable is selected


    Parameters
    ----------
    scenario_drop : str
        Output of string dropdown
    var_drop : str
        Var dropdown output
    mod_drop : str
        Mod dropdown selection
    mod_comp_drop : str
        Mod comp dropdown selection
    date_input : str
        Input date selection
    exp_drop : str
        Experiment dropdown selection

    Returns
    -------
    Plotly figure
        The plotly figure produced by plot_member_line_plot
    """
    date_list = date_input.split("/")
    start_date = date_list[0]
    end_date = str(int(date_list[0]) + 1)
    if scenario_drop == "None":
        dset_list = get_cmpi6_model_run(col, var_drop, mod_drop, exp_drop, 3)
        dset = join_members(dset_list).sel(time=slice(start_date, end_date))
    else:
        folder_path = path + scenario_drop.split(".")[0]
        with open(path + scenario_drop) as f:
            data = json.load(f)
        dset = xr.open_dataset(f"{folder_path}/{mod_drop}_{var_drop}.nc")

    fig = plot_member_line_comp(dset, var_drop)
    return fig


# Callbacks
@app.callback(
    Output("histogram_comparison", "figure"),
    Input("scenario_drop", "value"),
    Input("var_drop", "value"),
    Input("mod_drop", "value"),
    Input("mod_comp_drop", "value"),
    Input("date_input", "value"),
    Input("exp_drop", "value"),
)
def update_comparison_hist(
    scenario_drop, var_drop, mod_drop, mod_comp_drop, date_input, exp_drop
):
    """Updates the model comparison plot when inputs are changed

    Parameters
    ----------
    scenario_drop : str
        Output of string dropdown
    var_drop : str
        Var dropdown output
    mod_drop : str
        Mod dropdown selection
    mod_comp_drop : str
        Mod comp dropdown selection
    date_input : str
        Input date selection
    exp_drop : str
        Experiment dropdown selection

    Returns
    -------
    Plotly Figure
        Plotly figure plotted
    """
    date_list = date_input.split("/")

    if scenario_drop == "None":
        dset_comp = get_cmpi6_model_run(col, var_drop, mod_comp_drop, exp_drop)[0]
        dset_comp = get_month_and_year(
            dset_comp, var_drop, date_list[1], date_list[0], exp_drop
        )
        filt_dset = get_cmpi6_model_run(col, var_drop, mod_drop, exp_drop)[0]
        filt_dset = get_month_and_year(
            filt_dset, var_drop, date_list[1], date_list[0], exp_drop
        )
        dset_tuple = (filt_dset, dset_comp)
    else:
        folder_path = path + scenario_drop.split(".")[0]
        filt_dset = xr.open_dataset(f"{folder_path}/{mod_drop}_{var_drop}.nc")
        filt_dset = get_month_and_year(
            filt_dset, var_drop, date_list[1], date_list[0], exp_drop
        )
        dset_comp = xr.open_dataset((f"{folder_path}/{mod_comp_drop}_{var_drop}.nc"))
        dset_comp = get_month_and_year(
            dset_comp, var_drop, date_list[1], date_list[0], exp_drop
        )
        dset_tuple = (filt_dset, dset_comp)

    fig = plot_model_comparisons(
        dset_tuple,
        var_drop,
        mod_drop,
        mod_comp_id=mod_comp_drop,
    )
    return fig


@app.callback(
    [
        Output("var_drop", "options"),
        Output("mod_drop", "options"),
        Output("mod_comp_drop", "options"),
        Output("date_input", "value"),
        Output("exp_drop", "options"),
    ],
    Input("scenario_drop", "value"),
)
def update_options(scenario_drop):
    """Updates the options for var_drop, mod_drop, and exp_drop based on scenario

    Parameters
    ----------
    scenario_drop : str
        Output of string dropdown
    Returns
    -------
    var_opts
        Updated set of values in the variable options dropdown from scenario
    mod_opts
        Updated set of values in the model options dropdown from scenario
    date_val
        Start date of scenario
    exp_opts
        Exp of the scenario selected to set exp options to
    """
    # Stops this from updating if we no scenario selected
    if scenario_drop == "None":
        raise PreventUpdate

    # Read the json file for the selected case
    with open(path + scenario_drop) as f:
        data = json.load(f)
    var_opts = dict_to_dash_opts(var_key, key_subset=data["var_id_list"])
    mod_opts = dict_to_dash_opts(mod_key, key_subset=data["mod_id_list"])
    mod_comp_opts = mod_opts
    exp = data["exp_id"]
    exp_opts = [{"label": exp, "value": exp}]

    start_dates = data["start_date"].split("-")
    date_val = start_dates[0] + "/" + start_dates[1]

    return var_opts, mod_opts, mod_comp_opts, date_val, exp_opts


@app.callback(Output("mean_card", "children"), Input("histogram", "selectedData"))
def update_mean(selection):
    """Updates the mean card depending on the selected data in the graph


    Parameters
    ----------
    selection : dictionary
        Data selected on the climate graph

    Returns
    -------
    str
        Mean climatology selected for a given time period
    """
    if selection is None:
        return 0
    var_vals = []
    for dict in selection["points"]:
        val = dict["marker.color"]
        var_vals.append(val)
        mean = np.mean(np.array(var_vals))
    return f"{mean:.2e}"


@app.callback(Output("var_card", "children"), Input("histogram", "selectedData"))
def update_variance(selection):
    """Updates the variance of card based on selection on graph

    Parameters
    ----------
    selection : dictionary
        Data selected on the climate graph

    Returns
    -------
    str
        Standard deviation of the map selection
    """
    if selection is None:
        return 0
    var_vals = []
    for dict in selection["points"]:
        val = dict["marker.color"]
        var_vals.append(val)
        std = np.std(np.array(var_vals))
    return f"{std:.2e}"


@app.callback(Output("tab_switch_content", "children"), Input("tab_switch", "value"))
def render_content(tab):
    """Switches the content displayed when a different tab is selected

    Parameters
    ----------
    tab : str
        Which tab is selected

    Returns
    -------
    Dbc. Col
        Dash code defined above for different tab content
    """
    if tab == "map_tab":
        return climate_heatmap_card
    elif tab == "comp_tab":
        return comp_tab_contents


# Remove the debug=True here in deployment
if __name__ == "__main__":
    app.run_server(debug=True)
