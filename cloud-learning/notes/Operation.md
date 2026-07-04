# 运维操作手册

> 按阶段记录，需要时直接复制命令。

---

## Phase 1 基础操作

### ECS 初始设置

```bash
# 更新包列表
apt update

# 安装 Nginx
apt install nginx -y

# 启动 + 开机自启
systemctl start nginx
systemctl enable nginx

# 查看状态
systemctl status nginx --no-pager
```

### 文件上传到服务器

```bash
# 用 scp 上传单个文件
scp index.html root@60.205.219.2:/var/www/html/

# 覆盖已有文件（权限不足时）
scp index.html root@60.205.219.2:/tmp/
# 然后 SSH 进去 sudo cp /tmp/index.html /var/www/html/
```

### Nginx 基础操作

```bash
nginx -t                         # 检查配置语法
nginx -s reload                  # 重载配置
systemctl status nginx           # 查看运行状态
systemctl restart nginx          # 重启
```

### 验证网站各层

```bash
# 第一层：本机服务
curl http://127.0.0.1/

# 第二层：公网 IP
curl http://60.205.219.2/

# 第三层：域名
curl http://mingyue15.xyz/

# 检查 HTTP 头（看跳转、服务器信息）
curl -I https://mingyue15.xyz/
```

### HTTPS 证书（Let's Encrypt + certbot）

```bash
# 安装 certbot
apt install certbot python3-certbot-nginx -y

# 申请证书（自动改 Nginx 配置 + 配自动续签）
certbot --nginx -d mingyue15.xyz -d www.mingyue15.xyz --non-interactive --agree-tos -m 你的邮箱

# 查看证书状态
certbot certificates

# 测试自动续签（不真续，只是演练）
certbot renew --dry-run
```

### 安全组检查清单

| 端口 | 用途 | 来源 |
|------|------|------|
| 22 | SSH | 0.0.0.0/0 |
| 80 | HTTP | 0.0.0.0/0 |
| 443 | HTTPS | 0.0.0.0/0 |

其他端口全部关闭。出方向默认全开。

---

## Phase 2 常用操作

### 查端口 & 杀进程

```bash
# 查谁占了 5000 端口
ss -tlnp | grep 5000

# 查端口对应的 PID
lsof -t -i:5000

# 杀掉占 5000 的进程
kill $(lsof -t -i:5000)

# 有多个残留进程杀不掉时强制杀
kill -9 PID1 PID2
```

### WAL 锁文件清理

```bash
# 查看残留锁文件
ls -la messages.db*

# 删除残留的 WAL 文件
rm -f messages.db-shm messages.db-wal
```

### Flask 启动

```bash
cd /root/resume                  # 进项目目录
source venv/bin/activate         # 激活虚拟环境
python app.py &                  # 后台启动
```

### Nginx 操作

```bash
nginx -t                         # 检查配置语法
nginx -s reload                  # 重载配置

# 查看站点配置
ls /etc/nginx/sites-enabled/
cat /etc/nginx/sites-enabled/mingyue
```

### 分层排查

```bash
# 第一层：Flask 本身
curl http://127.0.0.1:5000/api/messages

# 第二层：Nginx 反向代理
curl http://localhost/api/messages

# 第三层：浏览器 → F12 → Network 看请求状态
```

---

## Phase 3 数据库操作

### 云数据库连通性测试

```bash
# -h 后面填 MySQL 实例的**内网地址**（不是 ECS 的 IP！）
mysql -h rm-xxx.mysql.rds.aliyuncs.com -u root -p
```

进入 MySQL 命令行后：

```sql
SHOW DATABASES;
USE message_book;
SHOW TABLES;
SELECT * FROM messages;
```

### 环境变量持久化（~/.bashrc 方式）

```bash
echo 'export DB_HOST="rm-xxx.mysql.rds.aliyuncs.com"' >> ~/.bashrc
echo 'export DB_PORT="3306"' >> ~/.bashrc
echo 'export DB_USER="root"' >> ~/.bashrc
echo 'export DB_PASSWORD="你的密码"' >> ~/.bashrc
echo 'export DB_NAME="message_book"' >> ~/.bashrc

# 立即生效
source ~/.bashrc

# 验证
echo $DB_HOST
```

### 环境变量持久化（systemd service 方式）

创建 `/etc/systemd/system/guestbook.service`：

```ini
[Unit]
Description=留言板 Flask 后端
After=network.target

[Service]
User=root
WorkingDirectory=/root/resume
ExecStart=/root/resume/venv/bin/python /root/resume/app.py
Restart=always
Environment="DB_HOST=内网地址"
Environment="DB_PORT=3306"
Environment="DB_USER=root"
Environment="DB_PASSWORD=密码"
Environment="DB_NAME=数据库名"

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable guestbook        # 开机自启
systemctl start guestbook         # 立即启动
systemctl status guestbook        # 查看状态
journalctl -u guestbook -f        # 实时看日志
```

### 数据迁移（SQLite → MySQL）

