"""Handles imports from shotwell databases."""

from multiprocessing import Pool

from collections import defaultdict
from logging import getLogger
from os.path import expanduser

from myarchive.db.tag_db.tables import TrackedFile, Tag
from myarchive.db.tag_db.tables.file import get_md5sum_by_filename
from myarchive.db.shotwell.shotwell_db import ShotwellDB
from myarchive.db.shotwell.tables import PhotoTable, VideoTable, TagTable


LOGGER = getLogger("myarchive")


DEFAULT_STORAGE_FILEPATH = expanduser("~/.local/share/shotwell/images/")


def import_from_shotwell_db(
        tag_db, media_storage_path, sw_database_path, sw_media_path):
    """Imports images from the shotwell DB into ours."""
    sw_db = ShotwellDB(
        db_name=sw_database_path,
    )

    # if sw_media_path != DEFAULT_STORAGE_FILEPATH:
    #     pass

    shotwell_tag = Tag.get_tag(db_session=tag_db.session, tag_name="shotwell")
    tag_db.session.commit()

    LOGGER.info("Importing images... [Part 1 of 3]")
    # Grab all the photos and add them.
    files_by_id = dict()
    for table in (PhotoTable, VideoTable):

        # if sw_media_path != DEFAULT_STORAGE_FILEPATH:
        #     pass
        # if sw_storage_folder_override:
        #     filepath = original_storage_path.replace(
        #         original_storage_path, sw_storage_folder_override)

        # Calculate md5sums ahead of time and in parallel to speed this all up
        # dramatically.
        row_tuples = [
            (photo_row[0], photo_row[1]) for photo_row in
            sw_db.session.query(table.id, table.filename).all()]
        md5sum_pool = Pool()
        media_tuples = md5sum_pool.starmap(get_md5sum_by_filename, row_tuples)

        for media_tuple in media_tuples:
            media_id, media_path, media_md5sum = media_tuple
            tracked_file, existing = TrackedFile.add_file(
                db_session=tag_db.session,
                media_path=media_storage_path,
                copy_from_filepath=media_path,
                md5sum_override=media_md5sum,
            )
            files_by_id[media_id] = tracked_file
            tracked_file.tags.append(shotwell_tag)
            tag_db.session.add(tracked_file)
    tag_db.session.commit()

    LOGGER.info("Reading in tags... [Part 2 of 3]")
    # Grab all the tags and apply them to the photos.
    tags_by_id = defaultdict(list)
    tags_by_tag_name = dict()
    for tag_tuple in sw_db.session.query(
            TagTable.name, TagTable.photo_id_list).all():
        tag_name = tag_tuple[0]
        tag_ids = list()
        photo_id_str = tag_tuple[1]
        if not photo_id_str:
            continue
        for photo_id in photo_id_str.split(","):
            if not photo_id:
                continue
            tag_ids.append(int(photo_id[5:], 16))
        for tag_id in tag_ids:
            tags_by_id[tag_id].append(tag_name)
        tags_by_tag_name[tag_name] = \
            Tag.get_tag(db_session=tag_db.session, tag_name=tag_name)

    LOGGER.info("Attaching tags... [Part 3 of 3]")
    for photo_id, tracked_file in files_by_id.items():
        for tag_name in tags_by_id[photo_id]:
            tag = tags_by_tag_name[tag_name]
            tracked_file.tags.append(tag)
    tag_db.session.commit()
