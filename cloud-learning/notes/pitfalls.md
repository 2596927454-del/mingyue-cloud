# 踩坑记录

> 格式：现象 → 原因 → 解决 → 学到的。踩坑后立刻记，趁热写。

---

## 2026-05-29 Docker Compose 挂载文件报 "not a directory"

**现象**：`docker-compose up -d` 启动 Nginx 容器时报错：
```
not a directory: Are you trying to mount a directory onto a file (or vice-versa)?
Check if the specified host path exists and is the expected type
```

**原因**：`docker-compose.yml` 里写了 `- ./index.html:/usr/share/nginx/html/index.html:ro`，但宿主机 `/root/project/index.html` 不存在。Docker 发现源路径不存在时，**不会报"文件不存在"，而是自动创建一个同名目录**占位。然后试图把目录挂载到容器内的文件上，类型不匹配（目录 vs 文件），就炸了。

**解决**：确保 `index.html` 和 `avatar.jpg` 都跟 `docker-compose.yml` 放在同一目录下，文件确实存在后再启动：
```bash
ls -la /root/project/index.html /root/project/avatar.jpg
docker-compose up -d --build
```

**学到的**：
- Docker 的卷挂载逻辑是：源路径不存在 → 创建一个空目录。这个设计对挂载目录很贴心，但对挂载单个文件是致命陷阱——它会创建一个跟文件名同名的目录
- 排查方向：看到 "not a directory" 或 "not a file" 这种报错，第一反应是"源路径是不是不存在被 Docker 自动建成了相反类型"
- 上传文件到服务器时记得把所有被挂载的文件都传上去，不只是主配置文件

---

## 2026-05-30 GitHub Actions：SSH 私钥格式不完整导致认证失败

**现象**：workflow 日志显示 `ssh.ParsePrivateKey: ssh: no key found`，然后 `ssh: handshake failed: ssh: unable to authenticate`，runner 无法连上服务器。

**原因**：`cat` 私钥时只复制了中间那段 base64 编码文本，**漏掉了头尾两行**：
```
-----BEGIN OPENSSH PRIVATE KEY-----
（base64 内容）
-----END OPENSSH PRIVATE KEY-----
```
没有这两行，SSH 库不知道这是什么格式的密钥，直接报 "no key found"。

**解决**：`cat ~/.ssh/github-actions` 时**全选完整输出**，包括 `-----BEGIN OPENSSH PRIVATE KEY-----` 头行、base64 内容、`-----END OPENSSH PRIVATE KEY-----` 尾行。不能删除换行，不能只复制中间部分。以原始格式整坨贴入 GitHub Secrets 的 `SSH_PRIVATE_KEY`。

**学到的**：
- 私钥是一个完整的 PEM 格式文件，`-----BEGIN` / `-----END` 是格式标记，不是装饰——没有它们 SSH 解析器完全不认识
- `cat ~/.ssh/github-actions` 输出必须**全选复制**，一行都不能少
- 排查方向：看到 "no key found" 或 "ParsePrivateKey" 报错，第一反应检查私钥内容是否完整、头尾行是否缺失

---

## 2026-05-30 GitHub Actions Secrets 创建晚于 workflow 运行，读到空值

**现象**：workflow 日志中 `INPUT_HOST: `、`INPUT_USERNAME: `、`INPUT_KEY: ` 全部为空，报 `error: missing server host`。但去 Settings → Secrets 页面检查，三个 Secret 明明都有值。

**原因**：Secrets 的创建时间（05:13~05:15 UTC）**晚于** workflow 运行时间（04:56 UTC）。第一次 push 触发 workflow 时 Secrets 还不存在，runner 读到的是空值。Secrets 配好之后没有重新触发运行。

**解决**：重新触发 workflow（Re-run jobs 或再 push 一次），runner 就能读到正确的 Secret 值了。

**学到的**：
- GitHub Actions 的 Secret 值在运行时注入，创建之前的运行读不到。先配 Secrets，再 push——这个顺序很重要
- 日志里 Secret 值显示为 `***` 不代表是空的，但显示为空就真的是空的
- `gh secret list` 只能验证 Secret 存在，验证不了值是否有效。最快的确诊方式是看 workflow 日志：`INPUT_HOST: ***` 说明有值，`INPUT_HOST: ` 后面空白说明没读到

