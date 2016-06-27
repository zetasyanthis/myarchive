"""
This module contains definitions for association tables used in many-to-many
mappings.
"""

from sqlalchemy import Column, ForeignKey, Integer, Table

from myarchive.db.tables.base import Base

at_file_tag = Table(
    'at_file_tag', Base.metadata,
    Column("file_id", Integer, ForeignKey("files.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
    info="Association table for mapping files to tags and vice versa.")

at_file_tweet = Table(
    'at_tweet_tag', Base.metadata,
    Column("tweet_id", Integer, ForeignKey("tweets.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
    info="Association table for mapping files to tags and vice versa.")
