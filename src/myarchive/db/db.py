"""Generic database module using SQLAlchemy."""

import logging
import os

from sqlalchemy import create_engine, event
from sqlalchemy.engine.url import URL as SQLAlchemyURL
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import IntegrityError

from taginator.db.tables import Base, TrackedFile, Tag

# Get the module logger.
logger = logging.getLogger(__name__)


class DB(object):
    """Database linking files and tags."""

    SQLITE_MEMORY_URL = 'sqlite:///:memory:'

    db_url = property(lambda self: self.__db_url,  # pylint: disable=W0212
                      doc='Protected SQLAlchemy URL object.')
    engine = property(lambda self: self.__engine,  # pylint: disable=W0212
                      doc='Protected SQLAlchemy engine object.')
    name = property(lambda self: self.__name,  # pylint: disable=W0212
                    doc=('The name of the database we are connected to. '
                         '(None for SQLite).'))
    metadata = property(lambda self: self.__metadata,  # pylint: disable=W0212
                        doc='Protected SQLAlchemy metadata object.')
    session = property(lambda self: self.__session,  # pylint: disable=W0212
                       doc='Protected SQLAlchemy database session object.')

    logger = property(lambda self: self.__logger,  # pylint: disable=W0212
                      doc='Database logger.')
    dump_directory = property(lambda self: self.__dump_directory,  # pylint: disable=W0212
                              doc='Location of imported files.')

    def __init__(self,
                 drivername=None, username=None, password=None, db_name=None,
                 host=None, port=None, pool_size=5):
        self.__base = Base
        self.__name = db_name

        if drivername is None:
            logger.warning(
                'Using in-memory SQLite database! Results will be lost on '
                'program close!')
            self.__db_url = self.SQLITE_MEMORY_URL
        else:
            self.__db_url = SQLAlchemyURL(
                drivername=drivername,
                username=username,
                password=password,
                host=host,
                port=port,
                database=db_name
            )
            logger.debug(self.__db_url)

        logger.debug("Creating database connection.")
        if 'sqlite' in str(self.db_url):
            # SQLite does not support a pool_size argument.
            self.__engine = create_engine(self.__db_url)
            # SQLite doesn't enforce foreign keys by default due to ancient
            # sqlite2 backwards compatibility rules.  This turns that on via a
            # pragma flag every time a connection is made to the DB.
            logger.debug("Added foreign key pragma listener for SQLite DB.")
            event.listen(self.__engine, 'connect',
                         self._fk_pragma_on_connect)
        else:
            self.__engine = create_engine(self.__db_url, pool_size=pool_size)

        self.__session = scoped_session(sessionmaker(bind=self.__engine))
        self.__metadata = Base.metadata

    def __del__(self):
        if hasattr(self, '_session'):
            self.session.flush()
            self.session.close()

    @staticmethod
    def _fk_pragma_on_connect(dbapi_con, unused_con_record):
        """
        Special event trigger used for SQLite support since SQLite does
        not enforce foreign keys by default.
        """
        dbapi_con.execute('pragma foreign_keys=ON')


class TagDB(DB):

    def __init__(self,
                 drivername=None, username=None, password=None, db_name=None,
                 host=None, port=None, pool_size=5):
        super(TagDB, self).__init__(
            drivername=drivername, username=username, password=password,
            db_name=db_name, host=host, port=port, pool_size=pool_size
        )
        self.metadata.create_all(self.engine)

    def import_files(self, path):
        if os.path.isdir(path):
            for root, dirnames, filenames in os.walk(path):
                logger.debug("Importing from %s...", root)
                for filename in sorted(filenames):
                    logger.debug("Importing %s...", filename)
                    db_file = TrackedFile(root, filename)
                    try:
                        self.session.add(db_file)
                        self.session.commit()
                    except IntegrityError:
                        self.session.rollback()
                        logger.warning(
                            "Ignoring previously imported file: %s" % filename)
        if os.path.isfile(path):
            logger.debug("Importing %s...", path)
            directory, filename = os.path.split(path)
            db_file = TrackedFile(directory, filename)
            try:
                self.session.add(db_file)
                self.session.commit()
            except IntegrityError:
                self.session.rollback()
                logger.warning(
                    "Ignoring previously imported file: %s" % filename)
        logger.debug("Import Complete!")


if __name__ == '__main__':

    # Establish DB connection and session.
    db = DB()
    db.metadata.create_all(db.engine)

    tag1 = Tag('tag1')
    tag2 = Tag('tag2')
    db.session.add(tag1)
    tag1.add_child(tag2)

    # Try to cause an explosion.
    from taginator.db.tables.tag import CircularDependencyError
    try:
        tag2.add_child(tag1)
    except CircularDependencyError as e:
        logger.error("  Error: %s", e)

    for tag in db.session.query(Tag):
        logger.info(tag)
