"""
This module contains definitions for association tables used in many-to-many
mappings.
"""

from sqlalchemy import Column, ForeignKey, Integer, Table

from myarchive.db.tables.base import Base

at_file_tag = Table(
    'at_file_tag', Base.metadata,
    Column("file_id", Integer, ForeignKey("files.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.tag_id"), primary_key=True),
    info="Association table for mapping files to tags and vice versa.")

at_tweet_tag = Table(
    'at_tweet_tag', Base.metadata,
    Column("tweet_id", Integer, ForeignKey("tweets.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.tag_id"), primary_key=True),
    info="Association table for mapping tweets to tags and vice versa.")

at_ljcomment_tag = Table(
    'at_ljcomment_tag', Base.metadata,
    Column(
        "lj_comment_id", Integer, ForeignKey("lj_comments.id"),
        primary_key=True),
    Column(
        "tag_id", Integer, ForeignKey("tags.tag_id"),
        primary_key=True),
    info="Association table for mapping LJ comments to tags and vice versa.")

at_ljentry_tag = Table(
    'at_ljentry_tag', Base.metadata,
    Column(
        "lj_entry_id", Integer, ForeignKey("lj_entries.id"), primary_key=True),
    Column(
        "tag_id", Integer, ForeignKey("tags.tag_id"), primary_key=True),
    info="Association table for mapping LJ entries to tags and vice versa.")

at_tweet_file = Table(
    'at_tweet_file', Base.metadata,
    Column("tweet_id", Integer, ForeignKey("tweets.id"), primary_key=True),
    Column("file_id", Integer, ForeignKey("files.id"), primary_key=True),
    info="Association table for mapping tweets to files and vice versa.")

at_twuser_file = Table(
    'at_twuser_file', Base.metadata,
    Column("twuser_id", Integer,
           ForeignKey("twitter_users.id"), primary_key=True),
    Column("file_id", Integer,
           ForeignKey("files.id"), primary_key=True),
    info="Association table for mapping users to files and vice versa.")
