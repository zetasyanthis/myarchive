#!/usr/bin/python

import argparse
import os
import sys

from twitterlib import TwitterAPI
from ljlib import LJAPIConnection
from accounts import LJ_API_ACCOUNTS, TWITTER_API_ACCOUNTS
from db import TagDB
# from gui import Gtk, MainWindow
from util.logger import myarchive_LOGGER as logger


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
        '--username',
        action="store",
        help='Accepts a service username.')
    parser.add_argument(
        '--import-tweets-from-api',
        action="store_true",
        default=False,
        help='Downloads user tweets and favorites..')
    parser.add_argument(
        '--import-tweets-from-archive-csv',
        action="store",
        help='Accepts a CSV filepath..')
    parser.add_argument(
        '--parse-tweets',
        action="store_true",
        default=False,
        help='Prints all tweets.')
    parser.add_argument(
        '--download-media',
        action="store_true",
        default=False,
        help="Downloads all associated media.")
    parser.add_argument(
        '--print-tweets',
        action="store_true",
        default=False,
        help='Prints all tweets.')
    parser.add_argument(
        '--import_lj_entries',
        action="store_true",
        default=False,
        help='Imports LJ entries.'
    )
    args = parser.parse_args()

    logger.debug(args)

    if args.import_folder:
        if not os.path.exists(args.import_folder):
            raise Exception("Import folder path does not exist!")
        if not os.path.isdir(args.import_folder):
            raise Exception("Import folder path is not a folder!")

    tag_db = TagDB(
        drivername='sqlite',
        db_name=os.path.join(args.storage_folder, "archive.sqlite"))
    tag_db.session.autocommit = False

    raw_tweets = []
    csv_only_tweets = []
    if args.import_tweets_from_api:
        for twitter_api_account in TWITTER_API_ACCOUNTS:
            api = TwitterAPI(
                consumer_key=twitter_api_account.consumer_key,
                consumer_secret=twitter_api_account.consumer_secret,
                access_token_key=twitter_api_account.access_key,
                access_token_secret=twitter_api_account.access_secret,
                sleep_on_rate_limit=True)
            raw_tweets.extend(
                api.archive_tweets(
                    db_session=tag_db.session,
                    username=twitter_api_account.username
                )
            )
    if args.import_tweets_from_archive_csv:
        if not args.username:
            logger.error("Username is required for CSV imports!")
            sys.exit(1)
        for twitter_api_account in TWITTER_API_ACCOUNTS:
            if args.username == twitter_api_account.username:
                api = TwitterAPI(
                    consumer_key=twitter_api_account.consumer_key,
                    consumer_secret=twitter_api_account.consumer_secret,
                    access_token_key=twitter_api_account.access_key,
                    access_token_secret=twitter_api_account.access_secret,
                    sleep_on_rate_limit=True)
                csv_raw_tweets, csv_only_tweets = api.import_from_csv(
                    db_session=tag_db.session,
                    csv_filepath=args.import_tweets_from_archive_csv,
                    username=twitter_api_account.username)
                raw_tweets.extend(csv_raw_tweets)
                break
            else:
                raise Exception(
                    "Unable to find matching TwitterAPIAccount for CSV import.")
    if args.parse_tweets is True:
        TwitterAPI.parse_tweets(
            db_session=tag_db.session, parse_all_raw=True)
    if args.print_tweets is True:
        TwitterAPI.print_tweets(db_session=tag_db.session)

    # Parse any downloaded tweets immediately.
    if raw_tweets or csv_only_tweets:
        print "Processing %s new raw tweets and %s CSV-only tweets..." % (
            len(raw_tweets), len(csv_only_tweets))
        TwitterAPI.parse_tweets(
            db_session=tag_db.session, raw_tweets=raw_tweets,
            csv_only_tweets=csv_only_tweets)
    if args.download_media is True:
        TwitterAPI.download_media(
            db_session=tag_db.session, storage_folder=args.storage_folder)


    """
    LIVEJOURNAL SECTION
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


if __name__ == '__main__':
    main()
