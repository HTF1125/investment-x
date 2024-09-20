from dash import html
from dash_iconify import DashIconify
import dash_mantine_components as dmc


def get_icon(icon):
    return DashIconify(icon=icon, height=16)


def create_navbar_drawer(data):
    return dmc.Drawer(
        id="components-navbar-drawer",
        overlayProps={"opacity": 0.55, "blur": 3},
        zIndex=1500,
        offset=10,
        radius="md",
        withCloseButton=False,
        size="75%",
        # children=create_content(data),
        trapFocus=False,
    )


def create_content(data):

    links = []

    for entry in data:
        link = dmc.NavLink(
            label=entry["name"],
            href=entry["relative_path"],
            h=32,
            className="navbar-link",
            pl=30,
        )
        links.append(link)

    return dmc.ScrollArea(
        offsetScrollbars=True,
        type="scroll",
        style={"height": "100%"},
        children=dmc.Stack(gap=0, children=[*links, dmc.Space(h=90)], px=25),
    )


def create_navbar(data):
    return dmc.AppShellNavbar(
        children=html.Div(
            children=create_content(data),
        )
    )


def create_navbar_drawer(data):
    return dmc.Drawer(
        id="components-navbar-drawer",
        overlayProps={"opacity": 0.55, "blur": 3},
        zIndex=1500,
        offset=10,
        radius="md",
        withCloseButton=False,
        size="75%",
        children=create_content(data),
        trapFocus=False,
    )
