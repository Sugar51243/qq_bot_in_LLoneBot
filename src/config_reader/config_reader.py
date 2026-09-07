
import os
from src.project_locator.project_locator import get_project_location
from Config_reader import dump_config, load_config
from OneBotConnecter.loger.log_info import error


def read_bot_config() -> dict:
    path = get_project_location()
    config_location = os.path.join(path, "config.yaml")
    try:
        config = load_config(path=config_location)
        if not config: raise Exception()
    except Exception as e:
        def_config_location = os.path.join(path, "samples\\onebot_config.json")
        config = load_config(def_config_location)
        dump_config(path=config_location, data=config)
    return config

def read_plugin_config(plugin_folder) -> dict:
    file = os.path.join(plugin_folder, f"info.json")
    try:
        config = load_config(path=file)
        if not config: raise Exception()
    except Exception as e:
        path = get_project_location()
        def_config_location = os.path.join(path, "samples\\plugin_samples.json")
        config = load_config(def_config_location)
        dump_config(path=file, data=config)
    return config

def read_config(path) -> dict:
    try:
        config = load_config(path=path)
        if not config: raise Exception()
    except Exception as e:
        error("Config Not Found")
        return {}
    return config
