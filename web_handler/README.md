# 小生物v2 网页管理面板（web_handler）

接入小生物v2项目**数据库**（`data/db/*.db`）与**文件**（整个项目文件夹）的独立 Node.js 网页管理软件。
零 npm 依赖（仅用 Node 22+ 内置模块：`node:http` / `node:sqlite` / 原生 `WebSocket` / `node:crypto`）。

## 快速开始

1. 确认已安装 **Node.js 22.5+**（推荐 22.13+，自带 SQLite 模块）。
2. 双击 `start.bat`，或在本目录执行 `node server.js`。
3. 首次启动会自动生成 `web_handler/config.yaml`，控制台会打印**初始管理员密码**（账号 `admin`）。
4. 浏览器打开 `http://127.0.0.1:8570`。

> 面板默认仅监听本机 `127.0.0.1`。如需公网访问，见下文"公网部署"。
> 启动时若提示端口占用，修改 `config.yaml` 的 `port` 字段后重启。

## 登录

登录页需要同时输入三样：

| 输入项 | 说明 |
|---|---|
| 管理员账号 | 在 `web_handler/config.yaml` 的 `admins` 中手动配置（支持多个管理员，改密即编辑该文件，不提供网页注册） |
| 管理员密码 | 同上 |
| 机器人账号 | 机器人自己的 QQ 号 |

机器人账号采用**混合验证**：
- 静态比对：与 `config.yaml` 的 `botQq` 一致才能通过；
- 实时核对：若 OneBot 在线（面板按 根目录 `config.yaml` → `samples/onebot_config.json` → `ws://127.0.0.1:3001` 的顺序解析连接地址，调用 `get_login_info`），还会核对 OneBot 实际在线账号与 `botQq` 是否一致（双重保险）；
- OneBot 离线时仅做静态比对，仍可登录管理。

登录成功后浏览器留下 **30 天有效**（`sessionDays` 可调）的 HttpOnly Cookie，下次打开自动登录。
`botQq: 0` 表示未配置，此时禁止登录。

## 页面

- **登录页** `/login.html`：唯一入口；带有效 Cookie 访问会自动跳主页。
- **主页** `/index.html`：登录后进入；"项目架构"与"数据库管理"的唯一入口。
- **项目架构** `/files.html`：从根目录浏览整个小生物v2文件夹；代码/配置文件（.py/.yaml/.json/.txt 等）在线编辑保存（Ctrl+S）；日志文件（.log）**只读实时跟踪查看**（每 2 秒自动刷新增量内容，支持暂停/自动滚动、**关键词过滤**（只显示含关键词的行、高亮命中、↑↓ 跳转匹配、忽略大小写可切换），不受 2MB 编辑上限限制）；图片/音频/视频内联预览；上传/新建文件夹/新建文件/重命名/删除；点击 `.db` 文件直接进入数据库管理页并定位该库。
- **数据库管理** `/db.html`：左侧切换 11 个数据库与各库表格；表格分页查看（含 rowid）；**排序**：点击列头循环"升序 → 降序 → 取消"，或通过页首"排序"下拉按指定列/指定索引（含主键索引预设，多列索引按其键列顺序）排序，排序作用于全表且翻页稳定；**关键词搜索**：页首搜索框对全列（含 rowid）做子串过滤（LIKE 大小写不敏感、`% _ \` 转义为字面匹配），命中单元格高亮，可与排序组合，分页按过滤后行数计算；单行**编辑/删除/新增**；页首常驻显示当前数据库位置（如 `data/db/Score.db`）与当前表名。
- **数据统计** `/stats.html`（主页亦有精简区块）：分类分区展示机器人实时采集的统计——「消息与接口」（次数 + 条/day 频率）、「指令」（触发次数/频率 + 不计插件指令名排行 + 按插件分类排行）、「场景」（已添加/已启用插件 × 总/群聊/私聊）；点击卡片打开详情弹窗，按 **年/月/日/小时** 粒度查看折线图或文本表格（服务端补零聚合）；数据存 `data/db/stats.db`（`GET /api/stats` 汇总、`GET /api/stats/detail?key=&unit=&kind=` 详情）；每 10 秒自动刷新，页面隐藏时暂停；机器人未运行或库不存在时显示"暂无数据"（不报错）。

以上 2/3/4/5 页均需登录，未登录或会话过期一律跳回登录页。

## config.yaml 字段

```yaml
port: 8570          # 面板监听端口
host: "127.0.0.1"   # 监听地址：127.0.0.1=仅本机（默认）；公网部署改为 0.0.0.0
admins:             # 管理员列表（用户名: 密码；密码可明文，公网建议 "sha256:<64位hex>" 哈希形式）
  admin: "密码"
