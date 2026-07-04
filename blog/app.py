import os, re
from datetime import datetime
from flask import Flask, render_template, abort
import markdown as md

app = Flask(__name__)
POSTS_DIR = os.path.join(os.path.dirname(__file__), 'posts')


def parse_post(filepath):
    """解析 Markdown 文件，提取元数据和内容"""
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()

    meta = {}
    # 解析 YAML-like front matter
    if text.startswith('---'):
        parts = text.split('---', 2)
        if len(parts) >= 3:
            for line in parts[1].strip().split('\n'):
                if ':' in line:
                    k, v = line.split(':', 1)
                    meta[k.strip()] = v.strip()
            content = parts[2].strip()
        else:
            content = text
    else:
        content = text

    # 取第一行非空作为标题
    lines = content.strip().split('\n')
    title = meta.get('title', lines[0].lstrip('#').strip() if lines[0].startswith('#') else '未命名')
    slug = os.path.splitext(os.path.basename(filepath))[0]
    date_str = meta.get('date', '')
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        date = datetime.fromtimestamp(os.path.getmtime(filepath))

    return {
        'slug': slug,
        'title': title,
        'date': date,
        'date_str': date.strftime('%Y年%m月%d日'),
        'excerpt': meta.get('excerpt', content[:200].replace('\n', ' ').strip() + '…'),
        'content': md.markdown(content, extensions=['fenced_code', 'codehilite', 'tables']),
    }


def load_posts():
    posts = []
    for f in sorted(os.listdir(POSTS_DIR), reverse=True):
        if f.endswith('.md'):
            try:
                posts.append(parse_post(os.path.join(POSTS_DIR, f)))
            except Exception:
                pass
    return posts


@app.route('/blog/')
def blog_list():
    posts = load_posts()
    return render_template('list.html', posts=posts)


@app.route('/blog/<slug>')
def blog_post(slug):
    filepath = os.path.join(POSTS_DIR, slug + '.md')
    if not os.path.exists(filepath):
        abort(404)
    post = parse_post(filepath)
    posts = load_posts()
    return render_template('post.html', post=post, posts=posts)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=False)
