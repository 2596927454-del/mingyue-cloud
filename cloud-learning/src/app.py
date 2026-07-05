import os
import uuid
import pymysql
import oss2
from dbutils.pooled_db import PooledDB
from flask import Flask, request, jsonify, g
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB

# 频率限制
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["30 per minute"],
)

# 数据库连接池
DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
DB_PORT = int(os.getenv('DB_PORT', '3306'))
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_NAME = os.getenv('DB_NAME', 'guestbook')

pool = PooledDB(
    creator=pymysql,
    maxconnections=10,
    mincached=2,
    maxcached=5,
    blocking=True,
    host=DB_HOST,
    port=DB_PORT,
    user=DB_USER,
    password=DB_PASSWORD,
    database=DB_NAME,
    charset='utf8mb4',
    cursorclass=pymysql.cursors.Cursor,
)

# OSS 客户端
OSS_KEY_ID = os.getenv('OSS_ACCESS_KEY_ID', '')
OSS_KEY_SECRET = os.getenv('OSS_ACCESS_KEY_SECRET', '')
OSS_BUCKET = os.getenv('OSS_BUCKET', '')
OSS_ENDPOINT = os.getenv('OSS_ENDPOINT', '')
OSS_EXTERNAL = os.getenv('OSS_EXTERNAL_ENDPOINT', OSS_ENDPOINT)

auth = oss2.Auth(OSS_KEY_ID, OSS_KEY_SECRET)
bucket = oss2.Bucket(auth, OSS_ENDPOINT, OSS_BUCKET)

ALLOWED_EXT = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
MIME_MAP = {
    'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
    'png': 'image/png', 'gif': 'image/gif', 'webp': 'image/webp',
}


def get_db():
    if 'db' not in g:
        g.db = pool.connection()
    return g.db


def close_db():
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    conn = pool.connection()
    try:
        with conn.cursor() as cur:
            cur.execute('''CREATE TABLE IF NOT EXISTS messages (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nickname VARCHAR(30) NOT NULL,
                content VARCHAR(500) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')
            cur.execute('''CREATE TABLE IF NOT EXISTS images (
                id INT AUTO_INCREMENT PRIMARY KEY,
                filename VARCHAR(255) NOT NULL,
                oss_url VARCHAR(512) NOT NULL,
                content_type VARCHAR(64),
                size INT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')
        conn.commit()
    finally:
        conn.close()


@app.teardown_appcontext
def teardown_db(exception):
    close_db()


def fmt_time(dt):
    """格式化时间"""
    if dt is None:
        return ''
    return dt.strftime('%Y-%m-%d %H:%M:%S')


# ——— 留言板 API ———

@app.route('/api/messages', methods=['GET'])
def get_messages():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT id, nickname, content, created_at FROM messages ORDER BY id DESC')
            rows = cur.fetchall()
        messages = [
            {'id': r[0], 'nickname': r[1], 'content': r[2],
             'created_at': fmt_time(r[3])}
            for r in rows
        ]
        return jsonify(messages)
    finally:
        close_db()


@app.route('/api/messages', methods=['POST'])
def post_message():
    data = request.get_json()
    if not data:
        return jsonify({'error': '请求数据不能为空'}), 400

    nickname = (data.get('nickname') or '').strip()
    content = (data.get('content') or '').strip()

    if not nickname:
        return jsonify({'error': '昵称不能为空'}), 400
    if len(nickname) > 30:
        return jsonify({'error': '昵称不能超过30个字符'}), 400
    if not content:
        return jsonify({'error': '留言内容不能为空'}), 400
    if len(content) > 500:
        return jsonify({'error': '留言内容不能超过500个字符'}), 400

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute('INSERT INTO messages (nickname, content) VALUES (%s, %s)',
                        (nickname, content))
        conn.commit()
        return jsonify({'ok': True}), 201
    finally:
        close_db()


@app.route('/api/messages/<int:msg_id>', methods=['DELETE'])
def delete_message(msg_id):
    data = request.get_json() or {}
    if data.get('password') != '月明':
        return jsonify({'error': '密码错误'}), 403

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT id FROM messages WHERE id = %s', (msg_id,))
            if not cur.fetchone():
                return jsonify({'error': '留言不存在'}), 404
            cur.execute('DELETE FROM messages WHERE id = %s', (msg_id,))
        conn.commit()
        return jsonify({'ok': True})
    finally:
        close_db()


# ——— 图床 API ———

@app.route('/api/images', methods=['GET'])
def get_images():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT id, filename, oss_url, content_type, size, created_at FROM images ORDER BY id DESC')
            rows = cur.fetchall()
        images = [
            {'id': r[0], 'filename': r[1], 'oss_url': r[2],
             'content_type': r[3], 'size': r[4],
             'created_at': r[5].strftime('%Y-%m-%d %H:%M:%S') if r[5] else ''}
            for r in rows
        ]
        return jsonify(images)
    finally:
        close_db()


@app.route('/api/upload', methods=['POST'])
@limiter.limit("5 per minute")
def upload_image():
    if 'file' not in request.files:
        return jsonify({'error': '请选择文件'}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({'error': '请选择文件'}), 400

    # 文件类型校验
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in ALLOWED_EXT:
        return jsonify({'error': f'不支持的文件类型: .{ext}，仅允许 {", ".join(ALLOWED_EXT)}'}), 400

    # 读取文件内容
    data = file.read()
    if len(data) > 5 * 1024 * 1024:
        return jsonify({'error': '文件大小不能超过 5MB'}), 400

    # 生成唯一文件名
    new_name = f"{uuid.uuid4().hex}.{ext}"
    oss_key = f"upload/{new_name}"
    content_type = MIME_MAP.get(ext, 'application/octet-stream')

    # 上传到 OSS
    try:
        bucket.put_object(oss_key, data, headers={'Content-Type': content_type})
    except Exception as e:
        return jsonify({'error': f'OSS 上传失败: {str(e)}'}), 500

    # 拼接公网 URL
    host = OSS_EXTERNAL.replace('http://', '').replace('https://', '')
    public_url = f"https://{OSS_BUCKET}.{host}/{oss_key}"

    # 存入 MySQL
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'INSERT INTO images (filename, oss_url, content_type, size) VALUES (%s, %s, %s, %s)',
                (new_name, public_url, content_type, len(data))
            )
        conn.commit()
        return jsonify({'ok': True, 'url': public_url, 'filename': new_name}), 201
    finally:
        close_db()


@app.route('/api/images/<int:image_id>', methods=['DELETE'])
@limiter.limit("10 per minute")
def delete_image(image_id):
    data = request.get_json() or {}
    if data.get('password') != '0125':
        return jsonify({'error': '密码错误'}), 403
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT oss_url FROM images WHERE id = %s', (image_id,))
            row = cur.fetchone()
            if not row:
                return jsonify({'error': '图片不存在'}), 404

            oss_url = row[0]
            # 从 URL 提取 OSS key
            key = oss_url.split('.com/')[-1] if '.com/' in oss_url else oss_url.split('/')[-1]

            cur.execute('DELETE FROM images WHERE id = %s', (image_id,))
        conn.commit()
    finally:
        close_db()

    # 删除 OSS 文件
    try:
        bucket.delete_object(key)
    except Exception:
        pass

    return jsonify({'ok': True})


if __name__ == '__main__':
    init_db()
    app.run(host=os.getenv('FLASK_HOST', '127.0.0.1'), port=5000, debug=False)
