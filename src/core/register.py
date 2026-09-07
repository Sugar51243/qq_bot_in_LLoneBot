
import os, time
from src.config_reader.config_reader import read_plugin_config
from src.project_locator.project_locator import get_project_location
from src.db_handler.database_handler import get_all_data_from, return_default_folder, call_database, get_from_database
from OneBotConnecter.loger.log_info import error, log

permission_db = return_default_folder()
permission_db = os.path.join(permission_db, "permissions.db")

table_name = "permission_records"

def gen_scene_id(message) -> str:
    scene_id = message.group_or_private()
    scene_id += str(message.raw_data.get("group_id", "")) if "group" in scene_id else str(message.user_id)
    return scene_id

def create_database():
    path = return_default_folder()
    if not os.path.exists(path):
        os.makedirs(path)
    if os.path.exists(permission_db):
        return
    log(f"数据库{permission_db}未存在，正在生成")
    global table_name
    sta = f'''CREATE TABLE IF NOT EXISTS {table_name} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scene_id TEXT NOT NULL,
    plugin_id TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    UNIQUE(scene_id, plugin_id)
    );
    '''
    call_database(path=permission_db, sta=sta)
    sta = f"CREATE INDEX idx_scene ON {table_name}(scene_id);"
    call_database(path=permission_db, sta=sta)
    sta = f"CREATE INDEX idx_plugin ON {table_name}(plugin_id);"
    call_database(path=permission_db, sta=sta)

def register(scene_id, target):
    create_database()
    now = int(time.time())
    global table_name
    sta =f'''INSERT OR IGNORE INTO {table_name} (
    scene_id, plugin_id, enabled, created_at, updated_at
    ) VALUES (
    "{scene_id}", "{target}", 1, {now}, {now}
    )
    '''
    call_database(path=permission_db, sta=sta)
    sta =f'''UPDATE {table_name}
    SET enabled = 1, updated_at = {now}
    WHERE scene_id = "{scene_id}" AND plugin_id = "{target}";
    '''
    call_database(path=permission_db, sta=sta)

def unenable(scene_id, target):
    create_database()
    now = int(time.time())
    global table_name
    sta =f'''INSERT OR IGNORE INTO {table_name} (
    scene_id, plugin_id, enabled, created_at, updated_at
    ) VALUES (
    "{scene_id}", "{target}", 1, {now}, {now}
    )
    '''
    call_database(path=permission_db, sta=sta)
    sta =f'''UPDATE {table_name}
    SET enabled = 0, updated_at = {now}
    WHERE scene_id = "{scene_id}" AND plugin_id = "{target}";
    '''
    call_database(path=permission_db, sta=sta)

def sreach_enabled_plugin(scene_id: str):
    create_database()
    global table_name
    sta =f'''SELECT plugin_id
    FROM {table_name}
    WHERE scene_id = "{scene_id}" AND enabled = 1;
    '''
    result = [plugin_id[0] for plugin_id in get_from_database(path=permission_db, sta=sta)]
    return result

def sreach_enabled_scene(plugin_id: str):
    create_database()
    global table_name
    sta =f'''SELECT scene_id
    FROM {table_name}
    WHERE plugin_id = "{plugin_id}" AND enabled = 1;
    '''
    result = [scene_id[0] for scene_id in get_from_database(path=permission_db, sta=sta)]
    return result

def sreach_by_scene_id(scene_id: str):
    create_database()
    global table_name
    sta =f'''SELECT plugin_id, enabled
    FROM {table_name}
    WHERE scene_id = "{scene_id}";
    '''
    result = [plugin_id[0] for plugin_id in get_from_database(path=permission_db, sta=sta)]
    return result

def sreach_by_plugin_id(plugin_id: str):
    create_database()
    global table_name
    sta =f'''SELECT scene_id, enabled
    FROM {table_name}
    WHERE plugin_id = "{plugin_id}";
    '''
    result = [scene_id[0] for scene_id in get_from_database(path=permission_db, sta=sta)]
    return result

def test_database():
    return get_all_data_from(path=permission_db, table=table_name)

def list_plugins():
    location = os.path.join(get_project_location(), "src", "plugins")
    if not os.path.isdir(location):
        return []
    return [item for item in os.listdir(location) if os.path.isdir(os.path.join(location, item))]

def list_plugin_ids():
    result = []
    plugins = list_plugins()
    for plugin_name in plugins:
        file = get_plugin_location(plugin_folder=plugin_name)
        plugin_config = read_plugin_config(file)
        plugin_id = plugin_config.get("plugin_id")
        if plugin_id == "插件ID样版": continue
        result.append(plugin_id)
    return result

def get_plugin_location(plugin_folder):
    location = os.path.join(get_project_location(), "src", "plugins")
    return os.path.join(location, str(plugin_folder))

def get_plugin_location_by_id(target_plugin_id):
    plugins = list_plugins()
    for plugin_name in plugins:
        file = get_plugin_location(plugin_folder=plugin_name)
        plugin_config = read_plugin_config(file)
        plugin_id = plugin_config.get("plugin_id")
        if plugin_id == target_plugin_id:
            return file
    error("Plugin not Found")
    