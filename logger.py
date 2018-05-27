import logging
from logging.handlers import RotatingFileHandler

_logger = None


def logger():
    global _logger
    if _logger is None:
        _logger = logging.getLogger()
        _logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s :: %(levelname)s :: %(message)s')
        text_formatter = logging.Formatter('%(asctime)s : %(levelname)s : %(message)s')
        file_handler = RotatingFileHandler('backup_activity.log', 'a', 1000000, 1)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        _logger.addHandler(file_handler)

        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)
        stream_handler.setFormatter(text_formatter)
        _logger.addHandler(stream_handler)
    return _logger
