# 学习反思

> 记录学习过程中的困惑、思考和答案，不追求格式，追求真实。

---

## 2026-07-04 第二次走第一阶段：从"亲手敲"到"懂原理"的转变

### 背景

第二次走第一阶段。上一次（2026年5月）是纯新手，每一步都自己亲手敲命令、踩坑、排查。这次 ECS 重置后重来，全程由 Claude Code 通过 SSH 直接操作服务器，我只在旁边看着、决策、验证。

### 核心感受：速度快了 10 倍，但理解没有缩水

上次走第一阶段花了整整一周（包括踩坑），这次从创建 HTML 到 HTTPS 配通，总共不到 10 分钟。原因是：
1. 操作层面的东西（装 Nginx、配 certbot、上传文件）AI 直接搞定，不需要我查文档、复制粘贴、等加载
2. 所有踩过的坑（SSH 超时、Nginx 配置冲突、安全组端口）这次直接绕过去了，因为上次的笔记里有预案

但快不代表没学到东西。恰恰相反——上次是"手在忙"，这次是"眼在看、脑在想"。具体来说：

**上次（第一次）的收获**：知道了怎么操作，建立了肌肉记忆
**这次（第二次）的收获**：看到了"全貌"，理解了每一步在整个链路中的位置

### 几个新的理解

- **DNS 和 HTTPS 是独立的**：上次觉得"配好 DNS 才能申请证书"，这次发现 certbot 申请证书时走的域名验证，只要 DNS 已经指向服务器 IP 就行，和 Nginx 有没有配 HTTP 没关系
- **Nginx 默认页和 index 指令**：Nginx 自带 `/etc/nginx/sites-enabled/default` 配置，里面 `root /var/www/html`。只需要把自己的 index.html 放到这个目录，它自动覆盖默认页——因为 index 指令优先匹配 `index.html` 再匹配 `index.nginx-debian.html`
- **certbot 会自动改 Nginx 配置**：`--nginx` 参数让 certbot 自动找到 Nginx 的 server 块，添加 443 监听和证书路径。不需要手动改 Nginx 配置，也不需要理解 SSL 配置细节。但缺点是如果以后要理解 Nginx 的 SSL 配置，还是得回头看它改了什么

### 结论

第二次走同样的路线，价值在于"知识的巩固和深化"，不在于"重新操作一遍"。速度快是好事，说明上次学会的东西已经内化了。如果每次重走还要花同样的时间，那才说明第一次没学到东西。

这次的一个意外收获是：看到 AI 怎么操作服务器，对我自己以后独立操作也有帮助——相当于看了一个"最佳实践演示"。

---

## 2026-07-04 第二次走第二阶段：AI 写代码，我审架构

第二次走第二阶段。Flask 后端和留言板前端代码全由 AI 写，我负责架构决策、审核代码、验收。

上次第二阶段踩的坑（WAL 锁残留、Nginx default 冲突）这次直接绕过——因为笔记里记着，AI 按正确方式做：WAL 模式 + 显式 commit、标准 Nginx 站点管理模式。

关键收获：AI 时代"审代码"比"写代码"更重要。路由设计、数据校验、XSS 防护、数据库连接管理、Nginx proxy header——这些决策是我做的，AI 只是实现。如果不懂这些，AI 写出来的安全漏洞我也看不出来。

---

## 2026-07-04 第二次走第三阶段：SQLite → MySQL，前端的甜头

第三阶段更简单——数据库从 SQLite 换成云 MySQL，前端一行不改，Nginx 一行不改。真正体会到了"前后端分离"的价值。

上次踩坑总结：用了错误的 `with get_db() as conn` 导致 commit 失败、混淆 ECS IP 和 MySQL 地址。这次直接用 DBUtils 连接池 + 显式 `try/finally close_db()`，避开所有坑。

新收获：系统学了一遍 systemd service 的完整配置——Environment 字段注入环境变量、ExecStart 指定 venv 里的 Python、Restart=always 保证崩溃自动重启。这比上次用 `nohup python app.py &` 正规太多了。

数据迁移 3 条记录从 SQLite → MySQL，直接在服务器上用 Python 脚本读写两边数据库，比上次用 sqlite3 命令行导出再 scp 再 mysql 导入高效得多。

---

## 2026-07-04 第二次走第四阶段：Docker + CI/CD，真正的一键部署

第四阶段彻底改变了部署方式——从"SSH 上去手动敲命令"变成"git push 完事"。

### Docker 容器化收获

- 两个容器（Nginx + Flask）通过 Docker Compose 编排，内部网络自动 DNS 解析（`proxy_pass http://flask:5000`）
- SSL 证书从宿主机挂载进 Nginx 容器，HTTPS 正常工作
- 环境变量通过 `.env` 文件注入，不硬编码

