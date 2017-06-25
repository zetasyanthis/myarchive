"""
Module containing class definitions for files to be tagged.
"""

import hashlib
import imghdr
import logging
import os
import requests
import shutil

from hashlib import md5
from urllib.parse import urlparse
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import backref, relationship

from myarchive.db.tag_db.tables.association_tables import at_file_tag
from myarchive.db.tag_db.tables.base import Base

LOGGER = logging.getLogger(__name__)


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
    def add_file(cls, db_session, media_path,
                 file_buffer=None,
                 copy_from_filepath=None,
                 original_filename=None,
                 url=None):
        existing = False
        if file_buffer is not None:
            md5sum = md5(file_buffer).hexdigest()
            # Detect an extension incase the URL doesn't have one.
            extension = os.path.splitext(original_filename)[1]
            if extension == '':
                imghdr_extension = imghdr.what("", file_buffer)
                if imghdr_extension:
                    extension = "." + imghdr_extension
            filepath = os.path.join(media_path, str(md5sum)) + extension
            tracked_file = db_session.query(cls).filter_by(md5sum=md5sum).all()
            if tracked_file:
                LOGGER.debug(
                    "Repeated hash: %s [%s, %s]",
                    md5sum, tracked_file[0].filepath, filepath)
                existing = True
            else:
                with open(filepath, "wb") as fptr:
                    fptr.write(file_buffer)
        elif copy_from_filepath is not None:
            original_filename = os.path.basename(copy_from_filepath)
            extension = os.path.splitext(original_filename)[1]
            with open(copy_from_filepath, 'rb') as fptr:
                md5sum = cls.get_file_md5sum(fptr=fptr)
            filepath = os.path.join(media_path, md5sum + extension)
            tracked_file = db_session.query(cls).filter_by(md5sum=md5sum).all()
            if tracked_file:
                existing = True
                LOGGER.debug(
                    "Repeated hash: %s [%s, %s]",
                    md5sum, tracked_file[0].filepath, filepath)
            else:
                shutil.copy2(src=copy_from_filepath, dst=filepath)
        else:
            raise Exception("Not sure what to do with this???")

        return TrackedFile(original_filename, filepath, md5sum, url), existing

    @classmethod
    def download_file(cls, db_session, media_path, url):
        tracked_files = db_session.query(cls).filter_by(url=url).all()
        if tracked_files:
            return tracked_files[0]

        # Download the file.
        filename = os.path.basename(urlparse(url).path)
        LOGGER.info("Downloading %s...", url)
        media_request = requests.get(url)

        # Add file to DB (runs a md5sum).
        tracked_file = TrackedFile.add_file(
            db_session=db_session,
            media_path=media_path,
            file_buffer=media_request.content,
            original_filename=filename,
            url=url)
        return tracked_file

    @staticmethod
    def get_file_md5sum(fptr, block_size=2 ** 20):
        md5 = hashlib.md5()
        while True:
            data = fptr.read(block_size)
            if not data:
                break
            md5.update(data)
        return md5.hexdigest()
