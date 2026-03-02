import sys
import typing
import logging
import os

from ix.utils.logger import (
    DEFAULT_LOG_DATE_FORMAT,
    DEFAULT_LOG_FORMAT,
    DEFAULT_SERVICE_NAME,
    TextFormatter,
    configure_root_logger,
)


def progress(
    current_bar: int,
    total_bar: int,
    prefix: str = "",
    suffix: str = "",
    bar_length: int = 50,
) -> None:
    # pylint: disable=expression-not-assigned
    """
    Calls in a loop to create a terminal progress bar.

    Args:F
        current_bar (int): Current iteration.
        total_bar (int): Total iteration.
        prefix (str, optional): Prefix string. Defaults to ''.
        suffix (str, optional): Suffix string. Defaults to ''.
        bar_length (int, optional): Character length of the bar.
            Defaults to 50.

    References:
        https://gist.github.com/aubricus/f91fb55dc6ba5557fbab06119420dd6a
    """
    # Calculate the percent completed.
    percents = current_bar / float(total_bar)
    # Calculate the length of bar.
    filled_length = int(round(bar_length * current_bar / float(total_bar)))
    # Fill the bar.
    block = "█" * filled_length + "-" * (bar_length - filled_length)
    # Print new line.
    sys.stdout.write(f"\r{prefix} |{block}| {percents:.2%} {suffix}")

    if current_bar == total_bar:
        sys.stdout.write("\n")
    sys.stdout.flush()


def func_scope(func: typing.Callable) -> str:
    current_module = sys.modules[func.__module__]
    return f"{current_module.__name__}.{func.__name__}"

def get_logger(
    arg: str | typing.Callable,
    level: int | str = logging.INFO,
    fmt: str = DEFAULT_LOG_FORMAT,
    stream: bool = True,
    filename: str | None = None,
) -> logging.Logger:
    logger_name = func_scope(arg) if callable(arg) else arg
    root_logger = logging.getLogger()
    if stream and not root_logger.handlers:
        configure_root_logger(
            service_name=DEFAULT_SERVICE_NAME,
            level=level,
            enable_stream=True,
            enable_file=False,
            enable_db=False,
        )

    logger = logging.getLogger(logger_name)

    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(level)
    logger.propagate = True

    if filename is not None:
        if not filename.endswith(".log"):
            filename += ".log"
        dir_name = os.path.dirname(filename)
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name)
        abs_filename = os.path.abspath(filename)
        existing_handler = next(
            (
                handler
                for handler in logger.handlers
                if isinstance(handler, logging.FileHandler)
                and getattr(handler, "_investment_x_file", None) == abs_filename
            ),
            None,
        )
        if existing_handler is None:
            file_handler = logging.FileHandler(filename=abs_filename)
            file_handler._investment_x_file = abs_filename
            if fmt == DEFAULT_LOG_FORMAT:
                file_handler.setFormatter(TextFormatter(DEFAULT_SERVICE_NAME))
            else:
                file_handler.setFormatter(
                    logging.Formatter(fmt=fmt, datefmt=DEFAULT_LOG_DATE_FORMAT)
                )
            logger.addHandler(file_handler)

    return logger
