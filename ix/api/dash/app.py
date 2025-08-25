import os
import flask
import pandas as pd
from dash import Dash, dcc, html, dash_table, callback_context
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
from ix.db import Timeseries
import dash


from bson.regex import Regex
import re



VISIBLE_COLS = [
    "code","name","provider","asset_class","category","frequency","unit","scale",
    "currency","country","start","end","num_data","source","source_code","parent_id","remark"
]
READONLY_COLS = {"code","start","end","num_data"}  # read-only in grid

def create_dash_app(requests_pathname_prefix: str = None) -> Dash:
    server = flask.Flask(__name__)
    server.secret_key = os.environ.get("SECRET_KEY", "secret")

    app = Dash(
        __name__,
        server=server,
        external_stylesheets=[dbc.themes.BOOTSTRAP],
        requests_pathname_prefix=requests_pathname_prefix,
    )

    # ---------- helpers ----------
    def fetch_timeseries():
        try:
            docs = [doc.dict() for doc in Timeseries.find().run()]
            # keep only known fields in a stable order
            return [{k: d.get(k) for k in VISIBLE_COLS} for d in docs]
        except Exception as e:
            print(f"Error fetching timeseries: {e}")
            return []

    def search_by_name(name_query: str = None):
        try:
            return search_timeseries(name_query)
        except Exception as e:
            print(f"Error searching timeseries: {e}")
            return fetch_timeseries()


    def search_timeseries(query: str):
        if not query or not query.strip():
            return [doc.dict() for doc in Timeseries.find().run()]

        # Normalize and split into tokens
        tokens = re.split(r"\s+", query.strip())

        # Build Mongo regex for each token (case-insensitive, partial match)
        regex_tokens = [Regex(f".*{re.escape(tok)}.*", "i") for tok in tokens]

        # Searchable fields
        fields = [
            "code", "name", "provider", "source", "source_code",
            "asset_class", "category", "currency", "country",
            "unit", "frequency", "remark"
        ]

        # For each token, build an OR over all fields
        and_clauses = []
        for rt in regex_tokens:
            or_clauses = [{field: rt} for field in fields]
            and_clauses.append({"$or": or_clauses})

        mongo_query = {"$and": and_clauses}

        return [doc.dict() for doc in Timeseries.find(mongo_query).run()]


    # initial data/columns once
    initial_rows = fetch_timeseries()
    initial_cols = [
        {
            "name": c.capitalize().replace("_", " "),
            "id": c,
            "editable": c not in READONLY_COLS,
            "type": "numeric" if c in ("scale","num_data") else "text",
        }
        for c in VISIBLE_COLS
    ]

    # ---------- layout ----------
    app.layout = dbc.Container(
        fluid=True,
        className="p-0",
        style={"minHeight": "100vh", "display": "flex", "flexDirection": "column"},
        children=[
            # navbar
            dbc.NavbarSimple(
                brand="Timeseries Manager",
                color="dark",
                dark=True,
                className="mb-3",
            ),
            # controls row
            dbc.Row(
                [
                    dbc.Col(
                        dbc.InputGroup(
                            [
                                dbc.InputGroupText("Search"),
                                dbc.Input(
                                    id="search-input",
                                    type="text",
                                    placeholder="Enter timeseries name…",
                                    debounce=True,
                                ),
                                dbc.Button("Clear", id="clear-search", color="secondary", outline=True),
                            ]
                        ),
                        xs=12, md=8, lg=9, className="px-3"
                    ),
                    dbc.Col(
                        html.Div(
                            [
                                dbc.Button("New Timeseries", id="open-modal", color="primary", className="me-2"),
                                dbc.Button("Export CSV", id="export-csv", color="secondary", outline=True),
                            ],
                            className="d-flex justify-content-end"
                        ),
                        xs=12, md=4, lg=3, className="px-3 mt-2 mt-md-0"
                    ),
                ],
                className="g-0 mb-2",
            ),
            # status
            dbc.Alert(id="status-alert", is_open=False, duration=3500, className="mx-3 mb-2"),
            # table wrapper that fills the remaining viewport height
            html.Div(
                id="table-wrap",
                className="mx-3 mb-3",
                style={
                    "flex": "1 1 auto",
                    "minHeight": 0,  # critical for flex overflow
                },
                children=[
                    dbc.Spinner(
                        dash_table.DataTable(
                            id="ts-table",
                            columns=initial_cols,
                            data=initial_rows,
                            page_action="none",            # we’ll scroll instead of paging
                            sort_action="native",
                            filter_action="none",
                            row_selectable="single",
                            selected_rows=[],
                            fixed_rows={"headers": True},  # sticky header
                            virtualization=True,           # smoother scroll for big data
                            style_table={
                                # lock within the viewport:
                                # header(56) + controls(~96) + margins ≈ 170; give cushion
                                "height": "calc(100vh - 220px)",
                                "overflowY": "auto",
                                "overflowX": "auto",
                                "border": "1px solid #dee2e6",
                            },
                            style_cell={
                                # clean overflow + hover tooltips
                                "whiteSpace": "nowrap",
                                "textOverflow": "ellipsis",
                                "overflow": "hidden",
                                "maxWidth": 240,
                                "fontSize": 13,
                                "padding": "8px",
                            },
                            style_header={
                                "backgroundColor": "#f8f9fa",
                                "fontWeight": "600",
                                "borderBottom": "1px solid #dee2e6",
                            },
                            style_data_conditional=[
                                # row hover
                                {"if": {"state": "active"}, "backgroundColor": "#f1f3f5"},
                                # selected row
                                {"if": {"state": "selected"}, "backgroundColor": "#e7f1ff"},
                            ],
                            tooltip_delay=300,
                            tooltip_duration=None,
                            tooltip_data=[
                                {c: {"type": "text", "value": str(r.get(c) or "")} for c in VISIBLE_COLS}
                                for r in (initial_rows or [])
                            ],
                        ),
                        color="primary",
                    )
                ],
            ),
            # modal
            dbc.Modal(
                id="ts-modal",
                is_open=False,
                size="lg",
                children=[
                    dbc.ModalHeader(dbc.ModalTitle(id="modal-title"), close_button=True),
                    dbc.ModalBody(
                        dbc.Form(
                            [
                                dbc.Row(
                                    [
                                        dbc.Col(
                                            [
                                                dbc.Label("Code", html_for="modal-code"),
                                                dbc.Input(id="modal-code", type="text", placeholder="Unique identifier", required=True),
                                            ],
                                            md=6,
                                        ),
                                        dbc.Col(
                                            [
                                                dbc.Label("Name", html_for="modal-name"),
                                                dbc.Input(id="modal-name", type="text", placeholder="Descriptive name", required=True),
                                            ],
                                            md=6,
                                        ),
                                    ],
                                    className="mb-3",
                                ),
                                dbc.Row(
                                    [
                                        dbc.Col(
                                            [
                                                dbc.Label("Provider", html_for="modal-provider"),
                                                dbc.Input(id="modal-provider", type="text", placeholder="Data provider"),
                                            ],
                                            md=6,
                                        ),
                                        dbc.Col(
                                            [
                                                dbc.Label("Asset Class", html_for="modal-asset_class"),
                                                dbc.Select(
                                                    id="modal-asset_class",
                                                    options=[
                                                        {"label": "Equity","value": "equity"},
                                                        {"label": "Fixed Income","value": "fixed_income"},
                                                        {"label": "Commodity","value": "commodity"},
                                                        {"label": "Currency","value": "currency"},
                                                        {"label": "Other","value": "other"},
                                                    ],
                                                ),
                                            ],
                                            md=6,
                                        ),
                                    ],
                                    className="mb-3",
                                ),
                            ]
                        )
                    ),
                    dbc.ModalFooter(
                        [
                            dbc.Button("Delete", id="delete-button", color="danger", outline=True, className="me-auto", disabled=True),
                            dbc.Button("Cancel", id="cancel-button", color="secondary", className="me-2"),
                            dbc.Button("Save", id="save-button", color="primary"),
                        ]
                    ),
                ],
            ),
            # csv download
            dcc.Download(id="download-csv"),
        ],
    )

    # tiny CSS fix for tooltips to wrap long text (applies app-wide)
    app.css.append_css({
        "external_url": "https://cdn.jsdelivr.net/gh/plotly/dash-table@master/tests/selenium/assets/dash_table.css"
    })

    # ---------- callbacks ----------
    @app.callback(Output("ts-table", "data"), Output("ts-table", "tooltip_data"),
                  Input("search-input", "value"))
    def update_table(search_query):
        rows = search_by_name(search_query)
        tooltips = [{c: {"type": "text", "value": str(r.get(c) or "")} for c in VISIBLE_COLS} for r in rows]
        return rows, tooltips

    @app.callback(Output("search-input", "value"), Input("clear-search", "n_clicks"))
    def clear_search(n_clicks):
        if n_clicks:
            return ""
        raise dash.exceptions.PreventUpdate

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
    def toggle_modal(open_click, cancel_click, save_click, selected_rows, table_data, is_open):
        ctx = callback_context
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

        if trigger_id == "open-modal":
            return True, "Create New Timeseries", "", "", "", "", False, True
        elif trigger_id == "ts-table" and selected_rows:
            row = table_data[selected_rows[0]]
            return (
                True,
                f"Edit Timeseries: {row.get('code','')}",
                row.get("code",""),
                row.get("name",""),
                row.get("provider",""),
                row.get("asset_class",""),
                True,
                False,
            )
        elif trigger_id in ["cancel-button","save-button"]:
            return False, "", "", "", "", "", False, True
        return is_open, "", "", "", "", "", False, True

    @app.callback(
        Output("ts-table", "data", allow_duplicate=True),
        Output("ts-table", "tooltip_data", allow_duplicate=True),
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
            rows = search_by_name(search_query)
            tips = [{c: {"type": "text", "value": str(r.get(c) or "")} for c in VISIBLE_COLS} for r in rows]
            return rows, tips, True, "Code and Name are required fields!", "danger"

        doc = {
            "code": code.strip(),
            "name": name.strip(),
            "provider": provider.strip() if provider else None,
            "asset_class": asset_class.strip() if asset_class else None,
        }
        try:
            existing = Timeseries.find_one({"code": code}).run()
            if existing:
                Timeseries.find_one_and_update({"code": code}, {"$set": doc}).run()
                msg = f"Successfully updated timeseries: {code}"
            else:
                Timeseries(**doc).insert().run()
                msg = f"Successfully created new timeseries: {code}"
            rows = search_by_name(search_query)
            tips = [{c: {"type": "text", "value": str(r.get(c) or "")} for c in VISIBLE_COLS} for r in rows]
            return rows, tips, True, msg, "success"
        except Exception as e:
            rows = search_by_name(search_query)
            tips = [{c: {"type": "text", "value": str(r.get(c) or "")} for c in VISIBLE_COLS} for r in rows]
            return rows, tips, True, f"Error saving timeseries: {e}", "danger"

    @app.callback(
        Output("ts-table", "data", allow_duplicate=True),
        Output("ts-table", "tooltip_data", allow_duplicate=True),
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
            rows = search_by_name(search_query)
            tips = [{c: {"type": "text", "value": str(r.get(c) or "")} for c in VISIBLE_COLS} for r in rows]
            return rows, tips, True, f"Successfully deleted timeseries: {code}", "success"
        except Exception as e:
            rows = search_by_name(search_query)
            tips = [{c: {"type": "text", "value": str(r.get(c) or "")} for c in VISIBLE_COLS} for r in rows]
            return rows, tips, True, f"Error deleting timeseries: {e}", "danger"

    @app.callback(
        Output("download-csv", "data"),
        Input("export-csv", "n_clicks"),
        State("ts-table", "data"),
        prevent_initial_call=True,
    )
    def export_csv(n, rows):
        df = pd.DataFrame(rows)
        return dcc.send_data_frame(df.to_csv, "timeseries.csv", index=False)

    return app

if __name__ == "__main__":
    app = create_dash_app()
    app.run_server(debug=True, port=8050)
