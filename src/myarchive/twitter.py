#!/usr/bin/env python
#
# Load favorites for a Twitter user and output them to a file.
#

import argparse
import csv
import os
import twitter

from cPickle import dump
from collections import defaultdict
from time import sleep

from account_info import *

SLEEP_TIME = 60 * (60 / 15)

KEYS = [
    u'user',
    u'text',
    u'in_reply_to_screen_name',
    u'media',

    # Not that interesting, but saved.
    u'hashtags',
    u'id',
    u'in_reply_to_status_id',
    # Seems to be empty a lot. Put it at the end.
    u'urls',

    # Don't really care about these.
    # u'user_mentions',
    # u'source',
    # u'created_at',
    # u'id_str',
    # u'place',
    # u'in_reply_to_user_id',
    # u'lang',
    # u'possibly_sensitive',
    # u'favorited',
    # u'favorite_count',
    # u'retweeted',
    # u'retweet_count',
]


def archive_favorites(**kwargs):
    try:
        os.remove(kwargs["output_file"])
    except OSError:
        pass
    api = twitter.Api(
        CONSUMER_KEY, CONSUMER_SECRET, ACCESS_KEY, ACCESS_SECRET,
        sleep_on_rate_limit=True)

    max_id = None
    while True:
        print max_id

        statuses = api.GetFavorites(
            screen_name=kwargs['screenname'],
            count=200,
            since_id=None,
            max_id=max_id,
            include_entities=True)
        # print api.rate_limit.get_limit("favorites/list")
        if not statuses:
            break

        # Format things the way we want and handle max_id changes.
        status_dicts = []
        for status in statuses:
            status_dict = status.AsDict()
            status_id = int(status_dict["id"])
            # Pickle the tweets out to save the original format.
            with open(
                "%s/%s.pickle" %
                    (kwargs["pickle_folder"], status_id), "w") as pickle_fptr:
                dump(status_dict, pickle_fptr)
            # Capture new max_id
            if status_id < max_id or max_id is None:
                max_id = status_id - 1
            # Override fields
            status_dict["user"] = status_dict["user"]["screen_name"]
            status_dict["text"] = status_dict["text"].encode('utf-8')
            # Filter crap we don't care about.
            keys = list(status_dict.keys())
            for key in keys:
                if key not in KEYS:
                    del status_dict[key]
            status_dicts.append(status_dict)

        file_exists = False
        try:
            if os.path.getsize(kwargs['output_file']) > 0:
                file_exists = True
        except OSError:
            pass
        with open(kwargs['output_file'], 'a') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=KEYS)
            if file_exists is False:
                writer.writeheader()
            for status_dict in status_dicts:
                try:
                    writer.writerow(status_dict)
                except:
                    print "ERROR: ", status_dict
                    raise

        # Twitter rate-limits us to 15 requests / 15 minutes, so
        # space this out a bit to avoid a super-long sleep at the
        # end which could lose the connection.
        print "Sleeping for %s seconds to ease up rate limit..." % SLEEP_TIME
        sleep(SLEEP_TIME)


def check_duplicates(**kwargs):
    rows_by_id = defaultdict(list)
    with open(kwargs["file_path"]) as csv_fptr:
        dict_reader = csv.DictReader(csv_fptr)
        # fieldnames = dict_reader.fieldnames
        for index, row in enumerate(dict_reader):
            rows_by_id[row["id"]].append((index, row))
        for id, row_tuple in rows_by_id.items():
            if len(row_tuple) > 1:
                for item in row_tuple:
                    print "DUPLICATE on line %s. [id: %s]" % (
                        item[0], item[1]["id"])


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-f', '--favorites',
        action="store",
        help='Downloads favorites. Accepts a Twitter username.')
    parser.add_argument(
        '-d', '--check_duplicates',
        action="store",
        help='Checks CSV for duplicates.')
    parser.add_argument(
        '-o', '--output-file',
        default="twitter.csv",
        help='Write to file instead of stdout')
    parser.add_argument(
        '-p', '--pickle-folder',
        default="pickle_dump",
        help='Write to file instead of stdout')
    args = parser.parse_args()
    if not all([CONSUMER_KEY, CONSUMER_SECRET, ACCESS_KEY, ACCESS_SECRET]):
        raise ValueError(
            "You must define CONSUMER_KEY, CONSUMER_SECRET, "
            "ACCESS_KEY, ACCESS_SECRET in account_info.py")

    if args.favorites:
        archive_favorites(
            pickle_folder=args.pickle_folder,
            screenname=args.favorites,
            output_file=args.output_file)
    elif args.check_duplicates:
        check_duplicates(file_path=args.check_duplicates)

if __name__ == "__main__":
    main()
