"""
Module containing class definitions for files to be tagged.
"""

import logging
import re

from myarchive.db.tag_db.tables.association_tables import (
    at_tweet_tag, at_tweet_file, at_twuser_file)
from myarchive.db.tag_db.tables.base import Base
from sqlalchemy import (
    Boolean, Column, Integer, String, Text, ForeignKey)
from sqlalchemy.orm import backref, relationship

from myarchive.db.tag_db.tables.file import TrackedFile


LOGGER = logging.getLogger(__name__)


HASHTAG_REGEX = r'#([\d\w]+)'


class Tweet(Base):
    """Class representing a file tweet by the database."""

    __tablename__ = 'tweets'

    id = Column(Integer, index=True, primary_key=True)
    text = Column(String)
    in_reply_to_screen_name = Column(String)
    in_reply_to_status_id = Column(Integer, nullable=True)
    user_id = Column(Integer, ForeignKey("twitter_users.id"), nullable=True)
    files_downloaded = Column(Boolean, default=False)
    media_urls_str = Column(Text, default="")
    hashtags_str = Column(Text, default="")
    favorited_by_str = Column(Text, default="")

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

    @property
    def favorited_by(self):
        return self.favorited_by_str.split(",")

    @property
    def media_urls(self):
        return self.media_urls_str.split(",")

    @property
    def hashtags(self):
        return self.hashtags_str.split(",")

    def __init__(self, id, text, in_reply_to_status_id, created_at,
                 media_urls_list, hashtags_list):
        self.id = int(id)
        self.text = text
        if in_reply_to_status_id not in ("", None):
            self.in_reply_to_status_id = int(in_reply_to_status_id)
        self.created_at = created_at
        if media_urls_list:
            self.media_urls_str = ",".join(media_urls_list)
        if hashtags_list:
            self.hashtags_str = ",".join(hashtags_list)
        self.files_downloaded = False

    def __repr__(self):
        return "<Tweet(id='%s', text='%s')>" % (self.id, self.text)

    def add_user_favorite(self, user_id):
        if self.favorited_by_str:
            if user_id not in self.favorited_by_str:
                self.favorited_by_str = (
                    ",".join(self.favorited_by_str.split(',') + [user_id]))
        else:
            self.favorited_by_str = user_id

    @classmethod
    def make_from_csvtweet(cls, csv_tweet):
        return cls(
            id=csv_tweet.id,
            text=csv_tweet.text,
            in_reply_to_status_id=csv_tweet.in_reply_to_status_id,
            created_at=csv_tweet.timestamp,
            hashtags_list=re.findall(HASHTAG_REGEX, str(csv_tweet.text)),
        )

    def download_media(self, db_session, media_path):
        """Retrieve media files."""
        for media_url in self.media_urls:
            if media_url != "":
                tracked_file, existing = TrackedFile.download_file(
                    db_session, media_path, media_url)
                if (tracked_file is not None and
                        tracked_file not in self.files):
                    self.files.append(tracked_file)


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

    def download_media(self, db_session, media_path):
        for media_url in (
                self.profile_image_url,
                self.profile_background_image_url,
                self.profile_banner_url):
            if media_url is None:
                continue

            # Add file to DB (runs a sha1sum).
            tracked_file, existing = TrackedFile.download_file(
                db_session=db_session, media_path=media_path, url=media_url)
            if tracked_file is not None:
                self.files.append(tracked_file)
        db_session.commit()
