"""
This app creates an animated sidebar using the dbc.Nav component and some local
CSS. Each menu item has an icon, when the sidebar is collapsed the labels
disappear and only the icons remain. Visit www.fontawesome.com to find
alternative icons to suit your needs!

dcc.Location is used to track the current location, a callback uses the current
location to render the appropriate page content. The active prop of each
NavLink is set automatically according to the current pathname. To use this
feature you must install dash-bootstrap-components >= 0.11.0.

For more details on building multi-page Dash applications, check out the Dash
documentation: https://dash.plot.ly/urls
"""
import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, dcc, html
import os

# Etc
import pandas as pd

# e-mission modules
import emission.core.get_database as edb

# Data/file handling imports
import pathlib

# Global data modules to share data across callbacks
# (Not sure how this stands up in multi-user/hosted situations)
import globals as gl
import globalsUpdater as gu

OPENPATH_LOGO = "https://www.nrel.gov/transportation/assets/images/openpath-logo.jpg"

#------------------------------------------------#
# Set the data path
#------------------------------------------------#

# For data that lives within the application.
# Set the path to the data directory
DATA_PATH = pathlib.Path(__file__).parent.joinpath("./data/").resolve()

app = dash.Dash(
    external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME],
    use_pages=True
)

sidebar = html.Div(
    [
        
        html.Div(
            [
                # width: 3rem ensures the logo is the exact width of the
                # collapsed sidebar (accounting for padding)
                html.Img(src=OPENPATH_LOGO, style={"width": "3rem"}),
                html.H2("OpenPATH"),
            ],
            className="sidebar-header",
        ),
        html.Hr(),
        dbc.Nav(
            [
                dbc.NavLink(
                    [
                        html.I(className="fas fa-home me-2"), 
                        html.Span("Overview")
                    ],
                    href="/",
                    active="exact",
                ),
                dbc.NavLink(
                    [
                        html.I(className="fas fa-sharp fa-solid fa-database me-2"),
                        html.Span("Data"),
                    ],
                    href="/data",
                    active="exact",
                ),
                dbc.NavLink(
                    [
                        html.I(className="fas fa-solid fa-globe me-2"),
                        html.Span("Map"),
                    ],
                    href="/map",
                    active="exact",
                ),
                dbc.NavLink(
                    [
                        html.I(className="fas fa-solid fa-envelope-open-text me-2"),
                        html.Span("Push notification"),
                    ],
                    href="/push_notification",
                    active="exact",
                ),
                dbc.NavLink(
                    [
                        html.I(className="fas fa-gear me-2"),
                        html.Span("Settings"),
                    ],
                    href="/settings",
                    active="exact",
                )
            ],
            vertical=True,
            pills=True,
        ),
    ],
    className="sidebar",
)

CONTENT_STYLE = {
    "margin-left": "5rem",
    "margin-right": "2rem",
    "padding": "2rem 1rem",
}
content = html.Div(dash.page_container, style=CONTENT_STYLE)

app.layout = html.Div(
    [
        dcc.Location(id="url"), 
        sidebar, 
        content,
        dcc.Store(id="store-trips", data={}),
        dcc.Store(id="store-uuids", data={}),
        dcc.Interval(id='interval-component', interval=60*1000, n_intervals=0),
    ]
)

# Load data stores
@app.callback(
    Output("store-uuids", "data"),
    [Input('interval-component', 'n_intervals')]
)
def update_store_uuids(n_intervals):
    dff = query_uuids()
    store = {
        "data": dff.to_dict("records"),
        "columns": [{"name": i, "id": i} for i in dff.columns],
    }
    return store

def query_uuids():
    uuid_data = list(edb.get_uuid_db().find({}, {"_id": 0}))
    df = pd.json_normalize(uuid_data)
    df.rename(
        columns={"user_email": "user_token",
                "uuid": "user_id"},
        inplace=True
    )
    df['user_id'] = df['user_id'].astype(str)
    df['update_ts'] = pd.to_datetime(df['update_ts'])
    return(df)

def query_confirmed_trips():
    query_result = edb.get_analysis_timeseries_db().find(
        {'$and':
            [
                {'metadata.key': 'analysis/confirmed_trip'},
                {'data.user_input.trip_user_input': {'$exists': False}}
            ]
         },
         {
            "_id": 0,
            "user_id": 1,
            "trip_start_time_str": "$data.start_fmt_time",
            "trip_start_time_tz": "$data.start_local_dt.timezone",
            "travel_modes": "$data.user_input.trip_user_input.data.jsonDocResponse.data.travel_mode"
        }
    )
    df = pd.DataFrame(list(query_result))
    df['user_id'] = df['user_id'].astype(str)
    return df

@app.callback(
    Output("store-trips", "data"),
    [Input('interval-component', 'n_intervals')]
)
def update_store_trips(n_intervals):
    dff = query_confirmed_trips()
    store = {
        "data": dff.to_dict("records"),
        "columns": [{"name": i, "id": i} for i in dff.columns],
    }
    return store

if __name__ == "__main__":
    envPort = int(os.getenv('DASH_SERVER_PORT', '8050'))
    envDebug = os.getenv('DASH_DEBUG_MODE', 'True').lower() == 'true'
    app.run_server(debug=envDebug, host='0.0.0.0', port=envPort)
