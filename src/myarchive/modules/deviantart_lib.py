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

            da = deviantart.Api(
                client_id=client_id[0],
                client_secret=client_secret[0],
            )
            da.oauth.request_token(grant_type="client_credentials")

            # If authenticated and access_token present
            if da.access_token:
                # Grab the User object of the authorized user
                user = da.get_user(username=username)
                LOGGER.info("Pulling data for user: %s", user.username)

                # user.usericon
                # user.userid

                collections = da.get_collections(username=username)
                for collection in collections["results"]:
                    LOGGER.info(
                        "Pulling favorited deviations from collection: %s..." %
                        collection["name"])
                    folderid = collection["folderid"]

                    deviations = []
                    offset = 0
                    has_more = True
                    # while there are more deviations to fetch
                    while has_more:
                        try:
                            # fetch deviations from user
                            fetched_deviations = da.get_collection(
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

                        except deviantart.api.DeviantartError as e:
                            # catch and print API exception and stop loop
                            LOGGER.error(e)
                            has_more = False

                    # Loop through and save deviations.
                    for deviation in deviations:
                        # If there's no content (if it's a story), skip for now.
                        deviation_name = (
                            str(deviation.title) + str(deviation.author)). \
                            replace(" ", "_")
                        deviation_url = deviation.url
                        if deviation.content is None:
                            LOGGER.warning(
                                "Ignoring story (download unsupported for now) "
                                "%s", deviation_name)
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