---

## 2026-05-28 Flask + PyMySQL + DBUtils 连接池：INSERT 返回 201 但数据未落库

**现象**：留言板 POST `/api/messages` 返回 201 `{"ok": true}`，toast 提示"留言成功！"，但 GET 刷新后列表里没有新留言。查数据库发现数据根本没写进去。

**原因**：两个问题叠加。第一，pymysql 默认 `autocommit=False`，INSERT 后没有显式 `conn.commit()`，事务在连接归还池子时被回滚。第二，更隐蔽的是 `with get_db() as conn:` 这个写法在 DBUtils PooledConnection 上的行为不可靠——pymysql 的 `Connection.__enter__()` 返回的是 **Cursor 而不是 Connection**，导致 `conn` 变量实际指向了 Cursor 对象，即使加了 `conn.commit()` 调的也可能是错误对象的 commit，事务仍然没提交到真正的数据库连接上。

**解决**：不用 `with get_db() as conn`，改为显式操作连接对象：

```python
conn = get_db()
try:
    with conn.cursor() as cur:
        cur.execute("INSERT INTO ...", (...))
    conn.commit()          # 确保调的是 Connection 的 commit
finally:
    close_db()             # 连接归还池子
```

**学到的**：
- pymysql 的 `Connection.__enter__()` 返回 Cursor，不是 Connection 本身——这个设计很容易踩坑，用 `with conn as xxx` 时 xxx 拿到的是 cursor
- DBUtils PooledDB 套了一层又一层，`with` 上下文管理器的行为更不可预测。涉及事务（INSERT/UPDATE/DELETE）时，别用 `with` 包裹连接，老老实实显式 `conn = get_db()` + `try/finally close_db()`
- 凡是返回 200/201 但数据没落库，第一反应就应该是**事务没提交**。立刻检查 commit 调用是否到位、commit 的对象是否正确
- SELECT 不需要 commit 所以 `with get_db()` 的写法在 GET 请求里能正常工作，这会让问题更隐蔽——GET 正常 + POST "成功"但无效，很容易被误判为前端渲染 bug

---

## 2026-05-28 Docker 容器内 Flask 启动报错 Working outside of application context

**现象**：`docker run guestbook-flask` 后容器立刻退出，`docker logs` 显示：
```
RuntimeError: Working outside of application context.
```
发生在 `init_db()` → `get_db()` → `g.db` 这一行

**原因**：Phase 3 引入连接池时，`get_db()` 用到了 Flask 的 `g` 对象（`hasattr(g, "db")`）。但 `g` 只在请求上下文中有效。`init_db()` 在 `app.run()` 之前调用，此时还没有第一个请求进来，没有应用上下文，`g` 未绑定，直接报错

**解决**：`init_db()` 是启动时的初始化操作，不需要走请求级的 `g`。改成直接从连接池取连接：

```python
def init_db():
    conn = pool.connection()       # 直接从池子拿
    try:
        with conn.cursor() as cur:
            cur.execute("CREATE TABLE IF NOT EXISTS messages (...)")
    finally:
        conn.close()               # 用完归还
```

**学到的**：
- Flask 的 `g` 对象有严格的作用域——只在请求上下文中存在。启动初始化、定时任务、命令行脚本里都不能用 `g`
- `get_db()` 配合 `g` 是给请求处理用的（一个请求复用一条连接），`init_db()` 这种一次性操作直接用 `pool.connection()` 就行
- 报 `Working outside of application context` 就是在说"你现在不在请求里，但我需要请求上下文才能工作"，查调用栈里哪个函数碰了 `g` / `session` / `request` / `current_app`

---

## 2026-05-28 docker run 拉取镜像超时——国内无法直连 Docker Hub

**现象**：`docker run hello-world` 报错 `failed to resolve reference "docker.io/library/hello-world:latest": dial tcp ... i/o timeout`

