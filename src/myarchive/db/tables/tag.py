"""
Module containing definitions of tag hierarchies.
"""

from sqlalchemy import Column, ForeignKey, Integer, String, Table
from sqlalchemy.orm import backref, relationship

from myarchive.db.tables.base import Base


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

    _at_tag_tag = Table(
        'at_tag_tag', Base.metadata,
        Column("tag1_id", Integer, ForeignKey("tags.id"), primary_key=True),
        Column("tag2_id", Integer, ForeignKey("tags.id"), primary_key=True),
        info="Association table for self-referential many-to-many mappings.")

    __tablename__ = 'tags'

    _id = Column(Integer,
                 doc="Auto-incrementing ID field",
                 name="id",
                 primary_key=True)
    name = Column(String,
                  doc="The tag name",
                  name="name",
                  unique=True)

    __child_tags = relationship(
        "Tag",
        doc="Child tags.  DO NOT APPEND TO THIS RELATIONSHIP DIRECTLY! Use "
            "add_child() for safety!",
        backref=backref(
            "__parent_tags",
            doc=("Parent tags. DO NOT APPEND TO THIS RELATIONSHIP DIRECTLY! "
                 "Use add_child() for safety!")),
        primaryjoin=(_id == _at_tag_tag.c.tag1_id),
        secondaryjoin=(_id == _at_tag_tag.c.tag2_id),
        secondary=_at_tag_tag)

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return "<Tag(name='%s')>" % self.name

    def add_child(self, tag):
        """Creates an instance, performing a safety check first."""
        if self in tag.get_child_tags():
            raise CircularDependencyError(
                "Attempting to create a self-referential tag loop!")
        else:
            self.__child_tags.append(tag)

    def get_child_tags(self):
        return self.__child_tags
