"""
Module containing class definitions for files to be tagged.
"""

from sqlalchemy import (
    LargeBinary, Boolean, Column, Integer, String, PickleType, ForeignKey)
from sqlalchemy.orm import backref, relationship

from myarchive.db.tables.base import Base
from myarchive.db.tables.file import TrackedFile
from myarchive.db.tables.association_tables import (
    at_tweet_tag, at_tweet_file, at_twuser_file)


class RawTweet(Base):
    """Class representing a raw tweet."""

    __tablename__ = 'rawtweets'

    id = Column(Integer, index=True, primary_key=True)
    favorited_by_str = Column(String, default="")
    raw_status_dict = Column(PickleType)

    @property
    def favorited_by(self):
        return self.favorited_by_str.split(",")

    def __init__(self, status_dict):
        self.id = int(status_dict["id"])
        self.raw_status_dict = status_dict

    def __repr__(self):
        return (
            "<Tweet(id='%s', raw_data='%s')>" % (self.id, self.raw_status_dict))

    def add_user_favorite(self, type_):
        if self.favorited_by_str:
            if type_ not in self.favorited_by_str:
                self.favorited_by_str = (
                    ",".join(self.favorited_by_str.split(',') + [type_]))
        else:
            self.favorited_by_str = type_


class CSVTweet(Base):
    """
    Class representing a tweet taken from a CSV file, which may or may not have
    been cross-imported from the Twitter API.
    """

    __tablename__ = 'csvtweets'

    id = Column(Integer, index=True, primary_key=True)
    username = Column(String)
    in_reply_to_status_id = Column(Integer)
    in_reply_to_user_id = Column(Integer)
    timestamp = Column(String)
    text = Column(LargeBinary)
    retweeted_status_id = Column(Integer)
    retweeted_status_user_id = Column(Integer)
    retweeted_status_timestamp = Column(String)
    expanded_urls = Column(String)
    favorited_by_str = Column(String, default="")
    api_import_complete = Column(Boolean, default=False)

    def __init__(self, id, username, in_reply_to_status_id, in_reply_to_user_id,
                 timestamp, text, retweeted_status_id, retweeted_status_user_id,
                 retweeted_status_timestamp, expanded_urls):
        self.id = int(id)
        self.username = username
        if in_reply_to_status_id:
            self.in_reply_to_status_id = int(in_reply_to_status_id)
        if in_reply_to_user_id:
            self.in_reply_to_user_id = int(in_reply_to_user_id)
        self.timestamp = timestamp
        self.text = text
        if retweeted_status_id:
            self.retweeted_status_id = int(retweeted_status_id)
        if retweeted_status_user_id:
            self.retweeted_status_user_id = int(retweeted_status_user_id)
        self.retweeted_status_timestamp = retweeted_status_timestamp
        self.expanded_urls = expanded_urls

    def __repr__(self):
        return (
            "<Tweet(id='%s', api_import_complete='%s')>" % (
                self.id, self.api_import_complete))


class Tweet(Base):
    """Class representing a file tweet by the database."""

    __tablename__ = 'tweets'

    id = Column(Integer, index=True, primary_key=True)
    text = Column(String)
    in_reply_to_screen_name = Column(String)
    in_reply_to_status_id = Column(Integer)
    user_id = Column(Integer, ForeignKey("twitter_users.id"), nullable=True)

    files = relationship(
        "TrackedFile",
        backref=backref(
            "tweets",
            doc="Tweets associated with this file"),
        doc="Files associated with this tweet.",
        secondary=at_tweet_file
    )
    tags = relationship(
        "Tag",
        backref=backref(
            "tweets",
            doc="Tweets associated with this tag"),
        doc="Tags that have been applied to this tweet.",
        secondary=at_tweet_tag
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

    def __repr__(self):
        return "<Tweet(id='%s', text='%s')>" % (self.id, self.text)

    @classmethod
    def make_from_raw(cls, raw_tweet):
        tweet = cls(raw_tweet.raw_status_dict)
        return tweet

    def download_associated_media(self, db_session, media_path, new_ids=None):
        # Retrieve media files.
        if media_path and "media" in raw_tweet.raw_status_dict:
            for media_item in raw_tweet.raw_status_dict["media"]:
                media_url = media_item["media_url_https"]
                tracked_file = TrackedFile.download_file(
                    db_session, media_path, media_url)
                if tracked_file is not None and tracked_file not in tweet.files:
                    tweet.files.append(tracked_file)
                db_session.commit()


class TwitterUser(Base):
    """Class representing a file tweet by the database."""

    __tablename__ = 'twitter_users'

    id = Column(Integer, index=True, primary_key=True)
    name = Column(String)
    screen_name = Column(String)
    url = Column(String)
    description = Column(String)
    location = Column(String)
    time_zone = Column(String)
    created_at = Column(String)

    profile_sidebar_fill_color = Column(String)
    profile_text_color = Column(String)
    profile_background_color = Column(String)
    profile_link_color = Column(String)
    profile_image_url = Column(String)
    profile_banner_url = Column(String)
    profile_background_image_url = Column(String)

    files = relationship(
        "TrackedFile",
        doc="Files associated with this user.",
        secondary=at_twuser_file
    )
    tweets = relationship(
        "Tweet",
        doc="Tweets tweeted by this user.",
    )

    def __init__(self, user_dict):
        self.id = int(user_dict["id"])
        self.name = user_dict["name"]
        self.screen_name = user_dict["screen_name"]
        self.url = user_dict.get("url")
        self.description = user_dict.get("description")
        self.created_at = user_dict["created_at"]
        self.location = user_dict.get("location")
        self.time_zone = user_dict.get("time_zone")
        self.profile_sidebar_fill_color = user_dict[
            "profile_sidebar_fill_color"]
        self.profile_text_color = user_dict[
            "profile_text_color"]
        self.profile_background_color = user_dict[
            "profile_background_color"]
        self.profile_link_color = user_dict[
            "profile_link_color"]
        self.profile_image_url = user_dict.get(
            "profile_image_url")
        self.profile_banner_url = user_dict.get(
            "profile_banner_url")
        self.profile_background_image_url = user_dict.get(
            "profile_background_image_url")

    def __repr__(self):
        return (
            "<TwitterUser(id='%s', name='%s' screen_name='%s')>" %
            (self.id, self.name, self.screen_name))

    def download_files(self, db_session, media_path):
        for media_url in (
                self.profile_image_url,
                self.profile_background_image_url,
                self.profile_banner_url):
            if media_url is None:
                continue

            # Add file to DB (runs a sha1sum).
            tracked_file = TrackedFile.download_file(
                db_session=db_session, media_path=media_path, url=media_url)
            if tracked_file is not None:
                self.files.append(tracked_file)
        db_session.commit()
