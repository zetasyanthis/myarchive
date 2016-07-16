from sqlalchemy import (
    LargeBinary, Boolean, Column, Integer, String, PickleType, ForeignKey)
from sqlalchemy.orm import backref, relationship
from sqlalchemy.orm.exc import NoResultFound

from myarchive.db.tables.base import Base
from myarchive.db.tables.file import TrackedFile
from myarchive.db.tables.association_tables import (
    at_tweet_tag, at_tweet_file, at_twuser_file)


class RawTweet(Base):
    """Class representing a raw tweet."""
    pass
