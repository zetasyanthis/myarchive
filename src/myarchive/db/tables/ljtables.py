from sqlalchemy import (
    Column, Integer, String, TIMESTAMP, ForeignKey)
from sqlalchemy.orm import backref, relationship
from sqlalchemy.orm.exc import NoResultFound

from myarchive.db.tables.base import Base
from myarchive.db.tables.file import TrackedFile


class LJHost(Base):
    """Class representing a user retrieved from a LJ-like service."""

    __tablename__ = 'lj_hosts'

    id = Column(Integer, index=True, primary_key=True)
    url = Column(String)

    def __init__(self, url):
        self.url = url


class LJUser(Base):
    """Class representing a user retrieved from a LJ-like service."""

    __tablename__ = 'lj_users'

    id = Column(Integer, index=True, primary_key=True)
    username = Column(String)
    host_id = Column(Integer, ForeignKey("lj_hosts.id"))

    def __init__(self, user_id, username):
        self.id = user_id
        self.username = username


class LJEntries(Base):
    """Class representing an entry retrieved from a LJ-like service."""

    __tablename__ = 'lj_entries'

    id = Column(Integer, index=True, primary_key=True)
    # itemid is unique only to the user, possibly only to the pull...
    itemid = Column(Integer)
    eventtime = Column(TIMESTAMP)
    subject = Column(String)
    text = Column(String)
    current_music = Column(String)
    user_id = Column(Integer, ForeignKey("lj_users.id"))

    def __init__(self, itemid, eventtime, subject, text, current_music):
        self.itemid = itemid
        self.eventtime = eventtime
        self.subject = subject
        self.text = text
        self.current_music = current_music
        # props["taglist"]
        # props["current_music"]


class LJComments(Base):
    """Class representing a comment retrieved from a LJ-like service."""

    __tablename__ = 'lj_comments'

    id = Column(Integer, index=True, primary_key=True)
    body = Column(String)
    date = Column(TIMESTAMP)
    parent_id = Column(Integer, ForeignKey("lj_comments.id"))
    entry_id = Column(Integer, ForeignKey("lj_entries.id"))