**原因**：Docker 默认从 Docker Hub 拉取镜像，国内服务器直连 Docker Hub 被墙

**第一次尝试**（不完整）：只用阿里云专属加速器 `https://xxx.mirror.aliyuncs.com`，配完 `docker run hello-world` 成功了，但 `docker pull python:3.12-slim` 还是报 not found——因为单个阿里云镜像源是个人专属的，缓存覆盖不全，小镜像能拉，大镜像和冷门 tag 没缓存

**最终解决**：参考阿里云开发者博客，配多个公共镜像源，单个挂了自动试下一个：
  mkdir -p /etc/docker
  vim /etc/docker/daemon.json
```json
{
  "registry-mirrors": [
    "https://docker.m.daocloud.io",
    "https://dockerproxy.com",
    "https://registry.docker-cn.com",
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com",
    "https://hub.uuuadc.top",
    "https://docker.anyhub.us.kg",
    "https://dockerhub.jobcher.com",
    "https://dockerhub.icu",
    "https://docker.ckyl.me",
    "https://docker.awsl9527.cn",
    "https://mirror.baidubce.com"
  ]
}
```

`systemctl restart docker` 后成功拉取 python:3.12-slim

**学到的**：
- 国内配 Docker 镜像加速器，单个源不够——挂掉的、没缓存的都会导致拉取失败。配一串镜像源，Docker 会按顺序尝试
- 阿里云专属加速器只适合拉热门镜像（hello-world、nginx 等），冷门 tag 或大镜像容易被"漏掉"
- 这些公共镜像源可能随时失效，遇到拉取失败优先怀疑源的问题，搜"2026 Docker 可用镜像加速器"找最新可用的

---

## 2026-05-27 数据迁移导入 MySQL 报错 Column count doesn't match value count

**现象**：执行 `mysql ... < dump.sql` 时报错 `ERROR 1136 (21S01): Column count doesn't match value count at row 1`

**原因**：`SELECT nickname, content, created_at` 只导出了 3 列，但 MySQL 的 messages 表定义了 4 列（id + nickname + content + created_at），SQL 要求的列数和表定义的列数不匹配

**解决**：导出时把 id 也带上：`SELECT id, nickname, content, created_at FROM messages;`

**学到的**：
- SQLite 的 `.mode insert` 生成的是隐式 INSERT（`INSERT INTO table VALUES(...)`），不指定列名，依赖值的顺序和数量必须和表结构完全一致。导出几列就导入几列——不能表有 4 列你却只给 3 个值
- 更稳妥的做法是导出时写完整列名（`.mode insert` 不会自动加列名），或者导入后手动处理
- 数据迁移前先 `DESCRIBE messages;` 看两边表结构是否一致，不一致就先改导出的 SQL 或者先 ALTER TABLE 对齐

---

## 2026-05-27 mysql 客户端连接云数据库一直超时——拿错 IP 了

**现象**：在 ECS 上执行 `mysql -h 云服务器公网IP -u 用户名 -p` 一直连不上，超时报错

**原因**：搞混了两个内网地址——需要填的是 **MySQL 实例的内网地址**，不是 ECS 云服务器的 IP。云数据库和 ECS 是两个独立的云产品，各自有各自的地址。用 ECS 的 IP 去连数据库，等于去敲邻居家的门找自己家里人

**解决**：
1. 打开云数据库控制台 → 找到 MySQL 实例详情
2. 复制"内网地址"（形如 `mysql-abc123.mysql.rds.aliyuncs.com` 或 `10.x.x.x`）
3. `mysql -h 内网地址 -u 用户名 -p`

**学到的**：
- `mysql -h` 后面填的是**数据库实例**的地址，不是服务器的地址。你要连去哪里就填哪里的地址，这个"哪里"是数据库不是服务器
- 云厂商会给每个云产品分配独立的内网地址，ECS 有 ECS 的，MySQL 有 MySQL 的，各是各的
- 连接不需要经过公网——ECS 和 MySQL 在同一个 VPC 下，直接内网互通，和公网 IP 没关系

---

