# Requires python-lj 0.2.
from lj import lj

from account_info import (EMAIL_ADDRESS, LJ_USER_AGENT, LJ_USERNAME, LJ_PASSWORD)

ljclient = lj.LJServer(
    "Python-Blog3/1.0",
    LJ_USER_AGENT)
ljclient.login(
    LJ_USERNAME,
    LJ_PASSWORD)
ljclient.postevent(
    "API Test post",
    "API Test Subject",
    props={"taglist": "github,livejournal"})
