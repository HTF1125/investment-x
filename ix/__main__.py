import ix
import click

logger = ix.misc.get_logger("InvestmentX")

@click.command()
@click.option("--task", is_flag=True, help="Enable task mode.")
@click.option("--bloomberg", is_flag=True, help="Enable task mode.")
@click.option("--reload", is_flag=True, help="Enable task mode.")
def cli(task: bool = False, bloomberg: bool = False,  reload: bool = False):
    """Run the application with specified tasks."""

    if task:
        ix.task.run()
        logger.info("All Tasks Completed Successfully.")
        return

    if bloomberg:
        ix.task.bloomberg_only()
        logger.info("All Tasks Completed Successfully.")
        return
    import uvicorn
    uvicorn.run("ix.api.main:app", reload=reload)


if __name__ == "__main__":
    cli()
