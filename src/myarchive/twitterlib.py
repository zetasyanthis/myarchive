#!/usr/bin/env python
#
# Load favorites for a Twitter user and output them to a file.
#

import copy
import csv
import os
import twitter

from time import sleep
from twitter.error import TwitterError
from sqlalchemy import desc
from sqlalchemy.orm.exc import NoResultFound

from myarchive.db.tables.file import TrackedFile
from myarchive.db.tables.twittertables import (
    CSVTweet, RawTweet, Tweet, TwitterUser)

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


class BulkApi(twitter.Api):
    """API with an extra call."""

    def LookupStatuses(self, status_ids, trim_user=False,
                       include_entities=True):
        """
        Returns up to 100 status messages, specified by a list passed to
        status_ids.

        Args:
          status_ids:
            A list of numeric IDs of the statuses you are trying to retrieve.
          trim_user:
            When set to True, each tweet returned in a timeline will include
            a user object including only the status authors numerical ID.
            Omit this parameter to receive the complete user object. [Optional]
          include_entities:
            If False, the entities node will be disincluded.
            This node offers a variety of metadata about the tweet in a
            discreet structure, including: user_mentions, urls, and
            hashtags. [Optional]
        Returns:
          A twitter.Status instance representing that status message
        """
        url = '%s/statuses/lookup.json' % self.base_url

        parameters = dict()

        if not status_ids or len(status_ids) > 100:
            raise TwitterError(
                "status_ids must be between 1 and 100 in length.")
        # This takes a comma-separated list of up to 100 IDs.
        parameters['id'] = ",".join(status_ids)

        if trim_user:
            parameters['trim_user'] = True
        if include_entities:
            parameters['include_entities'] = True

        resp = self._RequestUrl(url, 'GET', data=parameters)
        data = self._ParseAndCheckTwitter(resp.content.decode('utf-8'))

        return [twitter.Status.NewFromJsonDict(x) for x in data]


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
                # 15 requests per 15 minutes.
                sleep_time = 60
            elif type_ == USER:
                statuses = api.GetUserTimeline(
                    screen_name=username,
                    count=200,
                    since_id=since_id,
                    max_id=max_id)
                # 300 requests per 15 minutes.
                sleep_time = 3
            print "Found %s tweets this iteration..." % len(statuses)
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
                    sleep_time)
                sleep(sleep_time)
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


def import_from_csv(db_session, csv_filepath, username):
    api = BulkApi(
        CONSUMER_KEY, CONSUMER_SECRET, ACCESS_KEY, ACCESS_SECRET,
        sleep_on_rate_limit=True)

    csv_rows_by_id = dict()
    with open(csv_filepath) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            csv_rows_by_id[int(row['tweet_id'])] = row
            csv_tweet = CSVTweet(
                id=row["tweet_id"],
                username=username,
                in_reply_to_status_id=row["in_reply_to_status_id"],
                in_reply_to_user_id=row["in_reply_to_user_id"],
                timestamp=row["timestamp"],
                text=row["text"],
                retweeted_status_id=row["retweeted_status_id"],
                retweeted_status_user_id=row["retweeted_status_user_id"],
                retweeted_status_timestamp=row["retweeted_status_timestamp"],
                expanded_urls=row["expanded_urls"])
            db_session.add(csv_tweet)
            db_session.commit()
    csv_ids = list(csv_rows_by_id.keys())
    new_api_tweets = []

    index = 0
    sliced_ids = csv_ids[:100]
    while sliced_ids:
        new_ids = []
        for status_id in sliced_ids:
            try:
                # If the tweet is found, it's already been imported. Ignore it.
                db_session.query(RawTweet.id).filter_by(id=status_id).one()
            except NoResultFound:
                new_ids.append(str(status_id))
        if new_ids:
            print "Attempting import of id %s to %s of %s..." % (
                index + 1, index + 100, len(csv_ids))
            try:
                statuses = api.LookupStatuses(
                    status_ids=new_ids, trim_user=False, include_entities=True)
                for status in statuses:
                    status_dict = status.AsDict()
                    raw_tweet = RawTweet(status_dict=status_dict)
                    db_session.add(raw_tweet)
                    raw_tweet.add_type(USER)
                    db_session.commit()
                    # Mark CSV tweet appropriately.
                    csv_tweet = db_session.query(CSVTweet).\
                        filter_by(id=int(status_dict["id"]))
                    csv_tweet.api_import_complete = True
                    # Record in new ID list.
                    new_api_tweets.append(status_dict["id"])

                # Sleep to not hit the rate limit.
                # 60 requests per 15 minutes.
                sleep(15)
            except TwitterError as e:
                print e
        index += 100
        sliced_ids = csv_ids[index:100 + index]

    return new_api_tweets


def print_tweets(db_session):
    for raw_tweet in db_session.query(RawTweet).all():
        print raw_tweet
