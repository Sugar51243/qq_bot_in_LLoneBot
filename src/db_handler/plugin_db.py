
# == 插件数据库工具 ==

# 每个插件使用一个独立的sqlite数据库文件(data/db/<plugin_id>.db)
# 数据按类别使用分表功能储存
# 由于v2插件为每条消息动态加载新模块，此模块经由普通import缓存于sys.modules，
# 因此本模块内的字典/线程注册表可跨消息保留状态

import json, os, sqlite3, threading
from OneBotConnecter.loger.log_info import error, log
from src.db_handler.database_handler import return_default_folder


class PluginDB:
    """插件独立数据库：一个插件一个db文件，数据按表分表储存

    plugin_id: 插件ID(插件名称)
    db_name:   数据库文件名(不含.db)，默认与plugin_id相同
    """

    def __init__(self, plugin_id: str, tables: dict, db_name: str = None):
        self.plugin_id = plugin_id
        self.db_name = db_name if db_name else plugin_id
        self.path = os.path.join(return_default_folder(), f"{self.db_name}.db")
        self.tables = tables
        self.create()

    def create(self):
        folder = os.path.dirname(self.path)
        if not os.path.exists(folder):
            os.makedirs(folder)
        for table, sta in self.tables.items():
            self.execute(sta)
        return True

    def execute(self, sta: str, params: tuple = ()) -> bool:
        try:
            con = sqlite3.connect(self.path)
            cur = con.cursor()
            cur.execute(sta, params)
            con.commit()
            con.close()
            return True
        except sqlite3.OperationalError as e:
            error(f"[{self.plugin_id}] {e}")
        except Exception as e:
            error(f"[{self.plugin_id}] [{type(e)}] {e}")
        return False

    def query(self, sta: str, params: tuple = ()) -> list:
        try:
            con = sqlite3.connect(self.path)
            cur = con.cursor()
            cur.execute(sta, params)
            rows = cur.fetchall()
            con.commit()
            con.close()
            return rows
        except Exception as e:
            error(f"[{self.plugin_id}] [{type(e)}] {e}")
        return []

    def query_one(self, sta: str, params: tuple = ()):
        rows = self.query(sta, params)
        return rows[0] if rows else None


# == 跨消息持久状态 ==

_states = {}
_states_lock = threading.Lock()

def get_plugin_state(plugin_id: str) -> dict:
    """获取插件持久状态字典(跨消息保留，替代v1的模块级变量)"""
    with _states_lock:
        if plugin_id not in _states:
            _states[plugin_id] = {}
        return _states[plugin_id]


# == 后台线程(防重复启动) ==

_background_threads = {}
_background_lock = threading.Lock()

def start_background_once(name: str, target) -> None:
    """启动一次性后台线程，同名字线程已在运行时不重复启动"""
    with _background_lock:
        thread = _background_threads.get(name)
        if thread and thread.is_alive():
            return
        thread = threading.Thread(target=target, name=name, daemon=True)
        _background_threads[name] = thread
        thread.start()


def dumps(data) -> str:
    return json.dumps(data, ensure_ascii=False)

def loads(text: str):
    if not text: return None
    try:
        return json.loads(text)
    except Exception:
        return None
