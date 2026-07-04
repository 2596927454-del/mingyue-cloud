# 云计算概念理解

> 用自己的话写，不许抄文档。能用一句类比讲清楚，说明真懂了。

---

## Let's Encrypt / certbot

Let's Encrypt 是一个免费 SSL 证书颁发机构，工具叫 certbot。它为个人网站提供免费的 HTTPS 证书，有效期 90 天，自动续签。

`certbot --nginx -d 域名` 做的事：验证你确实拥有这个域名 → 颁发证书 → 自动改 Nginx 配置（加 443 监听、证书路径、HTTP→HTTPS 跳转）→ 添加定时任务自动续签。全程一条命令。

类比：Let's Encrypt 是免费的"网站身份证颁发机构"，certbot 是帮你填表、拿证、贴照片的跑腿机器人。

核心理解：certbot 验证的是"你控制这个域名"，不是"你控制这台服务器"。它通过让服务器临时响应一个特定 HTTP 请求来证明域名指向这里（HTTP-01 challenge）。

## DNS
互联网的电话簿。输入域名 → 查到 IP 地址 → 浏览器去连接。全称 Domain Name System，全球分布式部署，所以新增的解析记录要等 1~10 分钟才能在全球生效。

## 安全组
云服务器的"门禁系统"。默认所有入方向端口都关闭，只放行你指定的。出方向默认全开。工作在云平台层面，比操作系统防火墙更靠前。

## SSH
加密的远程命令行协议。连接过程：TCP 22 端口 → 服务器发公钥 → 协商对称密钥 → 认证 → 后续通信全加密。即使中间人抓包也解不开。

## Nginx
高性能 Web 服务器，负责接收浏览器请求并返回网页文件。也可以做反向代理、负载均衡。入门阶段先理解它最基本的作用：监听 80 端口，把 HTML 文件发给访问者。

---

## lsof
"进程户口本"——专门查"谁在用什么东西"。`lsof -i:5000` 就是"谁在用 5000 端口"，输出包含进程名、PID、用户等信息。加 `-t` 参数（terse，简洁模式）只输出 PID 数字，专门给脚本和 `kill $(...)` 用的。

## $() 命令替换
把括号里命令的输出"抓出来"直接拼到外层命令里。比如 `kill $(lsof -t -i:5000)`，shell 先执行括号里的 `lsof` 拿到 PID，再把 PID 替换进去变成 `kill 12345`，然后执行。省去了"手动看 PID → 复制 → 粘贴"的步骤。

它等价于反引号 `` `lsof -t -i:5000` ``，但 `$()` 更清晰且支持嵌套。

## ss -tlnp
查本机所有正在监听的 TCP 端口。比老命令 `netstat` 更快。
- `-t`：只看 TCP
- `-l`：只看正在监听（LISTEN）的
- `-n`：显示端口号而不是服务名（显示 80 而不是 http）
- `-p`：显示是谁在用这个端口（进程名 + PID）

## Nginx 站点管理模式（sites-available / sites-enabled）
Nginx 的标准配置组织方式，类似于"菜单"和"桌面快捷方式"：
- `sites-available/`：所有站点的配置文件都放在这，相当于"仓库"。存在不代表启用
- `sites-enabled/`：只放软链接（`ln -s`），指向 `sites-available/` 里的配置。谁被链过来了谁就生效

这样做的好处：上线一个站点 `ln -s`，下线直接 `rm` 软链接，不影响原始配置文件。`nginx.conf` 里通过 `include /etc/nginx/sites-enabled/*;` 自动加载所有已启用的站点。

## kill -9 vs kill
- `kill PID`（默认信号 SIGTERM，编号 15）：礼貌地"请"进程退出，进程有机会做清理工作（保存数据、关闭文件、释放资源）
- `kill -9 PID`（SIGKILL）：强制杀死，操作系统直接终止进程，不给任何反应时间。只在普通 kill 干不掉时才用