```bash
# 1. 导出 SQLite 数据
sqlite3 messages.db <<'EOF'
.mode insert messages
.output dump.sql
SELECT nickname, content, created_at FROM messages;
.output
.quit
EOF

# 2. 传到服务器（本地有文件时）
scp dump.sql root@服务器IP:/root/resume/

# 3. 导入 MySQL
mysql -h 内网地址 -u root -p 数据库名 < dump.sql

# 4. 验证
mysql -h 内网地址 -u root -p 数据库名 -e "SELECT * FROM messages;"
```

### 安装依赖 & 启动（Phase 3 版）

```bash
cd /root/resume
source venv/bin/activate
pip install flask pymysql dbutils     # 一次性装齐
python app.py                         # 先前台跑看报错
```

---

## Phase 4 Docker 操作

### Docker 安装

```bash
apt install docker.io -y
systemctl enable --now docker

# 配镜像加速器（国内必须）
mkdir -p /etc/docker
tee /etc/docker/daemon.json <<'EOF'
{
  "registry-mirrors": ["https://你的ID.mirror.aliyuncs.com"]
}
EOF
systemctl restart docker

# 验证
docker run hello-world
```

### 构建 Flask 镜像

```bash
cd /root/resume

# 构建（注意最后的点）
docker build -t guestbook-flask .

# 查看镜像
docker images
```

### 启动容器

```bash
# 启动（.--env-file 注入数据库环境变量）
docker run -d --name flask-app --env-file .env -p 5000:5000 guestbook-flask

# 查看运行中的容器
docker ps

# 查看日志
docker logs flask-app

# 进容器排查
docker exec -it flask-app bash
```

### 重启 / 停止 / 删除容器

```bash
docker restart flask-app        # 重启
docker stop flask-app           # 停止
docker rm flask-app             # 删除（需先 stop）
docker rm -f flask-app          # 强制删除（不管有没有在运行）
```

### 重建镜像（代码改了之后）

```bash
docker build -t guestbook-flask .   # 重新构建
docker rm -f flask-app              # 删旧容器
docker run -d --name flask-app --env-file .env -p 5000:5000 guestbook-flask  # 起新容器
```

### Docker Compose（阶段后半使用）

```bash
# 旧版 Docker 用 docker-compose（带连字符），新版用 docker compose（空格）
docker-compose up -d --build          # 构建镜像 + 后台启动所有服务
docker-compose ps                      # 查看所有服务状态
docker-compose logs -f                 # 实时看所有容器日志
docker-compose stop                    # 停止所有服务
docker-compose restart                 # 重启所有服务
docker-compose down                    # 停止并删除所有容器和网络
```

### 从单容器迁移到 Docker Compose 的步骤

```bash
# 1. 停掉旧的单容器
docker stop flask-app
docker rm flask-app

# 2. 停掉宿主机 Nginx（不再需要，Compose 里有 Nginx 容器）
systemctl stop nginx
systemctl disable nginx

# 3. 确保所有文件都在同一目录下
ls /root/project/
# 应有：app.py  Dockerfile  docker-compose.yml  index.html  avatar.jpg  nginx.conf  requirements.txt

# 4. 启动
cd /root/project
docker-compose up -d --build

# 5. 验证
docker-compose ps
curl http://localhost/api/messages
```

### Docker 常用命令速查

| 操作 | 命令 |
|------|------|
| 查看所有容器（含已停止） | `docker ps -a` |
| 查看镜像 | `docker images` |
| 删除镜像 | `docker rmi 镜像名` |
| 删除所有已停止容器 | `docker container prune` |
| 删除所有未使用镜像 | `docker image prune` |
| 看容器日志最后50行 | `docker logs --tail 50 flask-app` |
| 实时看日志 | `docker logs -f flask-app` |
| 进容器 | `docker exec -it flask-app bash` |

---

## Phase 4 CI/CD 操作

### SSH 密钥生成（CI/CD 用）

```bash
# 在服务器上生成专用密钥对
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/github-actions

# 公钥写入授权列表（放自己服务器上）
cat ~/.ssh/github-actions.pub >> ~/.ssh/authorized_keys

# 查看私钥（完整复制到 GitHub Secrets，包括 BEGIN/END 头尾行）
cat ~/.ssh/github-actions
```

### GitHub Secrets 配置

仓库 → Settings → Secrets and variables → Actions → New repository secret：

| Name | Value |
|------|-------|
| `SSH_HOST` | 服务器公网 IP |
| `SSH_USER` | root |
| `SSH_PRIVATE_KEY` | `cat ~/.ssh/github-actions` 的**完整输出**（含头尾行） |

### GitHub Actions 触发 & 排错

```bash
# 查看最近 workflow 运行
gh run list -R 用户名/仓库名 --limit 3

# 查看某次运行的日志
gh run view 运行ID -R 用户名/仓库名 --log

# 重新运行
gh run rerun 运行ID -R 用户名/仓库名

# 查看 Secrets 列表（不显示值）
gh secret list -R 用户名/仓库名
```

### 部署文件关联关系

