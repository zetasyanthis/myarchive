
import os
import youtube_dl

from logging import getLogger

#from myarchive.db.tag_db.tables.file import TrackedFile

# LOGGER = getLogger(__name__)
LOGGER = getLogger("main")


YDL_OPTS = {
    'format': 'best',
    'writethumbnail': True,
    # 'postprocessors': [{
    #     'key': 'FFmpegExtractAudio',
    #     'preferredcodec': 'mp3',
    #     'preferredquality': '192',
    # }],
    'logger': LOGGER,
    # 'keepvideo': True,
    "forcejson": True,
    "simulate": True,
}

with youtube_dl.YoutubeDL(YDL_OPTS) as ydl:
    asdf = ydl.download(["https://www.youtube.com/playlist?list=PL_O5K6dbEUPKDaeRONuivX4v5JMzYCSFe"])

# def download_youtube_playlists(db_session, media_storage_path, playlist_urls):
#     YDL_OPTS["outtmpl"] = \
#         os.path.join(media_storage_path, "%(uploader)_%(title)s.%(ext)s")
#     with youtube_dl.YoutubeDL(YDL_OPTS) as ydl:
#         ydl.download(["https://www.youtube.com/watch?v=2yYDJVEVxak"])
#
#     TrackedFile.add_file(db_session)
#     db_session.commit()
