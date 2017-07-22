#!/usr/bin/python3

import argparse
import configparser
import os
import re

from logging import getLogger

from myarchive.modules.myarchive import (
    deviantart, livejournal, shotwell, twitter, youtube)

from myarchive.db.tag_db.tag_db import TagDB
from myarchive.db.tag_db.tables.file import TrackedFile
from myarchive.util.logger import myarchive_LOGGER as logger

# from gui import Gtk, MainWindow


LOGGER = getLogger("myarchive")


def check_tf_consistency(db_session, media_storage_path):

    # Grab the md5sum named files already in the media folder.
    file_md5sums = dict()
    for root, dirnames, filenames in os.walk(media_storage_path):
        for filename in sorted(filenames):
            full_filepath = os.path.join(root, filename)
            match = re.search(r"^([0-9a-f]{32})\.?.*$", filename)
            if match:
                file_md5sums[match.group(1)] = full_filepath
            else:
                LOGGER.warning(
                    "Non-md5sum filename detected in media storage folder: %s",
                    full_filepath)

    # Check for files that are not in the DB and add their md5sums if needed.
    db_md5sums = [
        response_tuple[0] for response_tuple in
        db_session.query(TrackedFile.md5sum).all()]
    missing_md5sums = 0
    for file_md5sum, full_filepath in file_md5sums.items():
        if file_md5sum not in db_md5sums:
            missing_md5sums += 1
            tracked_file = TrackedFile.recover_file(
                filepath=full_filepath, md5sum=file_md5sum)
            db_session.add(tracked_file)
    db_session.commit()

    if missing_md5sums > 0:
        LOGGER.warning(
            "Added DB metadata for %s files in media storage folder not found "
            "in DB...", missing_md5sums)


def main():
    """Starts up the DB connection and GUI."""

    parser = argparse.ArgumentParser(
        description='Manages tagged files.')
    parser.add_argument(
        "--import_folder",
        type=str,
        dest="import_folder",
        help="Folder to organize.")
    parser.add_argument(
        '--import_from_twitter',
        nargs='*',
        action="store",
        default=None,
        help='Downloads user tweets and favorites.. Any number of CSV files '
             'from twitter exports can follow this argument. Regardless of '
             'whether any are provided, the API is polled for new tweets '
             'afterwards.')
    parser.add_argument(
        '--import_from_shotwell_db',
        action="store_true",
        default=False,
        help='Accepts a Shotwell database filepath.')
    parser.add_argument(
        "--import_from_deviantart",
        action="store_true",
        default=False,
        help='Imports files via the deviantart API.'
    )
    parser.add_argument(
        "--import_from_youtube",
        action="store_true",
        default=False,
        help='Imports files from Youtube.'
    )
    parser.add_argument(
        '--import_lj_entries',
        action="store_true",
        default=False,
        help='Imports LJ entries.'
    )
    parser.add_argument(
        '--detect_file_duplicates',
        action="store_true",
        default=False,
        help='Imports LJ entries.'
    )
    args = parser.parse_args()
    logger.debug(args)

    # Import config file data.
    config = configparser.ConfigParser()
    config.read("/etc/myarchive/myarchive.conf")
    # config.read("./myarchive/myarchive.conf")
    database_filepath = config.get(
        section="General", option="database_filepath")
    media_storage_path = config.get(
        section="General", option="media_storage_path")
    tweet_storage_path = config.get(
        section="General", option="tweet_storage_path")

    # Set up objects used everywhere.
    tag_db = TagDB(
        drivername='sqlite',
        db_name=database_filepath)
    tag_db.session.autocommit = False
    os.makedirs(media_storage_path, exist_ok=True)
    os.makedirs(tweet_storage_path, exist_ok=True)

    """
    Check media_storage_folder / TrackedFile consistency.
    """

    check_tf_consistency(
        db_session=tag_db.session, media_storage_path=media_storage_path)
    if args.detect_file_duplicates:
        db_md5sums = [
            response_tuple[0] for response_tuple in
            tag_db.session.query(TrackedFile.md5sum).all()]
        from collections import defaultdict
        md5_counters = defaultdict(int)
        for db_md5sum in db_md5sums:
            md5_counters[db_md5sum] += 1
        for md5sum, count in md5_counters.items():
            if count > 1:
                LOGGER.warning(
                    "Multiple TrackedFiles detected for md5sum: %s", md5sum)

    """
    Raw Folder Import Section
    """

    if args.import_folder:
        folder_import_glob_ignores = config.get(
            section="General", option="folder_import_glob_ignores"
        ).split("|")
        if not os.path.exists(args.import_folder):
            raise Exception("Import folder path does not exist!")
        if not os.path.isdir(args.import_folder):
            raise Exception("Import folder path is not a folder!")
        LOGGER.debug("Importing folder contents:" + args.import_folder)
        tag_db.import_files(
            import_path=args.import_folder,
            media_path=media_storage_path,
            glob_ignores=folder_import_glob_ignores)

    """
    Shotwell Section
    """

    if args.import_from_shotwell_db:
        sw_db_path = os.path.expanduser(
            config.get(section="Shotwell", option="db_filepath"))
        sw_media_path = os.path.expanduser(
            config.get(section="Shotwell", option="storage_filepath"))
        shotwell.import_from_shotwell_db(
            tag_db=tag_db,
            media_storage_path=media_storage_path,
            sw_database_path=sw_db_path,
            sw_media_path=sw_media_path,
        )

    """
    DeviantArt Section
    """

    if args.import_from_deviantart:
        deviantart.download_user_data(
            database=tag_db,
            config=config,
            media_storage_path=media_storage_path,
        )

    """
    Twitter Section
    """

    if args.import_from_twitter is not None:
        for csv_filepath in args.import_from_twitter:
            username = None
            while username is None:
                username = input(
                    "Enter username for import of %s: " % csv_filepath)
            twitter.import_tweets_from_csv(
                database=tag_db,
                config=config,
                tweet_storage_path=tweet_storage_path,
                username=username,
                csv_filepath=csv_filepath,
                media_storage_path=media_storage_path,
            )
        twitter.import_tweets_from_api(
            database=tag_db, config=config,
            tweet_storage_path=tweet_storage_path,
            media_storage_path=media_storage_path)

    if args.import_from_youtube:
        youtube_playlist_urls = config.get(
            section="Youtube", option="youtube_playlist_urls").split(",")
        youtube.download_youtube_playlists(
            tag_db.session, media_storage_path, youtube_playlist_urls)

    """
    LiveJournal Section
    """

    if args.import_lj_entries:
        livejournal.download_journals_and_comments(
            config=config,
            db_session=tag_db.session
        )

    # MainWindow(tag_db)
    # Gtk.main()

    tag_db.clean_db_and_close()


if __name__ == '__main__':
    main()
