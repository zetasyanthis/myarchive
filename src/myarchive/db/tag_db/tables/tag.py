"""
Module containing definitions of tag hierarchies.
"""

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import backref, relationship
from sqlalchemy.orm.exc import NoResultFound

from myarchive.db.tag_db.tables.base import Base


RECENT_TAG_CACHE = dict()


class CircularDependencyError(Exception):
    """
    Specific exception for attempting to create a self-referential
    infinite loop.
    """
    pass


class Tag(Base):
    """
    Tag storage table.  Allows nesting of tags via self-referential
    structure.
    """

    __tablename__ = 'tags'

    tag_id = Column(
        Integer,
        doc="Auto-incrementing ID field",
        name="tag_id",
        primary_key=True)
    name = Column(
        String,
        doc="The tag name",
        name="name",
        unique=True)
    _parent_id = Column(Integer, ForeignKey("tags.tag_id"))

    children = relationship(
        "Tag",
        backref=backref('parent', remote_side=[tag_id])
    )

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return "<Tag(name='%s')>" % self.name

    def add_child(self, tag):
        """Creates an instance, performing a safety check first."""
        if self in tag.children:
            raise CircularDependencyError(
                "Attempting to create a self-referential tag loop!")
        else:
            self.children.append(tag)

    @classmethod
    def get_tag(cls, db_session, tag_name):
        global RECENT_TAG_CACHE
        if tag_name in RECENT_TAG_CACHE:
            return RECENT_TAG_CACHE[tag_name]
        try:
            tag = db_session.query(cls).filter_by(name=tag_name).one()
            RECENT_TAG_CACHE[tag_name] = tag
            return tag
        except NoResultFound:
            tag = cls(name=tag_name)
            RECENT_TAG_CACHE[tag_name] = tag
            db_session.add(tag)
            return tag
