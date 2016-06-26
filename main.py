#!/usr/bin/env python
#
# Load favorites for a Twitter user and output them to a file.
#

import argparse
import csv
import sys

import twitter

from t import *

KEYS = [
    u'id',
    u'user',
    u'text',
    u'created_at',
    u'hashtags',
    u'favorited',
    u'retweeted',
    u'user_mentions',
    u'source',
    u'in_reply_to_screen_name',
    u'in_reply_to_status_id',
    u'urls',
    u'media',
    u'retweet_count',
    u'favorite_count',

    # Don't really care about these.
    u'id_str',
    u'place',
    u'in_reply_to_user_id',
    u'lang',
    u'possibly_sensitive',
]


def main(**kwargs):
    api = twitter.Api(
        CONSUMER_KEY, CONSUMER_SECRET, ACCESS_KEY, ACCESS_SECRET,
        sleep_on_rate_limit=True)

    statuses = None
    if kwargs['user_id'] is not None:
        statuses = api.GetFavorites(
            user_id=kwargs['user_id'],
            count=None,
            since_id=None,
            max_id=None,
            include_entities=True)
    elif kwargs['screenname'] is not None:
        statuses = api.GetFavorites(
            screen_name=kwargs['screenname'],
            count=10,
            since_id=None,
            max_id=None,
            include_entities=True)

    key_set = set()
    status_dicts = []
    for status in statuses:
        status_dict = status.AsDict()
        # Override field
        status_dict["user"] = status_dict["user"]["screen_name"]

        status_dicts.append(status_dict)
        key_set.update(status_dict.keys())


    with open(kwargs['output_file'], 'w+') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=KEYS)
        writer.writeheader()
        for status in statuses:
            #print("\n")
            #print(status.AsDict())
            writer.writerow(status.AsDict())



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '--user-id',
        help='User id for which to return timeline')
    group.add_argument(
        '-n', '--screenname',
        help='Screenname for which to return timeline')
    parser.add_argument(
        '-f', '--output-file',
        default="twitter.csv",
        help='Write to file instead of stdout')
    args = parser.parse_args()
    if not (args.user_id or args.screenname):
        raise ValueError("You must specify one of user-id or screenname")
    if not all([CONSUMER_KEY, CONSUMER_SECRET, ACCESS_KEY, ACCESS_SECRET]):
        raise ValueError(
            "You must define CONSUMER_KEY, CONSUMER_SECRET, "
            "ACCESS_KEY, ACCESS_SECRET in t.py")
    main(user_id=args.user_id,
         screenname=args.screenname,
         output_file=args.output_file)
