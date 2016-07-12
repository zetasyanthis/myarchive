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

from myarchive.db.tables.base import Base
from myarchive.db.tables.association_tables import at_file_tag


class TrackedFile(Base):
    """Class representing a file managed by the database."""

    __tablename__ = 'files'

    _id = Column(Integer, name="id", primary_key=True)
    original_filename = Column(String)
    filepath = Column(String)
    md5sum = Column(String(32), index=True)
    url = Column(String, index=True)

    tags = relationship(
        "Tag",
        backref=backref(
            "files",
            doc="Files associated with this tag"),
        doc="Tags that have been applied to this file.",
        secondary=at_file_tag
    )

    def __init__(self, original_filename, filepath, md5sum, url=None):
        self.original_filename = original_filename
        self.filepath = filepath
        self.md5sum = md5sum
        self.url = url

    def __repr__(self):
        return ("<File(original_filename='%s', filepath='%s', "
                "md5sum='%s', url='%s')>" %
                (self.original_filename, self.filepath, self.md5sum, self.url))

    @classmethod
    def add_file(cls, db_session, media_path, file_buffer=None,
                 original_filename=None, url=None):
        if file_buffer is not None:
            md5sum = md5(file_buffer).hexdigest()
            # Detect an extension incase the URL doesn't have one.
            extension = os.path.splitext(original_filename)[1]
            if extension == '':
                imghdr_extension = imghdr.what("", file_buffer)
                if imghdr_extension:
                    extension = "." + imghdr_extension
            filepath = os.path.join(media_path, str(md5sum)) + extension
            with open(filepath, "w") as fptr:
                fptr.write(file_buffer)
        else:
            filepath = os.path.join(os.path.join(media_path, original_filename))
            md5sum = md5(open(filepath, 'rb').read()).hexdigest()
        tracked_file = db_session.query(cls).\
            filter_by(md5sum=md5sum).all()
        if tracked_file:
            print "Repeated hash: %s [%s, %s]" % (
                md5sum, tracked_file[0].filepath, filepath)
        return TrackedFile(original_filename, filepath, md5sum, url)

    @classmethod
    def download_file(cls, db_session, media_path, url):
        tracked_files = db_session.query(cls).filter_by(url=url).all()
        if tracked_files:
            return tracked_files[0]

        # Download the file.
        filename = os.path.basename(urlparse(url).path)
        print "Downloading %s..." % url
        media_request = requests.get(url)

        # Add file to DB (runs a md5sum).
        tracked_file = TrackedFile.add_file(
            db_session=db_session,
            media_path=media_path,
            file_buffer=media_request.content,
            original_filename=filename,
            url=url)
        return tracked_file
