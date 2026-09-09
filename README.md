# 小生物v2

基于 OneBot 协议（WebSocket）的 QQ 机器人，内置功能管理/管理员指令核心，配合 13 个可注册插件提供邦邦、积分、睡眠、图片分享等群聊功能。由 v1 迁移并模块化重构而来。

- **机器人本体**：Python，连接 OneBot 实现端（如 LLOneBot，正向 WS）
- **网页管理面板**：[web_handler/](web_handler/README.md)，独立 Node.js 程序，管理项目数据库与文件
- **数据**：SQLite，每插件一库，位于 `data/db/`

## 快速开始

1. 安装依赖（Python 3）：

   ```bash
   pip install OneBotConnecter==1.0.0b0
   ```

2. 配置：将 [samples/onebot_config.json](samples/onebot_config.json) 复制为根目录 `config.yaml` 并修改：

   | 字段 | 说明 |
   |---|---|
   | `uri` | OneBot 实现端正向 WS 地址（默认 `ws://127.0.0.1:3001`） |
   | `owner` | 机器人管理员 QQ 号列表（可用内置管理员指令） |
   | `allowSlash` | 是否允许斜杠指令 |
   | `ban_user` / `ban_group` | 封禁用户 / 群 |

3. 启动 OneBot 实现端（如 LLOneBot），确认正向 WS 地址与 `uri` 一致。
4. 运行机器人：双击 `run.bat` 或 `python main.py`。

## 内置核心指令（无需注册）

请求处理（加群申请/好友申请自动审批与通知、白名单）为**常驻内置功能**，白名单存于 `data/db/permissions.db`。

| 指令 | 说明 |
|---|---|
| `帮助` / `help (插件ID)` | 返回对应插件指令详解；**裸插件 ID** 也直接显示其帮助 |
| `启用` / `开启 <插件ID>` | 为当前场景启用插件 |
| `停用` / `关闭 <插件ID>` | 为当前场景停用插件 |
| `功能列表` / `功能` | 列出全部插件及其简介 |
| `已启用功能` / `已启用` | 列出当前场景已启用插件 |
| `可启用功能` / `可启用` | 列出当前场景未启用插件 |
| `管理员帮助` / `admin` | 内置管理员指令详解（仅 owner） |
| `重启` | 重启机器人（仅 owner） |
| `退群` | 退出当前群（群主/管理；需再次发送或发 `确认`，`取消` 撤回） |
| `同意` | 处理加群/好友请求（仅 owner） |
| `添加白名单` | 将用户加入请求自动同意白名单（仅 owner） |

插件按**场景**（群或私聊）注册，注册后该场景内指令才生效。

## 插件列表

| 插件 ID | 文件夹 | 简介 |
|---|---|---|
| tsugu | tsugu_plugin | 茨菇：查询 BangDream 官方及 bestdori 社区谱面/歌曲/卡面/玩家/活动信息 |
| 小生物积分 | score | 积分系统（排名/查分/笨蛋机/加成卡/每日奖励/猜群友） |
| 每日老婆 | jrlp | 随机配对群友为"今日老婆"（仅群聊；换老婆/牛依赖积分系统） |
| MC服务器状态查询 | mc_server_status | 查询/绑定/删除 Minecraft 服务器状态 |
| pjsk | pjsk | PJSK（世界计划）游戏谱面与歌曲查询 |
| 睡眠助手 | sleep_assistant | 自动推测睡眠时间并分析，个性化早安（需先"开启功能"） |
| 图片分享 | image_share | 上传图片至图库，按快捷词分类（查图指令"看看<分类名>"） |
| 表情包合成 | gif_creator | 抽/撅/摸/镜像/变速 GIF 合成 |
| 猪人 | pig | 向群友的消息贴表情赞，可堆叠 |
| 远行商人 | traveling_merchant | 查询并自动推送远行商人在售物品 |
| 伪造信息 | forged_message | 生成指定用户的虚假聊天记录（仅管理员） |
| 群事件播报 | group_events | 入群欢迎/昵称更改播报/退群播报/播报开关 |
| 系统指令 | system_commands | 赞我 |
| 样本插件 | sample_plugin | 仅作开发参考，请勿启用 |

## 插件开发

每个插件是 `src/plugins/<英文文件夹>/` 下的**独立子项目**：

```
src/plugins/<folder>/
├── plugin.py     # 指令路由（on_all_case / on_msg，同步函数）
├── info.json     # {"plugin_id": "插件名", "info": "简介"}，plugin_id 即插件名称
├── help.txt      # 帮助文档（v2 格式：插件名 + =========== + 功能简解 + 指令行）
└── <模块>.py     # 功能模块（config/db/业务逻辑拆分）
```

约定：

