#!/usr/bin/python3

import argparse
import configparser
import os

from logging import getLogger

from myarchive.modules import dalib, shotwelllib

from myarchive.db.tag_db.tag_db import TagDB
from myarchive.modules.ljlib import LJAPIConnection
from myarchive.modules.twitterlib import TwitterAPI
from myarchive.util.logger import myarchive_LOGGER as logger

# from gui import Gtk, MainWindow


LOGGER = getLogger("myarchive")


def main():
    """Starts up the DB connection and GUI."""

    parser = argparse.ArgumentParser(
        description='Manages tagged files.')
    parser.add_argument(
        "--import-folder",
        type=str,
        dest="import_folder",
        help="Folder to organize.")
    parser.add_argument(
        '--import_tweets_from_api',
        action="store_true",
        default=False,
        help='Downloads user tweets and favorites..')
    parser.add_argument(
        '--import_tweets_from_csv',
        action="store",
        help='Accepts a CSV filepath..')
    parser.add_argument(
        '--import_from_shotwell_db',
        action="store_true",
        default=False,
        help='Accepts a Shotwell database filepath.')
    parser.add_argument(
        "--import_from_deviantart",
        action="store_true",
        default=False,
        help='Displays duplicates in TrackedFiles.'
    )
    parser.add_argument(
        '--import_lj_entries',
        action="store_true",
        default=False,
        help='Imports LJ entries.'
    )
    parser.add_argument(
        "--import_folder",
        action="store",
        help='Displays duplicates in TrackedFiles.'
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
    Raw folder import section
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
        shotwelllib.import_from_shotwell_db(
            tag_db=tag_db,
            media_storage_path=media_storage_path,
            sw_database_path=sw_db_path,
            sw_media_path=sw_media_path,
        )

    """
    Twitter Section
    """

    if args.import_tweets_from_api:
        TwitterAPI.import_tweets_from_api(
            database=tag_db, config=config,
            tweet_storage_path=tweet_storage_path,
            media_storage_path=media_storage_path)
    if args.import_tweets_from_csv:
        username = None
        while username is None:
            username = input("Enter username for CSV import: ")
        TwitterAPI.import_tweets_from_csv(
            database=tag_db,
            config=config,
            tweet_storage_path=tweet_storage_path,
            username=username,
            csv_filepath=args.import_tweets_from_csv,
            media_storage_path=media_storage_path,
        )
    if args.import_tweets_from_api or args.import_tweets_from_csv:
        # Parse the tweets and download associated media.
        LOGGER.info("Downloading media files...")
        TwitterAPI.download_media(
            database=tag_db, media_storage_path=media_storage_path)

    """
    DeviantArt Section
    """

    if args.import_from_deviantart:
        dalib.download_user_data(
            database=tag_db,
            config=config,
            media_storage_path=media_storage_path,
        )

    """
    LiveJournal Section
    """

    if args.import_lj_entries:
        for lj_api_account in LJ_API_ACCOUNTS:
            ljapi = LJAPIConnection(
                db_session=tag_db.session,
                host=lj_api_account.host,
                user_agent=lj_api_account.user_agent,
                username=lj_api_account.username,
                password=lj_api_account.password
            )
            ljapi.download_journals_and_comments(db_session=tag_db.session)

    # MainWindow(tag_db)
    # Gtk.main()

    tag_db.clean_db_and_close()


if __name__ == '__main__':
    main()
