import logging

def init_logger(name, log_file, level=logging.INFO):
    """Returns a logger instance

    Parameters
    ----------
    name : str
        The name of the logger

    log_file : str
        Filepath of the log file

    level : Level of the logger
        Should be INFO for output loggers. Debug messages are at DEBUG level.
    """

    formatter = logging.Formatter('%(message)s')
    handler = logging.FileHandler(log_file)
    handler.setFormatter(formatter)
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    logger.propagate = False

    return logger