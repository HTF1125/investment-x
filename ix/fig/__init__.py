class Fig:

    __name__ = ""

    __layout__ = dict(
        title=dict(
            text="",
            x=0.05,
            font=dict(size=12, family="Arial Black", color="#FFFFFF"),
        ),
        xaxis=dict(
            tickformat="%b<br>%Y",
            gridcolor="rgba(255,255,255,0.2)",
            zeroline=False,
            showline=True,
            linecolor="rgba(255,255,255,0.4)",
            mirror=True,
            tickangle=0,
            tickfont=dict(color="#FFFFFF"),
        ),
        yaxis=dict(
            title=dict(text="", font=dict(color="#FFFFFF")),
            gridcolor="rgba(255,255,255,0.2)",
            zeroline=False,
            showline=True,
            linecolor="rgba(255,255,255,0.4)",
            mirror=True,
            tickfont=dict(color="#FFFFFF"),
        ),
        yaxis2=dict(
            title=dict(text="", font=dict(color="#FFFFFF")),
            overlaying="y",
            side="right",
            tickformat=".0%",
            gridcolor="rgba(255,255,255,0.2)",
            zeroline=False,
            showline=False,
            linecolor="rgba(255,255,255,0.4)",
            mirror=True,
            tickfont=dict(color="#FFFFFF"),
        ),
        hovermode="x unified",
        legend=dict(
            x=0.5,
            y=-0.18,  # Move legend below the plot area
            xanchor="center",
            yanchor="top",
            orientation="h",
            bgcolor="rgba(0,0,0,0.6)",
            bordercolor="rgba(255,255,255,0.3)",
            borderwidth=1,
            font=dict(color="#FFFFFF"),
        ),
        paper_bgcolor="#111111",
        plot_bgcolor="#111111",
        hoverlabel=dict(
            bgcolor="rgba(0,0,0,0.9)",
            font=dict(color="#FFFFFF", size=10),
            bordercolor="rgba(255,255,255,0.2)",
        ),
        margin=dict(t=20, b=90),
    )
