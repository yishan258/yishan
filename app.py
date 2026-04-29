from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
BEARER_TOKEN = os.environ.get('BEARER_TOKEN', '')
app = Flask(__name__)
app.secret_key = 'miheai_beizhai_secret_key_2024'
app.config['JSON_AS_ASCII'] = False
app.json.ensure_ascii = False
basedir = os.path.abspath(os.path.dirname(__file__))
basedir = os.path.abspath(os.path.dirname(__file__))

if os.environ.get('VERCEL'):
    db_path = '/tmp/miheai.db'
else:
    db_path = os.path.join(basedir, 'miheai.db')

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
class Tutorial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    cover_image = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_published = db.Column(db.Boolean, default=True)
    is_pinned = db.Column(db.Boolean, default=False)

def verify_bearer_token():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return False
    token = auth_header.replace('Bearer ', '', 1)
    return token == BEARER_TOKEN

@app.route('/api/articles', methods=['GET'])
def get_articles():
    articles = Tutorial.query.order_by(Tutorial.created_at.desc()).all()
    return jsonify([
        {
            'id': a.id,
            'title': a.title,
            'content': a.content,
            'cover_image': a.cover_image,
            'created_at': a.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        }
        for a in articles
    ])

@app.route('/api/articles', methods=['POST'])
def create_article():
    if not verify_bearer_token():
        return jsonify({'error': 'Unauthorized', 'code': 401}), 401

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'error': 'Invalid request body', 'code': 400}), 400

    title = (data.get('title') or '').strip()
    content = data.get('content')
    cover_image = data.get('cover_image')

    if not title or not content:
        return jsonify({'error': 'Title and content are required', 'code': 400}), 400

    article = Tutorial(
        title=title,
        content=content,
        is_published=True,
        is_pinned=False,
        cover_image=cover_image,
    )

    db.session.add(article)
    db.session.commit()

    return jsonify({'id': article.id, 'title': article.title, 'message': '创建成功'}), 201
if os.environ.get('VERCEL'):
    UPLOAD_FOLDER = '/tmp/uploads'
else:
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@app.route('/')
def index():
    return send_from_directory(basedir, 'index.html')

@app.route('/api/tutorials')
def get_tutorials():
    tutorials = Tutorial.query.filter_by(is_published=True).order_by(Tutorial.created_at.desc()).all()
    result = []
    for t in tutorials:
        content = t.content
        if len(content) > 200:
            content = content[:200] + '...'
        result.append({
            'id': t.id,
            'title': t.title,
            'content': content,
            'cover_image': t.cover_image,
            'created_at': t.created_at.strftime('%Y-%m-%d')
        })
    return jsonify(result)

@app.route('/api/tutorial/<int:tutorial_id>')
def get_tutorial(tutorial_id):
    tutorial = Tutorial.query.get_or_404(tutorial_id)
    return jsonify({
        'id': tutorial.id,
        'title': tutorial.title,
        'content': tutorial.content,
        'cover_image': tutorial.cover_image,
        'created_at': tutorial.created_at.strftime('%Y-%m-%d %H:%M:%S')
    })

@app.route('/admin')
def admin():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('admin.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('admin'))
        return render_template('login.html', error='用户名或密码错误')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/api/admin/tutorials', methods=['GET'])
def admin_tutorials():
    if 'user_id' not in session:
        return jsonify({'error': '未登录'}), 401
    tutorials = Tutorial.query.order_by(Tutorial.created_at.desc()).all()
    return jsonify([{
        'id': t.id,
        'title': t.title,
        'content': t.content,
        'cover_image': t.cover_image,
        'created_at': t.created_at.strftime('%Y-%m-%d'),
        'is_published': t.is_published
    } for t in tutorials])

@app.route('/api/admin/tutorial', methods=['POST'])
def create_tutorial():
    if 'user_id' not in session:
        return jsonify({'error': '未登录，请先登录', 'code': 401}), 401
    
    try:
        data = request.form
        tutorial = Tutorial(
            title=data.get('title'),
            content=data.get('content'),
            is_published=data.get('is_published') == 'true'
        )
        
        if 'cover_image' in request.files:
            file = request.files['cover_image']
            if file.filename:
                filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                tutorial.cover_image = f'/uploads/{filename}'
        
        db.session.add(tutorial)
        db.session.commit()
        return jsonify({'success': True, 'id': tutorial.id})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'保存失败: {str(e)}', 'code': 500}), 500

@app.route('/api/admin/tutorial/<int:tutorial_id>', methods=['PUT'])
def update_tutorial(tutorial_id):
    if 'user_id' not in session:
        return jsonify({'error': '未登录，请先登录', 'code': 401}), 401
    
    try:
        tutorial = Tutorial.query.get_or_404(tutorial_id)
        data = request.form
        tutorial.title = data.get('title')
        tutorial.content = data.get('content')
        tutorial.is_published = data.get('is_published') == 'true'
        
        if 'cover_image' in request.files:
            file = request.files['cover_image']
            if file.filename:
                filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                tutorial.cover_image = f'/uploads/{filename}'
        
        db.session.commit()
        return jsonify({'success': True})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'保存失败: {str(e)}', 'code': 500}), 500

@app.route('/api/admin/tutorial/<int:tutorial_id>', methods=['DELETE'])
def delete_tutorial(tutorial_id):
    if 'user_id' not in session:
        return jsonify({'error': '未登录'}), 401
    tutorial = Tutorial.query.get_or_404(tutorial_id)
    db.session.delete(tutorial)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# 处理富文本编辑器图片上传
@app.route('/api/upload', methods=['POST'])
def upload_image():
    if 'user_id' not in session:
        return jsonify({'error': '未登录'}), 401
    
    if 'file' not in request.files:
        return jsonify({'error': '没有文件'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '文件名为空'}), 400
    
    if file:
        filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return jsonify({
            'location': f'/uploads/{filename}'
        })
    
    return jsonify({'error': '上传失败'}), 500

def init_db():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin')
            admin.set_password('adminpengpeng')
            db.session.add(admin)
            db.session.commit()
            print('默认管理员账号创建成功！')
            print('用户名: admin')
            print('密码: adminpengpeng')
if os.environ.get('VERCEL'):
    init_db()
if __name__ == '__main__':
    init_db()
    app.run(host='127.0.0.1', port=5001, debug=True, use_reloader=False)

# 为 Vercel 导出 app 实例
app = app
