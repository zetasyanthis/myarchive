# Requires python-lj 0.2.

from sqlalchemy.orm.exc import NoResultFound

from lj import lj
from lj.backup import (
    DEFAULT_JOURNAL, update_journal_entries, update_journal_comments)

from myarchive.db.tables.ljtables import LJComment, LJEntries, LJHost, LJUser


class LJAPIConnection(object):

    def __init__(self, db_session, host, user_agent, username, password):
        """
        WARNING: MUST use HTTPS since this API uses *md5sum* for
        authentication! D:
        :param db_session:
        :param host:
        :param user_agent:
        :param username:
        :param password:
        """
        self.journal = DEFAULT_JOURNAL.copy()
        self._server = lj.LJServer(
            "Python-Blog3/1.0",
            user_agent=user_agent,
            host=host)
        self.journal['login'] = self.login = self._server.login(
            user=username,
            password=password)
        try:
            self.ljhost = db_session.query(LJHost).filter_by(url=host).one()
        except NoResultFound:
            self.ljhost = LJHost(url=host)
            db_session.add(self.ljhost)
            db_session.commit()

    def post_journal(self, subject, post, tags):
        """
        Posts a journal to the specified LJ server.
        """
        self._server.postevent(
            event=post,
            subject=subject,
            props={"taglist": ",".join(tags)})

    def download_journals_and_comments(self, db_session):
        """Downloads journals and comments to a defined dictionary."""

        # Sync entries from the server
        print("Downloading journal entries")
        nj = update_journal_entries(server=self._server, journal=self.journal)

        # Sync comments from the server
        print("Downloading comments")
        nc = update_journal_comments(server=self._server, journal=self.journal)

        print("Updated %d entries and %d comments" % (nj, nc))

        users = {
            int(self.journal['login']["userid"]):
                self.journal['login']["username"],
        }
        for user_id, username in self.journal["comment_posters"].items():
            users[int(user_id)] = username

        for user_id, username in users.items():
            try:
                db_session.query(LJUser).filter_by(user_id=user_id).one()
            except NoResultFound:
                self.ljhost.users.append(
                    LJUser(user_id=user_id, username=username))
        db_session.commit()

        for entry_id, entry in self.journal["entries"].items():
            pass
        for comment_id, comment in self.journal["comments"].items():
            pass
