"""Handles deviantart calls."""

import deviantart
import logging

from sqlalchemy.orm.exc import NoResultFound

from myarchive.db.tag_db.tables import Deviation, Tag, TrackedFile
from myarchive.db.tag_db.tables.datables import get_da_user

LOGGER = logging.getLogger(__name__)

FAVORITES_RSS = "http://backend.deviantart.com/rss.xml?q=favby%%3A%(username)s"
GALLERY_RSS = "http://backend.deviantart.com/rss.xml?q=gallery%%3A%(username)s"


GALLERY = "GALLERY"
FAVORITES = "FAVORITES"


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

            # Grab user data.
            LOGGER.info("Pulling data for user: %s...", username)
            get_da_user(
                db_session=database.session,
                da_api=da_api,
                username=username,
                media_storage_path=media_storage_path)

            for sync_type in (GALLERY, FAVORITES):
                __download_user_deviations(
                    database=database,
                    da_api=da_api,
                    username=username,
                    sync_type=sync_type,
                    media_storage_path=media_storage_path,
                )


def __download_user_deviations(
        database, media_storage_path, da_api, username, sync_type,
        force_full_scan=False):

    if sync_type == GALLERY:
        collections = da_api.get_gallery_folders(username=username)
    elif sync_type == FAVORITES:
        collections = da_api.get_collections(username=username)
    else:
        raise Exception("Type of sync not supported: %s" % sync_type)

    for collection in collections["results"]:
        collection_name = collection["name"]
        LOGGER.info("Scanning %s (%s) for deviations...",
                    sync_type, collection_name)
        folderid = collection["folderid"]

        # Grab list of existing deviationids.
        query_results = database.session.query(Deviation.deviationid).all()
        existing_deviationids = [item for (item,) in query_results]

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

                # Normally, we only check
                if force_full_scan is False:
                    for deviation in fetched_deviations["results"]:
                        if deviation.deviationid in existing_deviationids:
                            break

            except deviantart.api.DeviantartError as error:
                # catch and print API exception and stop loop
                LOGGER.error("Error querying DA API for collection: %s" % error)
                has_more = False

        new_deviations = []
        for deviation in deviations:
            if deviation.deviationid not in existing_deviationids:
                new_deviations.append(deviation)
        LOGGER.info("%s new deviations found.", len(new_deviations))

        # Only pull all tags ahead of time if we have a lot of new files.
        existing_tags_by_name = dict()
        if len(new_deviations) > 50:
            existing_tags = database.session.query(Tag).all()
            existing_tags_by_name = {
                tag.name: tag for tag in existing_tags
            }

        # Loop through deviations and save author data.
        for deviation in new_deviations:
            # Grab user data.
            get_da_user(
                db_session=database.session,
                da_api=da_api,
                username=deviation.author.username,
                media_storage_path=media_storage_path)

        # Loop through and save deviations.
        for deviation in new_deviations:
            # If there's no content (if it's a story), skip for now.
            deviation_name = (
                str(deviation.title) + "." + str(deviation.author)). \
                replace(" ", "_")
            deviation_url = deviation.url

            # Text based deviations need another API call to grab them.
            file_url = None
            if deviation.content is None:
                # Flash files get handled specially.
                if deviation.__dict__.get("flash"):
                    file_url = deviation.__dict__.get("flash")["src"]
                # Otherwise it's probably a text file. We'll catch (and report)
                # the error if something blows up.
                else:
                    try:
                        text_buffer = da_api.get_deviation_content(
                            deviationid=deviation.deviationid)["html"]
                    except deviantart.api.DeviantartError:
                        LOGGER.error("Unable to download %s", deviation_name)
                        LOGGER.critical(deviation.__dict__)
                        continue
                    tracked_file, existing = TrackedFile.add_file(
                        db_session=database.session,
                        media_path=media_storage_path,
                        file_buffer=text_buffer.encode('utf-8'),
                        original_filename=(deviation_name + ".html")
                    )
            else:
                file_url = deviation.content["src"]

            # Grab the file if we were handed a URL.
            if file_url is not None:
                tracked_file, existing = TrackedFile.download_file(
                    db_session=database.session,
                    media_path=media_storage_path,
                    url=file_url,
                    filename_override=deviation_name,
                    saved_url_override=deviation_url,
                )

            # Grab metadata for the deviation.
            deviation_metadata = da_api.get_deviation_metadata(
                deviationids=[deviation.deviationid],
                ext_submission=True, ext_camera=True)[0]

            # Create the Deviation DB entry. If we already have it, skip all
            # this madness.
            try:
                database.session.query(Deviation).\
                    filter_by(deviationid=str(deviation.deviationid)).one()
                continue
            except NoResultFound:
                db_deviation = Deviation(
                    title=deviation.title,
                    description=deviation_metadata["description"],
                    deviationid=deviation.deviationid,
                )
                db_deviation.file = tracked_file
                database.session.add(db_deviation)

            # Handle tags, category, and author tags.
            if sync_type == GALLERY:
                sync_type_tag_name = "gallery"
            else:
                sync_type_tag_name = "favorite"
            tags_names = [
                "da.user.%s.%s" % (username, sync_type_tag_name),
                "da.user.%s.%s.%s" % (
                    username, sync_type_tag_name, collection_name),
                "da.author." + str(deviation.author),
                collection_name,
            ]
            tags_names.extend(str(deviation.category_path).split("/"))
            tags_names.extend(
                [tag_dict["tag_name"]
                 for tag_dict in deviation_metadata["tags"]]
            )
            if deviation_metadata["is_mature"]:
                tags_names.append("nsfw")
            for tag_name in tags_names:
                if tag_name in existing_tags_by_name:
                    tag = existing_tags_by_name[tag_name]
                else:
                    tag = Tag.get_tag(
                        db_session=database.session,
                        tag_name=tag_name)
                    existing_tags_by_name[tag_name] = tag
                if tag_name not in tracked_file.tag_names:
                    tracked_file.tags.append(tag)
                if tag_name not in db_deviation.tag_names:
                    db_deviation.tags.append(tag)

            database.session.commit()