botQq: 0            # 机器人 QQ 号（0 = 未配置，禁止登录）
onebotUri: ""       # OneBot WS 地址；留空走自动解析降级链
sessionSecret: ""   # 会话签名密钥；留空首启自动生成
sessionDays: 30     # 自动登录有效期（天）
httpsCert: ""       # HTTPS 证书文件路径（PEM）；与 httpsKey 都填写才启用 HTTPS
httpsKey: ""        # HTTPS 私钥文件路径（PEM）
cookieSecure: false # Cookie 加 Secure 标记；HTTPS 反代部署时设为 true（启用 httpsCert 时自动生效）
trustProxy: false   # 信任反代的 X-Forwarded-For（仅在有可信反代时开启，否则限速会被伪造头绕过）
```

本文件已被项目根 `.gitignore` 的 `config.yaml` 模式自动忽略，不会被 git 提交。

## 公网部署（重要）

面板默认只监听 `127.0.0.1`。要开放公网访问：

1. `config.yaml` 中设 `host: 0.0.0.0`，并**务必启用 HTTPS**（二选一）：
   - **内置 HTTPS**：填写 `httpsCert` / `httpsKey`（PEM 证书路径，如 certbot 签发的证书）；
   - **HTTPS 反代**：置于 nginx/caddy 之后（反代做 TLS 终结，面板仍走 http://127.0.0.1），并在 `config.yaml` 设 `cookieSecure: true`；此时若要按真实 IP 限速需同时设 `trustProxy: true`（**切勿**在直连公网时开启 trustProxy）。
2. 若用反代，还需把以下请求头转发给面板（信任链正确性依赖反代覆盖客户端伪造的头）：`Host`（必需）。
3. 登录密码建议在 `config.yaml` 中写成哈希形式：`密码: "sha256:<64位hex>"`（可用 `node -e "console.log(require('crypto').createHash('sha256').update('你的密码').digest('hex'))"` 生成）。
4. 修改配置后重启面板，启动日志会打印绑定地址与安全警告，请确认。

## 已内置的安全防护

- **会话**：HMAC-SHA256 签名 Cookie（HttpOnly + SameSite=Lax + 可选 Secure），30 天自动登录；篡改/过期即失效；密码比对走 timingSafeEqual（防时序侧信道）。
- **登录限速**：每(IP+账号) 10 分钟内失败 5 次锁定 15 分钟；每 IP 10 分钟内失败 20 次锁定 15 分钟；失败附加 600ms 延迟；失败登录记录到控制台日志。
- **CSRF**：SameSite=Lax 之外，所有写请求校验 Origin/Referer 与 Host 一致。
- **响应头**：CSP（脚本/连接仅同源）、X-Frame-Options DENY、nosniff、Referrer-Policy。
- **文件系统**：目录穿越/符号链接逃逸拦截；面板自身 `web_handler/` 整棵子树**只读**（防自毁、防向 public/ 注入恶意脚本）；`web_handler/config.yaml` 在文件页隐藏；rename 目标路径同样校验（防改名覆盖口令文件）。
- **信息泄露**：未登录时 `/api/onebot/status` 仅返回在线布尔值，不暴露机器人 QQ 号与连接地址。
- **服务器**：requestTimeout 30s / headersTimeout 10s；HTTP 错误响应不泄露堆栈。

## 其他注意事项

- 管理员密码明文存放于 `web_handler/config.yaml`（公网部署建议用 sha256: 哈希形式），仅本机可读，注意保护。
- 所有文件/数据库操作限制在项目根目录内；数据库与机器人主程序**共享** `data/db/*.db`：面板读写时若机器人正在写库（SQLITE_BUSY），会自动等待并重试，仍失败提示"数据库忙，请重试"。
- 两个管理员同时改同一文件/同一行时**后保存的覆盖先保存的**（不做锁）。
- 登录限速计数存于内存：重启面板即清零。
- 文本编辑上限 2MB，上传上限 64MB，单目录列出上限 10000 条，表格单元格超 100KB 显示截断（可点开看完整值）。
- 启动时的 Node "SQLite is experimental" 警告无害，`start.bat` 已用 `--no-warnings` 抑制。
