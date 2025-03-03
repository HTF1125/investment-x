import click
import os
from ix.misc import logger
from ix.wx.app import app


@click.command()
@click.option("--debug", is_flag=True, help="Run the app in debug mode.")
def cli(debug: bool = False) -> None:
    """
    Run the Dash application.
    """
    port = int(os.environ.get("PORT", 8050))
    logger.info("Starting app on port %d", port)
    app.run_server(port=port, debug=debug)


if __name__ == "__main__":
    cli()
