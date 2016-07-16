# Requires python-lj 0.2.
from lj import lj
from lj.backup import (
    DEFAULT_JOURNAL, update_journal_entries, update_journal_comments)


class LJAPIConnection(object):

    def __init__(self, host, user_agent, username, password):
        self.journal = DEFAULT_JOURNAL.copy()
        self._server = lj.LJServer(
            "Python-Blog3/1.0",
            user_agent=user_agent,
            host=host)
        self.journal['login'] = self.login = self._server.login(
            user=username,
            password=password)

    def post_journal(self, subject, post, tags):
        """
        Posts a journal to the specified LJ server.

        WARNING: MUST use HTTPS since this API uses *md5sum* for authentication! D:
        """
        self._server.postevent(
            event=post,
            subject=subject,
            props={"taglist": ",".join(tags)})

    def download_journals_and_comments(self):
        """Downloads journals and comments to a defined dictionary."""

        # Sync entries from the server
        print("Downloading journal entries")
        nj = update_journal_entries(server=self._server, journal=self.journal)

        # Sync comments from the server
        print("Downloading comments")
        nc = update_journal_comments(server=self._server, journal=self.journal)

        print("Updated %d entries and %d comments" % (nj, nc))

        username = self.journal['login']["username"]
        for entry in self.journal["entries"]:
            pass
        for comment_poster in self.journal["comment_posters"]:
            pass
        for comment in self.journal["comments"]:
            pass
