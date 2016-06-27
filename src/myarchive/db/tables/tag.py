"""
Module containing definitions of tag hierarchies.
"""

from sqlalchemy import Column, ForeignKey, Integer, String, Table
from sqlalchemy.orm import backref, relationship

from taginator.db.tables.base import Base


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

    child_tags = relationship(
        "Tag",
        doc="Child tags.  DO NOT APPEND TO THIS RELATIONSHIP DIRECTLY! Use "
            "add_child() for safety!",
        backref=backref(
            "parent_tags",
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
        if self in tag.child_tags:
            raise CircularDependencyError(
                "Attempting to create an infinite self referential loop!")
        else:
            self.child_tags.append(tag)
