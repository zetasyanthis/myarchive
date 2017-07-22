# @Author: Zeta Syanthis <zetasyanthis>
# @Date:   2017/07/21
# @Email:  zeta@zetasyanthis.org
# @Project: MyArchive
# @Last modified by:   zetasyanthis
# @Last modified time: 2017/07/21
# @License MIT

"""Package of database tables"""

from .base import Base
from .file import TrackedFile
from .tag import Tag
from .twittertables import Tweet, TwitterUser
from .datables import Deviation, DeviantArtUser
