"components"

from dash import html


def Grid(children: ..., gap: str = "24px", marginBottom: str = "40px"):
    return html.Div(
        style={
            "display": "grid",
            "gridTemplateColumns": "repeat(auto-fit, minmax(600px, 1fr))",
            "gap": gap,
            "marginBottom": marginBottom,
        },
        children=children,
    )


def Card(children: ...):
    return html.Div(
        style={
            "background": "linear-gradient(135deg, rgba(30, 41, 59, 0.95), rgba(15, 23, 42, 0.9))",
            "borderRadius": "18px",
            "padding": "24px",
            "boxShadow": "0 8px 32px rgba(0,0,0,0.25), 0 2px 16px rgba(0,0,0,0.1)",
            "border": "1px solid rgba(148, 163, 184, 0.15)",
            "backdropFilter": "saturate(180%) blur(20px)",
            "transition": "all 0.4s cubic-bezier(0.4, 0, 0.2, 1)",
            "height": "100%",
            "display": "flex",
            "flexDirection": "column",
            "position": "relative",
            "overflow": "hidden",
        },
        children=[
            # Subtle card decoration
            html.Div(
                style={
                    "position": "absolute",
                    "top": "-30%",
                    "right": "-30%",
                    "width": "80px",
                    "height": "80px",
                    "background": "radial-gradient(circle, rgba(59, 130, 246, 0.1) 0%, transparent 70%)",
                    "borderRadius": "50%",
                    "pointerEvents": "none",
                }
            ),
            html.Div(
                style={
                    "flex": "1",
                    "background": "rgba(15, 23, 42, 0.7)",
                    "borderRadius": "14px",
                    "padding": "16px",
                    "position": "relative",
                    "zIndex": 1,
                    "border": "1px solid rgba(148, 163, 184, 0.08)",
                },
                children=[children],
            ),
        ],
    )
