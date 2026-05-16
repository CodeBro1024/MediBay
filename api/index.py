import os
import sqlite3
from flask import Flask, request, render_template, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'SU386MAN1601SI')

# ── Database setup ────────────────────────────────────────────────────────────

DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    import psycopg2
    PH = '%s'
    def get_db():
        # Supabase requires SSL
        url = DATABASE_URL if 'sslmode' in DATABASE_URL else DATABASE_URL + '?sslmode=require'
        return psycopg2.connect(url)
else:
    PH = '?'
    def get_db():
        return sqlite3.connect('medicines.db')


def q(sql):
    return sql.replace('?', PH)


# ── DB init ───────────────────────────────────────────────────────────────────
# Only runs locally (SQLite). On Vercel the tables already exist in Supabase
# from running migrate.py, so we skip init to avoid crashing the serverless boot.

if not DATABASE_URL:
    conn   = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            name     TEXT,
            mobile   TEXT UNIQUE,
            password TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS medicines (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            formula TEXT,
            name    TEXT,
            price   INTEGER,
            best    TEXT
        )
    ''')
    cursor.execute("SELECT COUNT(*) FROM medicines")
    if cursor.fetchone()[0] == 0:
        for row in [
            ('paracetamol', 'Dolo 650',  30, 'Dolo 650'),
            ('paracetamol', 'Crocin',    25, 'Dolo 650'),
            ('paracetamol', 'Calpol',    28, 'Dolo 650'),
            ('ibuprofen',   'Brufen',    40, 'Brufen'),
            ('ibuprofen',   'Ibugesic',  35, 'Brufen'),
        ]:
            cursor.execute(
                'INSERT INTO medicines (formula, name, price, best) VALUES (?, ?, ?, ?)', row
            )
    conn.commit()
    conn.close()


# ── Helpers ───────────────────────────────────────────────────────────────────

ADMIN_USER = os.environ.get('ADMIN_USERNAME', 'Subhamds')
ADMIN_PASS = os.environ.get('ADMIN_PASSWORD', 'Mondal@2502')

def admin_required():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return None


# ── Admin auth ────────────────────────────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if (request.form['username'] == ADMIN_USER and
                request.form['password'] == ADMIN_PASS):
            session['logged_in'] = True
            return redirect(url_for('admin'))
        return "Invalid credentials"
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))


# ── Home ──────────────────────────────────────────────────────────────────────

@app.route('/', methods=['GET', 'POST'])
def home():
    user = session.get('user')
    if request.method == 'POST':
        formula = request.form['formula'].lower()
        conn    = get_db()
        cursor  = conn.cursor()
        cursor.execute(q("SELECT name, price FROM medicines WHERE formula = ?"), (formula,))
        results = cursor.fetchall()
        conn.close()
        return render_template('fp.html', results=results, formula=formula, user=user)
    return render_template('fp.html', results=None, user=user)


@app.route('/search', methods=['POST'])
def search():
    if 'user' not in session:
        return redirect(url_for('auth'))
    formula = request.form['formula'].lower()
    conn    = get_db()
    cursor  = conn.cursor()
    cursor.execute(q("SELECT name, price FROM medicines WHERE formula = ?"), (formula,))
    results = cursor.fetchall()
    conn.close()
    user = session.get('user')
    return render_template('fp.html', results=results, formula=formula, user=user)


# ── Admin panel ───────────────────────────────────────────────────────────────

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    guard = admin_required()
    if guard:
        return guard
    if request.method == 'POST':
        formula = request.form['formula'].lower()
        name    = request.form['name']
        price   = request.form['price']
        conn    = get_db()
        cursor  = conn.cursor()
        cursor.execute(
            q('INSERT INTO medicines (formula, name, price) VALUES (?, ?, ?)'),
            (formula, name, price)
        )
        conn.commit()
        conn.close()
        return 'Medicine added successfully!'
    return render_template('admin.html')


@app.route('/update_price', methods=['POST'])
def update_price():
    guard = admin_required()
    if guard:
        return guard
    name      = request.form['name'].lower()
    new_price = request.form['price']
    conn      = get_db()
    cursor    = conn.cursor()
    cursor.execute(
        q("UPDATE medicines SET price = ? WHERE lower(name) = ?"),
        (new_price, name)
    )
    conn.commit()
    conn.close()
    return "Price updated successfully!"


@app.route('/delete_dawa', methods=['POST'])
def delete_dawa():
    guard = admin_required()
    if guard:
        return guard
    dawa_name = request.form['name']
    conn      = get_db()
    cursor    = conn.cursor()
    cursor.execute(q("DELETE FROM medicines WHERE name = ?"), (dawa_name,))
    conn.commit()
    conn.close()
    return "Medicine deleted successfully!"


# ── User auth ─────────────────────────────────────────────────────────────────

@app.route('/auth', methods=['GET', 'POST'])
def auth():
    if request.method == 'POST':
        form_type = request.form.get('form_type')
        mobile    = request.form['mobile']
        password  = request.form['password']
        conn      = get_db()
        cursor    = conn.cursor()

        if form_type == 'signup':
            name   = request.form['name']
            hashed = generate_password_hash(password)
            try:
                cursor.execute(
                    q("INSERT INTO users (name, mobile, password) VALUES (?, ?, ?)"),
                    (name, mobile, hashed)
                )
                conn.commit()
                conn.close()
                return redirect('/')
            except Exception:
                conn.close()
                return "User already exists"

        elif form_type == 'login':
            cursor.execute(
                q("SELECT password FROM users WHERE mobile = ?"), (mobile,)
            )
            row = cursor.fetchone()
            conn.close()
            if row and check_password_hash(row[0], password):
                session['user'] = mobile
                return redirect('/')
            return "Invalid Login"

    return render_template('signup.html')


@app.route('/out')
def out():
    session.pop('user', None)
    return redirect('/')


@app.route('/submit_suggestion', methods=['POST'])
def submit_suggestion():
    if 'user' not in session:
        return redirect(url_for('auth'))
    suggestion = request.form.get('suggestion', '').strip()
    if suggestion:
        conn   = get_db()
        cursor = conn.cursor()
        if DATABASE_URL:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS suggestions (
                    id         SERIAL PRIMARY KEY,
                    mobile     TEXT,
                    suggestion TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            ''')
        else:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS suggestions (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    mobile     TEXT,
                    suggestion TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
        cursor.execute(
            q("INSERT INTO suggestions (mobile, suggestion) VALUES (?, ?)"),
            (session['user'], suggestion)
        )
        conn.commit()
        conn.close()
    return redirect('/')