### CI/CD 收获

GitHub Actions 工作流：push master → SSH 到 ECS → git pull → docker compose up -d --build。从提交代码到服务器更新，全自动。

### 这次踩的坑

1. Docker Hub 直连超时——国内 ECS 必须配镜像加速器，且 `systemctl restart docker` 后配置才生效
2. Flask 监听 `127.0.0.1` 导致容器间 502——Docker 内必须监听 `0.0.0.0`，Nginx 才能通过 Docker 网络访问
3. 容器化后 SSL 没了——需要把宿主机的 Let's Encrypt 证书挂载进 Nginx 容器，加上 443 端口映射

### 对比上次

上次第四阶段折腾了很久 Docker Compose 旧版本 KeyError。这次直接用新版 Docker 29.1.3 + Compose v2，整个过程顺利得多。

---

## 2026-07-04 第五阶段：图床，引入 OSS 对象存储

第五阶段新增了一个独立模块——图床，不依赖留言板，是在现有架构上横向扩展。

### 核心变化

- 新增 `images` 表，OSS SDK 集成
- `POST /api/upload`：接收文件 → 校验类型/大小 → OSS 上传 → MySQL 存链接 → 返回 URL
- `GET /api/images`、`DELETE /api/images/<id>`：列表和删除
- `flask-limiter` 频率限制（上传 5次/分钟）
- 前端 `upload.html`：拖拽上传 + 图片网格 + 一键复制链接 + 删除

### 踩坑

1. **Dockerfile 路径错配**：ECS 上旧版 Dockerfile 写 `COPY app.py .`，但新代码在 `project/phase2/app.py`。本地 repo 虽然更新了，但 ECS 上的旧 Dockerfile 没被 git pull 覆盖（因为它在 .gitignore 之外但在 git 里是 untracked）
2. **requirements.txt 被覆盖**：误将 app.py 内容写入了 requirements.txt，导致 pip install 失败
3. **flask-limiter API 变化**：3.x 版本参数从 `get_remote_address=` 改为 `key_func=`

### OSS URL 格式

内网上传用 `http://oss-cn-beijing-internal.aliyuncs.com`（免流量），公网访问 URL 用 `https://{bucket}.oss-cn-beijing.aliyuncs.com/{key}`。公私分离是关键。

---

---

## 2026-05-30 一周走完 1~2 个月的学习路线，代码没写，影响大吗？

### 背景

一到四阶段全程由 AI 代写代码，我只负责架构决策、部署操作、踩坑排查。学习路线图规定的入门时限是 1~2 个月，我一周就跑完了。省掉的是代码编写部分。

### 担心

- 对后续学习影响大吗？
- 项目里的代码文件，有没有必须会看会写的？

### 答案

**影响不大，但有前提。** 我的路线是云计算/运维，不是纯开发。运维的技能树主干是部署、编排、网络、自动化——Docker 打包、Compose 编排、Nginx 反向代理、GitHub Actions CI/CD，这些我全亲手做了。代码是 AI 写的，但我没看；架构、流程、排查，每一环是我自己走的。

前提：后续学 K8s、监控、日志、CI/CD 进阶时，同样需要"看懂配置和脚本"。**不需要从零写，但能读懂、能改参数才不会被卡住。**

### 项目文件重要程度排序

| 优先级 | 文件 | 要求 | 理由 |
|--------|------|------|------|
| 1 | `Dockerfile` | 会看会写 | 容器化入口。`FROM`/`COPY`/`RUN`/`CMD` 是云计算基本功 |
| 2 | `docker-compose.yml` | 会看会写 | 多容器编排唯一入口。`services`/`volumes`/`ports`/`depends_on` 必须掌握 |
| 3 | `nginx.conf` | 会看 | `server`→`location`→`proxy_pass` 是反向代理核心，运维每天都在碰 |
| 4 | `.github/workflows/deploy.yml` | 会看，会改参数 | CI/CD 标配技能，至少能看懂触发器和步骤 |
| 5 | `app.py` | 看懂架构即可 | 知道路由、请求处理、数据库连接，不需要手写 Flask |
| 6 | `index.html` | 不需要 | 前端是另一条路线，云计算路线上碰不到 |

### 核心结论

`Dockerfile` 和 `docker-compose.yml` 是吃饭的家伙，必须拿下来。`nginx.conf` 和 `deploy.yml` 能看懂能改。`app.py` 当阅读理解过一遍就行。代码不是我写的不是问题，代码是完全看不懂才是问题——但能读懂配置和脚本语法就够了，不用会从零写。
