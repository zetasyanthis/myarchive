"""Handles imports from shotwell databases."""

import os

from collections import defaultdict

from myarchive.db.tag_db.tables import TrackedFile, Tag
from myarchive.db.shotwell.shotwell_db import ShotwellDB
from myarchive.db.shotwell.tables import PhotoTable, VideoTable, TagTable


def import_from_shotwell_db(
        tag_db, media_path, sw_database_path, sw_storage_folder_override=None):
    """Imports images from the shotwell DB into ours."""
    sw_db = ShotwellDB(
        drivername='sqlite',
        db_name=sw_database_path,
    )

    if sw_storage_folder_override:
        photo_paths = []
        for photo_path, in sw_db.session.query(PhotoTable.filename):
            photo_paths.append(photo_path)
        original_storage_path = os.path.commonprefix(photo_paths)
        del photo_paths

    # Grab all the photos and add them.
    files_by_id = dict()
    for table in (PhotoTable, VideoTable):
        for photo_row in sw_db.session.query(table):
            filepath = str(photo_row.filename)
            if sw_storage_folder_override:
                filepath = filepath.replace(
                    original_storage_path, sw_storage_folder_override)
            tracked_file = TrackedFile.add_file(
                db_session=tag_db.session, media_path=media_path,
                copy_from_filepath=filepath)
            files_by_id[int(photo_row.id)] = tracked_file
            tag_db.session.add(tracked_file)
    tag_db.session.commit()

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

    for photo_id, tracked_file in files_by_id.items():
        for tag_name in tags_by_id[photo_id]:
            tag = tags_by_tag_name[tag_name]
            tracked_file.tags.append(tag)
    tag_db.session.commit()
