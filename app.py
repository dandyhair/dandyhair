from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json

basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
app.config['SECRET_KEY'] = 'haircare-finance-secret-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'finance.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='user')  # superadmin / admin / user
    system_name = db.Column(db.String(100), default='如福财务系统')
    expenses = db.relationship('Expense', backref='user', lazy=True)
    incomes = db.relationship('Income', backref='user', lazy=True)
    payment_methods = db.Column(db.Text, default='["银行转账","微信","支付宝","现金"]')
    suppliers = db.Column(db.Text, default='["供应商A","供应商B"]')
    expense_categories = db.Column(db.Text, default='["采购成本","物流","广告","包装","其他"]')
    platforms = db.Column(db.Text, default='["淘宝","抖音","拼多多"]')
    shops = db.Column(db.Text, default='{"淘宝":["旗舰店"],"抖音":["小店1"],"拼多多":["专营店"]}')

    def get_payment_methods(self):
        return json.loads(self.payment_methods)

    def get_suppliers(self):
        return json.loads(self.suppliers)

    def get_expense_categories(self):
        return json.loads(self.expense_categories)

    def get_platforms(self):
        return json.loads(self.platforms)

    def get_shops(self):
        return json.loads(self.shops)

    def serialize_payment_methods(self):
        return self.get_payment_methods()

    def serialize_suppliers(self):
        return self.get_suppliers()

    def serialize_expense_categories(self):
        return self.get_expense_categories()

    def serialize_platforms(self):
        return self.get_platforms()

    def serialize_shops(self):
        shops = self.shops
        if isinstance(shops, str):
            return json.loads(shops)
        return shops


class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.String(10), nullable=False)
    payment = db.Column(db.String(50))
    supplier = db.Column(db.String(50))
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50))
    note = db.Column(db.Text)

    def to_dict(self):
        return {
            'id': self.id, 'date': self.date, 'payment': self.payment,
            'supplier': self.supplier, 'amount': self.amount,
            'category': self.category, 'note': self.note
        }


