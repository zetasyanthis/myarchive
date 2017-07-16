"""
Module containing class definitions for files to be tagged.
"""

import logging

from deviantart.api import DeviantartError
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import backref, relationship
from sqlalchemy.ext.hybrid import hybrid_property

from myarchive.db.tag_db.tables.association_tables import at_deviation_tag
from myarchive.db.tag_db.tables.base import Base
from myarchive.db.tag_db.tables.file import TrackedFile


LOGGER = logging.getLogger(__name__)


EXISTING_USERNAME_CACHE = list()
HASHTAG_REGEX = r'#([\d\w]+)'


class DeviantArtUser(Base):
    """Class representing a DA user stored by the database."""

    __tablename__ = 'dausers'

    id = Column(Integer, index=True, primary_key=True)
    userid = Column(String)
    name = Column(String)
    profile = Column(String)
    stats = Column(String)
    details = Column(String)
    icon_id = Column(Integer, ForeignKey("files.id"))

    icon = relationship(
        "TrackedFile",
        doc="User icon.",
        uselist=False,
    )

    def __init__(self, userid, name, profile, stats, details):
        self.userid = userid
        self.name = name
        self.profile = profile
        self.stats = stats
        self.details = details

    def __repr__(self):
        return "<DeviantArtUser(name='%s')>" % self.name


class Deviation(Base):
    """Class representing a Deviation stored by the database."""

    __tablename__ = 'deviations'

    id = Column(Integer, index=True, primary_key=True)
    title = Column(String)
    description = Column(String)
    deviationid = Column(String)
    file_id = Column(Integer, ForeignKey("files.id"))

    file = relationship(
        "TrackedFile",
        doc="File associated with deviation.",
        uselist=False,
    )
    tags = relationship(
        "Tag",
        backref=backref(
            "deviations",
            doc="Deviations associated with this tag"),
        doc="Tags that have been applied to this deviation.",
        secondary=at_deviation_tag,
    )

    @hybrid_property
    def tag_names(self):
        return [tag.name for tag in self.tags]

    def __init__(self, title, description, deviationid):
        self.title = title
        self.description = description
        self.deviationid = deviationid


def get_da_user(db_session, da_api, username, media_storage_path):
    """
    Returns the DB user object if it exists, otherwise it grabs the user data
    from the API and stuffs it in the DB.
    """
    global EXISTING_USERNAME_CACHE
    if len(EXISTING_USERNAME_CACHE) == 0:
        EXISTING_USERNAME_CACHE = [
            username[0] for username in
            db_session.query(DeviantArtUser.name).all()]
    # Grab the User object from the API.
    if username in EXISTING_USERNAME_CACHE:
        da_user = db_session.query(DeviantArtUser).\
            filter_by(name=username).one()
    else:
        EXISTING_USERNAME_CACHE.append(username)
        try:
            user = da_api.get_user(username=username)
        except DeviantartError:
            LOGGER.error("Unable to obtain user data for %s", username)
            return None
        da_user = DeviantArtUser(
            userid=user.userid,
            name=user.username,
            profile=str(user.profile),
            stats=str(user.stats),
            details=str(user.details)
        )
        icon_file, existing = TrackedFile.download_file(
            file_source="deviantart",
            db_session=db_session,
            media_path=media_storage_path,
            url=user.usericon)
        da_user.icon = icon_file
        db_session.add(da_user)
        db_session.commit()
    return da_user
