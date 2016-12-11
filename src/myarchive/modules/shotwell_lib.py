"""Handles imports from shotwell databases."""

import os

from collections import defaultdict

from myarchive.db.tag_db.tables.file import TrackedFile
from myarchive.db.shotwell.shotwell_db import ShotwellDB
from myarchive.db.shotwell.tables import PhotoTable, TagTable


def import_from_shotwell_db(
        tag_db, media_path, sw_database_path, sw_storage_folder_override=None):
    """Imports images from the shotwell DB into ours."""
    sw_db = ShotwellDB(
        drivername='sqlite',
        db_name=sw_database_path,
    )

    # Grab all the photos and add them.
    photos_by_id = dict()
    for photo_row in sw_db.session.query(PhotoTable):
        filepath = str(photo_row.filename)
        # if sw_storage_folder_override:
        #     stripped_filename = filename.replace("", "")
        #     filename = os.path.join(
        #         sw_storage_folder_override, stripped_filename)
        tracked_file = TrackedFile.add_file(
            db_session=tag_db.session, media_path=media_path,
            copy_from_filepath=filepath)
        photos_by_id[int(photo_row.id)] = tracked_file
        tag_db.session.add(tracked_file)
    tag_db.session.commit()

    # Grab all the tags and apply them to the photos.
    ids_by_tag = dict()
    for tag_row in sw_db.session.query(TagTable):
        tag_name = tag_row.name
        tag_ids = [
            int(photo_id[5:], 16)
            for photo_id in tag_row.photo_id_list.split(",")]
        ids_by_tag[tag_name] = tag_ids

    for id, tracked_file in photos_by_id.items():
        pass
