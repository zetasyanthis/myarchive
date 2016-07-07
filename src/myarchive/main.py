#!/usr/bin/python

import argparse
import os
import sys

import twitterlib
from db import TagDB
# from gui import Gtk, MainWindow
from util.logger import myarchive_LOGGER as logger


def main():
    """Starts up the DB connection and GUI."""

    parser = argparse.ArgumentParser(
        description='Manages tagged files.')
    parser.add_argument(
        "-D", "--db_filename",
        action="store",
        default="/tmp/myarchive/db/archive.sqlite",
        help="Database filename.")
    parser.add_argument(
        '--media-path',
        action="store",
        default="/tmp/myarchive/media/",
        help='Prints all tweets.')
    parser.add_argument(
        "--import-folder",
        type=str,
        dest="import_folder",
        help="Folder to organize.")
    parser.add_argument(
        '--username',
        action="store",
        help='Accepts a service username.')
    parser.add_argument(
        '--import-tweets-from-api',
        action="store_true",
        default=False,
        help='Downloads favorites. Accepts a Twitter username.')
    parser.add_argument(
        '--import-tweets-from-archive-csv',
        action="store",
        help='Downloads favorites. Accepts a Twitter username.')
    parser.add_argument(
        '--parse-tweets',
        action="store_true",
        default=False,
        help='Prints all tweets.')
    parser.add_argument(
        '--print-tweets',
        action="store_true",
        default=False,
        help='Prints all tweets.')
    args = parser.parse_args()

    logger.debug(args)

    if args.import_folder:
        if not os.path.exists(args.import_folder):
            raise Exception("Import folder path does not exist!")
        if not os.path.isdir(args.import_folder):
            raise Exception("Import folder path is not a folder!")

    if args.db_filename:
        tag_db = TagDB(
            drivername='sqlite',
            db_name=args.db_filename)
    else:
        tag_db = TagDB()

    new_ids = None
    if args.import_tweets_from_api:
        if not args.username:
            logger.error("Username is required for tweet imports!")
            sys.exit(1)
        new_ids = twitterlib.archive_tweets(
            db_session=tag_db.session,
            username=args.username)
    if args.import_tweets_from_archive_csv:
        if not args.username:
            logger.error("Username is required for tweet imports!")
            sys.exit(1)
        new_ids = twitterlib.import_from_csv(
            db_session=tag_db.session,
            csv_filepath=args.import_tweets_from_archive_csv,
            username=args.username)
    if args.parse_tweets is True:
        twitterlib.parse_tweets(
            db_session=tag_db.session, media_path=args.media_path)
    if args.print_tweets is True:
        twitterlib.print_tweets(db_session=tag_db.session)

    if new_ids:
        print "Processing new tweets with the following IDs: %s" % new_ids
        twitterlib.parse_tweets(
            db_session=tag_db.session, media_path=args.media_path,
            new_ids=new_ids)

    # MainWindow(tag_db)
    # Gtk.main()


if __name__ == '__main__':
    main()
