from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from ix.db.conn import Base
import plotly.io as pio
import json


class Chart(Base):
    """
    Model for storing Plotly chart definitions.
    Stores the Python code to generate the figure, and the cached figure JSON.
    """

    __tablename__ = "charts"

    code = Column(Text, primary_key=True)  # Python code is the unique identifier
    figure = Column(
        JSONB, nullable=True
    )  # Cached Plotly JSON (nullable to allow init without render)
    description = Column(Text, nullable=True)
    category = Column(String, nullable=True)
    tags = Column(JSONB, default=list)
    updated_at = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    def render(self, force_update=False):
        """Executes the stored code and returns the Plotly Figure object."""
        if not force_update and self.figure:
            return pio.from_json(json.dumps(self.figure))

        # Defer import to avoid circular dependency
        from ix import cht
        from ix.cht.style import finalize_axis_colors

        local_scope = {}
        # Prepare execution globals with 'cht' available
        exec_globals = {"__name__": "__main__", "cht": cht}

        # Also inject all chart functions from 'cht' directly into the global namespace
        # so "AsianExportsYoY()" works without "cht." prefix
        for name in dir(cht):
            if not name.startswith("_"):
                exec_globals[name] = getattr(cht, name)

        fig = None

        # Prepare code for execution - add () if it's just a function name
        eval_code = self.code
        if not eval_code.endswith(")"):
            eval_code = f"{eval_code}()"

        # 1. Try to evaluate as a single expression (e.g. "AsianExportsYoY()")
        try:
            fig = eval(eval_code, exec_globals, local_scope)
        except (SyntaxError, Exception):
            # 2. If eval fails (e.g. it's a script), use exec and look for 'fig'
            try:
                exec(self.code, exec_globals, local_scope)
                if "fig" in local_scope:
                    fig = local_scope["fig"]
                else:
                    raise ValueError(
                        "Chart code must either be an expression returning a Figure or define a 'fig' variable."
                    )
            except Exception as e:
                # Use code snippet for identification
                code_snippet = (
                    (self.code[:50] + "...") if len(self.code) > 50 else self.code
                )
                raise RuntimeError(f"Failed to render chart code '{code_snippet}': {e}")

        # Ensure all axis colors are black after chart generation
        return finalize_axis_colors(fig)

    def update_figure(self):
        """Renders the chart and updates the cached JSON."""
        from datetime import datetime
        from sqlalchemy.orm.attributes import flag_modified

        fig = self.render(force_update=True)
        # Convert Figure to JSON-compatible dict.
        # pio.to_json returns a string, so we parse it back to a dict for JSONB storage.
        self.figure = json.loads(pio.to_json(fig))

        # Explicitly update timestamp and flag modifications for SQLAlchemy
        self.updated_at = datetime.now()
        flag_modified(self, "figure")

        return self.figure