能不用 `-9` 就别用，先试普通的 `kill`。但如果进程有两个 PID 都杀不死，用 `kill -9 PID1 PID2` 一次性强制带走。

## Flask
Python 的轻量级 Web 框架，几行代码就能搭一个后端服务。`@app.route` 定义"什么路径触发什么函数"，`jsonify` 把 Python 字典转成 JSON 返回给前端，`request.get_json` 解析前端发来的 JSON 数据。Flask 只跑在服务器本机的 5000 端口，外部通过 Nginx 才能间接访问——这就是反向代理的价值。

## SQLite
文件型数据库，整个数据库就是一个 `.db` 文件，不需要装软件、配用户密码、起服务进程。适合学习阶段和低并发场景（留言板、个人博客），生产环境高并发用 MySQL/PostgreSQL。Python 内置 `sqlite3` 模块直接操作它，零依赖。

## REST API
前后端通信的"约定"。两个核心约定：一是用 HTTP 方法表示动作（GET = 读取，POST = 新增，DELETE = 删除），二是数据用 JSON 格式传递。留言板的两个接口就是最简单的 REST 风格：GET /api/messages 拿数据，POST /api/messages 存数据。

## 反向代理 (Reverse Proxy)
Nginx 作为"前台接待"，接收所有浏览器请求，根据 URL 路径决定转发给哪个后端。浏览器只知道 Nginx 在 80 端口，完全不知道后面还有个 Flask 在 5000 端口。类比：酒店前台——客人只和前台打交道，前台把不同需求转给不同部门处理。好处是安全性（后端不暴露）、端口统一（用户不用记端口号）、扩展性（加新后端只需加 Nginx 规则）。

## JavaScript fetch API
浏览器自带的方法，前端用它向后端发 HTTP 请求。`fetch('/api/messages')` 默认发 GET 请求拿数据，`fetch(url, {method: 'POST', body: JSON.stringify(data)})` 发 POST 请求提交数据。返回的 `res.json()` 方法把 JSON 文本转回 JS 对象，前端拿到数据后动态渲染 HTML——这就是"前后端分离"在代码层面的体现。

## 虚拟环境 (venv)
Python 项目的"隔离沙箱"。`python3 -m venv venv` 创建一个独立的 Python 环境，里面装的包不影响系统 Python 也不被其他项目干扰。Ubuntu 24.04 强制要求用虚拟环境（PEP 668），否则 pip install 会报 externally-managed-environment。每次使用前要 `source venv/bin/activate` 激活，命令行前面出现 `(venv)` 标记表示已激活。

## HTTP 状态码
服务器在响应开头告诉浏览器的三位数字，表示"这次请求怎么样了"。2xx 表示成功（200 OK = 一般成功，201 Created = 创建资源成功），4xx 表示客户端的问题（400 Bad Request = 你发的东西不对，404 Not Found = 你要的东西不存在），5xx 表示服务器的问题（500 = 后端代码崩了，502 Bad Gateway = Nginx 转发给 Flask 但 Flask 没响应）。

## JSON
"键值对"格式的纯文本数据，人和机器都能读。`{"nickname": "明月", "content": "你好"}` 就是一个 JSON 对象。前端用 `JSON.stringify()` 把 JS 对象转成 JSON 文本发给后端，后端收到后解析。后端返回 JSON 文本给前端，前端用 `res.json()` 解析后渲染。JSON 是前后端之间的"通用语言"。

## WAL (Write-Ahead Logging)
"预写日志"——SQLite 保证数据不丢的机制。写数据时不直接改主文件，而是先写到日志文件（`.db-wal`），确认写入成功后再同步到主文件。如果中途崩溃断电，下次打开数据库时自动检查日志，发现未完成的操作就重做或回滚。`.db-shm` 是 WAL 的共享索引文件（Shared Memory），和 `.db-wal` 配合使用。这就是"原子性"的实现手段——一个操作要么全完成要么全不做。

