from sqlalchemy import (
    Column, Integer, String, TIMESTAMP, ForeignKey)
from sqlalchemy.orm import backref, relationship

from myarchive.db.tables.association_tables import (
    at_ljcomment_tag, at_ljentry_tag)
from myarchive.db.tables.base import Base


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
    url = Column(String, nullable=False)

    def __init__(self, url):
        self.url = url

    users = relationship(
        "LJUser",
        backref=backref('host')
    )


class LJUser(Base):
    """Class representing a user retrieved from a LJ-like service."""

    __tablename__ = 'lj_users'

    user_id = Column(Integer, index=True, primary_key=True)
    username = Column(String, nullable=False)
    host_id = Column(Integer, ForeignKey("lj_hosts.id"), nullable=False)

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
    user_id = Column(Integer, ForeignKey("lj_users.user_id"), nullable=False)

    tags = relationship(
        "Tag",
        backref=backref(
            "lj_entries",
            doc="Entries associated with this tag"),
        doc="Tags that have been applied to this LJ entry.",
        secondary=at_ljentry_tag
    )

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
    entry_id = Column(Integer, ForeignKey("lj_entries.id"), nullable=False)

    children = relationship(
        "LJComment",
        backref=backref('parent', remote_side=[id])
    )
    tags = relationship(
        "Tag",
        backref=backref(
            "lj_comments",
            doc="Entries associated with this tag"),
        doc="Tags that have been applied to this entry.",
        secondary=at_ljcomment_tag
    )

    def add_child(self, lj_comment):
        """Creates an instance, performing a safety check first."""
        if self in lj_comment.children:
            raise CircularDependencyError(
                "Attempting to create a self-referential tag loop!")
        else:
            self.children.append(lj_comment)
