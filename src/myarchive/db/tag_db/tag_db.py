"""Main database used by myarchive."""

import logging
import os

from myarchive.db.db import DB
from sqlalchemy.exc import IntegrityError

from myarchive.db.tag_db.tables import (
    Base, TrackedFile, Tag, RawTweet, Tweet)

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
        tweet_ids = [
            returned_tuple[0]
            for returned_tuple in
            self.session.query(Tweet.id).all()]
        rawtweet_ids = [
            returned_tuple[0]
            for returned_tuple in
            self.session.query(RawTweet.id).all()]
        tweet_id_set = set(tweet_ids)
        tweet_id_set.update(rawtweet_ids)
        return tweet_id_set

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
        # Run VACUUM.
        self.session.close()
        connection = self.engine.raw_connection()
        cursor = connection.cursor()
        cursor.execute("VACUUM")
        connection.commit()
        cursor.close()
