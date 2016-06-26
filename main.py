#!/usr/bin/env python
#
# Load the latest update for a Twitter user and output it as an HTML fragment
#

from __future__ import print_function
import argparse
import codecs
import sys

import twitter

from t import *

__author__ = 'dewitt@google.com'

TEMPLATE = """
<div>
  <a href="http://twitter.com/{user}">Twitter</a>: {user}<br>
  {tweet_text}<br>
  <a href="http://twitter.com/{user}/statuses/{status_id}">Posted {tweet_created}</a>
</div>
"""


def main(**kwargs):
    api = twitter.Api(
        CONSUMER_KEY, CONSUMER_SECRET, ACCESS_KEY, ACCESS_SECRET,
        sleep_on_rate_limit=True)

    statuses = None
    if kwargs['user_id'] is not None:
        statuses = api.GetFavorites(
            user_id=kwargs['user_id'],
            count=1,
            since_id=None,
            max_id=None,
            include_entities=True)
    elif kwargs['screenname'] is not None:
        statuses = api.GetFavorites(
            screen_name=kwargs['screenname'],
            count=1,
            since_id=None,
            max_id=None,
            include_entities=True)

    print(statuses)

    # if kwargs['output_file'] is not None:
    #     with open(kwargs['output_file'], 'w+') as f:
    #         for status in statuses:
    #             f.write(status)
    # else:
    #     for status in statuses:
    #         print(TEMPLATE.format(user=status.user.screen_name,
    #                               tweet_text=status.text.encode('utf-8'),
    #                               status_id=status.id,
    #                               tweet_created=status.created_at))


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
        '--output-file',
        #default="twitter.log"
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
