
# == Tomori OurNotes插件配置模块 ==

# 运行时配置存放于data/plugin/tomori_ournotes/config.yaml
# 初次运行时从samples/plugins/tomori_ournotes/config.yaml样本生成

import os, shutil
from Config_reader import dump_config
from OneBotConnecter.loger.log_info import log
from src.config_reader.config_reader import read_config
from src.project_locator.project_locator import get_project_location

default_ournotes_config = {
    "ournotes_uri": "http://127.0.0.1:3002",
    "time_out": 60,
    "compress": True,
    #机器人侧公告推流总开关(默认开启): 开启时bot启动自动建立四服务器公告长连接
    "announcement_stream": True
}

def get_config_path() -> str:
    return os.path.join(get_project_location(), "data", "plugin", "tomori_ournotes", "config.yaml")

def get_sample_path() -> str:
    return os.path.join(get_project_location(), "samples", "plugins", "tomori_ournotes", "config.yaml")

def load_config() -> dict:
    """加载运行时配置，缺失时从样本生成，缺失键以默认值补齐"""
    path = get_config_path()
    if not os.path.isfile(path):
        #若config.yaml位置被误建为文件夹(此时shutil.copy会把样本复制进文件夹内部), 清除后重新生成文件
        if os.path.isdir(path):
            shutil.rmtree(path)
            log(f"[TOMORI] 检测到配置路径为文件夹, 已清除并重新生成: {path}")
        #初次运行: 从样本配置生成
        os.makedirs(os.path.dirname(path), exist_ok=True)
        sample = get_sample_path()
        if os.path.isfile(sample):
            shutil.copy(sample, path)
            log(f"[TOMORI] 已从样本配置生成运行时配置: {path}")
        else:
            dump_config(path=path, data=dict(default_ournotes_config))
    config = read_config(path)
    if not config:
        config = dict(default_ournotes_config)
        dump_config(path=path, data=config)
        return config
    changed = False
    for key, value in default_ournotes_config.items():
        if key not in config:
            config[key] = value
            changed = True
    if changed:
        dump_config(path=path, data=config)
    return config
