

import sqlite3, os
from OneBotConnecter.loger.log_info import error, warning
from src.project_locator.project_locator import get_project_location

def return_default_folder() -> str:
    path = get_project_location()
    path = os.path.join(path, "data\\db")
    return path

def call_database(path: str = os.path.join(return_default_folder(), "\\default.db"), sta:str = ""):
    try:
        con = sqlite3.connect(path)
        cur = con.cursor()
        cur.execute(sta)
        con.commit()
        con.close()
        return True
    except sqlite3.OperationalError as e:
        warning(e)
    except Exception as e:
        error(e)
    return False

def get_from_database(path: str = os.path.join(return_default_folder(), "\\default.db"), sta:str = ""):
    try:
        con = sqlite3.connect(path)
        cur = con.cursor()
        cur.execute(sta)
        rows = cur.fetchall()
        con.commit()
        con.close()
        return rows
    except Exception as e:
        error(e)
    return []

def get_all_data_from(path: str = os.path.join(return_default_folder(), "\\default.db"), table: str = ""):
    try:
        con = sqlite3.connect(path)
        cur = con.cursor()
        cur.execute(f"SELECT * FROM {table}")
        rows = cur.fetchall()
        con.commit()
        con.close()
        return rows
    except Exception as e:
        error(e)
    return []