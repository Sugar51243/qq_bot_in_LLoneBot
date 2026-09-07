
from src.config_reader.config_reader import read_plugin_config
from src.project_locator.project_locator import get_project_location
from src.core.register import get_plugin_location, list_plugins, sreach_enabled_plugin, sreach_enabled_scene, sreach_by_scene_id, sreach_by_plugin_id
from src.core.register import register, unenable
from src.core.register import list_plugin_ids, get_plugin_location_by_id
from OneBotConnecter.loger.log_info import error, log
from OneBotConnecter.types import ForwardChain, NodeMessage
import os


def on_all_case(bot, message) -> bool: #call case including message, poke, request ...
    if "message" in message.event_type:
        return on_msg(bot, message=message)

def on_msg(bot, message) -> bool: # message
    handled = False
    handled = handle_noraml_order(bot=bot, message=message) or handle_test_order(bot=bot, message=message)
    return handled

# handling command
def handle_noraml_order(bot, message):
    if handle_help(message): return True
    if message.command in ["启用", "开启"]:
        handle_registe_command(message=message)
        return True
    elif message.command in ["停用", "关闭"]:
        handle_unenable_command(message=message)
        return True
    elif message.command in ["功能列表", "功能"]:
        handle_function_list_command(message=message)
        return True
    elif message.command in ["已启用功能", "已启用"]:
        handle_enable_function_list_command(message=message)
        return True
    elif message.command in ["可启用功能", "可启用"]:
        handle_unenable_function_list_command(message=message)
        return True
    return False

def handle_test_order(bot, message):
    if message.user_id not in bot.bot.owner: return False
    ...
    return False

def handle_help(message):
    test_command = False
    plugin_name = message.text
    if message.command in ["help", "帮助"]:
        test_command = True
        parameters = get_parameters(message=message, parameter_name="plugin ID")
        plugin_name = parameters[0] if len(parameters)>0 else ""
    if message.text in list_plugin_ids() or test_command:
        handle_help_command(message, plugin_name)
        return True
    return False

# tool functions
def get_parameters(message, parameter_name="parameter") -> list:
    targets = message.text.replace(message.command, "").strip().split(" ")
    log(f"Target {parameter_name} INPUT FROM {message.scene_id}: {targets}")
    return targets

def registe_for(targets: list, scene_id: str):
    registed = []
    for plugin_id in targets:
        if plugin_id not in list_plugin_ids():
            error(f"{plugin_id}并非合规ID参数")
            continue
        if plugin_id in sreach_enabled_plugin(scene_id=scene_id):
            error(f"{plugin_id}已在{scene_id}注册记录里")
            continue
        register(scene_id=scene_id, target=plugin_id)
        registed.append(plugin_id)
        log(f"已为{scene_id}注册{plugin_id}成功")
    return registed

def unenable_for(targets: list, scene_id: str):
    unenabled = []
    for plugin_id in targets:
        if plugin_id not in sreach_enabled_plugin(scene_id=scene_id):
            error(f"{plugin_id}并非合规ID参数")
            continue
        unenable(scene_id=scene_id, target=plugin_id)
        unenabled.append(plugin_id)
        log(f"已为{scene_id}停用{plugin_id}成功")
    return unenabled

def read_help_file(path):
    log(f"Now reading file: {path}")
    if not os.path.exists(path):
        default_path = get_project_location()
        default_path = os.path.join(default_path, "samples\\help_samples.txt")
        file = open(file=default_path, mode="r", encoding="utf-8")
        text = file.read()
        file.close()
        file = open(file=path, mode="w", encoding="utf-8")
        file.write(text)
        file.close()
    file = open(file=path, mode="r", encoding="utf-8")
    text = file.read()
    file.close()
    return text

