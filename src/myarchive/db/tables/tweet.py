"""
Module containing class definitions for files to be tagged.
"""

from hashlib import sha1
from sqlalchemy import Column, Integer, String, PickleType
from sqlalchemy.orm import backref, relationship

from myarchive.db.tables.base import Base
from myarchive.db.tables.association_tables import at_file_tweet


class Tweet(Base):
    """Class representing a file tweet by the database."""

    __tablename__ = 'tweets'

    _id = Column(Integer, name="id", primary_key=True)
    raw_data = PickleType()

    tags = relationship(
        "Tag",
        backref=backref(
            "tweets",
            doc="Tweets associated with this tag"),
        doc="Tags that have been applied to this file.",
        secondary=at_file_tweet
    )

    def __init__(self, tweet_dict):
        self.raw_data = tweet_dict

    def __repr__(self):
        return ("<File(Tweet='%s', id='%s', "
                "raw_data='%s')>" %
                (self.directory, self._id, self.raw_data))
