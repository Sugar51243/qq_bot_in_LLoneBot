
# == 配置初始化文件 ==

#此文件为OneBot11-小生物的初始化涵数文件
#应用环境为LL-Bot v2.4.4

#如果不清楚具体作用，除配置外，请不要修改任何参数代码


#引用库
#  ==> pip自动下载缺失的库
import os
try:
    from Config_reader import load_config as load, dump_config as dump
except:
    os.system("pip install Python-json-config-reader")
    exec("from Config_reader import load_config as load, dump_config as dump")

#默认初始配置
onebot_config = {
    "owner": [],
    "uri": "ws://127.0.0.1:3001",
    "backlist": [],
    "botName": []
}

#加载配置
def load_onebot_config(path):
    #加载配置文件
    try:
        config = load(path) #加载配置文件
        #检查配置文件完整
        owner = config["owner"]
        uri = config["uri"]
        backlist = config["backlist"]
        botName = config["botName"]
        #返回
        return config
    #初始化配置文件
    except:
        dump(path=path, data=onebot_config)
        return load_onebot_config(path)