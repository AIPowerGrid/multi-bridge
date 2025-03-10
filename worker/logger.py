import sys
from functools import partialmethod

from loguru import logger

STDOUT_LEVELS = ["GENERATION", "PROMPT"]
INIT_LEVELS = ["INIT", "INIT_OK", "INIT_WARN", "INIT_ERR"]
MESSAGE_LEVELS = ["MESSAGE"]
STATS_LEVELS = ["STATS"]
# By default we're at error level or higher
verbosity = 20
quiet = 0


def set_logger_verbosity(count):
    global verbosity
    # The count comes reversed. So count = 0 means minimum verbosity
    # While count 5 means maximum verbosity
    # So the more count we have, the lowe we drop the versbosity maximum
    verbosity = 20 - (count * 10)


def quiesce_logger(count):
    global quiet
    # The bigger the count, the more silent we want our logger
    quiet = count * 10


def is_stdout_log(record):
    if record["level"].name not in STDOUT_LEVELS:
        return False
    if record["level"].no < verbosity + quiet:
        return False
    return True


def is_init_log(record):
    if record["level"].name not in INIT_LEVELS:
        return False
    if record["level"].no < verbosity + quiet:
        return False
    return True


def is_msg_log(record):
    if record["level"].name not in MESSAGE_LEVELS:
        return False
    if record["level"].no < verbosity + quiet:
        return False
    return True


def is_stderr_log(record):
    if record["level"].name in STDOUT_LEVELS + INIT_LEVELS + MESSAGE_LEVELS + STATS_LEVELS:
        return False
    if record["level"].no < verbosity + quiet:
        return False
    return True


def is_stats_log(record):
    if record["level"].name not in STATS_LEVELS:
        return False
    return True


def is_not_stats_log(record):
    if record["level"].name in STATS_LEVELS:
        return False
    return True


def is_trace_log(record):
    if record["level"].name not in ["TRACE", "ERROR"]:
        return False
    return True


def test_logger():
    logger.generation(
        "This is a generation message\nIt is typically multiline\nThee Lines".encode("unicode_escape").decode("utf-8"),
    )
    logger.prompt("This is a prompt message")
    logger.debug("Debug Message")
    logger.info("Info Message")
    logger.warning("Info Warning")
    logger.error("Error Message")
    logger.critical("Critical Message")
    logger.init("This is an init message", status="Starting")
    logger.init_ok("This is an init message", status="OK")
    logger.init_warn("This is an init message", status="Warning")
    logger.init_err("This is an init message", status="Error")
    logger.message("This is user message")
    sys.exit()


logfmt = (
    "<green>{time:MM-DD HH:mm:ss}</green> | <level>{message}</level>"
)
genfmt = "<level>{level: <10}</level> @ <green>{time:YYYY-MM-DD HH:mm:ss.SSSSSS}</green> | <level>{message}</level>"
initfmt = "<green>{time:MM-DD HH:mm:ss}</green> | <magenta>{message}</magenta>"
msgfmt = "<green>{time:MM-DD HH:mm:ss}</green> | <level>{message}</level>"

try:
    logger.level("GENERATION", no=24, color="<cyan>")
    logger.level("PROMPT", no=23, color="<yellow>")
    logger.level("INIT", no=31, color="<white>")
    logger.level("INIT_OK", no=31, color="<green>")
    logger.level("INIT_WARN", no=31, color="<yellow>")
    logger.level("INIT_ERR", no=31, color="<red>")
    # Messages contain important information without which this application might not be able to be used
    # As such, they have the highest priority
    logger.level("MESSAGE", no=61, color="<green>")
    # Stats are info that might not display well in the terminal
    logger.level("STATS", no=19, color="<blue>")
except TypeError:
    pass

logger.__class__.generation = partialmethod(logger.__class__.log, "GENERATION")
logger.__class__.prompt = partialmethod(logger.__class__.log, "PROMPT")
logger.__class__.init = partialmethod(logger.__class__.log, "INIT")
logger.__class__.init_ok = partialmethod(logger.__class__.log, "INIT_OK")
logger.__class__.init_warn = partialmethod(logger.__class__.log, "INIT_WARN")
logger.__class__.init_err = partialmethod(logger.__class__.log, "INIT_ERR")
logger.__class__.message = partialmethod(logger.__class__.log, "MESSAGE")
logger.__class__.stats = partialmethod(logger.__class__.log, "STATS")

# Simplified config that only logs to stdout/stderr without file logging
# But ensures important job information is shown
config = {
    "handlers": [
        {
            "sink": sys.stderr,
            "format": logfmt,
            "colorize": True,
            "filter": is_stderr_log,
            "level": "WARNING",  # Only log warnings and above to stderr
        },
        {
            "sink": sys.stdout,
            "format": genfmt,
            "level": "PROMPT",
            "colorize": True,
            "filter": is_stdout_log,
        },
        {
            "sink": sys.stdout,
            "format": initfmt,
            "level": "INIT",
            "colorize": True,
            "filter": is_init_log,
        },
        {
            "sink": sys.stdout,
            "format": msgfmt,
            "level": "MESSAGE",
            "colorize": True,
            "filter": is_msg_log,
        },
        {
            "sink": sys.stdout,
            "format": logfmt,
            "level": "INFO",  # Show INFO level messages to capture job status
            "colorize": True,
            "filter": lambda record: record["level"].name == "INFO"
        },
    ],
}
logger.configure(**config)
