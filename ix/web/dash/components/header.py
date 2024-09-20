import dash_mantine_components as dmc
from dash_iconify import DashIconify
from dash import Output, Input, clientside_callback


def logo():

    return [
        dmc.GridCol(
            dmc.Group(
                [
                    dmc.Anchor(
                        "InvestmentX",
                        size="xl",
                        href="/web",
                        fw=600,
                        underline=False,
                    ),
                    dmc.ActionIcon(
                        DashIconify(
                            icon="radix-icons:hamburger-menu",
                            width=25,
                        ),
                        id="drawer-hamburger-button",
                        variant="transparent",
                        size="lg",
                        hiddenFrom="sm",
                    ),
                    dmc.ActionIcon(
                        [
                            DashIconify(
                                icon="radix-icons:sun",
                                width=25,
                                id="light-theme-icon",
                            ),
                            DashIconify(
                                icon="radix-icons:moon",
                                width=25,
                                id="dark-theme-icon",
                            ),
                        ],
                        variant="transparent",
                        color="yellow",
                        id="color-scheme-toggle",
                        size="lg",
                    ),
                ]
            ),
            span="content",
        ),
        dmc.GridCol(
            dmc.Group(
                [
                    # Add any additional content you want on the right side here
                    # Example: dmc.Text("Some text on the right"),
                ]
            ),
            span="content",
        ),
    ]


def layout():
    return dmc.AppShellHeader(
        px=25,
        children=[
            dmc.Stack(
                justify="center",
                h=70,
                children=[
                    dmc.Grid(
                        justify="space-between",
                        align="center",
                        children=logo(),
                    )
                ],
            )
        ],
    )


clientside_callback(
    """function(n_clicks) { return true }""",
    Output("components-navbar-drawer", "opened"),
    Input("drawer-hamburger-button", "n_clicks"),
    prevent_initial_call=True,
)