class Income(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.String(10), nullable=False)
    platform = db.Column(db.String(50))
    shop = db.Column(db.String(50))
    amount = db.Column(db.Float, nullable=False)
    withdraw_date = db.Column(db.String(10))
    withdraw_amount = db.Column(db.Float, default=0)
    note = db.Column(db.Text)

    def to_dict(self):
        return {
            'id': self.id, 'date': self.date, 'platform': self.platform,
            'shop': self.shop, 'amount': self.amount,
            'withdrawDate': self.withdraw_date,
            'withdrawAmount': self.withdraw_amount, 'note': self.note
        }


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
@login_required
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            return render_template('login.html', error='用户名和密码不能为空')
        user = User.query.filter_by(username=username).first()
        if user:
            if check_password_hash(user.password_hash, password):
                login_user(user)
                next_page = request.form.get('next') or request.args.get('next')
                return redirect(next_page or url_for('index'))
            return render_template('login.html', error='密码错误')
        # 用户不存在，自动注册
        user = User(username=username, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        login_user(user)
        next_page = request.form.get('next') or request.args.get('next')
        return redirect(next_page or url_for('index'))
    return render_template('login.html')


@app.route('/register', methods=['POST'])
def register():
    username = request.form.get('username')
    password = request.form.get('password')
    if User.query.filter_by(username=username).first():
        return '用户名已存在', 400
    user = User(username=username, password_hash=generate_password_hash(password))
    db.session.add(user)
    db.session.commit()
    login_user(user)
    return redirect(url_for('index'))


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/api/expenses', methods=['GET'])
@login_required
def get_expenses():
    return jsonify([e.to_dict() for e in current_user.expenses])


@app.route('/api/expenses', methods=['POST'])
@login_required
def add_expenses():
    items = request.get_json()
    if not isinstance(items, list):
        items = [items]
    for item in items:
        exp = Expense(
            user_id=current_user.id, date=item['date'],
            payment=item.get('payment', ''), supplier=item.get('supplier', ''),
            amount=float(item['amount']), category=item.get('category', '其他'),
            note=item.get('note', '')
        )
        db.session.add(exp)
    db.session.commit()
    return jsonify({'status': 'ok'})


@app.route('/api/expenses/<int:id>', methods=['GET'])
@login_required
def get_expense_detail(id):
    exp = Expense.query.filter_by(id=id, user_id=current_user.id).first()
    return jsonify(exp.to_dict()) if exp else ('', 404)


@app.route('/api/expenses/<int:id>', methods=['PUT'])
@login_required
def update_expense(id):
    exp = Expense.query.filter_by(id=id, user_id=current_user.id).first()
    if not exp:
        return ('', 404)
    data = request.get_json()
    if 'date' in data:
        exp.date = data['date']
    if 'payment' in data:
        exp.payment = data['payment']
    if 'supplier' in data:
        exp.supplier = data['supplier']
    if 'amount' in data:
        exp.amount = float(data['amount'])
    if 'category' in data:
        exp.category = data['category']
    if 'note' in data:
        exp.note = data['note']
    db.session.commit()
    return jsonify(exp.to_dict())


@app.route('/api/expenses/<int:id>', methods=['DELETE'])
@login_required
def delete_expense(id):
    exp = Expense.query.filter_by(id=id, user_id=current_user.id).first()
    if not exp:
        return ('', 404)
    db.session.delete(exp)
    db.session.commit()
    return jsonify({'status': 'ok'})


@app.route('/api/incomes', methods=['GET'])
@login_required
def get_incomes():
    return jsonify([i.to_dict() for i in current_user.incomes])


@app.route('/api/incomes', methods=['POST'])
@login_required
def add_incomes():
    items = request.get_json()
    if not isinstance(items, list):
        items = [items]
    for item in items:
        inc = Income(
            user_id=current_user.id, date=item['date'],
            platform=item.get('platform', ''), shop=item.get('shop', ''),
            amount=float(item['amount']),
            withdraw_date=item.get('withdrawDate', ''),
            withdraw_amount=float(item.get('withdrawAmount', 0)),
            note=item.get('note', '')
        )
        db.session.add(inc)
    db.session.commit()
    return jsonify({'status': 'ok'})


@app.route('/api/incomes/<int:id>', methods=['GET'])
@login_required
def get_income_detail(id):
    inc = Income.query.filter_by(id=id, user_id=current_user.id).first()
    return jsonify(inc.to_dict()) if inc else ('', 404)


@app.route('/api/incomes/<int:id>', methods=['PUT'])
@login_required
def update_income(id):
    inc = Income.query.filter_by(id=id, user_id=current_user.id).first()
    if not inc:
        return ('', 404)
    data = request.get_json()
    if 'date' in data:
        inc.date = data['date']
    if 'platform' in data:
        inc.platform = data['platform']
    if 'shop' in data:
        inc.shop = data['shop']
    if 'amount' in data:
        inc.amount = float(data['amount'])
    if 'withdrawDate' in data:
        inc.withdraw_date = data['withdrawDate']
    if 'withdrawAmount' in data:
        inc.withdraw_amount = float(data['withdrawAmount'])
    if 'note' in data:
        inc.note = data['note']
    db.session.commit()
    return jsonify(inc.to_dict())


@app.route('/api/incomes/<int:id>', methods=['DELETE'])
@login_required
def delete_income(id):
    inc = Income.query.filter_by(id=id, user_id=current_user.id).first()
    if not inc:
        return ('', 404)
    db.session.delete(inc)
    db.session.commit()
    return jsonify({'status': 'ok'})


@app.route('/api/shops', methods=['GET'])
@login_required
def get_shops():
    return jsonify(current_user.get_shops())


@app.route('/api/shops', methods=['POST'])
@login_required
def update_shops():
    data = request.get_json()
    current_user.shops = json.dumps(data) if isinstance(data, dict) else data
    db.session.commit()
    return jsonify({'status': 'ok'})


@app.route('/api/settings', methods=['GET'])
@login_required
def get_settings():
    return jsonify({
        'systemName': current_user.system_name,
        'paymentMethods': current_user.get_payment_methods(),
        'suppliers': current_user.get_suppliers(),
        'expenseCategories': current_user.get_expense_categories(),
        'platforms': current_user.get_platforms(),
        'shops': current_user.get_shops()
    })


@app.route('/api/settings', methods=['POST'])
@login_required
def update_settings():
    data = request.get_json()
    if 'systemName' in data:
        current_user.system_name = data['systemName']
    if 'paymentMethods' in data:
        current_user.payment_methods = json.dumps(data['paymentMethods'])
    if 'suppliers' in data:
        current_user.suppliers = json.dumps(data['suppliers'])
    if 'expenseCategories' in data:
        current_user.expense_categories = json.dumps(data['expenseCategories'])
    if 'platforms' in data:
        current_user.platforms = json.dumps(data['platforms'])
    if 'shops' in data:
        current_user.shops = json.dumps(data['shops'])
    db.session.commit()
    return jsonify({'status': 'ok'})


# ---------- 系统管理 API ----------
@app.route('/api/user/profile', methods=['GET'])
@login_required
def get_profile():
    return jsonify({
        'username': current_user.username,
        'paymentMethods': current_user.serialize_payment_methods(),
        'suppliers': current_user.serialize_suppliers(),
        'expenseCategories': current_user.serialize_expense_categories(),
        'platforms': current_user.serialize_platforms(),
        'shops': current_user.serialize_shops()
    })


@app.route('/api/user/profile', methods=['POST'])
@login_required
def update_profile():
    data = request.get_json()
    if 'username' in data and data['username']:
        existing = User.query.filter_by(username=data['username']).first()
        if existing and existing.id != current_user.id:
            return jsonify({'error': '用户名已存在'}), 400
        current_user.username = data['username']
    if 'paymentMethods' in data:
        current_user.payment_methods = json.dumps(data['paymentMethods'])
    if 'suppliers' in data:
        current_user.suppliers = json.dumps(data['suppliers'])
    if 'expenseCategories' in data:
        current_user.expense_categories = json.dumps(data['expenseCategories'])
    if 'platforms' in data:
        current_user.platforms = json.dumps(data['platforms'])
    if 'shops' in data:
        current_user.shops = json.dumps(data['shops']) if isinstance(data['shops'], dict) else data['shops']
    db.session.commit()
    return jsonify({'status': 'ok'})


@app.route('/api/user/password', methods=['POST'])
@login_required
def change_password():
    data = request.get_json()
    old_pw = data.get('oldPassword')
    new_pw = data.get('newPassword')
    if not check_password_hash(current_user.password_hash, old_pw):
        return jsonify({'error': '原密码错误'}), 400
    if len(new_pw) < 3:
        return jsonify({'error': '新密码至少3位'}), 400
    current_user.password_hash = generate_password_hash(new_pw)
    db.session.commit()
    return jsonify({'status': 'ok'})


@app.route('/api/all-shops', methods=['GET'])
@login_required
def get_all_shops():
    shops_data = current_user.serialize_shops()
    all_shops = []
    for platform, shops in shops_data.items():
        for shop in shops:
            all_shops.append({'platform': platform, 'shop': shop})
    return jsonify(all_shops)


@app.route('/mobile')
@login_required
def mobile():
    return render_template('mobile.html')


# ========== 权限装饰器 ==========
from functools import wraps

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        if current_user.role not in ('superadmin', 'admin'):
            return '无权限访问', 403
        return f(*args, **kwargs)
    return decorated

def superadmin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        if current_user.role != 'superadmin':
            return '仅超级管理员可操作', 403
        return f(*args, **kwargs)
    return decorated


# ========== 用户管理页面 ==========
@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    return render_template('admin_users.html')


# ========== 用户管理 API ==========
@app.route('/admin/api/current-user-role')
@login_required
def current_user_role_api():
    return jsonify({'role': current_user.role, 'username': current_user.username})


@app.route('/admin/api/users')
@login_required
@admin_required
def admin_get_users():
    if current_user.role == 'superadmin':
        users = User.query.all()
    else:
        users = User.query.filter(User.role == 'user').all()
    return jsonify([{
        'id': u.id, 'username': u.username, 'role': u.role
    } for u in users])


@app.route('/admin/api/users', methods=['POST'])
@login_required
@admin_required
def admin_add_user():
    data = request.get_json()
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    role = data.get('role', 'user')

    if not username or not password:
        return jsonify({'error': '用户名和密码不能为空'}), 400
    if len(password) < 3:
        return jsonify({'error': '密码至少3位'}), 400
    if role not in ('user', 'admin'):
        return jsonify({'error': '无效的角色'}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({'error': '用户名已存在'}), 400
    if role == 'admin' and current_user.role != 'superadmin':
        return jsonify({'error': '只有总管理员可以创建管理员'}), 403

    new_user = User(username=username, password_hash=generate_password_hash(password), role=role)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'id': new_user.id, 'username': new_user.username, 'role': new_user.role}), 201


