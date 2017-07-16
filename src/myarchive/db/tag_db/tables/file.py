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
from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound
from sqlalchemy.ext.hybrid import hybrid_property

from myarchive.db.tag_db.tables.association_tables import at_file_tag
from myarchive.db.tag_db.tables.base import Base

LOGGER = logging.getLogger(__name__)

MAX_BUFFER = 16 * 2 ** 20


class TrackedFile(Base):
    """Class representing a file managed by the database."""

    __tablename__ = 'files'

    _id = Column(Integer, name="id", primary_key=True)
    file_source = Column(String)
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

    @hybrid_property
    def tag_names(self):
        return [tag.name for tag in self.tags]

    def __init__(self, file_source, original_filename,
                 filepath, md5sum, url=None):
        self.file_source = file_source
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
                 file_source,
                 file_buffer=None,
                 copy_from_filepath=None,
                 original_filename=None,
                 url=None,
                 md5sum_override=None,
                 move_original_file=False):

        def set_params(tracked_file, file_source, original_filename, url):
            tracked_file.original_filename = original_filename
            tracked_file.url = url
            tracked_file.file_source = file_source
            return tracked_file

        existing = False
        if file_buffer is not None:
            md5sum = md5(file_buffer).hexdigest()
            # Fix up extensions in case they're wrong.
            extension = fix_file_extension(
                file_buffer=file_buffer, original_filename=original_filename)
            filepath = os.path.join(media_path, str(md5sum)) + extension
            try:
                tracked_file = \
                    db_session.query(cls).filter_by(md5sum=md5sum).one()
                LOGGER.debug(
                    "Repeated hash: %s [%s, %s]",
                    md5sum, tracked_file.original_filename, original_filename)
                existing = True
            except NoResultFound:
                tracked_file = TrackedFile(
                    file_source, original_filename, filepath, md5sum, url)
            except MultipleResultsFound:
                LOGGER.critical(
                    [file_source, original_filename, filepath, md5sum, url])
                raise
            if existing is True:
                # Update the database record of the file if it doesn't have
                # original_filename set. (This means that we recovered the file
                # while checking if all the files in the media folder were in
                # the DB and don't have the metadata to back it up.)
                if tracked_file.original_filename is None:
                    adjusted_file = set_params(
                        tracked_file, file_source, original_filename, url)
                    return adjusted_file, existing
                return tracked_file, existing
            else:
                with open(filepath, "wb") as fptr:
                    fptr.write(file_buffer)
        elif copy_from_filepath is not None:
            original_filename = os.path.basename(copy_from_filepath)

            # Fix up extensions in case they're wrong.
            extension = fix_file_extension(original_filename=original_filename)

            # Reopen just a pointer for md5sum, since we don't want to load
            # massive files into memory.
            if md5sum_override is not None:
                md5sum = md5sum_override
            else:
                with open(copy_from_filepath, 'rb') as fptr:
                    md5sum = get_fptr_md5sum(fptr=fptr)
            filepath = os.path.join(media_path, md5sum + extension)

            try:
                tracked_file = \
                    db_session.query(cls).filter_by(md5sum=md5sum).one()
                LOGGER.debug(
                    "Repeated hash: %s [%s, %s]",
                    md5sum, tracked_file.original_filename, original_filename)
                existing = True
            except NoResultFound:
                tracked_file = TrackedFile(
                    file_source, original_filename, filepath, md5sum, url)
            except MultipleResultsFound:
                LOGGER.critical(
                    [file_source, original_filename, filepath, md5sum, url])
                raise

            if existing is True:
                # Update the database record of the file if it doesn't have
                # original_filename set. (This means that we recovered the file
                # while checking if all the files in the media folder were in
                # the DB and don't have the metadata to back it up.)
                if tracked_file.original_filename is None:
                    adjusted_file = set_params(
                        tracked_file, file_source, original_filename, url)
                    return adjusted_file, existing
                return tracked_file, existing
            else:
                if move_original_file is True:
                    shutil.move(src=copy_from_filepath, dst=filepath)
                else:
                    shutil.copy2(src=copy_from_filepath, dst=filepath)
        else:
            raise Exception("Not sure what to do with this???")

        return TrackedFile(
            file_source, original_filename, filepath, md5sum, url), existing

    @classmethod
    def recover_file(cls, md5sum, filepath):
        """
        Only to be used for recovering DB information for files already in the
        media_storage_path.
        """
        return TrackedFile(None, None, filepath, md5sum, None)

    @classmethod
    def download_file(cls, db_session, media_path, url, file_source,
                      filename_override=None, saved_url_override=None):

        # Allow overriding the URL we save with the file. Sometimes we want
        # the origin page, like on deviantart.
        if saved_url_override is not None:
            saved_url = saved_url_override
        else:
            saved_url = url

        tracked_files = db_session.query(cls).filter_by(url=saved_url).all()
        if tracked_files:
            return tracked_files[0], True

        # Download the file.
        if filename_override is not None:
            extension = os.path.splitext(
                os.path.basename(urlparse(url).path))[1]
            filename = filename_override + extension
        else:
            filename = os.path.basename(urlparse(url).path)
        LOGGER.info("Downloading %s...", url)
        media_request = requests.get(url)

        # Add file to DB (runs a md5sum).
        tracked_file, existing = TrackedFile.add_file(
            file_source=file_source,
            db_session=db_session,
            media_path=media_path,
            file_buffer=media_request.content,
            original_filename=filename,
            url=saved_url)
        return tracked_file, existing


def get_md5sum_by_filename(file_id, filepath, block_size=2**20):
    with open(filepath, "rb") as fptr:
        md5sum = get_fptr_md5sum(fptr, block_size)
    # Can't do this here.
    # extension = fix_file_extension(filepath)
    return file_id, filepath, md5sum


def get_fptr_md5sum(fptr, block_size=2**20):
    """Processes a file md5sum 1MB at a time."""
    md5 = hashlib.md5()
    while True:
        data = fptr.read(block_size)
        if not data:
            break
        md5.update(data)
    return md5.hexdigest()


def fix_file_extension(original_filename, file_buffer=None):
    """
    Returns a fixed extension for a file buffer. (Many services, especially
    furaffinity and twitter, sometimes return files with the wrong extension or
    without extensions at all!)
    """
    filename, extension = os.path.splitext(original_filename)
    try:
        imghdr_extension = "." + imghdr.what(original_filename, h=file_buffer)
        if imghdr_extension == ".jpeg":
            imghdr_extension = ".jpg"
    except:
        imghdr_extension = None
    if imghdr_extension and imghdr_extension != extension:
        # LOGGER.warning("Fixing extension on '%s'. ('%s' -> '%s')",
        #                original_filename, extension, imghdr_extension)
        return imghdr_extension
    return extension
