
import os, sys, time, threading

from src.config_reader.config_reader import read_plugin_config
from src.project_locator.project_locator import get_project_location
from src.core.register import get_plugin_location, list_plugins, sreach_enabled_plugin, sreach_enabled_scene, sreach_by_scene_id, sreach_by_plugin_id
from src.core.register import register, unenable
from src.core.register import list_plugin_ids, get_plugin_location_by_id, delete_scene_records
from src.core import request_center
from OneBotConnecter.loger.log_info import error, log
from OneBotConnecter.types import ForwardChain, NodeMessage, MessageChain

#管理员帮助文件
admin_help_path = os.path.join(get_project_location(), "src", "core", "admin_help.txt")

#待确认退群场景
waiting_leave = []


def on_all_case(bot, message) -> bool: #call case including message, poke, request ...
    if "message" in message.event_type:
        return on_msg(bot, message=message)
    return on_event(bot, message=message)

def on_msg(bot, message) -> bool: # message
    handled = False
    handled = handle_noraml_order(bot=bot, message=message) or handle_test_order(bot=bot, message=message)
    return handled

def on_event(bot, message) -> bool: # notice, request ...
    #请求事件(入群/好友申请)为内置常驻功能
    if message.raw_data.get("post_type") == "request":
        return request_center.handle_request(bot, message)
    return False

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
    # == 内置管理员指令 ==
    elif message.command in ["管理员帮助", "管理帮助", "admin"]:
        handle_admin_help_command(bot=bot, message=message)
        return True
    elif message.command in ["重启"]:
        handle_restart_command(bot=bot, message=message)
        return True
    elif message.command in ["退群"]:
        handle_leave_command(bot=bot, message=message)
        return True
    elif message.command in ["确认"] and message.scene_id in waiting_leave:
        leave_group(bot=bot, message=message)
        return True
    elif message.command in ["取消"] and message.scene_id in waiting_leave:
        waiting_leave.remove(message.scene_id)
        message.reply_message(MessageChain([f"\n退群动作已取消。"]))
        return True
    elif "同意" in message.text and is_owner(bot=bot, message=message):
        request_center.handle_approve(bot, message)
        return True
    elif message.command in ["添加白名单"] and is_owner(bot=bot, message=message):
        request_center.handle_add_allow(bot, message)
        return True
    return False

def is_owner(bot, message) -> bool:
    return str(message.user_id) in [str(owner_id) for owner_id in bot.bot.owner]

#管理员帮助
def handle_admin_help_command(bot, message):
    if not is_owner(bot=bot, message=message):
        message.reply_message(MessageChain(["权限不足"]))
        return
    reply_message = ForwardChain(read_help_file(admin_help_path))
    help_text = '''帮助文件解读帮助:
    (): 可选参数
    <>: 必填参数
    ~: 指令别称
    →: 指令功能解释
    例: 指令使用例'''
    reply_message.add(help_text)
    message.reply_message(reply_message)

#重启
def handle_restart_command(bot, message):
    if not is_owner(bot=bot, message=message):
        message.reply_message(MessageChain(["权限不足"]))
        return
    message.reply_message(MessageChain(["程序即将重启"]))
    log("程序即将重启...")
    #延迟重启以留出消息发送时间
    threading.Thread(target=lambda: (time.sleep(2), os.execv(sys.executable, ['python'] + sys.argv)), daemon=True).start()

#退群
def handle_leave_command(bot, message):
    if "group" not in message.scene_id:
        message.reply_message(MessageChain([f"私聊不可使用退群指令"]))
        return
    if message.scene_id in waiting_leave:
        waiting_leave.remove(message.scene_id)
        leave_group(bot=bot, message=message)
        return
    #权限检查: 群主/管理
    try:
        member_data = bot.get_group_member_info(int(message.raw_data.get("group_id")), int(message.user_id))
        role = member_data.data.role
        if role not in ["owner", "admin"]:
            raise Exception("权限不足")
    except Exception:
        message.reply_message(MessageChain([f"你并非该群管理/群主"]))
        return
    message.reply_message(MessageChain([f'\n小生物将退出本群。\n请再次输入指令或发送"确认"以确认退群\n误触发请发送"取消"']))
    waiting_leave.append(message.scene_id)

def leave_group(bot, message):
    message.reply_message(MessageChain([f"小生物将退群"]))
    bot.set_group_leave(message.raw_data.get("group_id"))
    delete_scene_records(scene_id=message.scene_id)
    log(f"已退群[{message.scene_id}]并清理注册记录")

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

