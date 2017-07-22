# @Author: Zeta Syanthis <zetasyanthis>
# @Date:   2017/07/21
# @Email:  zeta@zetasyanthis.org
# @Project: MyArchive
# @Last modified by:   zetasyanthis
# @Last modified time: 2017/07/21
# @License MIT

import os
import pafy

from datetime import datetime
from logging import getLogger
from sqlalchemy.orm.exc import NoResultFound

from myarchive.db.tag_db.tables.file import TrackedFile
from myarchive.db.tag_db.tables.tag import Tag
from myarchive.db.tag_db.tables.yttables import YTPlaylist, YTVideo

LOGGER = getLogger(__name__)


def download_youtube_playlists(db_session, media_storage_path, playlist_urls):
    """Downloads videos"""
    LOGGER.warning(
        "Youtube downloads may take quite a lot of drive space! Make sure you "
        "have a good amount free before triggering video downloads.")
    for playlist_url in playlist_urls:
        playlist = pafy.get_playlist2(playlist_url=playlist_url)
        LOGGER.info(
            "Parsing playlist %s [%s]...", playlist.title, playlist.author)
        try:
            db_playlist = db_session.query(YTPlaylist).\
                filter_by(plid=playlist.plid).one()
        except NoResultFound:
            db_playlist = YTPlaylist(
                title=playlist.title,
                author=playlist.author,
                description=playlist.description,
                plid=playlist.plid)
            db_session.add(db_playlist)

        total_bytes = 0
        video_stream_tuples = []
        for video in playlist:
            try:
                pafy_stream = video.getbest()
                video_stream_tuples.append([video, pafy_stream])
                total_bytes += pafy_stream.get_filesize()
            except Exception as whatwasthat:
                LOGGER.error(whatwasthat)
        LOGGER.info("Playlist DL size: %s MB" % int(total_bytes / 2 ** 20))

        for video, stream in video_stream_tuples:
            LOGGER.info("Downloading %s...", stream.title)
            temp_filepath = "/tmp/" + stream.title + "." + stream.extension
            stream.download(filepath=temp_filepath)
            try:
                tracked_file, existing = TrackedFile.add_file(
                    db_session=db_session,
                    media_path=media_storage_path,
                    copy_from_filepath=temp_filepath,
                    move_original_file=True,
                )
                if existing is True:
                    os.remove(temp_filepath)
                    continue
                else:
                    db_session.add(tracked_file)

                ytvideo = YTVideo(
                    uploader=video.username,
                    description=video.description,
                    duration=video.duration,
                    publish_time=datetime.strptime(
                        video.published, "%Y-%m-%d %H:%M:%S"    ),
                    videoid=video.videoid
                )
                db_playlist.videos.append(ytvideo)
                ytvideo.file = tracked_file
                for keyword in video.keywords:
                    tag = Tag.get_tag(db_session=db_session, tag_name=keyword)
                    ytvideo.tags.append(tag)
                    tracked_file.tags.append(tag)
                db_session.commit()
            except:
                db_session.rollback()
                raise

    db_session.commit()
