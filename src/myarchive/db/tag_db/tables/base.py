# @Author: Zeta Syanthis <zetasyanthis>
# @Date:   2017/07/21
# @Email:  zeta@zetasyanthis.org
# @Project: MyArchive
# @Last modified by:   zetasyanthis
# @Last modified time: 2017/07/21
# @License MIT

"""SQLAlchemy base class."""

from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()  # pylint:disable=C0103