def gen_name_info_by_plugin_folder(plugin_folders: list, scene_id: str):
    enabled_plugin = sreach_enabled_plugin(scene_id=scene_id)
    result = ""
    i = 1
    for plugin_folder in plugin_folders:
        file = get_plugin_location(plugin_folder=plugin_folder)
        plugin_config = read_plugin_config(file)
        id = plugin_config.get("plugin_id")
        info = plugin_config.get("info")
        result += f"{i}. {id} "
        result += "[已启用]:\n" if id in enabled_plugin else "[未启用]:\n"
        result += f"{info}\n"
        i += 1
    if i == 1: result+="未有可用插件"
    return result

# command functions
#启用
def handle_registe_command(message):
    if message.at_other: return False
    targets = get_parameters(message=message, parameter_name="Plugin ID")
    if len(targets) == 1:
        if targets[0] == "all":
            targets = list_plugin_ids()
            targets.remove("样本插件")
    registed = registe_for(targets=targets, scene_id=message.scene_id)
    if registed != []:
        message.reply_message(f"已成功注册以下插件:\n{registed}\n(如果未列入，证明该插件已注册或不可用)")
    else: message.reply_message(f"插件注册未成功，无合规插件参数ID或插件已注册")
#停用
def handle_unenable_command(message):
    if message.at_other: return False
    targets = get_parameters(message=message, parameter_name="Plugin ID")
    if len(targets) == 1:
        if targets[0] == "all":
            targets = list_plugin_ids()
            targets.remove("样本插件")
    unenabled = unenable_for(targets=targets, scene_id=message.scene_id)
    if unenabled != []:
        message.reply_message(f"已成功停用以下插件:\n{unenabled}\n(如果未列入，证明该插件未注册)")
    else: message.reply_message(f"插件停用未成功，无合规插件参数ID或插件已注册")
#帮助
def handle_help_command(message, plugin_name):
    if message.at_other: return False
    if plugin_name in list_plugin_ids(): file_path = os.path.join(get_plugin_location_by_id(target_plugin_id=plugin_name), "help.txt")
    elif plugin_name == "": file_path = os.path.join(get_project_location(), "src\\core\\help.txt")
    else:
        error("Plugin ID invail")
        return
    reply_message = ForwardChain(read_help_file(file_path))
    help_text = '''帮助文件解读帮助:
    (): 可选参数
    <>: 必填参数
    ~: 指令别称
    →: 指令功能解释
    例: 指令使用例'''
    reply_message.add(help_text)
    message.reply_message(reply_message)
#功能列表
def handle_function_list_command(message):
    plugins = list_plugins()
    reply_message = "功能列表(全部):\n"
    reply_message += gen_name_info_by_plugin_folder(plugin_folders=plugins, scene_id=message.scene_id)
    message.reply_message(ForwardChain(reply_message))

#已启用功能
def handle_enable_function_list_command(message):
    enable_list = []
    plugins = list_plugins()
    enabled_plugin = sreach_enabled_plugin(scene_id=message.scene_id)
    reply_message = "功能列表(已启用):\n"
    for plugin_folder in plugins:
        file = get_plugin_location(plugin_folder=plugin_folder)
        plugin_config = read_plugin_config(file)
        id = plugin_config.get("plugin_id")
        if id in enabled_plugin: enable_list.append(plugin_folder)
    reply_message += gen_name_info_by_plugin_folder(plugin_folders=enable_list, scene_id=message.scene_id)
    message.reply_message(ForwardChain(reply_message))
#可启用功能
def handle_unenable_function_list_command(message):
    unenable_list = []
    plugins = list_plugins()
    enabled_plugin = sreach_enabled_plugin(scene_id=message.scene_id)
    reply_message = "功能列表(未启用):\n"
    for plugin_folder in plugins:
        file = get_plugin_location(plugin_folder=plugin_folder)
        plugin_config = read_plugin_config(file)
        id = plugin_config.get("plugin_id")
        if id not in enabled_plugin: unenable_list.append(plugin_folder)
    reply_message += gen_name_info_by_plugin_folder(plugin_folders=unenable_list, scene_id=message.scene_id)
    message.reply_message(ForwardChain(reply_message))

