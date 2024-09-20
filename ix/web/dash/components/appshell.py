from . import header, navbar, main, aside


from dash import dcc
import dash_mantine_components as dmc


def layout(data):

    print(data)

    return dmc.MantineProvider(
        children=[
            dcc.Location(id="url", refresh="callback-nav"),
            dmc.NotificationProvider(zIndex=2000),
            dmc.AppShell(
                children=[
                    header.layout(),
                    navbar.create_navbar(data),
                    navbar.create_navbar_drawer(data),
                    aside.layout(),
                    main.layout(),
                ],
                header={"height": 70},
                padding="xl",
                zIndex=1400,
                navbar={
                    "width": 200,
                    "breakpoint": "sm",
                    "collapsed": {"mobile": True},
                },
                aside={
                    "width": 300,
                    "breakpoint": "xl",
                    "collapsed": {"desktop": False, "mobile": True},
                },
            ),
        ],
    )