## 原子性 (Atomicity)
数据库四大保证之一（ACID 里的 A）。一条写入操作像"原子"一样不可再分——要么全部完成，要么什么都没发生。不会出现"写 SQL 插入了一半服务器断电，数据库里剩半条烂数据"。WAL 日志机制就是实现原子性的具体方式。

## 进程管理
Linux 运维的基本功。`python app.py &` 放后台运行，`ss -tlnp | grep 5000` 查端口被谁占了，`lsof -t -i:5000` 查端口对应的 PID，`kill PID` 结束进程。后台进程不会因为 SSH 断开而自动消失，再次登录后可能还占着端口，记得查和杀。

## sqlite3 模块
Python 自带的库，它的角色就像一个翻译官，只需写 Python代码，它帮你把代码翻译成对 .db 文件的读写操作。

## 并发安全
多个请求同时读写时不会互相踩数据。比如你和一个访客同时提交留言，两个 INSERT 不会打架导致数据损坏。SQLite 通过 WAL 模式实现了"读写不互斥"——读者不阻塞写者，写者不阻塞读者。

## 连接池 (Connection Pool)
一个预先建好的数据库连接"蓄水池"。Flask 启动时一次性建好几条到 MySQL 的长连接放在池子里。请求来了直接从池子拿一条现成的用，用完还回去（不断开）。下个请求来了再拿同一条或另一条。每条请求省掉了 TCP 三次握手 + MySQL 认证的时间（3~50ms），也不用反复建连接/断连接。

类比：共享单车。不用池子是每次出门现买一辆自行车，用完扔掉。用池子是路边停着一排共享单车，骑走一辆，到地方还回去，别人接着用。

PooledDB 的核心参数：
- `maxconnections`：池子最多放几条连接（防止打爆数据库）
- `mincached`：启动时预建几条（第一个请求不用等）
- `maxcached`：空闲时最多保留几条（省数据库资源）
- `blocking`：池子满了新请求是排队等还是直接报错

Flask 的 `g` 对象是配合连接池用的——同一个请求里多次调用 `get_db()` 拿到的都是同一条连接，挂在 `g.db` 上。请求结束 `close_db()` 归还池子，`g` 自动清空。

## JSON.stringify()
为什么需要它？
你在表单里填了"明月"和"你好"，JS 代码拿到了一个 JS 对象：

  { nickname: "明月", content: "你好" }

但这个对象不能直接放在 HTTP 请求里发出去。HTTP请求只能传文本（字符串），就像快递只能寄纸箱，不能寄一个"活的思想"。

  JSON.stringify() 把 JS 对象序列化成一段 JSON 格式的字符串：

  // 序列化前（JS 对象，内存里的数据结构）
  { nickname: "明月", content: "你好" }
  // 序列化后（JSON 字符串，可以放进 HTTP 请求体传输）
  '{"nickname":"明月","content":"你好"}'

等到 Flask 那边收到这个字符串，用 request.get_json() 做反向操作——把 JSON字符串反序列化回 Python 字典，继续处理。

类比：你寄一封信，JSON.stringify() 是把你的想法写成一页纸（编码），对方收到后读纸把信息还原成理解（解码）。没有"写纸"这一步，想法传不出去。

## request.get_json()
Flask 用 request.get_json() 把 JSON 文本还原成 Python字典。
这一来一回就是"序列化"和"反序列化"。

