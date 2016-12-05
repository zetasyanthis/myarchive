#!/usr/bin/env python
#
# Load favorites for a Twitter user and output them to a file.
#

import csv
import logging
import os
import time
import twitter

from time import sleep
from twitter.error import TwitterError
from sqlalchemy import desc
from sqlalchemy.orm.exc import NoResultFound

from myarchive.db.tables.twittertables import (
    CSVTweet, RawTweet, Tweet, TwitterUser)


LOGGER = logging.getLogger(__name__)


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


class TwitterAPI(twitter.Api):
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

    def archive_tweets(self, username, db_session, types=(USER, FAVORITES)):
        """
        Archives several types of new tweets along with their associated
        content.
        """
        new_tweets = []

        for type_ in types:

            # For favorites, always do a full sweep. We can't guarantee an older
            # tweet wasn't recently favorited!
            if type_ == FAVORITES:
                since_id = None
            else:
                since_id = db_session.query(RawTweet.id).\
                    filter(RawTweet.favorited_by_str.
                           like("%%%s%%" % username)).\
                    order_by(desc(RawTweet.id)).first()
            if since_id:
                since_id = since_id[0]
            # print(type_, since_id)

            start_time = -1
            sleep_time = 0
            max_id = None
            early_termination = False
            request_index = 0
            requests_before_sleeps = 1
            statuses = []
            while not early_termination:
                # Twitter rate-limits us. Space this out a bit to avoid a
                # super-long sleep at the end doesn't kill the connection.
                if request_index >= requests_before_sleeps:
                    duration = time.time() - start_time
                    if duration < sleep_time:
                        sleep_duration = sleep_time - duration
                        LOGGER.info(
                            "Sleeping for %s seconds to ease up on rate "
                            "limit...", sleep_duration)
                        sleep(sleep_duration)
                start_time = time.time()
                request_index += 1

                LOGGER.info(
                    "Pulling 200 tweets from API starting with ID %s and "
                    "ending with ID %s...", since_id, max_id)
                try:
                    if type_ == FAVORITES:
                        loop_statuses = self.GetFavorites(
                            screen_name=username,
                            count=200,
                            since_id=since_id,
                            max_id=max_id,
                            include_entities=True)
                        # 15 requests per 15 minutes.
                        requests_before_sleeps = 15 - 1
                        sleep_time = 60
                    elif type_ == USER:
                        loop_statuses = self.GetUserTimeline(
                            screen_name=username,
                            count=200,
                            since_id=since_id,
                            max_id=max_id)
                        # 300 requests per 15 minutes.
                        sleep_time = 3
                        requests_before_sleeps = 300 - 1
                except twitter.error.TwitterError as e:
                    # If we overran the rate limit, try again.
                    if e.message[0][u'code'] == 88:
                        LOGGER.warning(
                            "Overran rate limit. Sleeping %s seconds in an "
                            "attempt to recover...", sleep_time)
                        request_index = requests_before_sleeps
                        sleep(sleep_time)
                        continue
                    raise
                LOGGER.info(
                    "Found %s tweets this iteration...", len(loop_statuses))
                # Check for "We ran out of tweets via this API" termination
                # condition.
                if not loop_statuses:
                    break
                # Check for early termination condition.
                for loop_status in loop_statuses:
                    status_id = int(loop_status.AsDict()["id"])
                    if since_id is not None and status_id >= since_id:
                        early_termination = True
                        break
                    # Only append if we don't breach since_id.
                    statuses.append(loop_status)
                    # Capture new max_id
                    if max_id is None or status_id < max_id:
                        max_id = status_id - 1

            # Format things the way we want and handle max_id changes.
            LOGGER.info("Adding %s tweets to DB...", len(statuses))
            existing_rawtweet_ids = [
                returned_tuple[0]
                for returned_tuple in db_session.query(RawTweet.id).all()]
            for status in statuses:
                status_dict = status.AsDict()
                status_id = int(status_dict["id"])
                if status_id in existing_rawtweet_ids:
                    continue
                raw_tweet = RawTweet(status_dict=status_dict)
                new_tweets.append(raw_tweet)
                db_session.add(raw_tweet)
                if type_ == FAVORITES:
                    raw_tweet.add_user_favorite(username)
            db_session.commit()

        return new_tweets

    def import_from_csv(self, db_session, csv_filepath, username):
        LOGGER.info("Importing into CSVTweets...")
        csv_tweets_by_id = dict(
            (csv_tweet.id, csv_tweet)
            for csv_tweet in db_session.query(CSVTweet).all())
        with open(csv_filepath) as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                tweet_id = int(row['tweet_id'])
                if tweet_id not in csv_tweets_by_id:
                    csv_tweet = CSVTweet(
                        id=tweet_id,
                        username=username,
                        in_reply_to_status_id=row["in_reply_to_status_id"],
                        in_reply_to_user_id=row["in_reply_to_user_id"],
                        timestamp=row["timestamp"],
                        text=row["text"],
                        retweeted_status_id=row["retweeted_status_id"],
                        retweeted_status_user_id=
                        row["retweeted_status_user_id"],
                        retweeted_status_timestamp=
                        row["retweeted_status_timestamp"],
                        expanded_urls=row["expanded_urls"])
                    db_session.add(csv_tweet)
                    csv_tweets_by_id[tweet_id] = csv_tweet
        db_session.commit()

        LOGGER.info("Scanning for existing RawTweets...")
        existing_rawtweet_ids = [
            returned_tuple[0]
            for returned_tuple in db_session.query(RawTweet.id).all()]
        ids_to_remove = []
        for tweet_id, csv_tweet in csv_tweets_by_id.items():
            # If any aren't set as imported and should be, clean that up.
            if tweet_id in existing_rawtweet_ids:
                ids_to_remove.append(tweet_id)
                if not csv_tweet.api_import_complete:
                    csv_tweet.api_import_complete = True
        db_session.commit()
        for id_to_remove in ids_to_remove:
            csv_tweets_by_id.pop(id_to_remove)

        csv_ids = list(csv_tweets_by_id.keys())
        num_imports = len(csv_ids)
        LOGGER.info(
            "Attempting API import of %s tweets based on CSV file...",
            num_imports)

        # API allows 60 requests per 15 minutes.
        sleep_time = 15
        requests_before_sleeps = 60 - 1

        # Set loop starting values
        tweet_index = 0
        request_index = 0
        start_time = -1
        new_api_tweets = []
        sliced_ids = csv_ids[:100]
        while sliced_ids:

            # Sleep to not hit the rate limit.
            # Twitter rate-limits us. Space this out a bit to avoid a
            # super-long sleep at the end doesn't kill the connection.
            if request_index >= requests_before_sleeps:
                duration = time.time() - start_time
                if duration < sleep_time:
                    sleep_duration = sleep_time - duration
                    LOGGER.info(
                        "Sleeping for %s seconds to ease up on rate limit...",
                        sleep_duration)
                    sleep(sleep_duration)
            request_index += 1
            start_time = time.time()

            # Perform the import.
            LOGGER.info(
                "Attempting import of id %s to %s of %s...",
                tweet_index + 1, min(tweet_index + 100, num_imports),
                num_imports)
            try:
                statuses = self.LookupStatuses(
                    status_ids=[str(sliced_id) for sliced_id in sliced_ids],
                    trim_user=False,
                    include_entities=True)
                for status in statuses:
                    status_dict = status.AsDict()
                    # Create the RawTweet
                    raw_tweet = RawTweet(status_dict=status_dict)
                    db_session.add(raw_tweet)
                    # Mark CSVTweet appropriately.
                    csv_tweet = csv_tweets_by_id[int(status_dict["id"])]
                    csv_tweet.api_import_complete = True
                    # Append to new list.
                    new_api_tweets.append(raw_tweet)
                db_session.commit()

            except TwitterError as e:
                # If we overran the rate limit, try again.
                if e.message[0][u'code'] == 88:
                    LOGGER.warning(
                        "Overran rate limit. Sleeping %s seconds in an "
                        "attempt to recover...", sleep_time)
                    request_index = requests_before_sleeps
                    sleep(sleep_time)
                    continue
                raise
            tweet_index += 100
            sliced_ids = csv_ids[tweet_index:100 + tweet_index]

        csv_only_tweets = db_session.query(CSVTweet.api_import_complete).\
            filter_by(api_import_complete=False).all()

        return new_api_tweets, csv_only_tweets

    @staticmethod
    def parse_tweets(db_session, raw_tweets=None, csv_only_tweets=None,
                     parse_all_raw=False, username=None):
        user = None

        if parse_all_raw is True:
            # Process all captured raw tweets.
            raw_tweets = db_session.query(RawTweet)

        # Filter out existing tweets, making sure to compare with a a tuple
        # since SQLAlchemy will return a list of tuples.
        existing_tweet_ids = db_session.query(Tweet.id).all()
        raw_tweets_to_parse = [
            raw_tweet for raw_tweet in raw_tweets
            if (int(raw_tweet.raw_status_dict["id"]),) not in existing_tweet_ids]
        LOGGER.info("Found %s tweets to parse.", len(raw_tweets_to_parse))

        for index, raw_tweet in enumerate(raw_tweets_to_parse):
            if index % 100 == 0:
                LOGGER.info(
                    "Parsing tweet %s to %s of %s...",
                    index,
                    min(index + 100, len(raw_tweets_to_parse)),
                    len(raw_tweets_to_parse))

            # Generate User objects. Only really query if we absolutely have to.
            user_dict = raw_tweet.raw_status_dict["user"]
            user_id = int(user_dict["id"])
            if user and user.id == user_id:
                pass
            else:
                try:
                    user = db_session.query(TwitterUser).filter_by(id=user_id).one()
                except NoResultFound:
                    user = TwitterUser(user_dict)
                    db_session.add(user)

            # Generate Tweet objects.
            tweet = Tweet.make_from_raw(raw_tweet)
            user.tweets.append(tweet)
        db_session.commit()

        if csv_only_tweets:
            print("CSV Only: %s" % len(csv_only_tweets))
            for csv_only_tweet in csv_only_tweets:
                user = db_session.query(TwitterUser).\
                    filter_by(screen_name=csv_only_tweet.username).one()
                tweet = Tweet.make_from_csvtweet(csv_only_tweet)
                user.tweets.append(tweet)
            db_session.commit()

    @staticmethod
    def download_media(db_session, storage_folder):
        media_path = os.path.join(storage_folder, "media/")
        for user in db_session.query(TwitterUser):
            user.download_media(db_session=db_session, media_path=media_path)
        for tweet in db_session.query(Tweet):
            tweet.download_media(db_session=db_session, media_path=media_path)

    @staticmethod
    def print_tweets(db_session):
        for raw_tweet in db_session.query(RawTweet).all():
            print(raw_tweet)
