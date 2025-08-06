import os
import flask
import pandas as pd
from dash import Dash, dcc, html, dash_table, callback_context
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
from ix.db import Timeseries
import dash


def create_dash_app(requests_pathname_prefix: str = None) -> Dash:
    """
    Complete working Dash application with name-only search.
    """
    # Flask server
    server = flask.Flask(__name__)
    server.secret_key = os.environ.get("SECRET_KEY", "secret")

    # Dash app initialization
    app = Dash(
        __name__,
        server=server,
        external_stylesheets=[dbc.themes.BOOTSTRAP],
        requests_pathname_prefix=requests_pathname_prefix,
    )

    # Helper to fetch all timeseries
    def fetch_timeseries():
        try:
            docs = [doc.dict() for doc in Timeseries.find().run()]
            return docs if docs else []
        except Exception as e:
            print(f"Error fetching timeseries: {e}")
            return []

    # Helper to search by name
    def search_by_name(name_query: str = None):
        try:
            if not name_query or name_query.strip() == "":
                return fetch_timeseries()

            # Case-insensitive regex search on name field
            query = {"name": {"$regex": f".*{name_query}.*", "$options": "i"}}
            docs = [doc.dict() for doc in Timeseries.find(query).run()]
            return docs if docs else []
        except Exception as e:
            print(f"Error searching timeseries: {e}")
            return fetch_timeseries()

    # Initial layout
    app.layout = dbc.Container(
        fluid=True,
        className="p-4",
        children=[
            dbc.NavbarSimple(
                brand="Timeseries Manager",
                color="dark",
                dark=True,
                className="mb-4",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        dbc.InputGroup(
                            [
                                dbc.InputGroupText("Search by Name"),
                                dbc.Input(
                                    id="search-input",
                                    type="text",
                                    placeholder="Enter timeseries name...",
                                    debounce=True,
                                ),
                                dbc.Button(
                                    "Clear",
                                    id="clear-search",
                                    color="secondary",
                                    outline=True,
                                ),
                            ],
                            className="mb-3",
                        ),
                        width=8,
                    ),
                    dbc.Col(
                        dbc.Button(
                            "New Timeseries",
                            id="open-modal",
                            color="primary",
                            className="me-1",
                        ),
                        width="auto",
                    ),
                ],
                className="mb-2",
                justify="between",
            ),
            # Status alerts
            dbc.Alert(
                id="status-alert", is_open=False, duration=4000, className="mb-3"
            ),
            # DataTable
            dbc.Spinner(
                dash_table.DataTable(
                    id="ts-table",
                    columns=[
                        {
                            "name": col.capitalize().replace("_", " "),
                            "id": col,
                            "editable": (col != "code"),
                        }
                        for col in (
                            fetch_timeseries()[0].keys() if fetch_timeseries() else []
                        )
                    ],
                    data=fetch_timeseries(),
                    page_size=10,
                    page_action="native",
                    sort_action="native",
                    row_selectable="single",
                    selected_rows=[],
                    style_table={"overflowX": "auto"},
                    style_header={
                        "backgroundColor": "#f8f9fa",
                        "fontWeight": "bold",
                    },
                ),
                color="primary",
            ),
            # Modal for create/edit
            dbc.Modal(
                id="ts-modal",
                is_open=False,
                size="lg",
                children=[
                    dbc.ModalHeader(
                        dbc.ModalTitle(id="modal-title"),
                        close_button=True,
                    ),
                    dbc.ModalBody(
                        dbc.Form(
                            [
                                dbc.Row(
                                    [
                                        dbc.Col(
                                            [
                                                dbc.Label(
                                                    "Code", html_for="modal-code"
                                                ),
                                                dbc.Input(
                                                    id="modal-code",
                                                    type="text",
                                                    placeholder="Unique identifier",
                                                    required=True,
                                                ),
                                            ],
                                            width=6,
                                        ),
                                        dbc.Col(
                                            [
                                                dbc.Label(
                                                    "Name", html_for="modal-name"
                                                ),
                                                dbc.Input(
                                                    id="modal-name",
                                                    type="text",
                                                    placeholder="Descriptive name",
                                                    required=True,
                                                ),
                                            ],
                                            width=6,
                                        ),
                                    ],
                                    className="mb-3",
                                ),
                                dbc.Row(
                                    [
                                        dbc.Col(
                                            [
                                                dbc.Label(
                                                    "Provider",
                                                    html_for="modal-provider",
                                                ),
                                                dbc.Input(
                                                    id="modal-provider",
                                                    type="text",
                                                    placeholder="Data provider",
                                                ),
                                            ],
                                            width=6,
                                        ),
                                        dbc.Col(
                                            [
                                                dbc.Label(
                                                    "Asset Class",
                                                    html_for="modal-asset_class",
                                                ),
                                                dbc.Select(
                                                    id="modal-asset_class",
                                                    options=[
                                                        {
                                                            "label": "Equity",
                                                            "value": "equity",
                                                        },
                                                        {
                                                            "label": "Fixed Income",
                                                            "value": "fixed_income",
                                                        },
                                                        {
                                                            "label": "Commodity",
                                                            "value": "commodity",
                                                        },
                                                        {
                                                            "label": "Currency",
                                                            "value": "currency",
                                                        },
                                                        {
                                                            "label": "Other",
                                                            "value": "other",
                                                        },
                                                    ],
                                                ),
                                            ],
                                            width=6,
                                        ),
                                    ],
                                    className="mb-3",
                                ),
                            ]
                        )
                    ),
                    dbc.ModalFooter(
                        [
                            dbc.Button(
                                "Delete",
                                id="delete-button",
                                color="danger",
                                outline=True,
                                className="me-auto",
                                disabled=True,
                            ),
                            dbc.Button(
                                "Cancel",
                                id="cancel-button",
                                color="secondary",
                                className="me-2",
                            ),
                            dbc.Button("Save", id="save-button", color="primary"),
                        ]
                    ),
                ],
            ),
        ],
    )

    # Search functionality
    @app.callback(
        Output("ts-table", "data"),
        Input("search-input", "value"),
    )
    def update_table(search_query):
        return search_by_name(search_query)

    # Clear search input
    @app.callback(
        Output("search-input", "value"),
        Input("clear-search", "n_clicks"),
    )
    def clear_search(n_clicks):
        if n_clicks:
            return ""
        raise dash.exceptions.PreventUpdate

    # Modal open/close and pre-fill logic
    @app.callback(
        Output("ts-modal", "is_open"),
        Output("modal-title", "children"),
        Output("modal-code", "value"),
        Output("modal-name", "value"),
        Output("modal-provider", "value"),
        Output("modal-asset_class", "value"),
        Output("modal-code", "disabled"),
        Output("delete-button", "disabled"),
        Input("open-modal", "n_clicks"),
        Input("cancel-button", "n_clicks"),
        Input("save-button", "n_clicks"),
        Input("ts-table", "selected_rows"),
        State("ts-table", "data"),
        State("ts-modal", "is_open"),
        prevent_initial_call=True,
    )
    def toggle_modal(
        open_click, cancel_click, save_click, selected_rows, table_data, is_open
    ):
        ctx = callback_context
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

        # Handle modal opening
        if trigger_id == "open-modal":
            return True, "Create New Timeseries", "", "", "", "", False, True

        # Handle row selection for editing
        elif trigger_id == "ts-table" and selected_rows:
            row = table_data[selected_rows[0]]
            return (
                True,
                f"Edit Timeseries: {row['code']}",
                row.get("code", ""),
                row.get("name", ""),
                row.get("provider", ""),
                row.get("asset_class", ""),
                True,  # Disable code field for editing
                False,  # Enable delete button
            )

        # Handle modal closing
        elif trigger_id in ["cancel-button", "save-button"]:
            return False, "", "", "", "", "", False, True

        return is_open, "", "", "", "", "", False, True

    # Save handler
    @app.callback(
        Output("ts-table", "data", allow_duplicate=True),
        Output("status-alert", "is_open"),
        Output("status-alert", "children"),
        Output("status-alert", "color"),
        Input("save-button", "n_clicks"),
        State("modal-code", "value"),
        State("modal-name", "value"),
        State("modal-provider", "value"),
        State("modal-asset_class", "value"),
        State("search-input", "value"),
        prevent_initial_call=True,
    )
    def save_timeseries(n_clicks, code, name, provider, asset_class, search_query):
        if not code or not name:
            return (
                search_by_name(search_query),
                True,
                "Code and Name are required fields!",
                "danger",
            )

        doc = {
            "code": code.strip(),
            "name": name.strip(),
            "provider": provider.strip() if provider else None,
            "asset_class": asset_class.strip() if asset_class else None,
        }

        try:
            # Update if exists
            existing = Timeseries.find_one({"code": code}).run()
            if existing:
                Timeseries.find_one_and_update({"code": code}, {"$set": doc}).run()
                message = f"Successfully updated timeseries: {code}"
            else:
                Timeseries(**doc).insert().run()
                message = f"Successfully created new timeseries: {code}"

            return search_by_name(search_query), True, message, "success"

        except Exception as e:
            return (
                search_by_name(search_query),
                True,
                f"Error saving timeseries: {str(e)}",
                "danger",
            )

    # Delete handler
    @app.callback(
        Output("ts-table", "data", allow_duplicate=True),
        Output("status-alert", "is_open", allow_duplicate=True),
        Output("status-alert", "children", allow_duplicate=True),
        Output("status-alert", "color", allow_duplicate=True),
        Input("delete-button", "n_clicks"),
        State("modal-code", "value"),
        State("search-input", "value"),
        prevent_initial_call=True,
    )
    def delete_timeseries(n_clicks, code, search_query):
        if not n_clicks:
            raise dash.exceptions.PreventUpdate

        try:
            Timeseries.find_one_and_delete({"code": code}).run()
            return (
                search_by_name(search_query),
                True,
                f"Successfully deleted timeseries: {code}",
                "success",
            )
        except Exception as e:
            return (
                search_by_name(search_query),
                True,
                f"Error deleting timeseries: {str(e)}",
                "danger",
            )

    return app


if __name__ == "__main__":
    app = create_dash_app()
    app.run_server(debug=True, port=8050)
