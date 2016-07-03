"""
Module containing class definitions for files to be tagged.
"""

from sqlalchemy import Column, Integer, String, PickleType
from sqlalchemy.orm import backref, relationship

from myarchive.db.tables.base import Base
from myarchive.db.tables.association_tables import at_file_tweet


class RawTweet(Base):
    """Class representing a raw tweet."""

    __tablename__ = 'rawtweets'

    id = Column(Integer, primary_key=True)
    raw_status_dict = Column(PickleType)

    def __init__(self, status_dict):
        self.id = int(status_dict["id"])
        self.raw_status_dict = status_dict

    def __repr__(self):
        return (
            "<Tweet(id='%s', raw_data='%s')>" % (self.id, self.raw_status_dict))


class Tweet(Base):
    """Class representing a file tweet by the database."""

    __tablename__ = 'tweets'

    id = Column(Integer, primary_key=True)
    user = Column(String)
    text = Column(String)
    in_reply_to_screen_name = Column(String)
    in_reply_to_status_id = Column(Integer)

    tags = relationship(
        "Tag",
        backref=backref(
            "tweets",
            doc="Tweets associated with this tag"),
        doc="Tags that have been applied to this file.",
        secondary=at_file_tweet
    )

    def __init__(self, status_dict):
        self.id = int(status_dict["id"])
        self.text = status_dict["text"]
        in_reply_to_status_id = status_dict.get(
            "in_reply_to_status_id")
        if in_reply_to_status_id is not None:
            self.in_reply_to_status_id = int(in_reply_to_status_id)
        self.created_at = status_dict["created_at"]
        hashtags_list = status_dict.get("hashtags")
        if hashtags_list:
            self.hashtags = ",".join(
                [hashtag_dict[u"text"] for hashtag_dict in hashtags_list])

        # self.user = status_dict["user"]
        # self.in_reply_to_screen_name = str(status_dict.get(
        #     ["in_reply_to_screen_name"]))

    def __repr__(self):
        return (
            "<Tweet(id='%s', user='%s', in_reply_to_screen_name='%s')>" %
            (self._id, self.user, self.in_reply_to_screen_name))
