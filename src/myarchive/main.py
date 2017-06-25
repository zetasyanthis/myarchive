#!/usr/bin/python3

import argparse
import os
import sys

from myarchive.accounts import LJ_API_ACCOUNTS
from myarchive.db.tag_db.tag_db import TagDB
from myarchive.modules.ljl_ib import LJAPIConnection
from myarchive.modules.twitter_lib import TwitterAPI
from myarchive.modules.shotwell_lib import import_from_shotwell_db
from myarchive.util.logger import myarchive_LOGGER as logger

# from gui import Gtk, MainWindow


from logging import getLogger


LOGGER = getLogger("myarchive")


def main():
    """Starts up the DB connection and GUI."""

    parser = argparse.ArgumentParser(
        description='Manages tagged files.')
    parser.add_argument(
        "--storage-folder",
        action="store",
        default=os.path.join(os.path.expanduser("~"), ".myarchive/"),
        help="Storage folder.")
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
        '--shotwell_storage_folder_override',
        action="store",
        default=None,
        help='Accepts a Shotwell file storage folder path.')
    parser.add_argument(
        '--import_lj_entries',
        action="store_true",
        default=False,
        help='Imports LJ entries.'
    )
    parser.add_argument(
        "--check_duplicates",
        action="store_true",
        default=False,
        help='Displays duplicates in TrackedFiles.'
    )
    args = parser.parse_args()
    logger.debug(args)

    # Set up objects used everywhere.
    tag_db = TagDB(
        drivername='sqlite',
        db_name=os.path.join(args.storage_folder, "myarchive.sqlite"))
    tag_db.session.autocommit = False
    media_path = os.path.join(args.storage_folder, "media/")

    if args.import_folder:
        if not os.path.exists(args.import_folder):
            raise Exception("Import folder path does not exist!")
        if not os.path.isdir(args.import_folder):
            raise Exception("Import folder path is not a folder!")

    """
    Twitter Section
    """

    if args.import_tweets_from_api:
        TwitterAPI.import_tweets_from_api(database=tag_db)
    if args.import_tweets_from_csv:
        username = None
        while username is None:
            username = input("Enter username for CSV import: ")
        if not args.username:
            logger.error("Username is required for CSV imports!")
            sys.exit(1)
        TwitterAPI.import_tweets_from_csv(
            database=tag_db,
            username=username,
            csv_filepath=args.import_tweets_from_csv,
        )
    if args.import_tweets_from_api or args.import_tweets_from_csv:
        # Parse the tweets and download associated media.
        TwitterAPI.parse_tweets(database=tag_db)
        TwitterAPI.download_media(
            database=tag_db, storage_folder=args.storage_folder)

    """
    Shotwell Section
    """

    if args.import_from_shotwell_db:
        import_from_shotwell_db(
            tag_db=tag_db,
            media_path=media_path,
            sw_database_path=args.import_from_shotwell_db,
            sw_storage_folder_override=args.shotwell_storage_folder_override,
        )

    """
    Livejournal Section
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

    if args.check_duplicates:
        from collections import defaultdict
        from myarchive.db.tag_db.tables import TrackedFile
        dup_dict = defaultdict(list)
        for tracked_file in tag_db.session.query(TrackedFile):
            dup_dict[tracked_file.md5sum].append(tracked_file.original_filename)
        duplicated_hashes = 0
        for md5sum, filenames in dup_dict.items():
            if len(filenames) > 1:
                print(md5sum)
                for filename in filenames:
                    print("    %s" % filename)
                duplicated_hashes += 1
        print("Duplicated hashes: %s" % duplicated_hashes)

    # MainWindow(tag_db)
    # Gtk.main()

    tag_db.clean_db_and_close()


if __name__ == '__main__':
    main()
