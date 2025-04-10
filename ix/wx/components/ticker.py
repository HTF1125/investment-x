from dash import html, dcc, Input, Output, State, ctx, callback, no_update, ALL, MATCH
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
from ix.db.models import Ticker, Source, ValidSources
from functools import lru_cache
import time

def TickerEditor():
    # Common styling
    modal_style = {"maxWidth": "95vw", "width": "1200px"}
    input_style = {"marginBottom": "10px"}

    layout = html.Div(
        [
            html.H4("Ticker Management", className="mb-4"),
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Button(
                            "Add New Ticker",
                            id="te-open-modal",
                            color="primary",
                            className="me-2"
                        ),
                        width="auto"
                    ),
                    dbc.Col(
                        dbc.Input(
                            id="te-search",
                            placeholder="Search tickers...",
                            type="text",
                            className="mb-3",
                            debounce=True  # Add debounce to reduce unnecessary updates
                        ),
                        width=4
                    )
                ],
                className="mb-3 align-items-center"
            ),
            dbc.Spinner(html.Div(id="te-ticker-table"), color="primary"),
            dbc.Toast(
                id="te-status",
                header="Notification",
                is_open=False,
                dismissable=True,
                duration=4000,
                className="position-fixed top-0 end-0 m-3",
                style={"zIndex": 1000}
            ),
            dbc.Modal(
                [
                    dbc.ModalHeader(dbc.ModalTitle("Create / Edit Ticker")),
                    dbc.ModalBody(
                        [
                            dbc.Alert(
                                "Code is required and must be unique",
                                color="info",
                                className="mb-3"
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        dbc.Input(
                                            id="te-code",
                                            placeholder="Code (e.g., AAPL)",
                                            className="mb-2",
                                            style=input_style
                                        ),
                                        md=4
                                    ),
                                    dbc.Col(
                                        dbc.Input(
                                            id="te-name",
                                            placeholder="Name (e.g., Apple Inc.)",
                                            className="mb-2",
                                            style=input_style
                                        ),
                                        md=8
                                    ),
                                ],
                                className="mb-2",
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        dbc.Input(
                                            id="te-category",
                                            placeholder="Category (e.g., Tech)",
                                            className="mb-2",
                                            style=input_style
                                        ),
                                        md=4
                                    ),
                                    dbc.Col(
                                        dbc.Select(
                                            id="te-asset-class",
                                            placeholder="Asset Class",
                                            options=[
                                                {"label": "Stock", "value": "Stock"},
                                                {"label": "ETF", "value": "ETF"},
                                                {"label": "Bond", "value": "Bond"},
                                                {"label": "Commodity", "value": "Commodity"},
                                                {"label": "Currency", "value": "Currency"},
                                                {"label": "Crypto", "value": "Crypto"},
                                                {"label": "Index", "value": "Index"},
                                            ],
                                            className="mb-2",
                                            style=input_style
                                        ),
                                        md=4
                                    ),
                                    dbc.Col(
                                        dbc.Select(
                                            id="te-frequency",
                                            placeholder="Frequency",
                                            options=[
                                                {"label": "Daily", "value": "Daily"},
                                                {"label": "Weekly", "value": "Weekly"},
                                                {"label": "Monthly", "value": "Monthly"},
                                                {"label": "Quarterly", "value": "Quarterly"},
                                                {"label": "Annual", "value": "Annual"},
                                            ],
                                            className="mb-2",
                                            style=input_style
                                        ),
                                        md=4
                                    ),
                                ],
                                className="mb-3",
                            ),
                            dbc.Card(
                                [
                                    dbc.CardHeader("Data Sources"),
                                    dbc.CardBody(
                                        [
                                            dbc.Row(
                                                [
                                                    dbc.Col(
                                                        dbc.Input(
                                                            id="te-source-field",
                                                            placeholder="Field (e.g., price)",
                                                            className="mb-2"
                                                        ),
                                                        md=3
                                                    ),
                                                    dbc.Col(
                                                        dcc.Dropdown(
                                                            id="te-source-type",
                                                            options=[
                                                                {"label": s, "value": s}
                                                                for s in ValidSources.__args__
                                                            ],
                                                            placeholder="Source Type",
                                                            className="mb-2"
                                                        ),
                                                        md=3
                                                    ),
                                                    dbc.Col(
                                                        dbc.Input(
                                                            id="te-source-ticker",
                                                            placeholder="Source Ticker",
                                                            className="mb-2"
                                                        ),
                                                        md=3
                                                    ),
                                                    dbc.Col(
                                                        dbc.Input(
                                                            id="te-source-field-name",
                                                            placeholder="Source Field",
                                                            className="mb-2"
                                                        ),
                                                        md=3
                                                    ),
                                                ],
                                                className="mb-2",
                                            ),
                                            dbc.Row(
                                                dbc.Col(
                                                    dbc.Button(
                                                        "Add Source",
                                                        id="te-add-source",
                                                        color="primary",
                                                        className="w-100"
                                                    ),
                                                    width=12
                                                )
                                            ),
                                            html.Div(
                                                id="te-source-list",
                                                className="mt-3"
                                            )
                                        ]
                                    )
                                ],
                                className="mb-3"
                            )
                        ]
                    ),
                    dbc.ModalFooter(
                        [
                            dbc.Button(
                                "Save",
                                id="te-save",
                                color="success",
                                className="me-2",
                                n_clicks=0  # Initialize n_clicks
                            ),
                            dbc.Button(
                                "Cancel",
                                id="te-close-modal",
                                color="secondary"
                            ),
                        ]
                    )
                ],
                id="te-modal",
                is_open=False,
                size="xl",
                style=modal_style
            ),
            dcc.Store(id="te-current-ticker"),  # Store for edit mode
            dcc.Store(id="te-source-list-store"),  # Store for source list state
        ],
        className="p-4"
    )

    # Cache the ticker table to improve performance
    @lru_cache(maxsize=32)
    def get_tickers(search_term=None):
        start_time = time.time()
        query = {}
        if search_term:
            query["$or"] = [
                {"code": {"$regex": search_term, "$options": "i"}},
                {"name": {"$regex": search_term, "$options": "i"}},
                {"category": {"$regex": search_term, "$options": "i"}}
            ]
        result = list(Ticker.find(query).limit(20).sort("code"))
        print(f"get_tickers took {time.time() - start_time:.4f} seconds")
        return result

    @callback(
        Output("te-modal", "is_open"),
        Output("te-current-ticker", "data"),
        Output("te-source-list-store", "data"),
        Output("te-code", "value"),
        Output("te-name", "value"),
        Output("te-category", "value"),
        Output("te-asset-class", "value"),
        Output("te-frequency", "value"),
        Output("te-source-list", "children", allow_duplicate=True),
        Input("te-open-modal", "n_clicks"),
        Input({"type": "te-edit-ticker", "index": ALL}, "n_clicks"),
        State("te-modal", "is_open"),
        prevent_initial_call=True
    )
    def toggle_modal(new_click, edit_clicks, is_open):
        triggered_id = ctx.triggered_id

        if not triggered_id:
            raise PreventUpdate

        if triggered_id == "te-open-modal":
            # Reset form for new ticker
            return True, None, [], "", "", "", "", "", []

        if isinstance(triggered_id, dict) and triggered_id["type"] == "te-edit-ticker":
            # Load existing ticker for editing
            ticker_code = triggered_id["index"]
            ticker = Ticker.find_one(Ticker.code == ticker_code).run()
            if ticker:
                # Convert sources to serializable format for dcc.Store
                sources_data = [src.dict() for src in ticker.fields] if ticker.fields else []

                # Create source list display
                source_list_display = [
                    dbc.ListGroupItem(
                        [
                            html.Div(
                                [
                                    html.Strong(f"Field: "),
                                    s.field,
                                    html.Br(),
                                    html.Strong(f"Source: "),
                                    s.source,
                                    html.Br(),
                                    html.Strong(f"Ticker: "),
                                    s.source_ticker,
                                    html.Br(),
                                    html.Strong(f"Field: "),
                                    s.source_field or "-"
                                ],
                                className="d-inline-block me-2"
                            ),
                            dbc.Button(
                                "×",
                                id={"type": "te-remove-source", "index": i},
                                color="danger",
                                size="sm",
                                className="float-end"
                            )
                        ],
                        className="mb-1"
                    )
                    for i, s in enumerate(ticker.fields or [])
                ]

                return (
                    True,
                    ticker.code,
                    sources_data,
                    ticker.code,
                    ticker.name or "",
                    ticker.category or "",
                    ticker.asset_class or "",
                    ticker.frequency or "",
                    dbc.ListGroup(source_list_display, flush=True)
                )

        return not is_open, no_update, no_update, no_update, no_update, no_update, no_update, no_update, no_update

    @callback(
        Output("te-source-list", "children"),
        Output("te-source-field", "value"),
        Output("te-source-type", "value"),
        Output("te-source-ticker", "value"),
        Output("te-source-field-name", "value"),
        Output("te-source-list-store", "data", allow_duplicate=True),
        Input("te-add-source", "n_clicks"),
        Input({"type": "te-remove-source", "index": ALL}, "n_clicks"),
        State("te-source-field", "value"),
        State("te-source-type", "value"),
        State("te-source-ticker", "value"),
        State("te-source-field-name", "value"),
        State("te-source-list-store", "data"),
        prevent_initial_call=True
    )
    def manage_sources(add_click, remove_clicks, field, source_type, ticker, source_field, current_sources):
        triggered_id = ctx.triggered_id
        sources = current_sources.copy() if current_sources else []

        # Handle source removal
        if isinstance(triggered_id, dict) and triggered_id["type"] == "te-remove-source":
            index = triggered_id["index"]
            if index < len(sources):
                sources.pop(index)

        # Handle source addition
        elif triggered_id == "te-add-source":
            if not all([field, source_type, ticker]):
                raise PreventUpdate

            new_src = {
                "field": field,
                "source": source_type,
                "source_ticker": ticker,
                "source_field": source_field or ""
            }
            sources.append(new_src)

            # Clear the input fields
            field, source_type, ticker, source_field = "", None, "", ""

        # Display current sources
        source_list_display = [
            dbc.ListGroupItem(
                [
                    html.Div(
                        [
                            html.Strong(f"Field: "),
                            s["field"],
                            html.Br(),
                            html.Strong(f"Source: "),
                            s["source"],
                            html.Br(),
                            html.Strong(f"Ticker: "),
                            s["source_ticker"],
                            html.Br(),
                            html.Strong(f"Field: "),
                            s.get("source_field") or "-"
                        ],
                        className="d-inline-block me-2"
                    ),
                    dbc.Button(
                        "×",
                        id={"type": "te-remove-source", "index": i},
                        color="danger",
                        size="sm",
                        className="float-end"
                    )
                ],
                className="mb-1"
            )
            for i, s in enumerate(sources)
        ]

        return dbc.ListGroup(source_list_display, flush=True), field, source_type, ticker, source_field, sources

    @callback(
        Output("te-status", "is_open"),
        Output("te-status", "children"),
        Output("te-status", "header"),
        Output("te-modal", "is_open", allow_duplicate=True),
        Output("te-ticker-table", "children", allow_duplicate=True),
        Output("te-source-list-store", "data", allow_duplicate=True),
        Input("te-save", "n_clicks"),
        State("te-code", "value"),
        State("te-name", "value"),
        State("te-category", "value"),
        State("te-asset-class", "value"),
        State("te-frequency", "value"),
        State("te-source-list-store", "data"),
        State("te-current-ticker", "data"),
        prevent_initial_call=True
    )
    def save_ticker(save_clicks, code, name, category, asset_class, frequency, sources_data, current_ticker_code):
        if not save_clicks or not code:
            return True, "Code is required.", "Error", no_update, no_update, no_update

        # Convert sources data to Source objects
        fields = [Source(**src) for src in sources_data] if sources_data else []

        ticker_data = {
            "code": code,
            "name": name,
            "category": category,
            "asset_class": asset_class,
            "frequency": frequency,
            "fields": fields
        }

        if current_ticker_code:
            # Update existing ticker
            ticker = Ticker.find_one(Ticker.code == current_ticker_code).run()
            if ticker:
                ticker.update(**ticker_data)
                message = f"Updated ticker: {code}"
            else:
                return True, "Ticker not found.", "Error", no_update, no_update, no_update
        else:
            # Create new ticker
            if Ticker.find_one(Ticker.code == code).run():
                return True, f"Ticker with code {code} already exists.", "Error", no_update, no_update, no_update

            ticker = Ticker(**ticker_data).create()
            message = f"Created new ticker: {code}"

        # Clear cache to refresh data
        get_tickers.cache_clear()

        return (
            True,
            message,
            "Success",
            False,
            render_ticker_table(),
            []  # Clear the source list store
        )

    def render_ticker_table(search_term=None):
        try:
            tickers = get_tickers(search_term)
        except Exception as e:
            print(f"Error loading tickers: {e}")
            tickers = []
            get_tickers.cache_clear()

        if not tickers:
            return dbc.Alert("No tickers found", color="info")

        return dbc.Table(
            [
                html.Thead(
                    html.Tr([
                        html.Th("Code"),
                        html.Th("Name"),
                        html.Th("Category"),
                        html.Th("Asset Class"),
                        html.Th("Actions")
                    ])
                ),
                html.Tbody([
                    html.Tr([
                        html.Td(t.code),
                        html.Td(t.name or "-"),
                        html.Td(t.category or "-"),
                        html.Td(t.asset_class or "-"),
                        html.Td(
                            dbc.Button(
                                "Edit",
                                id={"type": "te-edit-ticker", "index": t.code},
                                color="primary",
                                size="sm",
                                className="me-1"
                            )
                        )
                    ])
                    for t in tickers
                ])
            ],
            bordered=True,
            striped=True,
            hover=True,
            responsive=True,
            className="mt-3"
        )

    @callback(
        Output("te-ticker-table", "children"),
        Input("te-open-modal", "n_clicks"),
        Input("te-search", "value"),
        Input("te-save", "n_clicks"),
        prevent_initial_call=False
    )
    def load_ticker_table(_, search_term=None, __=None):
        return render_ticker_table(search_term)

    return layout