## renderMessages() 渲染留言卡片
什么是渲染？
"渲染"就是把数据变成用户眼睛能看到的 HTML 元素。后端只返回了一堆 JSON 数据：
  [
    {"nickname": "访客A", "content": "你好", "created_at": "2026-05-26
  15:30:00"},
    {"nickname": "明月", "content": "欢迎", "created_at": "2026-05-26
  14:20:00"}
  ]

  这些数字和字符串，用户不能直接看 JSON 原文。renderMessages()
  做的事就是把每条 JSON 数据"翻译"成一段 HTML 卡片，拼进页面：

  // renderMessages 的核心逻辑：
  messages.forEach(function (msg) {
var card = document.createElement('div');  // 创建一个 <div> 元素
card.className = 'gb-card animate-in';     // 给它加 CSS 样式类
card.innerHTML =                           // 往里填 HTML 内容
      '<div class="gb-meta">'
      + '<span class="gb-nickname">' + escapeHtml(msg.nickname) + '</span>'
  // 昵称
      + '<span class="gb-time">' + formatTime(msg.created_at) + '</span>'
  // 时间
      + '</div>'
      + '<p class="gb-content">' + escapeHtml(msg.content) + '</p>';
  // 内容 
      gbList.appendChild(card); //把卡片挂到页面 DOM 树上
      });

  过程就是：
  1. 遍历 JSON 数组里每一条留言
  2. 给每条留言创建一个 <div> 卡片元素
  3. 把昵称塞进 <span class="gb-nickname">，时间格式化后塞进 <span
  class="gb-time">，内容塞进 <p class="gb-content">
  4. 卡片拼好后 appendChild 挂到页面上，用户就看到了

  类比：renderMessages()就像是流水线上的包装工——后端送来裸数据（JSON），它给每条数据套上一个好看的 HTML盒子（卡片），摆上货架（页面）。

## JS 阻止默认提交
因为 HTML <form>表单有自己的"默认提交行为"——不阻止的话页面会刷新。
不阻止默认提交页面会直接跳转到 http://你的域名/api/messages（后端返回的纯 JSON 页面）。
## CI/CD（持续集成 / 持续部署）

代码从你本地到服务器的"自动化传送带"。你只管 `git push`，剩下的——拉代码、构建镜像、重启容器——全自动完成。

- **CI（持续集成）**：每次 push 自动检查代码能不能跑通（测试、构建）
- **CD（持续部署）**：检查通过后自动部署到服务器，用户直接用到最新版本

类比：以前是手工打包快递、骑车送到驿站，CI/CD 是菜鸟物流全自动分拣配送——你把包裹丢进传送带，剩下的机器搞定。

你的场景就是最简版 CI/CD：push 触发 → GitHub Actions runner SSH 到 ECS → `git pull` + `docker compose up -d --build`。没有测试环节，没有镜像仓库，但已经实现了"代码推上去，服务器自动更新"的核心闭环。

## GitHub Actions

GitHub 官方的自动化引擎，免费。在你的仓库里放一个 `.github/workflows/deploy.yml` 文件，GitHub 读到之后就知道"当有人 push master 时，我要做这些事"。

核心概念：
- **workflow**：整个自动化流程（一个 `.yml` 文件）
- **trigger**：什么事件触发（`on: push: branches: - master`）
- **job**：workflow 里的一个任务单元，跑在一台临时虚拟机上
- **step**：job 里的一步（可以是跑脚本、调用第三方 action）
- **runner**：执行 job 的临时 Ubuntu 虚拟机，跑完自动销毁

## GitHub Secrets

加密存储敏感信息的地方。SSH 私钥、服务器 IP 这些不能写在代码里（公开仓库谁都能看到），存进 Secrets 后 workflow 运行时自动注入，日志里自动打码（`***`）。

操作路径：仓库 → Settings → Secrets and variables → Actions → New repository secret。每个 Secret 分 Name（变量名）和 Value（值）两个输入框，不是 Key=Value 格式。

workflow 中通过 `${{ secrets.SSH_HOST }}` 引用。值一旦保存就无法在页面上查看（只能更新或删除），这是设计如此——不是 bug。

## SSH 密钥认证

SSH 有两种登录方式：密码登录和密钥登录。密钥登录更安全，也是 CI/CD 自动化唯一的选择（不可能每次部署都手动输密码）。

原理：你生成一对"钥匙"——公钥和私钥。公钥放在服务器上（`~/.ssh/authorized_keys`），私钥留在自己手里。连接时服务器用公钥加密一段挑战数据，只有持有对应私钥的人才能解密回应，以此证明"我就是我"。

类比：服务器是一把锁（公钥），私钥是唯一能开这把锁的钥匙。把锁装在门上（公钥放服务器），钥匙揣兜里（私钥存本地/GitHub Secrets）。没有钥匙的人到门口也进不去。

生成命令：`ssh-keygen -t ed25519 -C "备注" -f ~/.ssh/文件名`
- `-t ed25519`：密钥类型，比 RSA 更短更安全
- `-C "备注"`：注释，方便以后知道这把钥匙的用途
- `-f`：输出文件名，公钥自动加 `.pub` 后缀

## Docker Compose

Docker 的"多容器编排工具"。以前要手动 `docker run` 启动 Flask 容器、再单独配 Nginx，两个容器之间的关系全靠脑子记。有了 Compose，一个 `docker-compose.yml` 文件描述所有服务和它们之间的关系（谁连谁、谁挂哪个目录、谁暴露哪个端口），一条 `docker-compose up -d` 全部搞。

核心概念：
- **service**：一个容器就是一个服务（flask、nginx）
- **network**：Compose 自动创建内部网络，服务之间用**服务名**当 hostname 互访（`proxy_pass http://flask:5000` 这里的 `flask` 就是服务名，DNS 自动解析）
- **volume**：把宿主机文件/目录挂进容器（`./index.html:/usr/share/nginx/html/index.html`）
- **depends_on**：启动顺序（nginx 等 flask 先起来）

和 `docker run` 的对应关系：以前 `-p 5000:5000` 现在写成 `ports: - "5000:5000"`，以前 `-v ./:/app` 现在写成 `volumes: - ./:/app`，以前 `--name flask-app` 现在写 `services: flask:`。都是同一个东西的不同表达方式。

## GitHub CLI（`gh` 命令）

GitHub 的命令行客户端。不用打开网页，在终端里就能操作 GitHub——查 issue、看 PR、管理 workflow 运行、查看 Secrets 列表。

你的场景中最常用的三个：

| 操作 | 命令 |
|------|------|
| 查看最近 workflow 运行 | `gh run list -R 用户名/仓库` |
| 查看运行日志 | `gh run view 运行ID -R 用户名/仓库 --log` |
| 重跑失败的工作流 | `gh run rerun 运行ID -R 用户名/仓库` |

类比：GitHub 网页是图形界面，`gh` 命令是纯键盘操作。能在终端做的事就不用切到浏览器点来点去。

## 版本管理与自动化的关系

Git（版本管理）和 GitHub Actions（自动化）是两件事，但配合在一起用：

- **Git** 管的是"代码的历史版本"——每次 `commit` 像一个存档点，随时能回溯。
- **GitHub Actions** 管的是"代码变动之后干什么"——push 了自动部署，本质是"检测到存档更新了就触发后续任务"。

所以你 push 一次，两件事同时发生：代码存档了（版本管理），服务器自动更新了（自动化）。rerun 是自动化跑失败时的补救手段，不是正常操作。

## Workflow 文件

放在 `.github/workflows/` 目录下的 YAML 文件，是 GitHub Actions 的"剧本"。它告诉 GitHub：什么事件触发、在什么环境上跑、每一步做什么。

你的 `deploy.yml` 拆开看就三个部分：

```yaml
name: 部署到服务器          # 1. 名字，显示在 Actions 页面

on:                         # 2. 触发器——什么时候执行
  push:
    branches: - master      #    push 到 master 时就触发

jobs:                       # 3. 具体做什么
  deploy:                   #    一个叫 deploy 的任务
    runs-on: ubuntu-latest  #    跑在 Ubuntu 虚拟机上
    steps:                  #    一步一步执行
      - uses: appleboy/ssh-action@v1  # 用别人的 action（SSH 工具）
        with:                #    传参
          host: ${{ secrets.SSH_HOST }}
          script: |
            cd /root/project && git pull && docker-compose up -d --build
```

关键要素：

| 要素 | 意思 |
|------|------|
| `on:` | 触发器。还可以是定时任务（`schedule`）、手动触发（`workflow_dispatch`） |
| `jobs` | 任务列表，可以有多个 job 并行或串行 |
| `runs-on` | 跑在什么系统上。GitHub 免费提供 ubuntu/windows/macos 三种 runner |
| `steps` | 每一步要么 `uses`（调用现成的 action），要么 `run`（直接写 shell 命令） |
| `secrets.XXX` | 引用 GitHub Secrets 里的值，运行时自动注入，日志里自动打码 |

类比：workflow 文件就像乐高图纸——每一步用现成的积木（`uses`）或自己搓一块（`run`），拼在一起就是一个完整的自动化流程。你不需要从零写 SSH 连接逻辑，`appleboy/ssh-action` 这块积木已经帮你封装好了，传几个参数就能用。

## Docker 为什么能消除环境差异

传统方式代码和运行环境是分开的——代码在一个地方（服务器），环境在另一个维度（Python 版本、pip 包、系统库），两个维度各管各的，很容易错位：

```
开发机                    服务器
Python 3.12  ──对不上──→  Python 3.10     ← 炸
pip 装了 A   ──对不上──→  A 没装          ← 炸
Ubuntu 22.04 ──对不上──→  CentOS 7        ← 炸
```

Docker 的做法：把代码和环境**打包成一个整体**——镜像。镜像里不仅有你写的 app.py，还有 Python 解释器、所有 pip 包、系统底层库，版本和路径全部写死。

```
镜像 = 代码 + Python 3.12 + flask==3.0 + pymysql==1.1 + Debian 系统库 + ...

开发机跑的镜像  ≡  服务器跑的镜像  ≡  同一個镜像
```

容器内环境由镜像定义，跟宿主机完全隔离。宿主机是 Ubuntu 还是 CentOS、装了什么版本 Python，容器完全不关心。镜像相同，环境就相同，代码行为就一致。

类比：传统部署像在不同厨房做同一道菜——食材牌子、火候、锅具不一样，味道不一样。Docker 把菜和厨房打包成"料理包"——不管身处何地，撕开加热就是同一个味道。

## Dockerfile：运行环境知识的书面表达

Docker 只是工具，不会帮你猜项目需要什么。你必须在 Dockerfile 里把"这个项目需要什么环境"写清楚：

```dockerfile
FROM python:3.12-slim          # 需要 Python 3.12
COPY requirements.txt .         # 需要这些 pip 包
RUN pip install -r requirements.txt
COPY app.py .                   # 需要这些代码文件
CMD ["python", "app.py"]        # 启动方式是 python app.py
```

写 Dockerfile 的过程就是梳理项目依赖的过程——Python 什么版本？依赖哪些包？需要哪些文件？启动命令是什么？答不出来，Dockerfile 就写不对；写不对，镜像就缺东西跑不起来。

所以 Docker 能消除环境差异的前提是：**你自己先搞清楚运行环境是什么**。Docker 负责执行，你负责定义。工具再强，不知道要打包什么进去也是白搭。

## OSS 存储类型（标准 / 低频 / 归档）

阿里云 OSS 提供三种存储类型，本质是在"访问速度"和"存储成本"之间做取舍。数据越"热"（被访问越频繁），存储费越贵但取回越便宜；越"冷"（吃灰），存储费越便宜但取回代价越高。

| 类型 | 标准存储 | 低频访问 | 归档存储 |
|------|---------|---------|---------|
| 场景 | 频繁访问的热数据 | 不常访问但需立即可读 | 几乎不访问的冷数据 |
| 月访问频次 | 随时 | 1~2 次 | 每年 1~2 次 |
| 最短存放 | 无限制 | 30 天（提前删也按 30 天计费） | 60 天（提前删也按 60 天计费） |
| 取回 | 直接读，免费 | 直接读，按取回量付费 | 需"解冻"（1 分钟~数小时）+ 取回费 |

核心权衡：存储费 标准 > 低频 > 归档，但取回代价 归档 >> 低频 > 标准。

选型原则：数据越"活"越选标准，越"死"越选归档。图床这种随时有人看的场景选标准存储；长期不用可以配生命周期策略自动降级（90 天转低频 → 180 天转归档）。

类比：标准是冰箱冷藏——打开门就拿；低频是冷冻——拿出来就能用但化冻要钱；归档是仓库深处——翻箱倒柜找出来还得除灰，费时费钱。

## OSS 核心三概念：Bucket / Object / Endpoint

OSS 的地址系统由三个概念构成，一个文件的"在哪存、叫什么、怎么访问"全由它们决定：

**Bucket（存储桶）**：OSS 最顶层容器，相当于在云上申请的专属仓库。名字全局唯一，全阿里云不能重名。创建时指定地域和存储类型，之后不可改。每个 Bucket 有独立的权限、域名和日志配置。

**Object（对象）**：Bucket 里存的每个文件就是一个 Object。叫"对象"不叫"文件"是因为它不只包含数据本身，还绑定了元数据（文件名、大小、Content-Type、上传时间）。没有真实的目录层级——`images/2026/photo.jpg` 只是 Key 的前缀，看起来像路径但实际是平铺的。每个 Object 有唯一 URL：`https://<Bucket>.<Endpoint>/<Key>`。

**Endpoint（访问入口）**：访问 OSS 的 URL 地址，分内网和外网两种。内网 Endpoint（`oss-cn-hangzhou-internal.aliyuncs.com`）供同地域 ECS 走内网访问，免流量费且低延迟。外网 Endpoint（`oss-cn-hangzhou.aliyuncs.com`）供浏览器或外部用户访问，按量收费。Flask 上传用内网，返回给浏览器的 URL 用外网。

类比：Bucket 是仓库名（全国唯一），Object 是货架上的一个档案袋（文件 + 标签），Endpoint 是进门方式——从后门进货（内网，免费）还是从正门迎客（外网，收费）。

## Content-Type（MIME 类型）

浏览器靠 Content-Type 决定"怎么对待收到的文件"——`image/jpeg` 就显示图片，`application/octet-stream` 就弹下载框。同一个文件内容不变，只是响应头里标的类型不同，浏览器的行为就完全不同。

上传到 OSS 时必须显式设 Content-Type，否则 OSS 默认给 `application/octet-stream`（通用二进制流），浏览器不认识就弹下载框。

类比：快递包装上的标签——同一个纸箱，贴"易碎品"快递员会轻放，贴"食品"会走食品通道，没贴标签就按默认处理。

## Session 认证

最简单的用户认证方式——输密码 → 服务器校验 → 往浏览器写一个加密 cookie → 后续请求自动带上这个 cookie。服务器读到 cookie 就知道"这个人之前登录过了"。

- 密码存在环境变量里（不存数据库），Flask 用 `session` 对象读写
- `session['logged_in'] = True` 写登录态，`session.get('logged_in')` 检查
- 退出登录就是删掉 cookie：`session.clear()` 或让浏览器过期 cookie

类比：Session 像演唱会的手环——门口验票通过给你戴上，后面进出凭手环认人，不用每次都查票。退场时把手环剪掉。

和 AccessKey 的区别：AccessKey 是程序访问云资源的凭证（机器对机器），Session 是浏览器端的登录态（人对网站）。

## 频率限制 (Rate Limiting)

防止恶意刷接口的一种防护手段。同一 IP 在指定时间窗口内请求超过阈值 → 返回 `429 Too Many Requests`，后续正常请求不受影响。

Flask 用 `flask-limiter` 实现，本质是一个装饰器：
```python
@limiter.limit("5 per minute")  # 同一个 IP 每分钟最多 5 次
```

简单接口（GET 查数据）可以松一点，写操作（上传、删除）要严。全局设一个大兜底（"30 per minute"），敏感接口按需收紧。

类比：食堂限流——每个人每分钟最多打 5 次饭，超出了请你过会儿再来。不是不让你吃，是防止有人端着盘子无限循环。

<!-- 学懂新概念后在上面加一条 -->
