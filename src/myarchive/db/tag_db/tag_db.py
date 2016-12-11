"""Generic database module using SQLAlchemy."""

import logging
import os

from myarchive.db.db import DB
from sqlalchemy.exc import IntegrityError

from myarchive.db.tag_db import Base, TrackedFile, Tag, Tweet, CSVTweet

# Get the module logger.
logger = logging.getLogger(__name__)


class TagDB(DB):

    def __init__(self,
                 drivername=None, username=None, password=None, db_name=None,
                 host=None, port=None, pool_size=5):
        super(TagDB, self).__init__(
            base=Base, drivername=drivername, username=username,
            password=password, db_name=db_name, host=host, port=port,
            pool_size=pool_size
        )
        self.metadata.create_all(self.engine)
        self.existing_tweet_ids = None

    def get_existing_tweet_ids(self):
        if not self.existing_tweet_ids:
            self.existing_tweet_ids = tuple([
               returned_tuple[0]
               for returned_tuple in
               self.session.query(Tweet.id).all()])
        return self.existing_tweet_ids

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

    def clean_db_and_close(self):

        # Clean all imported CSVTweets.
        imported_tweets = self.session.query(CSVTweet). \
            filter_by(api_import_complete=True).all()
        for imported_tweet in imported_tweets:
            self.session.delete(imported_tweet)
        self.session.commit()

        # Run VACUUM.
        self.session.close()
        connection = self.engine.raw_connection()
        cursor = connection.cursor()
        cursor.execute("VACUUM")
        connection.commit()
        cursor.close()
