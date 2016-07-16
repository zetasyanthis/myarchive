from collections import namedtuple

LJApiAccount = namedtuple(
    'LJApiAccount',
    ["user_agent", "email_address", "username", "password"])

TwitterApiAccount = namedtuple(
    'TwitterApiAccount',
    ["consumer_key", "consumer_secret", "access_key", "access_secret"])
