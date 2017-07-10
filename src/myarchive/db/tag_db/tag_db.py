"""Main database used by myarchive."""

import logging
import fnmatch
import os

from myarchive.db.db import DB

from myarchive.db.tag_db.tables import Base, TrackedFile, Tweet

# Get the module logger.
LOGGER = logging.getLogger(__name__)


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
        tweet_id_set = set(tweet_ids)
        return tweet_id_set

    def import_files(self, import_path, media_path, glob_ignores):
        if os.path.isdir(import_path):
            for root, dirnames, filenames in os.walk(import_path):
                for filename in sorted(filenames):
                    glob_match = False
                    for glob_ignore in glob_ignores:
                        if fnmatch.fnmatch(name=filename, pat=glob_ignore):
                            glob_match = True
                    if glob_match:
                        continue
                    full_filepath = os.path.join(root, filename)
                    LOGGER.debug("Importing %s...", full_filepath)
                    db_file, existing = TrackedFile.add_file(
                        db_session=self.session,
                        media_path=media_path,
                        copy_from_filepath=full_filepath,
                        original_filename=filename)
                    if existing is False:
                        self.session.add(db_file)
                self.session.commit()
        elif os.path.isfile(import_path):
            LOGGER.debug("Importing %s...", import_path)
            directory, filename = os.path.split(import_path)
            db_file, existing = TrackedFile.add_file(
                db_session=self.session,
                media_path=media_path,
                copy_from_filepath=import_path,
                original_filename=filename)
            if existing is False:
                self.session.add(db_file)
        else:
            LOGGER.error("Path does not exist: %s", import_path)
        self.session.commit()
        LOGGER.debug("Import Complete!")

    def clean_db_and_close(self):
        # Run VACUUM.
        self.session.close()
        connection = self.engine.raw_connection()
        cursor = connection.cursor()
        cursor.execute("VACUUM")
        connection.commit()
        cursor.close()
