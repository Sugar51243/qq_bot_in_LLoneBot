
# == Tsugu插件配置模块 ==

# 运行时配置存放于data/plugin/tsugu_plugin/config.yaml
# 初次运行时从samples/plugins/tsugu_plugin/config.yaml样本生成

import os, shutil
from Config_reader import dump_config
from OneBotConnecter.loger.log_info import log
from src.config_reader.config_reader import read_config
from src.project_locator.project_locator import get_project_location

default_tsugu_config = {
    "music_temp_path": "data/plugin/tsugu_plugin/song",
    "card_temp_path": "data/plugin/tsugu_plugin/card",
    "tsugu_uri": "http://tsugubot.com:8080",
    "backup_tsugu_uri": "",
    "use_uri": "tsugu_uri",
    "time_out": 20,
    "useEasyBG": False,
    "compress": True
}

def get_config_path() -> str:
    return os.path.join(get_project_location(), "data", "plugin", "tsugu_plugin", "config.yaml")

def get_sample_path() -> str:
    return os.path.join(get_project_location(), "samples", "plugins", "tsugu_plugin", "config.yaml")

def load_config() -> dict:
    """加载运行时配置，缺失时从样本生成，缺失键以默认值补齐"""
    path = get_config_path()
    if not os.path.isfile(path):
        #初次运行: 从样本配置生成
        os.makedirs(os.path.dirname(path), exist_ok=True)
        sample = get_sample_path()
        if os.path.isfile(sample):
            shutil.copy(sample, path)
            log(f"[Tsugu] 已从样本配置生成运行时配置: {path}")
        else:
            dump_config(path=path, data=dict(default_tsugu_config))
    config = read_config(path)
    if not config:
        config = dict(default_tsugu_config)
        dump_config(path=path, data=config)
        return config
    changed = False
    for key, value in default_tsugu_config.items():
        if key not in config:
            config[key] = value
            changed = True
    if changed:
        dump_config(path=path, data=config)
    return config
