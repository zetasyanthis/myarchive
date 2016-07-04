#!/usr/bin/env python
#
# Load favorites for a Twitter user and output them to a file.
#

import os
import twitter

from time import sleep
from sqlalchemy import desc

from myarchive.db.tables.file import TrackedFile
from myarchive.db.tables.twittertables import RawTweet, Tweet, TwitterUser

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


def archive_favorites(username, db_session):
    api = twitter.Api(
        CONSUMER_KEY, CONSUMER_SECRET, ACCESS_KEY, ACCESS_SECRET,
        sleep_on_rate_limit=True)

    since_id = db_session.query(RawTweet.id).order_by(desc(RawTweet.id)).first()
    if since_id:
        since_id = since_id[0]
    print since_id

    new_ids = []
    max_id = None
    early_termination = False
    while True:
        print 'asdf'
        statuses = api.GetFavorites(
            screen_name=username,
            count=200,
            since_id=since_id,
            max_id=max_id,
            include_entities=True)
        # print(api.rate_limit.get_limit("favorites/list"))
        if early_termination or not statuses:
            break

        # Format things the way we want and handle max_id changes.
        for status in statuses:
            status_dict = status.AsDict()
            status_id = int(status_dict["id"])
            if status_id >= since_id:
                early_termination = True
                break
            else:
                new_ids.append(status_id)
            db_session.add(RawTweet(status_dict=status_dict))
            db_session.commit()
            # Capture new max_id
            if status_id < max_id or max_id is None:
                max_id = status_id - 1

        # Twitter rate-limits us to 15 requests / 15 minutes, so
        # space this out a bit to avoid a super-long sleep at the
        # end which could lose the connection.
        if early_termination is False:
            print "Sleeping for %s seconds to ease up rate limit..." % (
                SLEEP_TIME)
            sleep(SLEEP_TIME)
    return new_ids


def parse_tweets(db_session, media_path, new_ids=None):

    if new_ids:
        raw_tweets = [db_session.query(RawTweet).filter_by(id=tweet_id)
                      for tweet_id in new_ids]
    else:
        raw_tweets = db_session.query(RawTweet)

    for raw_tweet in raw_tweets:

        # Generate User objects.
        user_dict = raw_tweet.raw_status_dict["user"]
        user = TwitterUser.add_from_user_dict(db_session, media_path, user_dict)

        # Generate Tweet objects.
        tweet = Tweet.add_from_raw(db_session, raw_tweet.raw_status_dict, user)
        if tweet not in user.tweets:
            user.tweets.append(tweet)
            db_session.commit()

        # Retrieve media files.
        if media_path and "media" in raw_tweet.raw_status_dict:
            for media_item in raw_tweet.raw_status_dict["media"]:
                media_url = media_item["media_url_https"]
                tracked_file = TrackedFile.download_file(
                    db_session, media_path, media_url)
                if tracked_file is not None and tracked_file not in tweet.files:
                    tweet.files.append(tracked_file)
                db_session.commit()


def print_tweets(db_session):
    for raw_tweet in db_session.query(RawTweet).all():
        print raw_tweet
