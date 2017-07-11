
import os
import pafy

from logging import getLogger

from myarchive.db.tag_db.tables.file import TrackedFile

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
        # print(
        #     [playlist.title, playlist.author,
        #      playlist.description, playlist.plid]
        # )

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
            tracked_file, existing = TrackedFile.add_file(
                db_session=db_session,
                media_path=media_storage_path,
                copy_from_filepath=temp_filepath,
                move_original_file=True,
            )
            if existing is True:
                os.remove(temp_filepath)
            else:
                db_session.add(tracked_file)
                db_session.commit()
