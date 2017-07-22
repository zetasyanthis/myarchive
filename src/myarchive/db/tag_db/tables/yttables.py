# @Author: Zeta Syanthis <zetasyanthis>
# @Date:   2017/07/21
# @Email:  zeta@zetasyanthis.org
# @Project: MyArchive
# @Last modified by:   zetasyanthis
# @Last modified time: 2017/07/21
# @License MIT

"""
Module containing class definitions for files to be tagged.
"""

import logging

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import backref, relationship

from myarchive.db.tag_db.tables.association_tables import at_ytvideo_tag
from myarchive.db.tag_db.tables.base import Base


LOGGER = logging.getLogger(__name__)


EXISTING_USERNAME_CACHE = list()
HASHTAG_REGEX = r'#([\d\w]+)'


class YTPlaylist(Base):
    """Class representing a Youtube playlist stored by the database."""

    __tablename__ = 'ytplaylists'

    id = Column(Integer, index=True, primary_key=True)
    title = Column(String)
    author = Column(String)
    description = Column(String)
    plid = Column(String, unique=True)

    videos = relationship(
        "YTVideo",
        doc="List of videos in the playlist.",
    )

    def __init__(self, title, author, description, plid):
        self.title = title
        self.author = author
        self.description = description
        self.plid = plid

    def __repr__(self):
        return "<%s('%r')>" % (self.__class__, self.__dict)


class YTVideo(Base):
    """Class representing a Youtube video stored by the database."""

    __tablename__ = 'ytvideos'

    id = Column(Integer, index=True, primary_key=True)
    uploader = Column(String)
    description = Column(String)
    duration = Column(String)
    publish_time = Column(DateTime)
    videoid = Column(String)
    playlist_id = Column(Integer, ForeignKey("ytplaylists.id"), nullable=True)
    file_id = Column(Integer, ForeignKey("files.id"))

    file = relationship(
        "TrackedFile",
        doc="File associated with deviation.",
        uselist=False,
    )
    tags = relationship(
        "Tag",
        backref=backref(
            "ytvideos",
            doc="Deviations associated with this tag"),
        doc="Tags that have been applied to this deviation.",
        secondary=at_ytvideo_tag,
    )

    def __init__(self, uploader, description, duration, publish_time, videoid):
        self.uploader = uploader
        self.description = description
        self.duration = duration
        self.publish_time = publish_time
        self.videoid = videoid
