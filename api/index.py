import os
import psycopg2
from psycopg2 import pool
from flask import Flask, request, render_template, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

# Database connection pool (Vercel-friendly)
db_pool = None

def get_db():
    global db_pool
    if db_pool is None:
        db_pool = psycopg2.pool.SimpleConnectionPool(
            1, 20, dsn=os.environ['DATABASE_URL']
        )
    return db_pool.getconn()

def return_db(conn):
    db_pool.putconn(conn)

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            name TEXT,
            mobile TEXT UNIQUE,
            password TEXT
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS medicines (
            id SERIAL PRIMARY KEY,
            formula TEXT,
            name TEXT,
            price INTEGER,
            best TEXT
        )
    ''')
    # Insert sample data if empty
    cur.execute("SELECT COUNT(*) FROM medicines")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            'INSERT INTO medicines (formula, name, price, best) VALUES (%s, %s, %s, %s)',
            [
                ('paracetamol', 'Dolo 650',  30, 'Dolo 650'),
                ('paracetamol', 'Crocin',    25, 'Dolo 650'),
                ('paracetamol', 'Calpol',    28, 'Dolo 650'),
                ('ibuprofen',   'Brufen',    40, 'Brufen'),
                ('ibuprofen',   'Ibugesic',  35, 'Brufen'),
            ]
        )
    conn.commit()
    cur.close()
    return_db(conn)

# Call this at startup (Vercel will run it once per cold start)
init_db()

def admin_required():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return None

# ------------------- Routes -------------------
@app.route('/')
def home():
    user = session.get('user')
    return render_template('FP.html', results=None, user=user)

@app.route('/search', methods=['POST'])
def search():
    user = session.get('user')
    if not user:
        return redirect(url_for('auth'))
    formula = request.form['formula'].lower()
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT name, price FROM medicines WHERE formula = %s", (formula,))
    results = cur.fetchall()
    cur.close()
    return_db(conn)
    return render_template('FP.html', results=results, formula=formula, user=user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        admin_user = os.environ.get('ADMIN_USER', 'Subhamds')
        admin_pass = os.environ.get('ADMIN_PASS', 'Mondal@2502')
        if username == admin_user and password == admin_pass:
            session['logged_in'] = True
            return redirect(url_for('admin'))
        return "Invalid credentials"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    guard = admin_required()
    if guard:
        return guard
    if request.method == 'POST':
        formula = request.form['formula'].lower()
        name = request.form['name']
        price = request.form['price']
        conn = get_db()
        cur = conn.cursor()
        cur.execute('INSERT INTO medicines (formula, name, price) VALUES (%s, %s, %s)',
                    (formula, name, price))
        conn.commit()
        cur.close()
        return_db(conn)
        return 'Medicine added successfully!'
    return render_template('admin.html')

@app.route('/update_price', methods=['POST'])
def update_price():
    guard = admin_required()
    if guard:
        return guard
    name = request.form['name'].lower()
    new_price = request.form['price']
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE medicines SET price = %s WHERE LOWER(name) = %s", (new_price, name))
    conn.commit()
    cur.close()
    return_db(conn)
    return "Price updated successfully!"

@app.route('/delete_dawa', methods=['POST'])
def delete_dawa():
    guard = admin_required()
    if guard:
        return guard
    dawa_name = request.form['name']
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM medicines WHERE name = %s", (dawa_name,))
    conn.commit()
    cur.close()
    return_db(conn)
    return "Medicine deleted successfully!"

@app.route('/auth', methods=['GET', 'POST'])
def auth():
    if request.method == 'POST':
        form_type = request.form.get('form_type')
        mobile = request.form['mobile']
        password = request.form['password']
        conn = get_db()
        cur = conn.cursor()
        if form_type == 'signup':
            name = request.form['name']
            hashed = generate_password_hash(password)
            try:
                cur.execute("INSERT INTO users (name, mobile, password) VALUES (%s, %s, %s)",
                            (name, mobile, hashed))
                conn.commit()
                cur.close()
                return_db(conn)
                return redirect('/')
            except Exception as e:
                cur.close()
                return_db(conn)
                return "User already exists"
        elif form_type == 'login':
            cur.execute("SELECT password FROM users WHERE mobile = %s", (mobile,))
            row = cur.fetchone()
            cur.close()
            return_db(conn)
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
    suggestion = request.form['suggestion']
    # For now, just print or store in a suggestions table
    print(f"Suggestion from {session['user']}: {suggestion}")
    return "Thank you for your suggestion!"

if __name__ == '__main__':
    app.run(debug=True)
