---
title: Docker 没那么可怕：一个初学者的容器化实践
date: 2026-06-10
excerpt: 从"手动拷文件、手动重启服务"到"git push 之后全自动"，记录第四阶段的学习心得。
---

## 为什么需要 Docker

前三阶段我一直在手动部署：

```
本地改代码 → scp 上传 → SSH 连服务器 → 重启 Flask → reload Nginx
```

每次更新要敲五六条命令，中间任何一个环节搞错，网站就挂了。

## Docker 解决了什么

**环境一致性**。开发机和服务器跑的是同一个镜像——Python 版本、pip 包、系统库全部打在一个包里。不存在"在我电脑上能跑啊"的问题。

我的 Dockerfile 只有六行：

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt -q
COPY app.py .
CMD ["python", "app.py"]
```

加上 `docker-compose.yml` 编排 Nginx + Flask 两个容器，整个应用变成了一条命令：

```bash
docker compose up -d --build
```

## CI/CD 的魔法

最后配了 GitHub Actions。从此以后：

```
git push → GitHub Actions 触发 → SSH 到 ECS → git pull → docker compose up -d --build
```

改一行文字，提交推送，30 秒后线上自动更新。这种体验会上瘾。

## 感想

Docker 不是银弹，但对于个人项目来说，它确实把"部署"这个动作从 5 分钟压缩到了 5 秒。更重要的是——换一台服务器、重装系统、给朋友演示，都是一条命令搞定，不再需要手动配环境。
