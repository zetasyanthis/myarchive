"""
Module containing class definitions for files to be tagged.
"""

from sqlalchemy import Column, Integer, String, PickleType
from sqlalchemy.orm import backref, relationship

from myarchive.db.tables.base import Base
from myarchive.db.tables.association_tables import at_tweet_tag, at_tweet_file


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

    files = relationship(
        "TrackedFile",
        backref=backref(
            "tweets",
            doc="Tweets associated with this tag"),
        doc="Tags that have been applied to this file.",
        secondary=at_tweet_file
    )
    tags = relationship(
        "Tag",
        backref=backref(
            "tweets",
            doc="Tweets associated with this tag"),
        doc="Tags that have been applied to this file.",
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

        # self.user = status_dict["user"]
        # self.in_reply_to_screen_name = str(status_dict.get(
        #     ["in_reply_to_screen_name"]))

    def __repr__(self):
        return (
            "<Tweet(id='%s', user='%s', in_reply_to_screen_name='%s')>" %
            (self._id, self.user, self.in_reply_to_screen_name))

    @classmethod
    def add_from_raw(cls, db_session, status_dict):
        id = int(status_dict["id"])
        tweet = db_session.query(cls).filter_by(id=id).all()
        if tweet:
            return tweet[0]
        return Tweet(status_dict)


class TwitterUser(Base):
    """Class representing a file tweet by the database."""

    __tablename__ = 'twitter_users'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    screen_name = Column(String)
    url = Column(String)
    description = Column(String)
    location = Column(String)
    timezone = Column(String)
    created_at = Column(String)

    profile_sidebar_fill_color = Column(String)
    profile_text_color = Column(String)
    profile_background_color = Column(String)
    profile_link_color = Column(String)
    profile_image_url = Column(String)
    profile_banner_url = Column(String)
    profile_background_image_url = Column(String)

    def __init__(self, user_dict):
        self.id = int(user_dict["id"])
        self.name = user_dict["name"]
        self.screen_name = user_dict["screen_name"]
        self.url = user_dict["url"]
        self.description = user_dict["description"]
        self.created_at = user_dict["created_at"]
        self.location = user_dict["location"]
        self.timezone = user_dict["timezone"]

        self.profile_sidebar_fill_color = user_dict["profile_sidebar_fill_color"]
        self.profile_text_color = user_dict[
            "profile_text_color"]
        self.profile_background_color = user_dict[
            "profile_background_color"]
        self.profile_link_color = user_dict[
            "profile_link_color"]
        self.profile_image_url = user_dict[
            "profile_image_url"]
        self.profile_banner_url = user_dict[
            "profile_banner_url"]
        self.profile_background_image_url = user_dict[
            "profile_background_image_url"]

    def __repr__(self):
        return (
            "<Tweet(id='%s', user='%s', in_reply_to_screen_name='%s')>" %
            (self._id, self.user, self.in_reply_to_screen_name))

    @classmethod
    def add_from_raw(cls, db_session, user_dict):
        id = int(user_dict["id"])
        twitter_users = db_session.query(cls).filter_by(id=id).all()
        if twitter_users:
            return twitter_users[0]

        twitter_user = TwitterUser(user_dict)
        for media_url in (twitter_user.profile_image_url,
                      twitter_user.profile_background_image_url,
                      twitter_user.profile_banner_url):
            filename = basename(urlparse(media_url).path)

            # Download the file.
            filepath = os.path.join(media_path, filename)
            media_request = requests.get(media_url)
            with open(filepath, "w") as fptr:
                fptr.write(media_request.content)

            # Add file to DB (runs a sha1sum).
            tracked_file = TrackedFile.add_file(
                db_session=db_session, directory=media_path, filename=filename)
            tweet.files.append(tracked_file)
            db_session.commit()
