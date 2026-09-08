
import importlib.util
import os
from threading import Thread

from OneBotConnecter.OneBot import OneBot
from OneBotConnecter.loger.log_info import error, log
from src.config_reader.config_reader import read_bot_config
from src.console.print_data import print_message
from src.core.register import get_plugin_location, list_plugins
from src.handle_message import handle_message

def add_thread(oncall_function):
    thread = Thread(target=oncall_function)
    thread.run()

def on_message(bot, message):
    print_message(message)
    handle_message(bot, message)

def load_plugin_listeners(bot):
    """bot初始化时扫描插件，启动各插件暴露的后台监听(plugin_listener)"""
    for plugin_name in list_plugins():
        try:
            file = get_plugin_location(plugin_folder=plugin_name)
            plugin_file = os.path.join(file, "plugin.py")
            if not os.path.isfile(plugin_file):
                continue
            #import plugin
            spec = importlib.util.spec_from_file_location(f"plugin_{plugin_name}_init", plugin_file)
            if spec is None or spec.loader is None:
                continue
            #load functions
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            #plugin_listener
            if not hasattr(module, "plugin_listener"):
                continue
            def listener_thread(func=module.plugin_listener, name=plugin_name):
                try:
                    func(bot)
                except Exception as e:
                    error(f"插件{name}后台监听异常: [{type(e)}] {e}")
            thread = Thread(target=listener_thread, daemon=True)
            thread.start()
            log(f"插件[{plugin_name}]后台监听已启动")
        except Exception as e:
            error(f"插件{plugin_name}后台监听加载失败: [{type(e)}] {e}")

def main():
    config = read_bot_config()
    uri = config.get("uri", "ws://127.0.0.1:3001")
    owner = config.get("owner", [])
    bot = OneBot(url=uri, call_function=on_message, owner=owner)
    load_plugin_listeners(bot=bot.handler.handler)
    bot.run()

if __name__ == "__main__":
    main()
