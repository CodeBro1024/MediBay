import sqlite3
from flask import Flask, request, render_template, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'SU386MAN1601SI'  # Move this to an environment variable in production


# ── DB init ──────────────────────────────────────────────────────────────────

def init_db():
    # Single DB for everything
    conn = sqlite3.connect('medicines.db')
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
        cursor.executemany(
            'INSERT INTO medicines (formula, name, price, best) VALUES (?, ?, ?, ?)',
            [
                ('paracetamol', 'Dolo 650',  30, 'Dolo 650'),
                ('paracetamol', 'Crocin',    25, 'Dolo 650'),
                ('paracetamol', 'Calpol',    28, 'Dolo 650'),
                ('ibuprofen',   'Brufen',    40, 'Brufen'),
                ('ibuprofen',   'Ibugesic',  35, 'Brufen'),
            ]
        )

    conn.commit()
    conn.close()

init_db()


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_db():
    """Return a connection to the single shared database."""
    return sqlite3.connect('medicines.db')

def admin_required():
    """Return a redirect if the admin is not logged in, else None."""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return None


# ── Admin auth ────────────────────────────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # FIX: keep credentials out of source code – use env vars in production
        if username == 'Subhamds' and password == 'Mondal@2502':
            session['logged_in'] = True
            return redirect(url_for('admin'))
        return "Invalid credentials"
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))


# ── Home / search ─────────────────────────────────────────────────────────────

# FIX: removed the duplicate @app.route('/') def main() that was overriding this
@app.route('/', methods=['GET', 'POST'])
def home():
    user = session.get('user')

    if request.method == 'POST':
        formula = request.form['formula'].lower()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name, price FROM medicines WHERE formula = ?", (formula,)
        )
        results = cursor.fetchall()
        conn.close()
        return render_template('FP.html', results=results, formula=formula, user=user)

    return render_template('FP.html', results=None, user=user)


@app.route('/search', methods=['POST'])
def search():
    if 'user' not in session:
        return redirect(url_for('auth'))

    formula = request.form['formula'].lower()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name, price FROM medicines WHERE formula = ?", (formula,)
    )
    results = cursor.fetchall()
    conn.close()
    return render_template('FP.html', results=results, formula=formula)


# ── Admin panel ───────────────────────────────────────────────────────────────

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    # FIX: protect GET requests too — previously only POST was gated
    guard = admin_required()
    if guard:
        return guard

    if request.method == 'POST':
        formula = request.form['formula'].lower()
        name    = request.form['name']
        price   = request.form['price']

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO medicines (formula, name, price) VALUES (?, ?, ?)',
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

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE medicines SET price = ? WHERE lower(name) = ?", (new_price, name)
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
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM medicines WHERE name = ?", (dawa_name,))
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

        # FIX: use the same DB that init_db() created the users table in
        conn   = get_db()
        cursor = conn.cursor()

        if form_type == 'signup':
            name = request.form['name']
            # FIX: hash the password before storing
            hashed = generate_password_hash(password)
            try:
                cursor.execute(
                    "INSERT INTO users (name, mobile, password) VALUES (?, ?, ?)",
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
                "SELECT password FROM users WHERE mobile = ?", (mobile,)
            )
            row = cursor.fetchone()
            conn.close()

            # FIX: verify hashed password
            if row and check_password_hash(row[0], password):
                session['user'] = mobile
                return redirect('/')
            return "Invalid Login"

    return render_template('signup.html')


@app.route('/out')
def out():
    session.pop('user', None)
    return redirect('/')


if __name__ == '__main__':
    app.run(debug=True)
