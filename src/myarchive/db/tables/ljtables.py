from sqlalchemy import (
    Column, Integer, String, TIMESTAMP, ForeignKey)
from sqlalchemy.orm import backref, relationship
from sqlalchemy.orm.exc import NoResultFound

from myarchive.db.tables.base import Base
from myarchive.db.tables.file import TrackedFile


class CircularDependencyError(Exception):
    """
    Specific exception for attempting to create a self-referential
    infinite loop.
    """
    pass


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

    user_id = Column(Integer, index=True, primary_key=True)
    username = Column(String)
    host_id = Column(Integer, ForeignKey("lj_hosts.id"))

    def __init__(self, user_id, username):
        self.user_id = user_id
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
    user_id = Column(Integer, ForeignKey("lj_users.user_id"))

    def __init__(self, itemid, eventtime, subject, text, current_music):
        self.itemid = itemid
        self.eventtime = eventtime
        self.subject = subject
        self.text = text
        self.current_music = current_music
        # props["taglist"]
        # props["current_music"]


class LJComment(Base):
    """Class representing a comment retrieved from a LJ-like service."""

    __tablename__ = 'lj_comments'

    id = Column(Integer, index=True, primary_key=True)
    body = Column(String)
    date = Column(TIMESTAMP)
    parent_id = Column(Integer, ForeignKey("lj_comments.id"))
    entry_id = Column(Integer, ForeignKey("lj_entries.id"))

    children = relationship(
        "LJComment",
        backref=backref('parent', remote_side=[id])
    )

    def add_child(self, lj_comment):
        """Creates an instance, performing a safety check first."""
        if self in lj_comment.children:
            raise CircularDependencyError(
                "Attempting to create a self-referential tag loop!")
        else:
            self.children.append(lj_comment)
