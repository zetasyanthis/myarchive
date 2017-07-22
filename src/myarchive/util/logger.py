# @Author: Zeta Syanthis <zetasyanthis>
# @Date:   2017/07/21
# @Email:  zeta@zetasyanthis.org
# @Project: MyArchive
# @Last modified by:   zetasyanthis
# @Last modified time: 2017/07/21
# @License MIT

import logging
import os

from logging.handlers import RotatingFileHandler


class ColoredFormatter(logging.Formatter):
    """Special custom formatter for colorizing log messages!"""

    BLACK = '\033[0;30m'
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    BROWN = '\033[0;33m'
    BLUE = '\033[0;34m'
    PURPLE = '\033[0;35m'
    CYAN = '\033[0;36m'
    GREY = '\033[0;37m'

    DARK_GREY = '\033[1;30m'
    LIGHT_RED = '\033[1;31m'
    LIGHT_GREEN = '\033[1;32m'
    YELLOW = '\033[1;33m'
    LIGHT_BLUE = '\033[1;34m'
    LIGHT_PURPLE = '\033[1;35m'
    LIGHT_CYAN = '\033[1;36m'
    WHITE = '\033[1;37m'

    RESET = "\033[0m"

    def __init__(self, *args, **kwargs):
        self._colors = {logging.DEBUG: self.DARK_GREY,
                        logging.INFO: self.RESET,
                        logging.WARNING: self.BROWN,
                        logging.ERROR: self.RED,
                        logging.CRITICAL: self.LIGHT_RED}
        super(ColoredFormatter, self).__init__(*args, **kwargs)

    def format(self, record):
        """Applies the color formats"""
        record.msg = self._colors[record.levelno] + record.msg + self.RESET
        return logging.Formatter.format(self, record)

    def setLevelColor(self, logging_level, escaped_ansi_code):
        self._colors[logging_level] = escaped_ansi_code


class ColorizingStreamHandler(logging.StreamHandler):
    """A StreamHandler object that colors its output based on level"""

    BLACK = '\033[0;30m'
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    BROWN = '\033[0;33m'
    BLUE = '\033[0;34m'
    PURPLE = '\033[0;35m'
    CYAN = '\033[0;36m'
    GREY = '\033[0;37m'

    DARK_GREY = '\033[1;30m'
    LIGHT_RED = '\033[1;31m'
    LIGHT_GREEN = '\033[1;32m'
    YELLOW = '\033[1;33m'
    LIGHT_BLUE = '\033[1;34m'
    LIGHT_PURPLE = '\033[1;35m'
    LIGHT_CYAN = '\033[1;36m'
    WHITE = '\033[1;37m'

    RESET = "\033[0m"

    def __init__(self, *args, **kwargs):
        self._colors = {logging.DEBUG: self.DARK_GREY,
                        logging.INFO: self.RESET,
                        logging.WARNING: self.BROWN,
                        logging.ERROR: self.RED,
                        logging.CRITICAL: self.LIGHT_RED}
        super(ColorizingStreamHandler, self).__init__(*args, **kwargs)

    @property
    def is_tty(self):
        isatty = getattr(self.stream, 'isatty', None)
        return isatty and isatty()

    def emit(self, record):
        try:
            message = self.format(record)
            stream = self.stream
            if not self.is_tty:
                stream.write(message)
            else:
                message = self._colors[record.levelno] + message + self.RESET
                stream.write(message)
            stream.write(getattr(self, 'terminator', '\n'))
            self.flush()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)

    def setLevelColor(self, logging_level, escaped_ansi_code):
        self._colors[logging_level] = escaped_ansi_code


# Get the main logger by name since __name__ will be __main__ here.
myarchive_LOGGER = logging.getLogger('myarchive')
myarchive_LOGGER.setLevel(logging.DEBUG)

stream_handler = ColorizingStreamHandler()
stream_formatter = logging.Formatter(
    fmt='%(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')
stream_handler.setFormatter(stream_formatter)
stream_handler.setLevel(logging.INFO)
myarchive_LOGGER.addHandler(stream_handler)

# TODO: Move this to syslog / systemd logger.
log_folder = os.path.join(
    os.path.join(os.path.expanduser("~"), ".myarchive/log/")
)
if not os.path.exists(log_folder):
    os.makedirs(log_folder)
log_file_path = os.path.join(log_folder, "myarchive.log")
file_handler = RotatingFileHandler(
    filename=log_file_path,
    maxBytes=10*2**20,
    backupCount=5)
file_formatter = logging.Formatter(
    fmt='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')
file_handler.setFormatter(file_formatter)
file_handler.setLevel(logging.DEBUG)
myarchive_LOGGER.addHandler(file_handler)
