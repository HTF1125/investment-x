import ix
import click

logger = ix.misc.get_logger("InvestmentX")


@click.command()
@click.option("--task", is_flag=True, help="Enable task mode.")
@click.option("--web", is_flag=True, help="Enable task mode.")
@click.option("--debug", is_flag=True, help="Enable task mode.")
def cli(task: bool = False, web: bool = False, debug: bool = False):
    """Run the application with specified tasks."""

    if task:
        logger.info("Start running task")
        ix.task.run()
        logger.info("All tasks completed successfully.")

    elif web:
        from ix.web.dash.main import get_app

        get_app().run_server(debug=True, port=8088)
    else:
        import uvicorn
        from ix import api

        uvicorn.run("ix.api.main:app", reload=debug)


if __name__ == "__main__":
    cli()
