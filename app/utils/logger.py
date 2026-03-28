import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional


DEFAULT_LEVEL = logging.INFO
DEBUG_MODE = os.environ.get("DEBUG", "").lower() in ("1", "true", "yes")

if DEBUG_MODE:
    DEFAULT_LEVEL = logging.DEBUG

LOG_DIR = "logs"
LOG_FILE = "app.log"
MAX_BYTES = 5 * 1024 * 1024  # 5MB
BACKUP_COUNT = 3


def _get_log_format():
    return "%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s"


def setup_logger(
    name: str,
    level: int = DEFAULT_LEVEL,
    format_string: Optional[str] = None
) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    if logger.handlers:
        return logger
    
    if format_string is None:
        format_string = _get_log_format()
    
    formatter = logging.Formatter(format_string)
    
    os.makedirs(LOG_DIR, exist_ok=True)
    log_path = os.path.join(LOG_DIR, LOG_FILE)
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


def get_agent_logger(agent_name: str, level: int = DEFAULT_LEVEL) -> logging.Logger:
    return setup_logger(f"agent.{agent_name.lower().replace(' ', '_')}", level)


def log_thinking(logger: logging.Logger, agent_name: str):
    logger.debug(f"{agent_name}: Thinking")


def log_acting(logger: logging.Logger, agent_name: str):
    logger.debug(f"{agent_name}: Acting")


def log_tool_call(logger: logging.Logger, tool_name: str, args: dict):
    logger.info(f"Tool called: {tool_name}")
    logger.debug(f"Tool arguments: {args}")


def log_tool_result(logger: logging.Logger, tool_name: str, result: str):
    logger.info(f"Tool result: {tool_name}")
    if result:
        preview = result[:500] + "..." if len(result) > 500 else result
        logger.debug(f"Tool output: {preview}")


def log_workflow_step(logger: logging.Logger, step: str, details: str = ""):
    if details:
        logger.info(f"Workflow: {step} - {details}")
    else:
        logger.info(f"Workflow: {step}")


def get_log_file_path() -> str:
    return os.path.abspath(os.path.join(LOG_DIR, LOG_FILE))