```
本地 C:\deep\resume\              →  GitHub 仓库            →  服务器 /root/project/
├── app.py                          （git push）              ├── app.py（git pull）
├── Dockerfile                                                ├── Dockerfile
├── docker-compose.yml                                        ├── docker-compose.yml
├── nginx.conf                                                ├── nginx.conf
├── index.html                                                ├── index.html
├── avatar.jpg                                                ├── avatar.jpg
└── requirements.txt                                          └── requirements.txt

GitHub Actions（.github/workflows/deploy.yml）
  → runner SSH 到服务器 → cd /root/project → git pull → docker-compose up -d --build
```

---

## 文件传输

```bash
# 上传到服务器
scp index.html app.py requirements.txt root@服务器IP:/root/resume/

# 下载到本地
scp root@服务器IP:/root/resume/messages.db ./
```

---

## 快捷命令速查

| 场景 | 命令 |
|------|------|
| Flask 占用的端口 | `ss -tlnp \| grep 5000` |
| 杀 Flask | `kill $(lsof -t -i:5000)` |
| 清 WAL 锁 | `rm -f messages.db-shm messages.db-wal` |
| Nginx 配置测试 | `nginx -t` |
| Nginx 重载 | `nginx -s reload` |
| 测 Flask | `curl http://127.0.0.1:5000/api/messages` |
| 测 Nginx 转发 | `curl http://localhost/api/messages` |
| 测 MySQL 连接 | `mysql -h 内网地址 -u root -p` |
| 环境变量立即生效 | `source ~/.bashrc` |
| Flask 前台启动 | `source venv/bin/activate && python app.py` |
| 查环境变量 | `echo $DB_HOST` |
| 生成 SSH 密钥 | `ssh-keygen -t ed25519 -C "备注" -f ~/.ssh/文件名` |
| 查看 workflow 运行 | `gh run list -R 用户名/仓库` |
| 重跑 workflow | `gh run rerun 运行ID -R 用户名/仓库` |
| 查看 workflow 日志 | `gh run view 运行ID -R 用户名/仓库 --log` |

---

## Phase 5 OSS 操作

### OSS 环境变量配置（.env）

```bash
OSS_ACCESS_KEY_ID=LTAI5t...
OSS_ACCESS_KEY_SECRET=83kYy...
OSS_BUCKET=my-project-beijing-ming
OSS_ENDPOINT=http://oss-cn-beijing-internal.aliyuncs.com
```

### OSS 连通性测试

```bash
cd /root/project
pip install oss2
python test_oss.py
```

### 上传到 ECS

```bash
# test_oss.py 和 .env 要一起传到服务器
scp test_oss.py .env root@服务器IP:/root/project/
```

### 签名 URL 验证

私有 Bucket 文件不能直接通过裸 URL 访问（返回 403），需要用签名 URL：

```bash
# test_oss.py 末尾已加 sign_url 生成临时下载链接（60 秒有效）
python test_oss.py
# 输出最后一行为签名 URL，复制到浏览器打开
```

### 三层存储类型选型

| 场景 | 类型 |
|------|------|
| 图床（频繁访问） | 标准存储 |
| 不常用备份 | 低频访问 |
| 长期归档 | 归档存储（需解冻） |

### 灾后重建（旧容器清理）

```bash
cd /root/project
docker-compose down
docker-compose rm -f
docker image prune -f
docker-compose up -d --build
```

### 单文件传输

```bash
# 不从 git pull 时，手动传单个文件到服务器
scp app.py root@服务器IP:/root/project/
scp requirements.txt root@服务器IP:/root/project/
scp docker-compose.yml root@服务器IP:/root/project/
scp .env root@服务器IP:/root/project/
```

### 图床上传接口测试

```bash
# 上传（使用服务器本地图片）
curl -F "file=@/root/project/avatar.jpg" http://localhost/api/upload

# 查看已上传列表
curl http://localhost/api/images
```

### Bucket 权限策略

| 权限 | 场景 |
|------|------|
| 私有 | 内部系统，不对外 |
| 公共读 | 图床/静态资源，任何人能看但只有你能写 |

注意：改为公共读后，图片 URL 无需签名即可在浏览器打开。

### 图床登录

```bash
# 登录（获取 session cookie）
curl -X POST http://localhost/api/login \
  -H "Content-Type: application/json" \
  -d '{"password":"mingyue123"}'

# 检查登录状态
curl http://localhost/api/check-login --cookie-jar -

# 带 cookie 上传 / 删除
curl -F "file=@图片.jpg" http://localhost/api/upload -b /tmp/cookie
curl -X DELETE http://localhost/api/images/1 -b /tmp/cookie
```

### 验证速率限制

```bash
# 连续上传 6 次，第 6 次应返回 429
for i in 1 2 3 4 5 6; do
  curl -F "file=@/root/project/avatar.jpg" http://localhost/api/upload -b /tmp/cookie
  echo " --- $i"
done
```

### 上传页面文件清单

传文件到 ECS 时别漏了：
```bash
scp upload.html docker-compose.yml app.py root@60.205.219.2:/root/project/
```

nginx 容器重启（不改镜像时不用 down 再 up）：
```bash
cd /root/project && docker-compose restart nginx
```