## 2026-05-26 curl 卡住无响应 / Nginx 返回 504 — WAL 锁文件残留

**现象**：启动 Flask 后 `curl http://127.0.0.1:5000/api/messages` 卡住不返回，Nginx 那层 `curl localhost/api/messages` 同样卡住，最终 Nginx 超时返回 504 Gateway Timeout

**原因**：之前用 `kill`（尤其是 `kill -9`）杀掉 Flask 进程时，SQLite 的 WAL 锁文件（`.db-shm`、`.db-wal`）没有被正常清理。新进程启动后，sqlite3 发现这些残留的锁文件，认为还有另一个进程持有数据库锁，于是陷入了"无限等锁释放"的状态——所有读写操作全部阻塞，请求进去就卡住

**解决**：
1. `ls -la messages.db*` 确认三个文件都在（`.db` / `.db-shm` / `.db-wal`）
2. `rm -f messages.db-shm messages.db-wal` 删除残留锁文件
3. 重启 Flask：`python app.py &`
4. `curl http://127.0.0.1:5000/api/messages` 验证正常返回

**学到的**：
- WAL 的 `.db-shm`（共享内存索引）和 `.db-wal`（预写日志）是运行时文件，进程正常退出时自动清理，**非正常退出（kill -9、崩溃、断电）会残留**
- 残留锁文件的症状是"端口在监听但请求卡住"，和"端口没进程"是两类问题。ss -tlnp 能看到 python 在 5000 端口，但进程实际上在等锁，没法响应请求
- 以后 kill Flask 进程时，顺手检查并删除这两个锁文件，养成肌肉记忆
- 能正常 kill 就别用 -9，优雅退出会自己清理 WAL 文件

---

## 2026-05-26 留言板部署：Nginx sites-enabled/default 冲突

**现象**：`nginx.conf` 里配了 `/api/` 反向代理、curl Flask 5000 端口正常返回，但网页留言仍然报错

**原因**：`nginx.conf` 第 60 行有 `include /etc/nginx/sites-enabled/*;`，里面的 `default` 站点也监听了 80 端口。当浏览器用公网 IP 访问时，Nginx 把请求交给了 `sites-enabled/default` 处理，而 default 里没有 `/api/` 的转发规则，导致 API 请求得不到正确响应。自带的 `default` 和你手写的 `server` 块形成了冲突——两个 server 都声称处理 80 端口，浏览器实际走的是 default。

**解决**：
1. 创建 `/etc/nginx/sites-available/mingyue`，写入完整 server 配置（静态文件 + `/api/` 反向代理）
2. `ln -s` 软链接到 `sites-enabled/`，`rm /etc/nginx/sites-enabled/default`
3. 清理 `nginx.conf` 里手写的 `server {}` 块
4. `nginx -t && nginx -s reload`

**学到的**：
- Nginx 标准做法：站点配置写在 `sites-available/`，启用时软链到 `sites-enabled/`，不要直接在 `nginx.conf` 里写 server 块
- `include /etc/nginx/sites-enabled/*;` 会把该目录下所有配置加载进来，`default` 不删就会一直存在
- 部署后排查要分层：先 `curl 127.0.0.1:5000` 确认服务本身正常，再 `curl localhost/api/messages` 确认 Nginx 转发正常，两层都通了浏览器还不行才是前端问题

---

## 2026-05-26 端口 5000 被占用（`Address already in use`）

**现象**：启动 Flask 报端口 5000 被占用，之前用 `python app.py &` 放后台的进程还活着

**原因**：`&` 只是把进程放到后台，不会因为 SSH 断开而自动结束。再次 SSH 登录后，之前的后台进程仍然占着 5000

**解决**：
- 查看谁占了 5000：`ss -tlnp | grep 5000` 或 `lsof -t -i:5000`
- 杀掉：`kill $(lsof -t -i:5000)`
- 如果有多个残留 PID 且 kill 不掉：`kill -9 PID1 PID2`

