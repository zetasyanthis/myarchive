# @Author: Zeta Syanthis <zetasyanthis>
# @Date:   2017/07/21
# @Email:  zeta@zetasyanthis.org
# @Project: MyArchive
# @Last modified by:   zetasyanthis
# @Last modified time: 2017/07/21
# @License MIT

import logging

from datetime import datetime
from lj import lj
from lj.backup import (
    DEFAULT_JOURNAL, update_journal_entries, update_journal_comments,
    datetime_from_string)
from sqlalchemy.orm.exc import NoResultFound

from myarchive.db.tag_db.tables.ljtables import (
    LJComment, LJEntry, LJHost, LJUser)


LOGGER = logging.getLogger(__name__)


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

        poster = None
        lj_users = dict()
        for user_id, username in users.items():
            ljuser = LJUser.get_user(
                db_session=db_session, user_id=user_id, username=username)
            self.ljhost.users.append(ljuser)
            lj_users[user_id] = ljuser
            if user_id == int(self.journal['login']["userid"]):
                poster = ljuser
        db_session.commit()

        lj_entries = dict()
        for entry_id, entry in self.journal["entries"].items():
            lj_entry = LJEntry.get_or_add_entry(
                db_session=db_session,
                lj_user=poster,
                itemid=entry_id,
                eventtime=datetime_from_string(entry["eventtime"]),
                subject=entry["subject"],
                text=entry["event"],
                current_music=entry["props"].get("current_music"),
                tag_list=entry["props"].get("taglist")
            )
            lj_entries[entry_id] = lj_entry
        db_session.commit()

        for comment_id, comment in self.journal["comments"].items():
            LJComment.get_or_add_comment(
                db_session=db_session,
                lj_user=lj_users[int(comment["posterid"])],
                lj_entry=lj_entries[int(comment["jitemid"])],
                itemid=int(comment_id),
                subject=comment["subject"],
                body=comment["body"],
                date=datetime.strptime(comment["date"], "%Y-%m-%dT%H:%M:%SZ"),
                parent_id=comment["parentid"]
            )
        db_session.commit()


def download_journals_and_comments(config, db_session):
    for config_section in config.sections():
        if config_section.startswith("LJ_"):
            LOGGER.info(config.get(section=config_section, option="host"))
            LOGGER.info(config.get(section=config_section, option="username"))
            ljapi = LJAPIConnection(
                db_session=db_session,
                host=config.get(
                    section=config_section, option="host"),
                user_agent=config.get(
                    section=config_section, option="user_agent"),
                username=config.get(
                    section=config_section, option="username"),
                password=config.get(
                    section=config_section, option="password"),
            )
            ljapi.download_journals_and_comments(db_session=db_session)
