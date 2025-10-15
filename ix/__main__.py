import click
import os
import sys
from typing import Optional
from dotenv import load_dotenv, find_dotenv
from ix.misc import logger
from ix.web.app import app


def load_environment(env: Optional[str] = None):
    """
    Load environment variables from .env file based on the environment type.

    Priority:
    1. .env.{env} (e.g., .env.local, .env.remote, .env.production)
    2. .env (default)
    3. Environment variables already set in the system
    """
    env_files = []

    if env:
        env_file = f".env.{env}"
        if os.path.exists(env_file):
            env_files.append(env_file)
            logger.info(f"Loading environment from: {env_file}")
        else:
            logger.warning(f"Environment file not found: {env_file}")

    # Try to find and load default .env
    default_env = find_dotenv()
    if default_env and default_env not in env_files:
        env_files.append(default_env)
        if not env:  # Only log if we're using the default
            logger.info(f"Loading environment from: {default_env}")

    # Load environment files (later files override earlier ones)
    for env_file in env_files:
        load_dotenv(env_file, override=True)

    # Display current configuration (without sensitive data)
    db_url = os.getenv("DB_URL", "")
    db_name = os.getenv("DB_NAME", "")

    if db_url:
        # Mask password in DB_URL for logging
        if "@" in db_url:
            parts = db_url.split("@")
            credentials = parts[0].split("://")[-1]
            if ":" in credentials:
                user = credentials.split(":")[0]
                masked_url = db_url.replace(credentials, f"{user}:****")
                logger.info(f"Database URL: {masked_url}")
            else:
                logger.info(f"Database URL: {db_url}")
        else:
            logger.info(f"Database URL: {db_url}")

        logger.info(f"Database Name: {db_name}")
    else:
        logger.error("DB_URL not set! Please configure your database connection.")
        logger.error("You can set it via:")
        logger.error("  1. Environment variable: export DB_URL='mongodb://...'")
        logger.error("  2. .env file in the project root")
        logger.error("  3. .env.{environment} file (use --env flag)")
        return False

    return True


def validate_database_connection():
    """Validate that database connection is configured and accessible."""
    from ix.db.conn import ensure_connection

    logger.info("Validating database connection...")
    if not ensure_connection():
        logger.error("Failed to connect to database. Please check your configuration.")
        logger.error("Common issues:")
        logger.error("  - Is MongoDB running?")
        logger.error("  - Is DB_URL correct?")
        logger.error("  - Are credentials valid?")
        logger.error("  - Is the server accessible (firewall/network)?")
        return False

    logger.info("Database connection validated successfully!")
    return True


@click.command()
@click.option(
    "--env",
    type=str,
    help="Environment to use (loads .env.{env} file). Examples: local, remote, production",
)
@click.option(
    "--port",
    type=int,
    default=None,
    help="Port to run the application on (default: 8050 or PORT env var)",
)
@click.option(
    "--host",
    type=str,
    default="127.0.0.1",
    help="Host to bind the application to (default: 127.0.0.1)",
)
@click.option(
    "--debug",
    is_flag=True,
    help="Run the app in debug mode with auto-reload.",
)
@click.option(
    "--skip-db-check",
    is_flag=True,
    help="Skip database connection validation on startup (not recommended).",
)
@click.option(
    "--db-url",
    type=str,
    help="Override database URL (takes precedence over env files)",
)
def cli(
    env: Optional[str] = None,
    port: Optional[int] = None,
    host: str = "127.0.0.1",
    debug: bool = False,
    skip_db_check: bool = False,
    db_url: Optional[str] = None,
) -> None:
    """
    Run the Investment-X Dash application.

    Examples:

    \b
    # Run with local MongoDB (using .env.local)
    python -m ix --env local

    \b
    # Run locally connecting to remote MongoDB (using .env.remote)
    python -m ix --env remote

    \b
    # Run with custom database URL
    python -m ix --db-url mongodb://admin:password@server.com:27017/

    \b
    # Run on a different port
    python -m ix --port 8080

    \b
    # Run in debug mode with auto-reload
    python -m ix --debug

    \b
    # Run accessible from network (0.0.0.0)
    python -m ix --host 0.0.0.0
    """
    logger.info("=" * 60)
    logger.info("Investment-X Application Starting...")
    logger.info("=" * 60)

    # Load environment configuration
    if not load_environment(env):
        logger.error("Failed to load environment configuration")
        sys.exit(1)

    # Override DB_URL if provided via command line
    if db_url:
        os.environ["DB_URL"] = db_url
        logger.info("Using database URL from command line argument")

    # Validate database connection unless skipped
    if not skip_db_check:
        if not validate_database_connection():
            logger.error("Database validation failed. Exiting...")
            logger.info("Use --skip-db-check to bypass this check (not recommended)")
            sys.exit(1)
    else:
        logger.warning("Skipping database connection validation")

    # Determine port
    if port is None:
        port = int(os.getenv("PORT", 8050))

    # Display startup information
    logger.info("-" * 60)
    logger.info(f"Environment: {env if env else 'default'}")
    logger.info(f"Host: {host}")
    logger.info(f"Port: {port}")
    logger.info(f"Debug Mode: {debug}")
    logger.info(f"Access URL: http://{host}:{port}")
    if host == "0.0.0.0":
        logger.info(f"Network Access: http://localhost:{port}")
    logger.info("-" * 60)

    # Start the application
    try:
        logger.info("Starting Dash server...")
        app.run_server(host=host, port=port, debug=debug)
    except KeyboardInterrupt:
        logger.info("\nShutting down gracefully...")
    except Exception as e:
        logger.error(f"Application error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli()