- **注册生效**：插件无 always_on 机制，一律由用户 `启用` 后生效；常驻功能放核心内置（见上文）。
- **bot 对象**：回调签名 `on_all_case(bot, message)`，`bot` 是 message_interface 本体，OneBot API 直接调 `bot.send_group_msg(...)` 等（勿用 `bot.handler.*`）；机器人本体信息在 `bot.bot`（含 `owner`/`user_id`）。
- **后台监听**：需后台任务的插件在 plugin.py 模块级暴露 `plugin_listener(bot)`（入口先 `while not getattr(bot.bot, "user_id", None): time.sleep(1)` 等待初始化），由 main.py 在启动时统一扫描启动；勿在 on_msg 中懒启动线程。
- **子模块导入**：一律绝对导入 `from src.plugins.<folder>.<module> import ...`（plugin.py 经 spec 动态加载，相对导入会失败）。
- **跨插件调用**：从专用模块导入（如 `from src.plugins.score.scores import get_user_score`），不要导入别的插件的 plugin.py；启用检查用 `"小生物积分" in sreach_enabled_plugin(scene_id)`。
- **数据**：每插件一个 SQLite 库 `data/db/<Plugin>.db`（db 文件名用 ASCII，如 `Score.db`），用 `src/db_handler/plugin_db.py` 的 `PluginDB`/`get_plugin_state`/`start_background_once`（v2 每条消息重载插件模块，模块级变量会丢失）。
- **配置**：运行时配置放 `data/plugin/<插件ID>/`（如 tsugu 的 config.yaml），样本放 `samples/plugins/<文件夹>/`（严禁隐私数据），插件首次运行从样本生成。
- **事件格式（v2）**：入群 `group_increase[_sub_type]`（用 startswith 匹配）、`group_card`、`group_decrease[_sub_type]`；群请求用 `raw_data` 判断（post_type=request + request_type=group）更稳。
- **裸插件 ID** 由核心保留用于显示帮助，插件不得拿裸 ID 做功能指令。

## v1 数据迁移

从 v1（类茨菇 qq_bot_in_LLoneBot）迁移旧数据，使用根目录独立脚本 [migrate_old_data.py](migrate_old_data.py)（仅标准库，不依赖 v2 项目）：

```bash
python migrate_old_data.py --old <v1的data目录> [--dest <v2根目录>] [--dry-run]
```

插件/核心代码内不含迁移逻辑。关键转换：插件名映射、MC place_id 补下划线、image_share 按文件重算 md5、tsugu 配置键过滤与路径重映射、score cards 拆表等。

## 数据统计

机器人运行时会自动采集 7 项计数并写入 `data/db/stats.db`（可在面板"数据库管理"中查看/编辑），网页管理面板主页与"数据统计"页（`/stats.html`）实时展示：

| 指标 | 口径 |
|---|---|
| 信息接收次数 | 收到的 QQ 消息事件（群聊/私聊，post_type=message） |
| 信息发送次数 | 调用发送消息 API 的次数（send_private_msg / send_group_msg / 转发消息） |
| 信息接收发送总次数 | 前两者之和（面板计算） |
| 接口上行次数 | 从 OneBot 收到的全部事件（消息/通知/请求/元事件，不含心跳） |
| 接口下行次数 | 调用 OneBot API 的总次数（含查资料、踢人等所有 action） |
| 接口上下行总次数 | 前两者之和（面板计算） |
| 指令触发次数 | 被核心内置功能或插件成功处理的消息事件数 |

计数在 `src/core/stats.py` 中采集（`main.py` 入口钩子 + `handle_message.py` 指令钩子），仅统计机器人运行期间产生的流量；重启不清零（持久化于 SQLite）。

## 网页管理面板（web_handler）

独立 Node.js 程序（零 npm 依赖，Node 22+），提供项目文件浏览/在线编辑与 11 个数据库的表管理。登录需管理员账号+密码+机器人 QQ（`web_handler/config.yaml` 的 `botQq`，**当前为 0 未配置，填入机器人真实 QQ 后重启面板才能登录**）。

快速启动：双击 [web_handler/start.bat](web_handler/start.bat)，浏览器打开 `http://127.0.0.1:8570`（默认仅本机；公网部署需 HTTPS，详见 [web_handler/README.md](web_handler/README.md)）。

## 项目结构

```
小生物v2/
├── main.py               # 入口：连接 OneBot、消息分发、启动插件后台监听
├── config.yaml           # 机器人配置（从 samples/onebot_config.json 复制，已 gitignore）
├── run.bat               # 双击运行
├── pip.txt               # 依赖（OneBotConnecter==1.0.0b0）
├── migrate_old_data.py   # v1 → v2 数据迁移脚本
├── src/
│   ├── core/             # 核心内置：功能管理/管理员指令(core_function.py)、
│   │                     #   请求处理/白名单(request_center.py)、数据统计(stats.py)、help.txt、admin_help.txt
│   ├── plugins/          # 13 个插件 + 样本插件（各为独立子项目）
│   ├── db_handler/       # PluginDB 等数据库工具
│   ├── handle_message.py # 消息分发（启用检查 + 调用各插件）
│   └── ...               # config_reader / project_locator / console / tools 等
├── samples/              # 配置样本：onebot_config.json、plugins/<文件夹>/ 样本配置
├── data/                 # 运行时数据：db/（SQLite 库）、plugin/（插件运行时配置）
├── web_handler/          # Node.js 网页管理面板（见其 README.md）
└── old_data/             # v1 旧数据（迁移脚本输入，已 gitignore）
```
