"""
Module containing class definitions for files to be tagged.
"""

import imghdr
import os
import requests

from hashlib import md5
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
    md5sum = Column(String(32), unique=True)
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

    def __init__(self, directory, filename, md5sum, url=None):
        self.directory = directory
        self.filename = filename
        self.md5sum = md5sum
        self.url = url
        # self.prefixed_filename = '_' + self.sha1_hash + '_' + filename

    def __repr__(self):
        return ("<File(directory='%s', filename='%s', "
                "sha1_hash='%s', url='%s')>" %
                (self.directory, self.filename, self.sha1_hash, self.url))

    @classmethod
    def add_file(cls, db_session, directory, filename, url=None):
        filepath = os.path.join(directory, filename)
        md5sum = md5(open(filepath, 'rb').read()).hexdigest()
        tracked_file = db_session.query(cls).\
            filter_by(md5sum=md5sum).all()
        if tracked_file:
            print "Repeated hash: %s [%s, %s]" % (
                md5sum, tracked_file[0].filepath, filepath)
            return tracked_file[0]
        return TrackedFile(directory, filename, md5sum, url)

    @classmethod
    def download_file(cls, db_session, media_path, url):
        tracked_files = db_session.query(cls).filter_by(url=url).all()
        if tracked_files:
            return tracked_files[0]

        # Download the file.
        filename = os.path.basename(urlparse(url).path)
        media_request = requests.get(url)
        # Detect an extension incase the URL doesn't have one.
        if os.path.splitext(filename)[1] == '':
            extension = imghdr.what("", media_request.content)
            if extension:
                filename += extension
            else:
                return None
        filepath = os.path.join(media_path, filename)
        with open(filepath, "w") as fptr:
            fptr.write(media_request.content)

        # Add file to DB (runs a md5sum).
        tracked_file = TrackedFile.add_file(
            db_session=db_session, directory=media_path,
            filename=filename, url=url)
        return tracked_file