@app.route('/admin/api/users/<int:user_id>', methods=['PUT'])
@login_required
@admin_required
def admin_update_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': '用户不存在'}), 404

    data = request.get_json()
    current_role = current_user.role

    # 不能修改 superadmin
    if user.role == 'superadmin':
        return jsonify({'error': '不能修改总管理员'}), 403
    # admin 只能改普通用户
    if current_role == 'admin' and user.role != 'user':
        return jsonify({'error': '无权操作该用户'}), 403

    if data.get('password'):
        if len(data['password']) < 3:
            return jsonify({'error': '新密码至少3位'}), 400
        user.password_hash = generate_password_hash(data['password'])

    new_role = data.get('role')
    if new_role and new_role != user.role:
        if current_role != 'superadmin':
            return jsonify({'error': '只有总管理员可以修改角色'}), 403
        if new_role not in ('user', 'admin'):
            return jsonify({'error': '无效角色'}), 400
        user.role = new_role

    db.session.commit()
    return jsonify({'id': user.id, 'username': user.username, 'role': user.role})


@app.route('/admin/api/users/<int:user_id>', methods=['DELETE'])
@login_required
@admin_required
def admin_delete_user(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': '用户不存在'}), 404
    if user.id == current_user.id:
        return jsonify({'error': '不能删除自己'}), 400
    if user.role == 'superadmin':
        return jsonify({'error': '不能删除总管理员'}), 403
    if current_user.role == 'admin' and user.role != 'user':
        return jsonify({'error': '无权删除该用户'}), 403

    # 删除用户关联的收支数据
    Expense.query.filter_by(user_id=user.id).delete()
    Income.query.filter_by(user_id=user.id).delete()
    db.session.delete(user)
    db.session.commit()
    return jsonify({'status': 'ok'})


# ========== 数据库迁移 & 初始化超级管理员 ==========
with app.app_context():
    db.create_all()
    # SQLite 兼容：如果 role 列不存在则添加
    try:
        db.session.execute(db.text("SELECT role FROM user LIMIT 1"))
    except:
        db.session.execute(db.text("ALTER TABLE user ADD COLUMN role VARCHAR(20) DEFAULT 'user'"))
        db.session.commit()
    # SQLite 兼容：如果 system_name 列不存在则添加
    try:
        db.session.execute(db.text("SELECT system_name FROM user LIMIT 1"))
    except:
        db.session.execute(db.text("ALTER TABLE user ADD COLUMN system_name VARCHAR(100) DEFAULT '如福财务系统'"))
        db.session.commit()
    # 初始化超级管理员 dandyhair / 123456
    superadmin = User.query.filter_by(username='dandyhair').first()
    if not superadmin:
        sa = User(username='dandyhair', password_hash=generate_password_hash('123456'), role='superadmin')
        db.session.add(sa)
        db.session.commit()
    elif superadmin.role != 'superadmin':
        superadmin.role = 'superadmin'
        superadmin.password_hash = generate_password_hash('123456')
        db.session.commit()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5050))
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    app.run(host='0.0.0.0', port=port, debug=debug)
