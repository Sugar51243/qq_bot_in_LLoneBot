#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小生物v1数据迁移脚本(独立单文件项目，仅依赖python标准库，不依赖小生物v2项目)

用法:
    python migrate_old_data.py [--old OLD_DATA] [--dest DEST_ROOT] [--dry-run]

OLD_DATA: 小生物v1的data目录副本(默认: ./old_data)，内部结构与v1的data目录一致:
    old_data/
    ├── permissions.yaml                # 场景插件注册记录
    ├── allow_add.yaml                  # 拉群请求白名单
    └── plugin/
        ├── bangdream/                  # tsugu插件数据
        ├── jrlp/jrlp.json
        ├── MC/bind_server.db
        ├── pjsk/
        ├── score/
        ├── sleepCounter/user_data.db
        ├── image_upload/
        ├── gifcreater/
        ├── pig/
        ├── 远行商人/notify_record.json
        └── basic/
DEST_ROOT: 小生物v2项目根目录(默认: 本脚本所在目录)

数据对应关系(旧值→新值转换见各migrate_函数):
    v1数据                                   → v2数据库/位置
    permissions.yaml                        → data/db/permissions.db.permission_records
                                               (插件名按映射表转换，"功能注册器"由v2核心替代被丢弃)
    allow_add.yaml                          → data/db/permissions.db.allow_add
    plugin/basic/nicknameCall.yaml          → data/db/GroupEvents.db.nickname_switch
    plugin/basic/leavelGroupCall.yaml       → data/db/GroupEvents.db.leave_switch
    plugin/pig/config.yaml                  → data/db/Pig.db.config
    plugin/pig/record.yaml                  → data/db/Pig.db.record
    plugin/pig/permissions.yaml             → data/db/Pig.db.permissions
    plugin/pig/emoji_to_id.json             → data/db/Pig.db.emoji_ids
    plugin/bangdream/keyset.json            → data/db/Tsugu.db.key_set
    plugin/bangdream/userBinding.json       → data/db/Tsugu.db.user_binding
    plugin/bangdream/short_order.json       → data/db/Tsugu.db.short_order
    plugin/bangdream/card_list.json         → data/db/Tsugu.db.card_cache
    plugin/bangdream/config.yaml            → data/plugin/tsugu_plugin/config.yaml
                                               (键过滤: key_set_path/user_acc_path移除; 路径重映射: bangdream→tsugu_plugin)
    plugin/bangdream/{card,char,song}文件    → data/plugin/tsugu_plugin/{card,char,song}/
    plugin/jrlp/jrlp.json                   → data/db/Jrlp.db.pairing
    plugin/MC/bind_server.db                → data/db/McServerStatus.db.bind_data
                                               (place_id补下划线: group123→group_123)
    plugin/pjsk/*                           → data/plugin/pjsk/
    plugin/score/guess_scores.json          → data/db/Score.db.users + Score.db.cards(卡牌拆表)
    plugin/score/get_card_list.json         → data/db/Score.db.daily_cards
    plugin/score/get_scores_list.json       → data/db/Score.db.daily_scores
    plugin/sleepCounter/user_data.db        → data/db/SleepAssistant.db(users/record/sleep_data, date统一TEXT)
    plugin/image_upload/image_info.json     → data/db/ImageShare.db.image_info
                                               (旧checksum基于hash()进程随机不可用，按图片文件重算md5)
    plugin/image_upload/short_cut.json      → data/db/ImageShare.db.short_cut
    plugin/image_upload/image_database/*    → data/plugin/image_share/image_database/
    plugin/gifcreater/image_user_nickName.json → data/db/GifCreator.db.nick_names
    plugin/gifcreater/{Erenn,fuc}.gif/output → data/plugin/gif_creator/
    plugin/远行商人/notify_record.json       → data/db/TravelingMerchant.db.notify_record
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
import sys
import time

# == v1插件名 → v2插件ID 映射 ==
# None表示该插件在v2中不存在(功能注册器由v2核心内置指令替代)，丢弃
V1_PLUGIN_ALIASES = {
    "tsugu": "tsugu",
    "jrlp": "每日老婆",  # v2中jrlp为功能指令，插件ID改为"每日老婆"
    "MC服务器状态查询": "MC服务器状态查询",
    "pjsk": "pjsk",
    "伪造信息": "伪造信息",
    "图片分享": "图片分享",
    "小生物积分": "小生物积分",
    "猪人": "猪人",
    "睡眠助手": "睡眠助手",
    "表情包合成": "表情包合成",
    "远行商人": "远行商人",
    # 以下为v1的伪插件/被替代插件，迁移时丢弃
    "功能注册器": None,
    "register": None,
    "小生物": None,
}

# v1数据库字段顺序为旧值顺序，转换后按v2结构插入
DROPPED_PLUGINS = {k for k, v in V1_PLUGIN_ALIASES.items() if v is None}


# == 简易yaml解析器 ==
# 仅支持v1数据使用的yaml子集: 缩进映射/列表、单双引号标量(含\u转义)、
# true/false、数字、空字典{}。足够解析v1的全部yaml数据文件。

def _unescape(s):
    def simple(m):
        c = m.group(1)
        return {"n": "\n", "r": "\r", "t": "\t", "b": "\b", "f": "\f", "v": "\v", "0": "\0"}.get(c, c)
    s = re.sub(r"\\([nrtbfv0\"'\\])", simple, s)
    s = re.sub(r"\\[uU]([0-9a-fA-F]{4,8})", lambda m: chr(int(m.group(1), 16)), s)
    return s

def _scalar(text):
    text = text.strip()
    if not text: return None
    if text == "{}": return {}
    if text == "[]": return []
    if text.startswith("'"):
        return text[1:-1].replace("''", "'") if text.endswith("'") else text[1:]
    if text.startswith('"'):
        inner = text[1:-1] if text.endswith('"') else text[1:]
        return _unescape(inner)
    if text == "true": return True
    if text == "false": return False
    if text in ("null", "~"): return None
    try:
        f = float(text)
        return int(f) if f.is_integer() else f
    except ValueError:
        return text

def parse_yaml(text):
    """解析v1数据使用的yaml子集，返回python对象"""
    lines = []
    for raw in text.splitlines():
        line = raw.rstrip("\n")
        if not line.strip() or line.strip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        lines.append((indent, line.strip()))

    def parse_map(i, indent):
        result = {}
        while i < len(lines):
            ind, line = lines[i]
            if ind < indent:
                break
            if ind > indent:
                i += 1
                continue
            if line.startswith("-"):
                break
            key_part, _, value_part = line.partition(":")
            key = _scalar(key_part)
            if value_part.strip() == "":
                i += 1
                if i < len(lines):
                    nxt_indent, nxt_line = lines[i]
                    # yaml允许序列与键同缩进(如 allow_add.yaml 的 id: 列表)
                    if nxt_line.startswith("-") and nxt_indent >= indent:
                        value, i = parse_list(i, nxt_indent)
                    elif nxt_indent > indent:
                        value, i = parse_map(i, nxt_indent)
                    else:
                        value = None
                else:
                    value = None
            else:
                value = _scalar(value_part)
                i += 1
            result[key] = value
        return result, i

    def parse_list(i, indent):
        result = []
        while i < len(lines):
            ind, line = lines[i]
            if ind < indent or ind > indent:
                break
            if not line.startswith("-"):
                break
            item = line[1:].strip()
            if not item:
                i += 1
                if i < len(lines) and lines[i][0] > indent:
                    value, i = parse_map(i, lines[i][0])
                else:
                    value = None
                result.append(value)
                continue
            k, sep, v = item.partition(":")
            if not sep:
                #纯标量列表项
                result.append(_scalar(item))
                i += 1
                continue
            if v.strip() == "":
                #"- key:" 形式的映射项
                i += 1
                if i < len(lines) and lines[i][0] > indent:
                    value, i = parse_map(i, lines[i][0])
                else:
                    value = None
                result.append({_scalar(k): value})
            else:
                result.append({_scalar(k): _scalar(v)})
            i += 1
        return result, i

    result, _ = parse_map(0, 0)
    return result


# == 工具 ==

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return parse_yaml(f.read())

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def db_exec(db_path, sql, params=()):
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute(sql, params)
    con.commit()
    con.close()

def db_many(db_path, sql, rows):
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.executemany(sql, rows)
    con.commit()
    con.close()

def db_query(db_path, sql, params=()):
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute(sql, params)
    rows = cur.fetchall()
    con.close()
    return rows

class Report:
    def __init__(self, dry_run):
        self.dry_run = dry_run
        self.items = []
    def add(self, name, action, detail):
        self.items.append((name, action, detail))
    def print(self):
        print("")
        print("=" * 50)
        print(f"迁移报告({'试运行，未写入' if self.dry_run else '已执行'})")
        print("=" * 50)
        for name, action, detail in self.items:
            print(f"[{name}] {action}: {detail}")


# == 各数据迁移函数 ==

def migrate_permissions(old, dest, report):
    """permissions.yaml → permissions.db.permission_records(插件名映射, 功能注册器丢弃)"""
    path = os.path.join(old, "permissions.yaml")
    if not os.path.isfile(path):
        report.add("permissions", "跳过", "未找到permissions.yaml")
        return
    data = load_yaml(path)
    db_path = os.path.join(dest, "data", "db", "permissions.db")
    ensure_dir(os.path.dirname(db_path))
    db_exec(db_path, """CREATE TABLE IF NOT EXISTS permission_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scene_id TEXT NOT NULL,
        plugin_id TEXT NOT NULL,
        enabled INTEGER NOT NULL DEFAULT 0,
        created_at INTEGER NOT NULL,
        updated_at INTEGER NOT NULL,
        UNIQUE(scene_id, plugin_id)
    );""")
    now = int(time.time())
    rows, dropped, unknown = [], 0, []
    for scene_id, plugins in data.items():
        scene_id = str(scene_id)
        if not isinstance(plugins, list):
            continue
        for plugin in plugins:
            plugin = str(plugin)
            if plugin in DROPPED_PLUGINS:
                dropped += 1
                continue
            new_id = V1_PLUGIN_ALIASES.get(plugin)
            if new_id is None:
                unknown.append(plugin)
                continue
            rows.append((scene_id, new_id, 1, now, now))
    if not report.dry_run:
        db_many(db_path, "INSERT OR IGNORE INTO permission_records (scene_id, plugin_id, enabled, created_at, updated_at) VALUES (?, ?, ?, ?, ?);", rows)
    report.add("permissions", f"迁移{len(rows)}条注册记录", f"丢弃功能注册器等{dropped}条" + (f"，未知插件{set(unknown)}" if unknown else ""))


def migrate_allow_add(old, dest, report):
    """allow_add.yaml → permissions.db.allow_add"""
    path = os.path.join(old, "allow_add.yaml")
    if not os.path.isfile(path):
        report.add("allow_add", "跳过", "未找到allow_add.yaml")
        return
    data = load_yaml(path)
    db_path = os.path.join(dest, "data", "db", "permissions.db")
    ensure_dir(os.path.dirname(db_path))
    db_exec(db_path, "CREATE TABLE IF NOT EXISTS allow_add (user_id TEXT PRIMARY KEY);")
    rows = [(str(uid),) for uid in data.get("id", [])]
    if not report.dry_run:
        db_many(db_path, "INSERT OR IGNORE INTO allow_add (user_id) VALUES (?);", rows)
    report.add("allow_add", f"迁移{len(rows)}条白名单", "")


def migrate_group_events(old, dest, report):
    """basic/nicknameCall.yaml + leavelGroupCall.yaml → GroupEvents.db"""
    db_path = os.path.join(dest, "data", "db", "GroupEvents.db")
    ensure_dir(os.path.dirname(db_path))
    for file, table in [("basic/nicknameCall.yaml", "nickname_switch"), ("basic/leavelGroupCall.yaml", "leave_switch")]:
        path = os.path.join(old, "plugin", file)
        if not os.path.isfile(path):
            report.add("GroupEvents", "跳过", f"未找到{file}")
            continue
        data = load_yaml(path)
        db_exec(db_path, f"CREATE TABLE IF NOT EXISTS {table} (group_id TEXT PRIMARY KEY, enabled INTEGER NOT NULL DEFAULT 1);")
        rows = [(str(gid), 1 if enabled else 0) for gid, enabled in data.items()]
        if not report.dry_run:
            db_many(db_path, f"INSERT OR IGNORE INTO {table} (group_id, enabled) VALUES (?, ?);", rows)
        report.add("GroupEvents", f"{table}迁移{len(rows)}条", f"来源: {file}")


def migrate_pig(old, dest, report):
    """pig/*.yaml + emoji_to_id.json → Pig.db"""
    db_path = os.path.join(dest, "data", "db", "Pig.db")
    ensure_dir(os.path.dirname(db_path))
    pig_dir = os.path.join(old, "plugin", "pig")
    # config.yaml → config
    path = os.path.join(pig_dir, "config.yaml")
    if os.path.isfile(path):
        data = load_yaml(path)
        db_exec(db_path, "CREATE TABLE IF NOT EXISTS config (emoji TEXT PRIMARY KEY, enabled INTEGER NOT NULL DEFAULT 1);")
        rows = [(str(emoji), 1 if enabled else 0) for emoji, enabled in data.items()]
        if not report.dry_run:
            db_many(db_path, "INSERT OR IGNORE INTO config (emoji, enabled) VALUES (?, ?);", rows)
        report.add("Pig", f"config迁移{len(rows)}条", "来源: config.yaml")
    # record.yaml → record
    path = os.path.join(pig_dir, "record.yaml")
    if os.path.isfile(path):
        data = load_yaml(path)
        db_exec(db_path, "CREATE TABLE IF NOT EXISTS record (user_id TEXT NOT NULL, emoji TEXT NOT NULL, times INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(user_id, emoji));")
        rows = []
        for user_id, package in data.items():
            for emoji, times in (package or {}).items():
                rows.append((str(user_id), str(emoji), int(times)))
        if not report.dry_run:
            db_many(db_path, "INSERT OR IGNORE INTO record (user_id, emoji, times) VALUES (?, ?, ?);", rows)
        report.add("Pig", f"record迁移{len(rows)}条", "来源: record.yaml")
    # permissions.yaml → permissions
    path = os.path.join(pig_dir, "permissions.yaml")
    if os.path.isfile(path):
        data = load_yaml(path)
        db_exec(db_path, "CREATE TABLE IF NOT EXISTS permissions (user_id TEXT NOT NULL, emoji TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 1, PRIMARY KEY(user_id, emoji));")
        rows = []
        for user_id, package in data.items():
            for emoji, enabled in (package or {}).items():
                rows.append((str(user_id), str(emoji), 1 if enabled else 0))
        if not report.dry_run:
            db_many(db_path, "INSERT OR IGNORE INTO permissions (user_id, emoji, enabled) VALUES (?, ?, ?);", rows)
        report.add("Pig", f"permissions迁移{len(rows)}条", "来源: permissions.yaml")
    # emoji_to_id.json → emoji_ids
    path = os.path.join(pig_dir, "emoji_to_id.json")
    if os.path.isfile(path):
        data = load_json(path)
        db_exec(db_path, "CREATE TABLE IF NOT EXISTS emoji_ids (emoji TEXT PRIMARY KEY, emoji_id INTEGER NOT NULL);")
        rows = [(str(emoji), int(emoji_id)) for emoji, emoji_id in data.items()]
        if not report.dry_run:
            db_many(db_path, "INSERT OR IGNORE INTO emoji_ids (emoji, emoji_id) VALUES (?, ?);", rows)
        report.add("Pig", f"emoji_ids迁移{len(rows)}条", "来源: emoji_to_id.json")


def migrate_tsugu(old, dest, report):
    """bangdream/* → Tsugu.db + tsugu_plugin配置/文件"""
    db_path = os.path.join(dest, "data", "db", "Tsugu.db")
    ensure_dir(os.path.dirname(db_path))
    bang_dir = os.path.join(old, "plugin", "bangdream")
    # keyset.json → key_set
    path = os.path.join(bang_dir, "keyset.json")
    if os.path.isfile(path):
        data = load_json(path)
        db_exec(db_path, "CREATE TABLE IF NOT EXISTS key_set (keyword TEXT PRIMARY KEY, song_ids TEXT NOT NULL);")
        rows = [(str(keyword), json.dumps([str(i) for i in ids], ensure_ascii=False)) for keyword, ids in data.items() if isinstance(ids, list)]
        if not report.dry_run:
            db_many(db_path, "INSERT OR IGNORE INTO key_set (keyword, song_ids) VALUES (?, ?);", rows)
        report.add("Tsugu", f"key_set迁移{len(rows)}条", "来源: keyset.json")
    # userBinding.json → user_binding
    path = os.path.join(bang_dir, "userBinding.json")
    if os.path.isfile(path):
        data = load_json(path)
        db_exec(db_path, "CREATE TABLE IF NOT EXISTS user_binding (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, acc TEXT NOT NULL, server TEXT NOT NULL, UNIQUE(user_id, acc, server));")
        rows = []
        for user_id, bindings in data.items():
            for item in bindings or []:
                rows.append((str(user_id), str(item.get("acc", "")), str(item.get("server", ""))))
        if not report.dry_run:
            db_many(db_path, "INSERT OR IGNORE INTO user_binding (user_id, acc, server) VALUES (?, ?, ?);", rows)
        report.add("Tsugu", f"user_binding迁移{len(rows)}条", "来源: userBinding.json")
    # short_order.json → short_order
    path = os.path.join(bang_dir, "short_order.json")
    if os.path.isfile(path):
        data = load_json(path)
        db_exec(db_path, "CREATE TABLE IF NOT EXISTS short_order (user_id TEXT NOT NULL, order_key TEXT NOT NULL, target TEXT NOT NULL, PRIMARY KEY(user_id, order_key));")
        rows = [(str(uid), str(k), str(v)) for uid, orders in data.items() for k, v in (orders or {}).items()]
        if not report.dry_run:
            db_many(db_path, "INSERT OR IGNORE INTO short_order (user_id, order_key, target) VALUES (?, ?, ?);", rows)
        report.add("Tsugu", f"short_order迁移{len(rows)}条", "来源: short_order.json")
    # card_list.json → card_cache
    path = os.path.join(bang_dir, "card_list.json")
    if os.path.isfile(path):
        data = load_json(path)
        db_exec(db_path, "CREATE TABLE IF NOT EXISTS card_cache (card_id TEXT PRIMARY KEY, data TEXT NOT NULL);")
        rows = [(str(card_id), json.dumps(card_data, ensure_ascii=False)) for card_id, card_data in data.items() if isinstance(card_data, dict)]
        if not report.dry_run:
            db_many(db_path, "INSERT OR IGNORE INTO card_cache (card_id, data) VALUES (?, ?);", rows)
        report.add("Tsugu", f"card_cache迁移{len(rows)}条", "来源: card_list.json")
    # config.yaml → data/plugin/tsugu_plugin/config.yaml(键过滤+路径重映射)
    path = os.path.join(bang_dir, "config.yaml")
    if os.path.isfile(path):
        old_cfg = load_yaml(path)
        new_cfg = {}
        for key in ["music_temp_path", "card_temp_path", "tsugu_uri", "backup_tsugu_uri", "use_uri", "time_out", "useEasyBG", "compress"]:
            if key in old_cfg:
                new_cfg[key] = old_cfg[key]
        # 路径重映射: data/plugin/bangdream/... → data/plugin/tsugu_plugin/...
        for key in ["music_temp_path", "card_temp_path"]:
            if key in new_cfg:
                new_cfg[key] = str(new_cfg[key]).replace("data/plugin/bangdream/", "data/plugin/tsugu_plugin/")
        target = os.path.join(dest, "data", "plugin", "tsugu_plugin", "config.yaml")
        ensure_dir(os.path.dirname(target))
        if not report.dry_run:
            # 合并: 保留目标已有v2专属键，迁移键以v1为准
            merged = dict(new_cfg)
            if os.path.isfile(target):
                try:
                    existing = load_yaml(target)
                    for k, v in existing.items():
                        if k not in merged:
                            merged[k] = v
                except Exception:
                    pass
            with open(target, "w", encoding="utf-8", newline="\n") as f:
                for k, v in merged.items():
                    if isinstance(v, bool):
                        sv = "true" if v else "false"
                    elif isinstance(v, (int, float)):
                        sv = str(v)
                    else:
                        sv = json.dumps(str(v), ensure_ascii=False)
                    f.write(f"{k}: {sv}\n")
        report.add("Tsugu", f"config迁移{len(new_cfg)}个键", f"目标: data/plugin/tsugu_plugin/config.yaml")
    # 文件复制: card/char/song
    for sub in ["card", "char", "song"]:
        src_dir = os.path.join(bang_dir, sub)
        if not os.path.isdir(src_dir):
            continue
        dst_dir = os.path.join(dest, "data", "plugin", "tsugu_plugin", sub)
        n = copy_dir(src_dir, dst_dir, report.dry_run)
        report.add("Tsugu", f"复制{sub}目录{n}个文件", f"目标: data/plugin/tsugu_plugin/{sub}/")


def migrate_jrlp(old, dest, report):
    """jrlp/jrlp.json → Jrlp.db.pairing(双向配对行原样保留)"""
    path = os.path.join(old, "plugin", "jrlp", "jrlp.json")
    if not os.path.isfile(path):
        report.add("Jrlp", "跳过", "未找到jrlp.json")
        return
    data = load_json(path)
    db_path = os.path.join(dest, "data", "db", "Jrlp.db")
    ensure_dir(os.path.dirname(db_path))
    db_exec(db_path, "CREATE TABLE IF NOT EXISTS pairing (date TEXT NOT NULL, group_id TEXT NOT NULL, user_id TEXT NOT NULL, partner_id TEXT NOT NULL, PRIMARY KEY(date, group_id, user_id));")
    rows = []
    for day, groups in data.items():
        for gid, pairs in (groups or {}).items():
            for uid, partner in (pairs or {}).items():
                rows.append((str(day), str(gid), str(uid), str(partner)))
    if not report.dry_run:
        db_many(db_path, "INSERT OR IGNORE INTO pairing (date, group_id, user_id, partner_id) VALUES (?, ?, ?, ?);", rows)
    report.add("Jrlp", f"pairing迁移{len(rows)}条", "来源: jrlp.json")


def migrate_mc(old, dest, report):
    """MC/bind_server.db → McServerStatus.db.bind_data(place_id补下划线)"""
    path = os.path.join(old, "plugin", "MC", "bind_server.db")
    if not os.path.isfile(path):
        report.add("McServerStatus", "跳过", "未找到bind_server.db")
        return
    con = sqlite3.connect(path)
    cur = con.cursor()
    cur.execute("SELECT place_id, server_location FROM bind_data;")
    legacy_rows = cur.fetchall()
    con.close()
    db_path = os.path.join(dest, "data", "db", "McServerStatus.db")
    ensure_dir(os.path.dirname(db_path))
    db_exec(db_path, "CREATE TABLE IF NOT EXISTS bind_data (bind_id INTEGER PRIMARY KEY AUTOINCREMENT, place_id TEXT NOT NULL, server_location TEXT NOT NULL, UNIQUE(place_id, server_location));")
    rows = []
    for place_id, server_location in legacy_rows:
        place_id = str(place_id)
        # v1中place_id去掉了下划线: group123456 → group_123456
        m = re.match(r"^(group|private)(\d+)$", place_id)
        if m:
            place_id = f"{m.group(1)}_{m.group(2)}"
        rows.append((place_id, str(server_location)))
    if not report.dry_run:
        db_many(db_path, "INSERT OR IGNORE INTO bind_data (place_id, server_location) VALUES (?, ?);", rows)
    report.add("McServerStatus", f"bind_data迁移{len(rows)}条", "来源: bind_server.db")


def migrate_pjsk(old, dest, report):
    """pjsk目录 → data/plugin/pjsk/(曲库与谱面缓存原样复制)"""
    src_dir = os.path.join(old, "plugin", "pjsk")
    if not os.path.isdir(src_dir):
        report.add("Pjsk", "跳过", "未找到pjsk目录")
        return
    dst_dir = os.path.join(dest, "data", "plugin", "pjsk")
    n = copy_dir(src_dir, dst_dir, report.dry_run)
    report.add("Pjsk", f"复制{n}个文件", f"目标: data/plugin/pjsk/")


def migrate_score(old, dest, report):
    """score/*.json → Score.db(users/cards拆表/daily_cards/daily_scores)"""
    db_path = os.path.join(dest, "data", "db", "Score.db")
    ensure_dir(os.path.dirname(db_path))
    score_dir = os.path.join(old, "plugin", "score")
    # guess_scores.json → users + cards
    path = os.path.join(score_dir, "guess_scores.json")
    if os.path.isfile(path):
        data = load_json(path)
        db_exec(db_path, """CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, scores REAL NOT NULL DEFAULT 0, chart REAL NOT NULL DEFAULT 0, card REAL NOT NULL DEFAULT 0, sp REAL NOT NULL DEFAULT 0, name TEXT NOT NULL DEFAULT '', use_card INTEGER NOT NULL DEFAULT 1, time REAL NOT NULL DEFAULT 0);""")
        db_exec(db_path, "CREATE TABLE IF NOT EXISTS cards (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, card_score REAL NOT NULL);")
        user_rows, card_rows = [], []
        for uid, item in data.items():
            if not isinstance(item, dict):
                continue
            user_rows.append((str(uid), float(item.get("scores", 0)), float(item.get("chart", 0)), float(item.get("card", 0)), float(item.get("sp", 0)), str(item.get("name", "")), 1 if item.get("use_card", True) else 0, float(item.get("time", 0.0))))
            for card_score in item.get("cards", []) or []:
                card_rows.append((str(uid), float(card_score)))
        if not report.dry_run:
            db_many(db_path, "INSERT OR IGNORE INTO users (user_id, scores, chart, card, sp, name, use_card, time) VALUES (?, ?, ?, ?, ?, ?, ?, ?);", user_rows)
            db_many(db_path, "INSERT INTO cards (user_id, card_score) VALUES (?, ?);", card_rows)
        report.add("Score", f"users迁移{len(user_rows)}条/cards迁移{len(card_rows)}条", "来源: guess_scores.json")
    # get_card_list.json → daily_cards
    path = os.path.join(score_dir, "get_card_list.json")
    if os.path.isfile(path):
        data = load_json(path)
        db_exec(db_path, "CREATE TABLE IF NOT EXISTS daily_cards (date TEXT NOT NULL, user_id TEXT NOT NULL, PRIMARY KEY(date, user_id));")
        rows = [(str(day), str(uid)) for day, uids in data.items() for uid in (uids or [])]
        if not report.dry_run:
            db_many(db_path, "INSERT OR IGNORE INTO daily_cards (date, user_id) VALUES (?, ?);", rows)
        report.add("Score", f"daily_cards迁移{len(rows)}条", "来源: get_card_list.json")
    # get_scores_list.json → daily_scores
    path = os.path.join(score_dir, "get_scores_list.json")
    if os.path.isfile(path):
        data = load_json(path)
        db_exec(db_path, "CREATE TABLE IF NOT EXISTS daily_scores (date TEXT NOT NULL, user_id TEXT NOT NULL, PRIMARY KEY(date, user_id));")
        rows = [(str(day), str(uid)) for day, uids in data.items() for uid in (uids or [])]
        if not report.dry_run:
            db_many(db_path, "INSERT OR IGNORE INTO daily_scores (date, user_id) VALUES (?, ?);", rows)
        report.add("Score", f"daily_scores迁移{len(rows)}条", "来源: get_scores_list.json")


def migrate_sleep(old, dest, report):
    """sleepCounter/user_data.db → SleepAssistant.db(date统一为TEXT)"""
    path = os.path.join(old, "plugin", "sleepCounter", "user_data.db")
    if not os.path.isfile(path):
        report.add("SleepAssistant", "跳过", "未找到user_data.db")
        return
    con = sqlite3.connect(path)
    cur = con.cursor()
    cur.execute("SELECT user_id, time_zone, plugin_on, good_nighted FROM users;")
    users = cur.fetchall()
    cur.execute("SELECT time, user_id FROM record;")
    records = cur.fetchall()
    cur.execute("SELECT date, user_id, sleep_time, wake_up_time, sleep_duration FROM sleep_data;")
    sleeps = cur.fetchall()
    con.close()
    db_path = os.path.join(dest, "data", "db", "SleepAssistant.db")
    ensure_dir(os.path.dirname(db_path))
    db_exec(db_path, "CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, time_zone INTEGER NOT NULL DEFAULT 8, plugin_on INTEGER NOT NULL DEFAULT 0, good_nighted INTEGER NOT NULL DEFAULT 0);")
    db_exec(db_path, "CREATE TABLE IF NOT EXISTS record (message_id INTEGER PRIMARY KEY AUTOINCREMENT, time REAL NOT NULL, user_id INTEGER NOT NULL);")
    db_exec(db_path, "CREATE TABLE IF NOT EXISTS sleep_data (sleep_data_id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, user_id INTEGER, sleep_time REAL, wake_up_time REAL, sleep_duration REAL);")
    if not report.dry_run:
        db_many(db_path, "INSERT OR IGNORE INTO users (user_id, time_zone, plugin_on, good_nighted) VALUES (?, ?, ?, ?);", users)
        db_many(db_path, "INSERT OR IGNORE INTO record (time, user_id) VALUES (?, ?);", records)
        # v1中date可能为整数(如20260904)，v2统一TEXT
        sleep_rows = [(None if d is None else str(d), uid, st, wu, sd) for d, uid, st, wu, sd in sleeps]
        db_many(db_path, "INSERT OR IGNORE INTO sleep_data (date, user_id, sleep_time, wake_up_time, sleep_duration) VALUES (?, ?, ?, ?, ?);", sleep_rows)
    report.add("SleepAssistant", f"users{len(users)}/record{len(records)}/sleep_data{len(sleeps)}条", "来源: user_data.db")


def migrate_image_share(old, dest, report):
    """image_upload/* → ImageShare.db + 图片文件复制(checksum重算md5)"""
    db_path = os.path.join(dest, "data", "db", "ImageShare.db")
    ensure_dir(os.path.dirname(db_path))
    up_dir = os.path.join(old, "plugin", "image_upload")
    old_img_dir = os.path.join(up_dir, "image_database")
    new_img_dir = os.path.join(dest, "data", "plugin", "image_share", "image_database")
    # image_info.json → image_info
    path = os.path.join(up_dir, "image_info.json")
    if os.path.isfile(path):
        data = load_json(path)
        db_exec(db_path, "CREATE TABLE IF NOT EXISTS image_info (id TEXT PRIMARY KEY, names TEXT NOT NULL, uploader TEXT NOT NULL, checksum TEXT NOT NULL);")
        rows = []
        for image_id, info in data.items():
            if not isinstance(info, dict):
                continue
            names = info.get("name", []) or []
            # v1的checksum基于hash()(进程随机)不可复现，按图片文件内容重算md5
            checksum = None
            image_file = os.path.join(old_img_dir, f"{image_id}.png")
            if os.path.isfile(image_file):
                with open(image_file, "rb") as f:
                    checksum = hashlib.md5(f.read()).hexdigest()
            else:
                checksum = f"legacy_{info.get('checksum', '')}"
            rows.append((str(image_id), json.dumps([str(n) for n in names], ensure_ascii=False), str(info.get("uploader", "")), checksum))
        if not report.dry_run:
            db_many(db_path, "INSERT OR IGNORE INTO image_info (id, names, uploader, checksum) VALUES (?, ?, ?, ?);", rows)
        report.add("ImageShare", f"image_info迁移{len(rows)}条(checksum已按文件重算md5)", "来源: image_info.json")
    # short_cut.json → short_cut
    path = os.path.join(up_dir, "short_cut.json")
    if os.path.isfile(path):
        data = load_json(path)
        db_exec(db_path, "CREATE TABLE IF NOT EXISTS short_cut (name TEXT NOT NULL, image_id TEXT NOT NULL, PRIMARY KEY(name, image_id));")
        rows = [(str(name), str(i)) for name, ids in data.items() for i in (ids or [])]
        if not report.dry_run:
            db_many(db_path, "INSERT OR IGNORE INTO short_cut (name, image_id) VALUES (?, ?);", rows)
        report.add("ImageShare", f"short_cut迁移{len(rows)}条", "来源: short_cut.json")
    # 图片文件复制
    if os.path.isdir(old_img_dir):
        n = copy_dir(old_img_dir, new_img_dir, report.dry_run)
        report.add("ImageShare", f"复制{n}张图片", f"目标: data/plugin/image_share/image_database/")


def migrate_gif_creator(old, dest, report):
    """gifcreater/* → GifCreator.db + 模板/输出文件复制"""
    db_path = os.path.join(dest, "data", "db", "GifCreator.db")
    ensure_dir(os.path.dirname(db_path))
    gif_dir = os.path.join(old, "plugin", "gifcreater")
    # image_user_nickName.json → nick_names
    path = os.path.join(gif_dir, "image_user_nickName.json")
    if os.path.isfile(path):
        data = load_json(path)
        db_exec(db_path, "CREATE TABLE IF NOT EXISTS nick_names (nick TEXT PRIMARY KEY, user_id TEXT NOT NULL);")
        rows = [(str(nick), str(qq)) for nick, qq in data.items()]
        if not report.dry_run:
            db_many(db_path, "INSERT OR IGNORE INTO nick_names (nick, user_id) VALUES (?, ?);", rows)
        report.add("GifCreator", f"nick_names迁移{len(rows)}条", "来源: image_user_nickName.json")
    # 模板与输出文件复制
    for sub in ["Erenn.gif", "fuc.gif"]:
        src = os.path.join(gif_dir, sub)
        if os.path.isfile(src):
            dst = os.path.join(dest, "data", "plugin", "gif_creator", sub)
            if not report.dry_run:
                ensure_dir(os.path.dirname(dst))
                shutil.copy2(src, dst)
            report.add("GifCreator", f"复制模板{sub}", f"目标: data/plugin/gif_creator/{sub}")
    src_dir = os.path.join(gif_dir, "output")
    if os.path.isdir(src_dir):
        dst_dir = os.path.join(dest, "data", "plugin", "gif_creator", "output")
        n = copy_dir(src_dir, dst_dir, report.dry_run)
        report.add("GifCreator", f"复制output目录{n}个文件", f"目标: data/plugin/gif_creator/output/")


def migrate_merchant(old, dest, report):
    """远行商人/notify_record.json → TravelingMerchant.db.notify_record"""
    path = os.path.join(old, "plugin", "远行商人", "notify_record.json")
    if not os.path.isfile(path):
        report.add("TravelingMerchant", "跳过", "未找到notify_record.json")
        return
    data = load_json(path)
    db_path = os.path.join(dest, "data", "db", "TravelingMerchant.db")
    ensure_dir(os.path.dirname(db_path))
    db_exec(db_path, "CREATE TABLE IF NOT EXISTS notify_record (scene_id TEXT PRIMARY KEY, round INTEGER NOT NULL);")
    rows = [(str(scene_id), int(round_no)) for scene_id, round_no in data.items()]
    if not report.dry_run:
        db_many(db_path, "INSERT OR IGNORE INTO notify_record (scene_id, round) VALUES (?, ?);", rows)
    report.add("TravelingMerchant", f"notify_record迁移{len(rows)}条", "来源: notify_record.json")


def copy_dir(src_dir, dst_dir, dry_run=False):
    """递归复制目录，返回复制文件数"""
    n = 0
    for root, dirs, files in os.walk(src_dir):
        for file in files:
            src = os.path.join(root, file)
            rel = os.path.relpath(src, src_dir)
            dst = os.path.join(dst_dir, rel)
            if not dry_run:
                ensure_dir(os.path.dirname(dst))
                shutil.copy2(src, dst)
            n += 1
    return n


def main():
    parser = argparse.ArgumentParser(description="小生物v1数据迁移脚本(独立于v2项目)")
    parser.add_argument("--old", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "old_data"), help="v1的data目录副本路径(默认: ./old_data)")
    parser.add_argument("--dest", default=os.path.dirname(os.path.abspath(__file__)), help="小生物v2项目根目录(默认: 本脚本所在目录)")
    parser.add_argument("--dry-run", action="store_true", help="仅检查与报告，不写入任何数据")
    args = parser.parse_args()

    old = args.old
    dest = args.dest
    if not os.path.isdir(old):
        print(f"错误: 未找到v1数据目录 {old}")
        print("请将小生物v1的data目录复制为 ./old_data 后重试，或使用 --old 指定路径")
        sys.exit(1)

    print(f"v1数据目录: {old}")
    print(f"v2项目目录: {dest}")
    if args.dry_run:
        print("模式: 试运行(不写入)")

    report = Report(dry_run=args.dry_run)
    migrate_permissions(old, dest, report)
    migrate_allow_add(old, dest, report)
    migrate_group_events(old, dest, report)
    migrate_pig(old, dest, report)
    migrate_tsugu(old, dest, report)
    migrate_jrlp(old, dest, report)
    migrate_mc(old, dest, report)
    migrate_pjsk(old, dest, report)
    migrate_score(old, dest, report)
    migrate_sleep(old, dest, report)
    migrate_image_share(old, dest, report)
    migrate_gif_creator(old, dest, report)
    migrate_merchant(old, dest, report)
    report.print()
    print("迁移完成。")


if __name__ == "__main__":
    main()
