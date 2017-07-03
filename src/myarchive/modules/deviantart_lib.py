"""Handles deviantart calls."""

import deviantart
import logging

from myarchive.db.tag_db.tables.file import TrackedFile
from myarchive.db.tag_db.tables.tag import Tag

LOGGER = logging.getLogger(__name__)

FAVORITES_RSS = "http://backend.deviantart.com/rss.xml?q=favby%%3A%(username)s"
GALLERY_RSS = "http://backend.deviantart.com/rss.xml?q=gallery%%3A%(username)s"


def download_user_data(database, config, media_storage_path):
    """Grabs user galleries and favorites."""
    for config_section in config.sections():
        if config_section.startswith("DeviantArt_"):
            username = config_section[11:]
            client_id = config.get(
                section=config_section, option="client_id"),
            client_secret = config.get(
                section=config_section, option="client_secret"),

            da_api = deviantart.Api(
                client_id=client_id[0],
                client_secret=client_secret[0],
            )
            da_api.oauth.request_token(grant_type="client_credentials")
            if not da_api.access_token:
                raise Exception("Access token not acquired!")

            # Grab the User object of the authorized user
            user = da_api.get_user(username=username)
            LOGGER.info("Pulling data for user: %s", user.username)

            # Grab user data.
            # user.userid
            # user.profile
            # user.stats
            # user.details
            # user.usericon

            LOGGER.critical(user.__dict__)

            for sync_type in ("gallery", "favorites"):
                LOGGER.info("Pulling deviations from %s", sync_type)
                __download_user_deviations(
                    database=database,
                    da_api=da_api,
                    username=username,
                    sync_type=sync_type,
                    media_storage_path=media_storage_path,
                )


def __download_user_deviations(
        database, media_storage_path, da_api, username, sync_type):

    if sync_type == "gallery":
        collections = da_api.get_gallery_folders(username=username)
    elif sync_type == "favorites":
        collections = da_api.get_collections(username=username)
    else:
        raise Exception("Type of sync not supported: %s" % sync_type)

    for collection in collections["results"]:
        LOGGER.info(
            "Pulling deviations from collection: %s..." %
            collection["name"])
        folderid = collection["folderid"]

        deviations = []
        offset = 0
        has_more = True
        # while there are more deviations to fetch
        while has_more:
            try:
                # fetch deviations from user
                fetched_deviations = da_api.get_collection(
                    folderid=folderid,
                    username=username,
                    offset=offset,
                    limit=10)
                # Add fetched deviations to list.
                deviations.extend(fetched_deviations['results'])
                # Update offset
                offset = fetched_deviations['next_offset']
                # Check if there are any deviations left that we can
                # fetch (if yes => repeat)
                has_more = fetched_deviations['has_more']

            except deviantart.api.DeviantartError as error:
                # catch and print API exception and stop loop
                LOGGER.error("Error pulling DA collection: %s" % error)
                has_more = False

        # Loop through and save deviations.
        for deviation in deviations:
            # If there's no content (if it's a story), skip for now.
            deviation_name = (
                str(deviation.title) + str(deviation.author)). \
                replace(" ", "_")
            deviation_url = deviation.url
            # Text based deviations need another API call to grab them.
            if deviation.content is None:
                try:
                    text_buffer = da_api.get_deviation_content(
                        deviationid=deviation.deviationid)["html"]
                except deviantart.api.DeviantartError:
                    LOGGER.error(
                        "Unable to download %s", deviation_name)
                    continue
                tracked_file, existing = TrackedFile.add_file(
                    db_session=database.session,
                    media_path=media_storage_path,
                    file_buffer=text_buffer.encode('utf-8'),
                    original_filename=(deviation_name + ".html")
                )
            else:
                file_url = deviation.content["src"]
                tracked_file, existing = TrackedFile.download_file(
                    db_session=database.session,
                    media_path=media_storage_path,
                    url=file_url,
                    filename_override=deviation_name,
                    saved_url_override=deviation_url,
                )

            for category in str(deviation.category_path).split("/"):
                tag = Tag.get_tag(
                    db_session=database.session, tag_name=category)
                if tag not in tracked_file.tags:
                    tracked_file.tags.append(tag)
            database.session.commit()
