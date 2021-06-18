import json
import os
import re
from pathlib import Path

import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import numpy as np
import xarray as xr
from dash.dependencies import Input
from dash.dependencies import Output
from dash.exceptions import PreventUpdate

from src.plot_utils import plot_member_line_comp
from src.plot_utils import plot_model_comparisons
from src.plot_utils import plot_year_plotly
from src.plot_utils import plotly_wrapper
from src.wrangling_utils import get_esm_datastore
from src.wrangling_utils import get_var_key

# Grabbing the ESM datastore
col = get_esm_datastore()

var_key = get_var_key()

# Getting the names of the cases for the dropdown
path = "cases/"
cases = os.listdir(path)
cases = [case for case in cases if re.search(r".json$", case)]
case_defs = [{"label": "None", "value": "None"}]
for case in cases:
    case_defs.append({"label": case, "value": case})

# Creating object with all variable full names for dropdown
full_name_key = []
for var in var_key:
    full_name_key.append({"label": var_key[var]["fullname"], "value": var})

# Model names for mod_drop
mod_options = [
    {"label": "CanESM5", "value": "CanESM5"},
    {"label": "HadGEM3-GC31-MM", "value": "HadGEM3-GC31-MM"},
    {"label": "CESM2", "value": "CESM2"},
]

# Plot displaying heatmap of selected run card
climate_heatmap_card = [
    dcc.Loading(
        dbc.Card(
            [
                dbc.CardHeader(
                    id="heatmap_title",
                    # "Climate Plot",
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

# Comparison tab
comp_tab_contents = dbc.Col(
    [
        dcc.Loading(
            dbc.Card(
                [
                    dbc.CardHeader(
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
                    dbc.CardHeader(
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
        dcc.Dropdown(id="var_drop", value="tas", options=full_name_key),
        html.Br(),
        html.H6("Model"),
        dcc.Dropdown(id="mod_drop", value="CanESM5", options=mod_options),
        html.Br(),
        html.H6("Model Comparison"),
        dcc.Dropdown(id="mod_comp_drop", value="CanESM5", options=mod_options),
        html.Br(),
        html.H6("Date YYYY/MM"),
        dcc.Input(
            id="date_input",
            value="1975/02",
            # debounce=True,
            style={"border-width": "0", "width": "100%"},
        ),
        html.Br(),
        html.Br(),
        html.H6("Experiment Label"),
        dcc.Dropdown(
            id="exp_drop",
            value="historical",
            style={"border-width": "0", "width": "100%"},
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

# Layout for the app
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
                        html.H1(
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
        dbc.Row(
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
        dbc.Row(
            [
                dashboard_controls,
                dbc.Col(id="tab_switch_content"),
            ]
        ),
        html.Hr(),
        html.P(""),
    ]
)


# Callbacks
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
        Output of
    """
    date_list = date_input.split("/")
    var_key = get_var_key()
    if scenario_drop == "None":
        date_list = date_input.split("/")
        fig = plotly_wrapper(
            col,
            var_drop,
            mod_drop,
            exp_drop,
            month=date_list[1],
            year=date_list[0],
            layer=1,
        )
        title = (
            var_key[var_drop]["fullname"]
            + " "
            + date_list[0]
            + "-"
            + date_list[1]
            + " "
            + exp_drop
            + " "
            + mod_drop
        )
    else:
        with open(path + scenario_drop) as f:
            data = json.load(f)
        dset = xr.open_dataset(path + scenario_drop.split(".")[0] + ".nc")
        fig = plot_year_plotly(
            dset.sel({"member_num": 0}),
            data["var_id"],
            data["mod_id"],
            month=date_list[1],
            year=date_list[0],
            exp_id=data["exp_id"],
            layer=1,
        )
        title = (
            var_key[data["var_id"]]["fullname"]
            + " "
            + date_list[0]
            + "-"
            + date_list[1]
            + " "
            + data["exp_id"]
            + " "
            + mod_drop
        )
    return fig, title


@app.callback(
    Output("mean_climatology", "figure"),
    Input("scenario_drop", "value"),
)
def update_line_comp(scenario_drop):
    """Updates the climate map graph when a different variable is selected


    Parameters
    ----------
    scenario_drop : str
        The scenario to plot

    Returns
    -------
    Plotly figure
        The plotly figure produced by plot_member_line_plot
    """
    with open(path + scenario_drop) as f:
        data = json.load(f)
    dset = xr.open_dataset(path + scenario_drop.split(".")[0] + ".nc")
    fig = plot_member_line_comp(dset, data["var_id"])
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
    fig = plot_model_comparisons(
        col,
        var_drop,
        mod_drop,
        exp_drop,
        month=date_list[1],
        year=date_list[0],
        layer=1,
        mod_comp_id=mod_comp_drop,
    )
    return fig


@app.callback(
    Output("exp_drop", "options"),
    Input("date_input", "value"),
    Input("mod_drop", "value"),
)
def restrict_experiments(date_input, mod_drop):
    """This function changes the possible values of the experiment drop downs based on the
    selected date and model selection.

    Parameters
    ----------
    date_input : [type]
        [description]
    mod_drop : [type]
        [description]

    Returns
    -------
    [type]
        [description]
    """
    date_list = date_input.split("/")
    year = int(date_list[0])
    if year < 2014:
        exp_options = [
            {"label": "Historical Runs", "value": "historical"},
            {"label": "Preindustrial Control", "value": "piControl"},
        ]
    elif mod_drop == "HadGEM3-GC31-MM":
        exp_options = [
            {"label": "SSP585", "value": "ssp585"},
            {"label": "Preindustrial Control", "value": "piControl"},
        ]
    else:
        exp_options = [
            {"label": "SSP245", "value": "ssp245"},
            {"label": "SSP585", "value": "ssp585"},
            {"label": "Preindustrial Control", "value": "piControl"},
        ]
    return exp_options


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
        [description]
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


@app.callback(
    Output("date_input", "value"),
    Input("scenario_drop", "value"),
)
def update_date_for_case(scenario_drop):
    """[summary]

    Parameters
    ----------
    scenario_drop : [type]
        [description]

    Returns
    -------
    [type]
        [description]

    Raises
    ------
    PreventUpdate
        [description]
    """
    if scenario_drop == "None":
        raise PreventUpdate
    with open(path + scenario_drop) as f:
        data = json.load(f)
    start_dates = data["start_date"].split("-")
    start_date = start_dates[0] + "/" + start_dates[1]
    return start_date


if __name__ == "__main__":
    app.run_server(debug=True)
