
import os, sys
from Config_reader import dump_config, load_config
from OneBotConnecter.loger.log_info import error


def get_project_location():
    main_file = sys.modules["__main__"].__file__
    path = os.path.dirname(os.path.abspath(main_file))
    return path

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
