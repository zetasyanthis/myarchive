# @Author: Zeta Syanthis <zetasyanthis>
# @Date:   2017/07/21
# @Email:  zeta@zetasyanthis.org
# @Project: MyArchive
# @Last modified by:   zetasyanthis
# @Last modified time: 2017/07/21
# @License MIT

"""Reverse-engineered Shotwell database, used for imports."""

import logging
import os

from myarchive.db.db import DB

from myarchive.db.shotwell.tables import Base

# Get the module logger.
logger = logging.getLogger(__name__)


class ShotwellDB(DB):

    def __init__(self,
                 drivername="sqlite", username=None, password=None,
                 db_name=os.path.expanduser(
                     "~/.local/share/shotwell/data/photo.db"),
                 host=None, port=None, pool_size=5):
        super(ShotwellDB, self).__init__(
            base=Base, drivername=drivername, username=username,
            password=password, db_name=db_name, host=host, port=port,
            pool_size=pool_size
        )
