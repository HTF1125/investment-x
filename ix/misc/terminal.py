import sys
import typing
import logging


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

    Args:
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
    level: int | str = logging.DEBUG,
    fmt: str = "%(asctime)s:%(name)s:%(levelname)s:%(message)s",
    stream: bool = True,
    filename: str | None = None,
) -> logging.Logger:

    logger_name = func_scope(arg) if callable(arg) else arg
    logger = logging.getLogger(logger_name)
    if isinstance(level, str):
        level = getattr(logging, level.upper())
    logger.setLevel(level=level)
    if len(logger.handlers) == 0:
        formatter = logging.Formatter(fmt=fmt)
        if stream:
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(fmt=formatter)
            logger.addHandler(stream_handler)
        if filename is not None:
            if not filename.endswith(".log"):
                filename += ".log"
            file_handler = logging.FileHandler(filename=filename)
            file_handler.setFormatter(fmt=formatter)
            logger.addHandler(file_handler)
    return logger
