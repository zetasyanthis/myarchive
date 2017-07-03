


def download_user_data(database, config, media_storage_path):
    for config_section in config.sections():
        if config_section.startswith("DeviantArt_"):
            client_id = config.get(
                section=config_section, option="client_id"),
            client_secret = config.get(
                section=config_section, option="client_secret"),
