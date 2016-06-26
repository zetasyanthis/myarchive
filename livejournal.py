# Requires python-lj 0.2.
from lj import lj

from account_info import (EMAIL_ADDRESS, LJ_USER_AGENT, LJ_USERNAME, LJ_PASSWORD)


def post_journal(subject, post, tags, host='https://www.livejournal.com/'):
    """
    Posts a journal to the specified LJ server.

    WARNING: MUST use HTTPS since this API uses *md5sum* for authentication! D:
    """
    ljclient = lj.LJServer(
        "Python-Blog3/1.0",
        LJ_USER_AGENT,
        host=host)
    ljclient.login(
        LJ_USERNAME,
        LJ_PASSWORD)
    ljclient.postevent(
        event=post,
        subject=subject,
        props={"taglist": ",".join(tags)})
