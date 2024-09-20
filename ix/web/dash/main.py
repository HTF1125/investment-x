from dash import Dash, _dash_renderer, page_registry

import dash_mantine_components as dmc

_dash_renderer._set_react_version("18.2.0")

from .components import appshell

def get_app(pathname: str = ""):

    app = Dash(
        __name__,
        use_pages=True,
        external_stylesheets=dmc.styles.ALL,
        requests_pathname_prefix=pathname + "/",
    )

    app.layout = appshell.layout(data=page_registry.values())
    return app


if __name__ == "__main__":
    get_app().run(debug=True)
