"""
Module containing class definitions for files to be tagged.
"""

import os
import requests

from hashlib import sha1
from urlparse import urlparse
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import backref, relationship
from sqlalchemy.ext.hybrid import hybrid_property

from myarchive.db.tables.base import Base
from myarchive.db.tables.association_tables import at_file_tag


class TrackedFile(Base):
    """Class representing a file managed by the database."""

    __tablename__ = 'files'

    _id = Column(Integer, name="id", primary_key=True)
    directory = Column(String)
    filename = Column(String)
    sha1_hash = Column(String(40), unique=True)
    url = Column(String)

    filepath = hybrid_property(
        lambda self: os.path.join(self.directory, self.filename))

    tags = relationship(
        "Tag",
        backref=backref(
            "files",
            doc="Files associated with this tag"),
        doc="Tags that have been applied to this file.",
        secondary=at_file_tag
    )

    def __init__(self, directory, filename, sha1_hash, url=None):
        self.directory = directory
        self.filename = filename
        self.sha1_hash = sha1_hash
        self.url = url
        # self.prefixed_filename = '_' + self.sha1_hash + '_' + filename

    def __repr__(self):
        return ("<File(directory='%s', filename='%s', "
                "sha1_hash='%s', url='%s')>" %
                (self.directory, self.filename, self.sha1_hash, self.url))

    @classmethod
    def add_file(cls, db_session, directory, filename, url=None):
        filepath = os.path.join(directory, filename)
        sha1_hash = sha1(open(filepath, 'rb').read()).\
            hexdigest()
        tracked_file = db_session.query(cls).\
            filter_by(sha1_hash=sha1_hash).all()
        if tracked_file:
            print "Repeated hash: %s [%s, %s]" % (
                sha1_hash, tracked_file[0].filepath, filepath)
            return tracked_file[0]
        return TrackedFile(directory, filename, sha1_hash, url)

    @classmethod
    def download_file(cls, db_session, media_path, url):
        tracked_files = db_session.query(cls).filter_by(url=url).all()
        if tracked_files:
            return tracked_files[0]

        # Download the file.
        filename = os.path.basename(urlparse(url).path)
        filepath = os.path.join(media_path, filename)
        media_request = requests.get(url)
        with open(filepath, "w") as fptr:
            fptr.write(media_request.content)

        # Add file to DB (runs a sha1sum).
        tracked_file = TrackedFile.add_file(
            db_session=db_session, directory=media_path,
            filename=filename, url=url)
        return tracked_file