**学到的**：
- `lsof -t -i:5000`：`-i` 指定端口，`-t` 只输出 PID（terse 模式），配合 `$()` 直接喂给 `kill`
- `ss -tlnp`：查看所有正在监听的 TCP 端口及对应的进程
- Flask debug 模式会启动双进程（重载器 + 工作进程），kill 时要两个都杀
- WAL 模式残留的 `messages.db-shm` / `messages.db-wal` 文件可能影响下次启动，旧进程死掉后这些锁文件可以安全删除

---

## 2026-05-26 `server` directive is not allowed here — server 块放错位置

**现象**：`nginx -t` 报错 `"server" directive is not allowed here in /etc/nginx/nginx.conf:63`

**原因**：`server {}` 块写在了 `http {}` 大括号的外面。nginx.conf 的层级结构是：`http {}` → `server {}` → `location {}`。`http` 是最外层的容器，`server` 必须嵌套在它里面。你手写的 server 在第 63 行，已经落到了 `http {}` 的闭合大括号之后

**解决**：把 `server {}` 移到 `http {}` 大括号内部，或者按标准做法写到 `sites-available/` 下用软链启用

**学到的**：Nginx 的配置层级是严格的树形结构——`http` 套 `server`，`server` 套 `location`，不能乱放。看到 "directive is not allowed here" 这种错，就是在告诉你"这个东西不能放在当前的位置"

---

## 2026-05-26 配置 Let's Encrypt 免费 SSL 证书（certbot）

**操作**：为 Nginx 站点申请 Let's Encrypt 证书，启用 HTTPS

**过程**：
1. 安装：`apt install certbot python3-certbot-nginx -y`
2. 申请：`certbot --nginx -d 域名 -d www.域名`
3. certbot 自动修改 Nginx 配置，添加 443 监听和证书路径
4. 自动配置 HTTP → HTTPS 跳转
5. 自动添加续签定时任务

**结果**：配置顺利，`https://域名` 访问正常，地址栏显示小锁

**学到的**：
- Let's Encrypt 是免费 SSL 证书颁发机构，工具叫 certbot
- `python3-certbot-nginx` 是 certbot 的 Nginx 插件，能自动改 Nginx 配置
- 证书有效期 90 天，certbot 会自动续签，不用手动维护
- 配通后 HTTP 自动跳转 HTTPS，浏览器强制走加密通道

---

## 2026-05-25 SSH 连接服务器超时

**现象**：`ssh root@公网IP` 一直超时，本地网络正常

**原因**：安全组入方向没有放行 22 端口

**解决**：云控制台 → 安全组 → 入方向规则 → 添加 TCP 22，来源 0.0.0.0/0

**学到的**：安全组是云主机的"门禁系统"，默认拒绝所有入流量。只有主动放行的端口才能被外部访问。

---

## 2026-05-25 Nginx 403 Forbidden（目录下只有 index.php）

**现象**：浏览器访问 `http://公网IP` 返回 403 Forbidden，但之前能正常打开

**原因**：nginx 默认 index 指令是 `index index.html index.htm`，当目录下没有 index.html 只有 index.php 时，nginx 找不到匹配的 index 文件，又默认关闭了目录浏览（`autoindex off`），直接返回 403

**解决**：临时验证——直接访问 `http://公网IP/index.php` 带完整文件名即可。根本方案——在 nginx.conf 的 index 指令里加上 index.php：`index index.html index.htm index.php;`

**学到的**：403 Forbidden 不一定是文件权限问题，更多时候是 nginx 找不到 index 文件。排查方向：先确认目录下有没有 index 文件，再确认 index 指令是否包含该文件名。

---

## 2026-05-25 直接访问 .php 文件弹出下载

**现象**：浏览器访问 `http://公网IP/index.php`，没显示页面内容，反而弹出下载 index.php 的对话框

**原因**：nginx 找到了 index.php 文件（所以不再是 403），但它没有 PHP 处理能力，按默认 MIME 类型（`application/octet-stream`）返回文件。浏览器收到这个 MIME 类型后，判断自己无法渲染，于是弹下载框

**解决**：临时方案——在 nginx.conf 的 `types` 或 default_type 里加上 `text/plain`，nginx 就会当纯文本返回，浏览器直接展示源码。根本方案——配置 PHP-FPM

