
# == 配置初始化文件 ==

#此文件为OneBot11-小生物的初始化涵数文件
#应用环境为LL-Bot v2.4.4

#如果不清楚具体作用，除配置外，请不要修改任何参数代码


#引用库
#  ==> pip自动下载缺失的库
# type: ignore
import os, traceback
from src.importer import import_package
import src.loger as loger
exec(import_package("Config_reader", package_pip_Name = "Python-json-config-reader"))

#默认初始配置
tsugu_config = {
    "music_temp_path": "data/plugin/bangdream/song",
    "key_set_path": "data/plugin/bangdream/keyset.json",
    "user_acc_path": "data/plugin/bangdream/userBinding.json",
    "tsugu_uri": "http://tsugubot.com:8080",
    "backup_tsugu_uri": "http://127.0.0.1:3000",
    "use_uri": "tsugu_uri",
    "time_out": 20,
    "useEasyBG": False,
    "compress": True
}

#加载配置
def load_config(path):
    #加载配置文件
    try:
        config = Config_reader.load_config(path) #加载配置文件
        #检查配置文件完整
        music_temp_path = config["music_temp_path"]
        key_set_path = config["key_set_path"]
        user_acc_path = config["user_acc_path"]
        tsugu_uri = config["tsugu_uri"]
        backup_tsugu_uri = config["backup_tsugu_uri"]
        use_uri = config["use_uri"]
        useEasyBG = config["useEasyBG"]
        compress = config["compress"]
        time_out = config["time_out"]
        #返回
        return config
    #初始化配置文件
    except Exception as e: 
        Config_reader.dump_config(path=path, data=tsugu_config)
        return load_config(path)