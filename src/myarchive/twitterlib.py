#!/usr/bin/env python
#
# Load favorites for a Twitter user and output them to a file.
#

import csv
import os
import twitter

from time import sleep
from twitter.error import TwitterError
from sqlalchemy import desc
from sqlalchemy.orm.exc import NoResultFound

from myarchive.db.tables.file import TrackedFile
from myarchive.db.tables.twittertables import RawTweet, Tweet, TwitterUser

from account_info import *

SLEEP_TIME = 60 * (60 / 15)

USER = "USER"
FAVORITES = "FAVORITES"

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


def archive_tweets(username, db_session, types=(USER, FAVORITES)):
    """
    Archives several types of new tweets along with their associated content.
    """
    new_ids = []
    api = twitter.Api(
        CONSUMER_KEY, CONSUMER_SECRET, ACCESS_KEY, ACCESS_SECRET,
        sleep_on_rate_limit=True)

    for type_ in types:

        # For favorites, always do a full sweep. We can't guarantee an older
        # tweet wasn't recently favorited!
        if type_ == FAVORITES:
            since_id = None
        else:
            since_id = db_session.query(RawTweet.id).\
                filter(RawTweet.types_str.like("%%%s%%" % type_)).\
                order_by(desc(RawTweet.id)).first()
        if since_id:
            since_id = since_id[0]
        print type_, since_id

        max_id = None
        early_termination = False
        while not early_termination:
            print ("Pulling 200 tweets from API starting with ID %s and "
                   "ending with ID %s..." % (since_id, max_id))
            if type_ == FAVORITES:
                statuses = api.GetFavorites(
                    screen_name=username,
                    count=200,
                    since_id=since_id,
                    max_id=max_id,
                    include_entities=True)
            elif type_ == USER:
                statuses = api.GetUserTimeline(
                    screen_name=username,
                    count=200,
                    since_id=since_id,
                    max_id=max_id)
            print "Found %s tweets this iteration..." % len(statuses)
            # print(api.rate_limit.get_limit("favorites/list"))
            if not statuses:
                break

            # Format things the way we want and handle max_id changes.
            for status in statuses:
                status_dict = status.AsDict()
                status_id = int(status_dict["id"])
                if since_id is not None and status_id >= since_id:
                    early_termination = True
                    break
                else:
                    new_ids.append(status_id)
                try:
                    raw_tweet = db_session.query(RawTweet).\
                        filter_by(id=status_id).one()
                    raw_tweet.add_type(type_)
                except NoResultFound:
                    raw_tweet = RawTweet(status_dict=status_dict)
                    db_session.add(raw_tweet)
                raw_tweet.add_type(type_)
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

    if new_ids is not None:
        raw_tweets = [db_session.query(RawTweet).filter_by(id=tweet_id).one()
                      for tweet_id in new_ids]
    else:
        # Process all captured raw tweets.
        raw_tweets = db_session.query(RawTweet)

    for raw_tweet in raw_tweets:

        # Generate User objects.
        user_dict = raw_tweet.raw_status_dict["user"]
        user = TwitterUser.add_from_user_dict(db_session, media_path, user_dict)

        # Generate Tweet objects.
        tweet = Tweet.add_from_raw(
            db_session=db_session,
            status_dict=raw_tweet.raw_status_dict,
            user=user)
        for type in raw_tweet.types:
            tweet.add_type(type)
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


def import_from_csv(db_session, username, csv_filepath):
    new_ids = []
    api = twitter.Api(
        CONSUMER_KEY, CONSUMER_SECRET, ACCESS_KEY, ACCESS_SECRET,
        sleep_on_rate_limit=True)

    with open(csv_filepath) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            new_ids.append(int(row['tweet_id']))

    for ii, new_id in enumerate(new_ids):
        if ii % 100 == 0:
            print "Importing id %s of %s..." % (ii, len(new_ids))
        try:
            # If the tweet is found, it's already been imported. Ignore it.
            db_session.query(RawTweet).filter_by(id=new_id).one()
        except NoResultFound:
            try:
                status = api.GetStatus(status_id=new_id)
                status_dict = status.AsDict()
                raw_tweet = RawTweet(status_dict=status_dict)
                db_session.add(raw_tweet)
                raw_tweet.add_type(USER)
                db_session.commit()

                # Sleep to not hit the rate limit.
                sleep(5)
            except TwitterError:
                print "Unable to import id %s!" % new_id


def print_tweets(db_session):
    for raw_tweet in db_session.query(RawTweet).all():
        print raw_tweet
