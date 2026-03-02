from ix.misc import get_logger

logger = get_logger(__name__)


def getEnv(filepath=".env"):
    """
    Get environment variables from a specified .env file.

    Parameters:
    - filepath (str): Path to the .env file. Default is ".env".

    Returns:
    - dict: Dictionary containing the environment variables.
    """
    variables = {}

    try:
        with open(filepath, "r") as file:
            for line in file:
                # Ignore comments and empty lines
                if line.strip() and not line.startswith("#"):
                    key, value = line.strip().split("=", 1)
                    variables[key.strip()] = value.strip()
    except FileNotFoundError:
        logger.warning("Environment file not found: %s", filepath)
    except Exception as e:
        logger.error("Error reading environment file %s: %s", filepath, e)

    return variables
