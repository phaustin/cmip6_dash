from pathlib import Path

import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import intake
import numpy as np
import pandas as pd
from dash.dependencies import Input
from dash.dependencies import Output

from src.a448_lib import data_read
from src.plot_fcns import get_var_key
from src.plot_fcns import plotly_wrapper

# Checking to see if the data is already downloaded
csv_filename = "pangeo-cmip6.csv"
root = "https://storage.googleapis.com/cmip6"
if Path(csv_filename).is_file():
    print(f"found {csv_filename}")
else:
    print(f"downloading {csv_filename}")
    data_read.download(csv_filename, root=root)

json_filename = "https://storage.googleapis.com/cmip6/pangeo-cmip6.json"

# Getting the esm data store
catalog_df = pd.read_csv(csv_filename)

col = intake.open_esm_datastore(json_filename)

var_key = get_var_key()

# Creating object with all variable full names for dropdown
full_name_key = []
for var in var_key:
    full_name_key.append({"label": var_key[var]["fullname"], "value": var})

# Experimental run names for exp_dropdown
exp_options = [
    {"label": "Historical Runs", "value": "historical"},
    {"label": "Preindustrial Control", "value": "piControl"},
    {"label": "SSP245", "value": "ssp245"},
    {"label": "SSP585", "value": "ssp585"},
]

# Model names for mod_drop
mod_options = [
    {"label": "CanESM5", "value": "CanESM5"},
    {"label": "HadGEM3-GC31-MM", "value": "HadGEM3-GC31-MM"},
    {"label": "CESM2", "value": "CESM2"},
]

# Plot displaying heatmap of selected run card
climate_heatmap_card = dbc.Col(
    [
        dcc.Loading(
            dbc.Card(
                [
                    dbc.CardHeader(
                        "Climate Plot",
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
)

# Dropdowns for specifying model run
dashboard_controls = dbc.Col(
    [
        html.H6("Model Variable"),
        dcc.Dropdown(id="var_drop", value="tas", options=full_name_key),
        html.Br(),
        html.H6("Model"),
        dcc.Dropdown(id="mod_drop", value="CanESM5", options=mod_options),
        html.Br(),
        html.H6("Date YYYY/MM"),
        dcc.Input(
            id="date_input",
            value="1975/02",
            debounce=True,
            style={"border-width": "0", "width": "100%"},
        ),
        html.Br(),
        html.Br(),
        html.H6("Experiment Label"),
        dcc.Dropdown(
            id="exp_drop",
            value="historical",
            options=exp_options,
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
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = dbc.Container(
    [
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H1(
                            "My splashboard demo",
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
                dashboard_controls,
                dbc.Col([dbc.Row([dbc.Col([climate_heatmap_card])])]),
            ]
        ),
        html.Hr(),
        html.P(""),
    ]
)


# Callbacks
@app.callback(
    Output("histogram", "figure"),
    Input("var_drop", "value"),
    Input("mod_drop", "value"),
    Input("date_input", "value"),
    Input("exp_drop", "value"),
)
def update_map(var_drop, mod_drop, date_input, exp_drop):
    """
    Updates the graph when the a different variable is selected
    """
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
    return fig


@app.callback(Output("mean_card", "children"), Input("histogram", "selectedData"))
def update_mean(selection):
    """
    Updates the mean card depending on the selected data in the graph
    """
    if selection is None:
        return 0
    var_vals = []
    for dict in selection["points"]:
        val = dict["marker.color"]
        var_vals.append(val)
        mean = np.mean(np.array(var_vals))
    return mean  # round(mean, 2)


@app.callback(Output("var_card", "children"), Input("histogram", "selectedData"))
def update_variance(selection):
    """
    Updates the variance card depending on the selected data in the graph
    """
    if selection is None:
        return 0
    var_vals = []
    for dict in selection["points"]:
        val = dict["marker.color"]
        var_vals.append(val)
        std = np.std(np.array(var_vals))
    return std  # round(std, 2)


if __name__ == "__main__":
    app.run_server(debug=True)
