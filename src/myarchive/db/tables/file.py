"""
Module containing class definitions for files to be tagged.
"""

from hashlib import sha1
from os.path import join
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import backref, relationship
from sqlalchemy.ext.hybrid import hybrid_property

from myarchive.db.tables.base import Base
from myarchive.db.tables.association_tables import at_file_tag


class TrackedFile(Base):
    """Class representing a file managed by the database."""

    __tablename__ = 'files'

    _id = Column(Integer, name="id", primary_key=True)
    sha1_hash = Column(String(40), unique=True)
    directory = Column(String)
    filename = Column(String)

    filepath = hybrid_property(lambda self: join(self.directory, self.filename))

    tags = relationship(
        "Tag",
        backref=backref(
            "files",
            doc="Files associated with this tag"),
        doc="Tags that have been applied to this file.",
        secondary=at_file_tag
    )

    def __init__(self, directory, filename):
        self.directory = directory
        self.filename = filename
        self.sha1_hash = sha1(open(self.filepath, 'rb').read()).hexdigest()
        self.prefixed_filename = '_' + self.sha1_hash + '_' + filename

    def __repr__(self):
        return ("<File(directory='%s', filename='%s', "
                "sha1_hash='%s')>" %
                (self.directory, self.filename, self.sha1_hash))
