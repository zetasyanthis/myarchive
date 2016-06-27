#!/usr/bin/python3

import argparse
import os

from db import TagDB
from gui import Gtk, MainWindow
from util.logger import myarchive_LOGGER as logger


def main():
    """Starts up the DB connection and GUI."""

    parser = argparse.ArgumentParser(
        description='Manages tagged files.')
    parser.add_argument(
        "-D", "--db_filename",
        type=str,
        dest="db_filename",
        nargs='?',
        const="archive.sqlite",
        help="Database filename.")
    parser.add_argument(
        "--import-folder",
        type=str, dest="import_folder",
        help="Folder to organize.")
    parser.add_argument(
        '--import-twitter-favorites',
        action="store",
        help='Downloads favorites. Accepts a Twitter username.')
    parser.add_argument(
        '--output-csv-file',
        default="twitter.csv",
        help='Write to file instead of stdout')
    parser.add_argument(
        '--pickle-folder',
        default="pickle_dump",
        help='Write to file instead of stdout')
    args = parser.parse_args()

    if args.import_folder:
        if not os.path.exists(args.import_folder):
            raise Exception("Import folder path does not exist!")
        if not os.path.isdir(args.import_folder):
            raise Exception("Import folder path is not a folder!")

    logger.debug(args)

    if args.db_filename:
        tag_db = TagDB(
            drivername='sqlite',
            db_name=args.db_filename)
    else:
        tag_db = TagDB()

    MainWindow(tag_db)
    Gtk.main()


if __name__ == '__main__':
    main()
