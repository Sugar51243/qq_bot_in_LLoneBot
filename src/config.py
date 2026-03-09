
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
onebot_config = {
    "uri": "ws://127.0.0.1:3001",
    "owner": [],
    "botName": [],
    "allowSlash": True
}

#加载配置
def load_config(path):
    #加载配置文件
    try:
        config = Config_reader.load_config(path) #加载配置文件
        #检查配置文件完整
        uri = config["uri"]
        owner = config["owner"]
        botName = config["botName"]
        allowSlash = config["allowSlash"]
        #返回
        return config
    #初始化配置文件
    except Exception as e: 
        Config_reader.dump_config(path=path, data=onebot_config)
        return load_config(path)