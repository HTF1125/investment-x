import ix
import click
import os
logger = ix.misc.get_logger("InvestmentX")

from wx.app import app



@click.command()
@click.option("--debug", is_flag=True, help="Enable task mode.")
def cli(debug: bool = False):
    """Run the application with specified tasks."""

    if debug:
        app.run(debug=True)
        logger.info("All Tasks Completed Successfully.")
        return

    app.run_server(host="0.0.0.0", port=int(os.environ.get("PORT", 8050)))


if __name__ == "__main__":
    cli()