**学到的**：nginx 的 MIME 类型决定了浏览器的行为。同一个 index.php 文件，Content-Type 设为 `text/html` 浏览器就渲染，设为 `application/octet-stream` 浏览器就下载。这就是为什么配好 PHP-FPM 后浏览器正常显示——因为 PHP-FPM 处理后返回的 Content-Type 是 `text/html`

---

## 2026-07-04 ECS 重置后 SSH 报 WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED

**现象**：重置 ECS 后尝试 SSH 连接，连接被拒绝，报错：
```
WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!
```
提示有人可能在中间人攻击，Password authentication 被禁用。

**原因**：ECS 重置相当于换了一台新机器，SSH host key 完全是新的。但本地 `~/.ssh/known_hosts` 里还保留着旧 ECS 的 host key。SSH 发现同一 IP 对应不同的 host key，认为不安全，拒绝连接。

**解决**：清理旧记录：
```bash
ssh-keygen -R 60.205.219.2
```
然后再 SSH 就会提示添加新 host key，正常连接。

**学到的**：每次重置/重装服务器，第一时间执行 `ssh-keygen -R IP地址`，这是个固定动作。

---

## 2026-05-31 docker-compose 旧版本 KeyError: 'ContainerConfig'

**现象**：CI/CD workflow 报错 `KeyError: 'ContainerConfig'`，`docker-compose up -d --build` 失败。日志还出现了 `parallel.parallel_execute` 相关 traceback。

**原因**：服务器上的 `docker-compose` 是旧版 Python 包（`/usr/lib/python3/dist-packages/compose/`），CI/CD runner 也是旧版。旧容器停止后残留的容器数据格式与新 build 的镜像不兼容，`get_container_data_volumes` 读取时找不到预期字段就炸了。

**解决**：
```bash
cd /root/project
docker-compose down        # 停止并清理
docker-compose rm -f       # 删除残留容器
docker image prune -f      # 清理旧镜像
docker-compose up -d --build
```
关键：不要只 `up --build`，必须先 `down` + `rm -f` 彻底清干净。

**学到的**：旧版 docker-compose 的容器数据持久化有坑。遇到莫名其妙的 `KeyError`，第一反应是清旧容器重来，而不是怀疑代码写错了。

---

## 2026-05-31 容器未挂载 env_file 导致 OSS 环境变量为空

**现象**：`docker-compose up -d --build` 后 Flask 立刻崩溃，日志显示：
```
TypeError: can only concatenate str (not "NoneType") to str
```
发生在 `oss2/api.py` 的 `_normalize_endpoint`。说明 `OSS_ENDPOINT` 环境变量是空字符串。

**原因**：`docker-compose.yml` 里 flask 服务只写了 `build: .`，没有 `env_file` 字段。Dockerfile 里只设了 `FLASK_HOST=0.0.0.0`，其他环境变量（DB_HOST、OSS_ENDPOINT 等）全没进容器。

**解决**：在 `docker-compose.yml` 的 flask 服务下加一行：
```yaml
services:
  flask:
    build: .
    env_file:
      - .env
```

**学到的**：Dockerfile 的 `ENV` 和 compose 的 `env_file` 是两回事。`ENV` 写死在镜像里，`env_file` 运行时注入。敏感信息（数据库密码、AccessKey）必须走 `env_file`，不能写死在 Dockerfile。

---

## 2026-05-31 OSS URL 漏了 Bucket 名

**现象**：上传接口返回的 URL 是 `https://oss-cn-beijing.aliyuncs.com/upload/xxx.jpg`，浏览器打不开（实际上是 403 或 404，因为路径不完整）。

**原因**：代码拼 URL 时直接把 endpoint 和 oss_key 拼了：
```python
public_url = f"{endpoint}/{oss_key}"
# 结果：https://oss-cn-beijing.aliyuncs.com/upload/xxx.jpg
```
漏了 Bucket 名。OSS 的完整 URL 格式是 `https://<Bucket>.<Endpoint>/<Key>`，Bucket 名是域名的一部分。

