from sqlalchemy import (
    Column, Integer, String, TIMESTAMP, ForeignKey)
from sqlalchemy.orm import backref, relationship
from sqlalchemy.orm.exc import NoResultFound

from myarchive.db.tables.association_tables import (
    at_ljcomment_tag, at_ljentry_tag)
from myarchive.db.tables.base import Base
from myarchive.db.tables.tag import Tag


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
    host_id = Column(
        Integer, ForeignKey("lj_hosts.id"),
        nullable=False, primary_key=True)

    entries = relationship(
        "LJEntry",
        backref=backref(
            "lj_user",
            doc="The user who wrote this entry.",
            uselist=False),
        doc="Entries written by this user."
    )
    comments = relationship(
        "LJComment",
        backref=backref(
            "lj_user",
            doc="User this comment belongs to.",
            uselist=False),
        doc="Comments on this entry.",
    )

    def __init__(self, user_id, username):
        self.user_id = user_id
        self.username = username

    @classmethod
    def get_user(cls, db_session, user_id, username):
        try:
            ljuser = db_session.query(cls).filter_by(user_id=user_id).one()
        except NoResultFound:
            ljuser = LJUser(user_id=user_id, username=username)
        return ljuser


class LJEntry(Base):
    """Class representing an entry retrieved from a LJ-like service."""

    __tablename__ = 'lj_entries'

    user_id = Column(Integer, index=True, primary_key=True)
    username = Column(String, nullable=False, )
    itemid = Column(Integer, index=True, primary_key=True)
    eventtime = Column(TIMESTAMP)
    subject = Column(String)
    text = Column(String)
    current_music = Column(String)

    comments = relationship(
        "LJComment",
        backref=backref(
            "lj_entry",
            doc="Entry this comment belongs to.",
            uselist=False),
        doc="Comments on this entry.",
    )
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

    @classmethod
    def get_or_add_entry(
            cls, db_session, lj_user, itemid, eventtime, subject, text,
            current_music, tag_list):
        try:
            lj_entry = db_session.query(cls).filter_by(itemid=itemid).one()
        except NoResultFound:
            lj_entry = cls(
                itemid, eventtime, subject, text, current_music)
        lj_user.entries.append(lj_entry)
        if tag_list:
            for tag_name in tag_list.split(", "):
                tag = Tag.get_tag(db_session=db_session, tag_name=tag_name)
                lj_entry.tags.append(tag)
        return lj_entry


class LJComment(Base):
    """Class representing a comment retrieved from a LJ-like service."""

    __tablename__ = 'lj_comments'

    itemid = Column(Integer, index=True, primary_key=True)
    subject = Column(String)
    body = Column(String)
    date = Column(TIMESTAMP)
    parent_id = Column(Integer, ForeignKey("lj_comments.itemid"))
    entry_id = Column(
        Integer, ForeignKey("lj_entries.itemid"),
        nullable=False, primary_key=True)
    user_id = Column(
        Integer, ForeignKey("lj_users.user_id"),
        nullable=False, primary_key=True)

    children = relationship(
        "LJComment",
        backref=backref('parent_comment', remote_side=[itemid])
    )
    tags = relationship(
        "Tag",
        backref=backref(
            "lj_comments",
            doc="Entries associated with this tag"),
        doc="Tags that have been applied to this entry.",
        secondary=at_ljcomment_tag
    )

    def __init__(self, itemid, subject, body, date):
        self.itemid = itemid
        self.subject = subject
        self.body = body
        self.date = date

    @classmethod
    def get_or_add_comment(
            cls, db_session, lj_user, lj_entry, itemid, subject, body, date,
            parent_id):
        try:
            lj_comment = db_session.query(cls).filter_by(itemid=itemid).one()
        except NoResultFound:
            lj_comment = cls(itemid, subject, body, date)
        lj_user.comments.append(lj_comment)
        lj_entry.comments.append(lj_comment)
        if parent_id:
            parent_comment = db_session.query(cls). \
                filter_by(itemid=int(parent_id)).one()
            parent_comment.add_child(lj_comment)
        return lj_comment

    def add_child(self, lj_comment):
        """Creates an instance, performing a safety check first."""
        if self in lj_comment.children:
            raise CircularDependencyError(
                "Attempting to create a self-referential comment loop!")
        else:
            self.children.append(lj_comment)
