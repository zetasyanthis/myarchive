"""Shotwell database, used for imports."""

import logging

from myarchive.db.db import DB

from myarchive.db.shotwell.tables import Base

# Get the module logger.
logger = logging.getLogger(__name__)


class ShotwellDB(DB):

    def __init__(self,
                 drivername=None, username=None, password=None, db_name=None,
                 host=None, port=None, pool_size=5):
        super(ShotwellDB, self).__init__(
            base=Base, drivername=drivername, username=username,
            password=password, db_name=db_name, host=host, port=port,
            pool_size=pool_size
        )
