
import importlib.util
import os

from src.Information_interpreter.message_interpreter import interpret_message
from src.config_reader.config_reader import read_bot_config, read_plugin_config
import src.core.core_function as core_function
from src.core.register import get_plugin_location, list_plugins, sreach_enabled_plugin
from src.core import stats as stats_module
from OneBotConnecter.loger.log_info import error, log
from datetime import datetime

def active_plugin(plugin_name, bot, message):
        order_handled = False
        file = get_plugin_location(plugin_folder=plugin_name)
        plugin_file = os.path.join(file, "plugin.py")
        if not os.path.isfile(plugin_file):
            error("插件内容未写入 ")
            return order_handled
        #import plugin
        spec = importlib.util.spec_from_file_location(f"plugin_{plugin_name}", plugin_file)
        if spec is None or spec.loader is None:
            return order_handled
        #load functions
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        #on_msg
        if hasattr(module, "on_all_case"):
            try:
                order_handled = module.on_all_case(bot, message)
            except Exception as e:
                error(f"[{type(e)}] {e}")
        log(f"{plugin_name} active complete for [{message.scene_id}]")
        return order_handled

def handle_message(bot, message):
    start_time = datetime.now()
    # ban list
    config = read_bot_config()
    ban_user = config.get("ban_user", [])
    ban_group = config.get("ban_group", [])
    if message.user_id in ban_user or message.raw_data.get("group_id", None) in ban_group:
        return
    # interpret message
    message = interpret_message(message=message, bot=bot)
    # core functions
    core_handled = core_function.on_all_case(bot, message=message)
    order_handled = core_handled
    # load plugins
    plugins = list_plugins()
    permissions = sreach_enabled_plugin(message.scene_id)
    log(f"loaded plugins: {plugins}")
    log(f"permissions of [{message.scene_id}]: {permissions}")
    # active plugins
    for plugin_name in plugins:
        log(f"loading {plugin_name} for [{message.scene_id}]")
        file = get_plugin_location(plugin_folder=plugin_name)
        plugin_config = read_plugin_config(file)
        plugin_id = plugin_config.get("plugin_id")
        if not plugin_id:
            log(f"{plugin_name} 未定义plugin_id")
            continue
        if plugin_id not in permissions:
            log(f"{plugin_name} not enabled on [{message.scene_id}]")
            continue
        handled = active_plugin(plugin_name, bot, message)
        if handled:
            order_handled = True
            stats_module.record_cmd_plugin(plugin_id, message.command)  # 统计：按插件分类排行
    end_time = datetime.now()
    current_time = end_time-start_time
    log(f"Handle message for [{message.scene_id}] in {current_time}")
    # 统计：消息事件被核心/插件成功处理（通知/请求类事件不计指令）
    if message.raw_data.get("post_type") == "message":
        if core_handled and message.command:
            stats_module.record_cmd_plugin("核心内置", message.command)  # 核心指令归入分类视图
        if order_handled and message.command:
            stats_module.record_cmd_any(message.command)  # 不计插件：全量指令名排行
        if order_handled:
            stats_module.record_command()