**解决**：
```python
public_url = f"https://{bucket_name}.{host}/{oss_key}"
# 结果：https://my-project-beijing-ming.oss-cn-beijing.aliyuncs.com/upload/xxx.jpg
```

**学到的**：OSS URL 的三段式结构——Bucket 是域名前缀，不是路径。`Bucket.Endpoint/Key` 不是 `Endpoint/Bucket/Key`。

---

## 2026-05-31 上传 OSS 未设 Content-Type 导致浏览器弹下载

**现象**：Bucket 改为公共读后，浏览器访问图片 URL 不显示图片，而是弹出下载对话框。

**原因**：`put_object` 上传时没有传 `headers`，OSS 默认给 Content-Type 设为 `application/octet-stream`（通用二进制流）。浏览器收到这个类型不知道自己能否渲染，就弹出下载。

**解决**：上传时根据文件后缀显式设 Content-Type：
```python
MIME_TYPES = {"jpg": "image/jpeg", "png": "image/png", "gif": "image/gif", "webp": "image/webp"}
headers = {"Content-Type": MIME_TYPES.get(ext, "image/jpeg")}
bucket.put_object(key, data, headers=headers)
```

**学到的**：同一个图片文件，Content-Type 是 `image/jpeg` 浏览器就显示，是 `application/octet-stream` 就下载。文件内容完全一样——浏览器只看标签不看内容。

---

## 2026-05-31 HTTP 下 navigator.clipboard 不可用

**现象**：复制按钮点击后显示「已复制」，但粘贴时什么都没有。浏览器控制台无报错（用了 `.catch(function(){})` 静默吞掉）。

**原因**：`navigator.clipboard.writeText()` 是 Secure Context API，只能在 HTTPS 或 localhost 下使用。站点是 HTTP，API 直接被屏蔽，`catch` 里空函数让错误静默消失。

**解决**：用 `window.isSecureContext` 判断 + 失败时 fallback 到 `document.execCommand('copy')`：
```javascript
if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(text).catch(function () { fallbackCopy(text); });
} else {
    fallbackCopy(text);  // 用 textarea + select + execCommand
}
```

**学到的**：HTTP 站点上 clipboard API 静默失败是经典坑。任何时候用 `navigator.clipboard` 都要加 fallback。生产站点配 HTTPS 一劳永逸。

---

## 2026-05-31 登录遮罩阻塞了不需要认证的功能

**现象**：登录遮罩覆盖整个页面，未登录时图片列表和复制功能虽然渲染了但完全无法交互。

**原因**：`position: fixed; inset: 0` 的全屏遮罩挡住了后面所有元素。设计上把"需要登录的区域"和"不需要登录的区域"混在一起遮了。

**解决**：去掉了全屏遮罩，改为在上传区内部切换状态——未登录时上传区显示密码输入框（替代原来的拖拽区），登录后切换为拖拽上传区。删除按钮根据登录态显示/隐藏。图片列表和复制始终可交互。

**学到的**：遮罩的权限控制要精确——遮住需要保护的元素，不要挡住不需要保护的。更好的方式是在对应区域内部做状态切换（upload zone → login prompt），而不是叠一层全局蒙版。

---

## 2026-05-31 OSS 手动删除后前端残影

**现象**：在 OSS 控制台删了图片后，图床页面仍显示该图片卡片，但图片加载失败显示占位符。实际上数据库记录还在，只是 OSS 上的文件没了。

**原因**：OSS 和 MySQL 是两套独立的系统，控制台删 OSS 文件不会自动同步删 MySQL 记录。前端只管从数据库查列表渲染 URL，不知道 OSS 那边文件已经没了。

**解决**：加了 `DELETE /api/images/<id>` 接口，删除时同时清理 OSS 文件和数据库记录。前端每个图片卡片加了删除按钮。图片加载失败时显示「图片已失效」占位提示。

**学到的**：存算分离架构下，存储层和数据库层的生命周期要联动管理。删文件不删记录 = 残影，删记录不删文件 = OSS 垃圾数据累积。
