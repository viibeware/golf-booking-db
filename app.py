import os
import io
import csv
import secrets
from datetime import datetime, date
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for, flash,
    session, jsonify, send_file, make_response, g
)
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['DATABASE'] = os.environ.get('DATABASE', '/data/golf_booking_db.db')
app.config['DEFAULT_ADMIN_USER'] = os.environ.get('DEFAULT_ADMIN_USER', 'admin')
app.config['DEFAULT_ADMIN_PASS'] = os.environ.get('DEFAULT_ADMIN_PASS', 'admin')

@app.after_request
def add_no_cache_headers(response):
    if 'text/html' in response.content_type:
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

# ─── Database helpers ───────────────────────────────────────────────

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    db.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'viewer',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            intake_number TEXT UNIQUE,
            bkg_number TEXT,
            date_of_call DATE,
            year TEXT,
            group_name TEXT,
            contact_name TEXT,
            contact_phone TEXT,
            contact_email TEXT,
            num_golfers INTEGER,
            preferred_date DATE,
            preferred_arrival DATE,
            preferred_departure DATE,
            second_option_date DATE,
            second_arrival DATE,
            second_departure DATE,
            golfed_before INTEGER DEFAULT 0,
            prior_group_name TEXT,
            breakfast TEXT,
            accommodation TEXT,
            jpc TEXT,
            jones_rounds TEXT,
            palmer_rounds TEXT,
            crispin_rounds TEXT,
            address TEXT,
            billing_method TEXT,
            golf_last_year TEXT,
            budget TEXT,
            pickup TEXT,
            notes TEXT,
            archived INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by INTEGER,
            FOREIGN KEY (created_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS tee_times (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id INTEGER NOT NULL,
            tee_date DATE,
            sort_order INTEGER DEFAULT 0,
            FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS tee_time_slots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tee_time_id INTEGER NOT NULL,
            course TEXT,
            tee_time TEXT,
            hour INTEGER,
            minute INTEGER,
            ampm TEXT,
            num_holes TEXT,
            slot_notes TEXT,
            sort_order INTEGER DEFAULT 0,
            FOREIGN KEY (tee_time_id) REFERENCES tee_times(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_bookings_archived ON bookings(archived);
        CREATE INDEX IF NOT EXISTS idx_bookings_group ON bookings(group_name);
        CREATE INDEX IF NOT EXISTS idx_bookings_bkg ON bookings(bkg_number);
    ''')

    # ─── Migrations for existing databases ───
    # Check which columns exist and add any missing ones
    existing_cols = {row[1] for row in db.execute("PRAGMA table_info(bookings)").fetchall()}
    migrations = {
        'intake_number': "ALTER TABLE bookings ADD COLUMN intake_number TEXT",
        'contact_phone': "ALTER TABLE bookings ADD COLUMN contact_phone TEXT",
        'contact_email': "ALTER TABLE bookings ADD COLUMN contact_email TEXT",
        'jpc': "ALTER TABLE bookings ADD COLUMN jpc TEXT",
        'jones_rounds': "ALTER TABLE bookings ADD COLUMN jones_rounds TEXT",
        'palmer_rounds': "ALTER TABLE bookings ADD COLUMN palmer_rounds TEXT",
        'crispin_rounds': "ALTER TABLE bookings ADD COLUMN crispin_rounds TEXT",
        'preferred_arrival': "ALTER TABLE bookings ADD COLUMN preferred_arrival DATE",
        'preferred_departure': "ALTER TABLE bookings ADD COLUMN preferred_departure DATE",
        'second_arrival': "ALTER TABLE bookings ADD COLUMN second_arrival DATE",
        'second_departure': "ALTER TABLE bookings ADD COLUMN second_departure DATE",
    }
    for col, sql in migrations.items():
        if col not in existing_cols:
            try:
                db.execute(sql)
            except sqlite3.OperationalError:
                pass

    # Migrate tee_time_slots table
    slot_cols = {row[1] for row in db.execute("PRAGMA table_info(tee_time_slots)").fetchall()}
    slot_migrations = {
        'course': "ALTER TABLE tee_time_slots ADD COLUMN course TEXT",
        'tee_time': "ALTER TABLE tee_time_slots ADD COLUMN tee_time TEXT",
        'slot_notes': "ALTER TABLE tee_time_slots ADD COLUMN slot_notes TEXT",
    }
    for col, sql in slot_migrations.items():
        if col not in slot_cols:
            try:
                db.execute(sql)
            except sqlite3.OperationalError:
                pass

    # Ensure intake_number index exists
    try:
        db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_bookings_intake ON bookings(intake_number)")
    except sqlite3.OperationalError:
        pass

    # Backfill intake numbers for any existing records that don't have one
    rows_without = db.execute(
        "SELECT id FROM bookings WHERE intake_number IS NULL OR intake_number = '' ORDER BY id"
    ).fetchall()
    if rows_without:
        # Find the current max intake number
        max_row = db.execute(
            "SELECT intake_number FROM bookings WHERE intake_number LIKE 'GBD%' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        next_num = 1001
        if max_row and max_row['intake_number']:
            try:
                next_num = int(max_row['intake_number'].replace('GBD', '')) + 1
            except ValueError:
                pass
        for row in rows_without:
            db.execute("UPDATE bookings SET intake_number=? WHERE id=?", (f'GBD{next_num}', row['id']))
            next_num += 1

    # Create default admin if none exists
    existing = db.execute('SELECT id FROM users LIMIT 1').fetchone()
    if not existing:
        db.execute(
            'INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
            (app.config['DEFAULT_ADMIN_USER'],
             generate_password_hash(app.config['DEFAULT_ADMIN_PASS']),
             'admin')
        )
    db.commit()

# ─── Auth decorators ────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in.', 'warning')
                return redirect(url_for('login'))
            if session.get('user_role') not in roles:
                flash('You do not have permission to perform this action.', 'danger')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated
    return decorator

# ─── Context processor ──────────────────────────────────────────────

@app.context_processor
def inject_user():
    ctx = {
        'current_user': {
            'id': session.get('user_id'),
            'username': session.get('username'),
            'role': session.get('user_role')
        } if 'user_id' in session else None,
        'recent_intakes': []
    }
    if 'user_id' in session:
        try:
            db = get_db()
            if session.get('user_role') == 'admin':
                ctx['recent_intakes'] = db.execute(
                    'SELECT id, intake_number, group_name, updated_at FROM bookings WHERE archived=0 ORDER BY updated_at DESC LIMIT 8'
                ).fetchall()
            else:
                ctx['recent_intakes'] = db.execute(
                    'SELECT id, intake_number, group_name, updated_at FROM bookings WHERE archived=0 AND created_by=? ORDER BY updated_at DESC LIMIT 8',
                    (session.get('user_id'),)
                ).fetchall()
        except Exception:
            pass
    return ctx

# ─── Auth routes ────────────────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['user_role'] = user['role']
            flash(f'Welcome back, {user["username"]}!', 'success')
            return redirect(url_for('index'))
        flash('Invalid username or password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# ─── User management ───────────────────────────────────────────────

@app.route('/users')
@role_required('admin')
def users():
    db = get_db()
    all_users = db.execute('SELECT * FROM users ORDER BY username').fetchall()
    return render_template('users.html', users=all_users)

@app.route('/api/users')
@role_required('admin')
def api_users():
    db = get_db()
    all_users = db.execute('SELECT id, username, role, created_at FROM users ORDER BY username').fetchall()
    return jsonify([dict(u) for u in all_users])

def _settings_redirect():
    """Redirect back to the referring page with settings modal open."""
    referer = request.referrer or url_for('index')
    sep = '&' if '?' in referer else '?'
    # Strip any existing settings param to avoid duplication
    if 'settings=1' in referer:
        return redirect(referer)
    return redirect(referer + sep + 'settings=1')

@app.route('/users/add', methods=['POST'])
@role_required('admin')
def add_user():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    role = request.form.get('role', 'viewer')
    if not username or not password:
        flash('Username and password are required.', 'danger')
        return _settings_redirect()
    db = get_db()
    try:
        db.execute(
            'INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
            (username, generate_password_hash(password), role)
        )
        db.commit()
        flash(f'User "{username}" created.', 'success')
    except sqlite3.IntegrityError:
        flash(f'Username "{username}" already exists.', 'danger')
    return _settings_redirect()

@app.route('/users/<int:user_id>/edit', methods=['POST'])
@role_required('admin')
def edit_user(user_id):
    role = request.form.get('role', 'viewer')
    password = request.form.get('password', '').strip()
    db = get_db()
    if password:
        db.execute('UPDATE users SET role=?, password_hash=? WHERE id=?',
                    (role, generate_password_hash(password), user_id))
    else:
        db.execute('UPDATE users SET role=? WHERE id=?', (role, user_id))
    db.commit()
    flash('User updated.', 'success')
    return _settings_redirect()

@app.route('/users/<int:user_id>/delete', methods=['POST'])
@role_required('admin')
def delete_user(user_id):
    if user_id == session.get('user_id'):
        flash('You cannot delete your own account.', 'danger')
        return _settings_redirect()
    db = get_db()
    db.execute('DELETE FROM users WHERE id=?', (user_id,))
    db.commit()
    flash('User deleted.', 'success')
    return _settings_redirect()

# ─── Intake helpers ────────────────────────────────────────────────

def generate_intake_number(db):
    """Generate the next intake number: GBD1001, GBD1002, etc."""
    row = db.execute(
        "SELECT intake_number FROM bookings WHERE intake_number LIKE 'GBD%' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if row and row['intake_number']:
        try:
            last_num = int(row['intake_number'].replace('GBD', ''))
            return f'GBD{last_num + 1}'
        except ValueError:
            pass
    return 'GBD1001'

def save_tee_times(db, booking_id, form_data):
    """Parse and save tee times from form data."""
    # Delete existing
    db.execute('DELETE FROM tee_time_slots WHERE tee_time_id IN (SELECT id FROM tee_times WHERE booking_id=?)', (booking_id,))
    db.execute('DELETE FROM tee_times WHERE booking_id=?', (booking_id,))

    # Parse tee time days
    day_index = 0
    while True:
        date_key = f'tee_day_date_{day_index}'
        if date_key not in form_data:
            break
        tee_date = form_data.get(date_key, '')
        if tee_date:
            cursor = db.execute(
                'INSERT INTO tee_times (booking_id, tee_date, sort_order) VALUES (?, ?, ?)',
                (booking_id, tee_date, day_index)
            )
            tee_time_id = cursor.lastrowid

            # Parse slots for this day
            slot_index = 0
            while True:
                course_key = f'tee_slot_course_{day_index}_{slot_index}'
                if course_key not in form_data:
                    break
                course = form_data.get(course_key, '')
                tee_time_val = form_data.get(f'tee_slot_time_{day_index}_{slot_index}', '')
                ampm = form_data.get(f'tee_slot_ampm_{day_index}_{slot_index}', '')
                holes = form_data.get(f'tee_slot_holes_{day_index}_{slot_index}', '')
                slot_notes = form_data.get(f'tee_slot_notes_{day_index}_{slot_index}', '')
                if course or tee_time_val:
                    db.execute(
                        'INSERT INTO tee_time_slots (tee_time_id, course, tee_time, ampm, num_holes, slot_notes, sort_order) VALUES (?, ?, ?, ?, ?, ?, ?)',
                        (tee_time_id, course, tee_time_val, ampm, holes, slot_notes.strip(), slot_index)
                    )
                slot_index += 1
        day_index += 1

def get_booking_with_tees(db, booking_id):
    booking = db.execute('SELECT * FROM bookings WHERE id=?', (booking_id,)).fetchone()
    if not booking:
        return None, []
    tee_days = db.execute('SELECT * FROM tee_times WHERE booking_id=? ORDER BY sort_order', (booking_id,)).fetchall()
    tee_data = []
    for day in tee_days:
        slots = db.execute('SELECT * FROM tee_time_slots WHERE tee_time_id=? ORDER BY sort_order', (day['id'],)).fetchall()
        tee_data.append({'day': day, 'slots': slots})
    return booking, tee_data

# ─── Main routes ────────────────────────────────────────────────────

def can_access_booking(booking):
    """Check if current user can access a booking. Admins see all, editors see own."""
    if session.get('user_role') == 'admin':
        return True
    return booking['created_by'] == session.get('user_id')

@app.route('/')
@login_required
def index():
    db = get_db()
    search = request.args.get('q', '').strip()
    sort = request.args.get('sort', 'date_of_call')
    order = request.args.get('order', 'desc')
    show_archived = request.args.get('archived', '0') == '1'

    valid_sorts = ['intake_number', 'bkg_number', 'date_of_call', 'group_name', 'contact_name', 'num_golfers', 'preferred_date', 'created_at']
    if sort not in valid_sorts:
        sort = 'date_of_call'
    if order not in ('asc', 'desc'):
        order = 'desc'

    query = 'SELECT * FROM bookings WHERE archived=?'
    params = [1 if show_archived else 0]

    # Editors only see their own records
    if session.get('user_role') != 'admin':
        query += ' AND created_by=?'
        params.append(session.get('user_id'))

    if search:
        query += ''' AND (
            bkg_number LIKE ? OR group_name LIKE ? OR contact_name LIKE ?
            OR address LIKE ? OR notes LIKE ? OR prior_group_name LIKE ?
            OR golf_last_year LIKE ? OR pickup LIKE ?
            OR intake_number LIKE ?
        )'''
        like = f'%{search}%'
        params.extend([like] * 9)

    query += f' ORDER BY {sort} {order}'
    bookings = db.execute(query, params).fetchall()

    return render_template('index.html', bookings=bookings, search=search,
                           sort=sort, order=order, show_archived=show_archived)

@app.route('/bookings/new', methods=['GET', 'POST'])
@role_required('admin', 'editor')
def new_booking():
    if request.method == 'POST':
        db = get_db()
        breakfast_vals = request.form.getlist('breakfast')
        breakfast = ','.join(breakfast_vals) if breakfast_vals else ''
        accommodation_vals = request.form.getlist('accommodation')
        accommodation = ','.join(accommodation_vals) if accommodation_vals else ''
        jpc_vals = request.form.getlist('jpc')
        jpc = ','.join(jpc_vals) if jpc_vals else ''

        intake_number = generate_intake_number(db)

        cursor = db.execute('''
            INSERT INTO bookings (
                intake_number, bkg_number, date_of_call, year, group_name, contact_name,
                contact_phone, contact_email,
                num_golfers, preferred_date, preferred_arrival, preferred_departure,
                second_option_date, second_arrival, second_departure,
                golfed_before, prior_group_name, breakfast, accommodation,
                jpc, address, billing_method, golf_last_year, budget, pickup, notes,
                jones_rounds, palmer_rounds, crispin_rounds,
                created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            intake_number,
            request.form.get('bkg_number', '').strip(),
            request.form.get('date_of_call', date.today().isoformat()),
            request.form.get('year', '').strip(),
            request.form.get('group_name', '').strip(),
            request.form.get('contact_name', '').strip(),
            request.form.get('contact_phone', '').strip(),
            request.form.get('contact_email', '').strip(),
            request.form.get('num_golfers', 0, type=int),
            request.form.get('preferred_date', ''),
            request.form.get('preferred_arrival', ''),
            request.form.get('preferred_departure', ''),
            request.form.get('second_option_date', ''),
            request.form.get('second_arrival', ''),
            request.form.get('second_departure', ''),
            1 if request.form.get('golfed_before') == 'yes' else 0,
            request.form.get('prior_group_name', '').strip(),
            breakfast, accommodation, jpc,
            request.form.get('address', '').strip(),
            request.form.get('billing_method', ''),
            request.form.get('golf_last_year', '').strip(),
            request.form.get('budget', '').strip(),
            request.form.get('pickup', '').strip(),
            request.form.get('notes', '').strip(),
            request.form.get('jones_rounds', '').strip(),
            request.form.get('palmer_rounds', '').strip(),
            request.form.get('crispin_rounds', '').strip(),
            session.get('user_id')
        ))
        booking_id = cursor.lastrowid
        save_tee_times(db, booking_id, request.form)
        db.commit()
        flash('Intake created successfully.', 'success')
        return redirect(url_for('view_booking', booking_id=booking_id))

    return render_template('booking_form.html', booking=None, tee_data=[], mode='new', today=date.today().isoformat())

@app.route('/bookings/<int:booking_id>')
@login_required
def view_booking(booking_id):
    db = get_db()
    booking, tee_data = get_booking_with_tees(db, booking_id)
    if not booking:
        flash('Intake not found.', 'danger')
        return redirect(url_for('index'))
    if not can_access_booking(booking):
        flash('You do not have access to this record.', 'danger')
        return redirect(url_for('index'))
    return render_template('view_booking.html', booking=booking, tee_data=tee_data)

@app.route('/bookings/<int:booking_id>/edit', methods=['GET', 'POST'])
@role_required('admin', 'editor')
def edit_booking(booking_id):
    db = get_db()
    # Check ownership before allowing edit
    check = db.execute('SELECT * FROM bookings WHERE id=?', (booking_id,)).fetchone()
    if not check:
        flash('Intake not found.', 'danger')
        return redirect(url_for('index'))
    if not can_access_booking(check):
        flash('You do not have access to this record.', 'danger')
        return redirect(url_for('index'))
    if request.method == 'POST':
        breakfast_vals = request.form.getlist('breakfast')
        breakfast = ','.join(breakfast_vals) if breakfast_vals else ''
        accommodation_vals = request.form.getlist('accommodation')
        accommodation = ','.join(accommodation_vals) if accommodation_vals else ''
        jpc_vals = request.form.getlist('jpc')
        jpc = ','.join(jpc_vals) if jpc_vals else ''

        db.execute('''
            UPDATE bookings SET
                bkg_number=?, date_of_call=?, year=?, group_name=?, contact_name=?,
                contact_phone=?, contact_email=?,
                num_golfers=?, preferred_date=?, preferred_arrival=?, preferred_departure=?,
                second_option_date=?, second_arrival=?, second_departure=?,
                golfed_before=?, prior_group_name=?, breakfast=?, accommodation=?,
                jpc=?, address=?, billing_method=?, golf_last_year=?, budget=?, pickup=?, notes=?,
                jones_rounds=?, palmer_rounds=?, crispin_rounds=?,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=?
        ''', (
            request.form.get('bkg_number', '').strip(),
            request.form.get('date_of_call', ''),
            request.form.get('year', '').strip(),
            request.form.get('group_name', '').strip(),
            request.form.get('contact_name', '').strip(),
            request.form.get('contact_phone', '').strip(),
            request.form.get('contact_email', '').strip(),
            request.form.get('num_golfers', 0, type=int),
            request.form.get('preferred_date', ''),
            request.form.get('preferred_arrival', ''),
            request.form.get('preferred_departure', ''),
            request.form.get('second_option_date', ''),
            request.form.get('second_arrival', ''),
            request.form.get('second_departure', ''),
            1 if request.form.get('golfed_before') == 'yes' else 0,
            request.form.get('prior_group_name', '').strip(),
            breakfast, accommodation, jpc,
            request.form.get('address', '').strip(),
            request.form.get('billing_method', ''),
            request.form.get('golf_last_year', '').strip(),
            request.form.get('budget', '').strip(),
            request.form.get('pickup', '').strip(),
            request.form.get('notes', '').strip(),
            request.form.get('jones_rounds', '').strip(),
            request.form.get('palmer_rounds', '').strip(),
            request.form.get('crispin_rounds', '').strip(),
            booking_id
        ))
        save_tee_times(db, booking_id, request.form)
        db.commit()
        flash('Intake updated successfully.', 'success')
        return redirect(url_for('view_booking', booking_id=booking_id))

    booking, tee_data = get_booking_with_tees(db, booking_id)
    if not booking:
        flash('Intake not found.', 'danger')
        return redirect(url_for('index'))
    return render_template('booking_form.html', booking=booking, tee_data=tee_data, mode='edit', today=date.today().isoformat())

@app.route('/bookings/<int:booking_id>/delete', methods=['POST'])
@role_required('admin')
def delete_booking(booking_id):
    db = get_db()
    check = db.execute('SELECT * FROM bookings WHERE id=?', (booking_id,)).fetchone()
    if check and not can_access_booking(check):
        flash('You do not have access to this record.', 'danger')
        return redirect(url_for('index'))
    db.execute('DELETE FROM bookings WHERE id=?', (booking_id,))
    db.commit()
    flash('Intake deleted.', 'success')
    return redirect(url_for('index'))

@app.route('/bookings/<int:booking_id>/archive', methods=['POST'])
@role_required('admin', 'editor')
def archive_booking(booking_id):
    db = get_db()
    booking = db.execute('SELECT * FROM bookings WHERE id=?', (booking_id,)).fetchone()
    if booking:
        if not can_access_booking(booking):
            flash('You do not have access to this record.', 'danger')
            return redirect(url_for('index'))
        new_status = 0 if booking['archived'] else 1
        db.execute('UPDATE bookings SET archived=? WHERE id=?', (new_status, booking_id))
        db.commit()
        action = 'archived' if new_status else 'restored'
        flash(f'Intake {action}.', 'success')
    return redirect(url_for('index'))

@app.route('/bookings/archive-bulk', methods=['POST'])
@role_required('admin', 'editor')
def archive_bulk():
    ids = request.form.getlist('booking_ids')
    action = request.form.get('action', 'archive')
    if ids:
        db = get_db()
        val = 1 if action == 'archive' else 0
        placeholders = ','.join(['?'] * len(ids))
        db.execute(f'UPDATE bookings SET archived=? WHERE id IN ({placeholders})', [val] + ids)
        db.commit()
        flash(f'{len(ids)} intake(s) {"archived" if val else "restored"}.', 'success')
    return redirect(url_for('index', archived='1' if action == 'restore' else '0'))

# ─── Print view ─────────────────────────────────────────────────────

@app.route('/bookings/<int:booking_id>/print')
@login_required
def print_booking(booking_id):
    db = get_db()
    booking, tee_data = get_booking_with_tees(db, booking_id)
    if not booking:
        flash('Intake not found.', 'danger')
        return redirect(url_for('index'))
    if not can_access_booking(booking):
        flash('You do not have access to this record.', 'danger')
        return redirect(url_for('index'))
    return render_template('print_booking.html', booking=booking, tee_data=tee_data)

# ─── PDF export ─────────────────────────────────────────────────────

@app.route('/bookings/<int:booking_id>/pdf')
@login_required
def export_pdf(booking_id):
    db = get_db()
    booking, tee_data = get_booking_with_tees(db, booking_id)
    if not booking:
        flash('Intake not found.', 'danger')
        return redirect(url_for('index'))
    if not can_access_booking(booking):
        flash('You do not have access to this record.', 'danger')
        return redirect(url_for('index'))

    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch,
                                leftMargin=0.6*inch, rightMargin=0.6*inch)
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle('CustomTitle', parent=styles['Title'], fontSize=14, spaceAfter=2, textColor=colors.HexColor('#1e40af'))
        heading_style = ParagraphStyle('CustomHeading', parent=styles['Heading2'], fontSize=10, textColor=colors.HexColor('#1e40af'), spaceBefore=8, spaceAfter=3)
        normal_style = ParagraphStyle('CustomNormal', parent=styles['Normal'], fontSize=8.5, leading=11)
        label_style = ParagraphStyle('Label', parent=styles['Normal'], fontSize=7.5, textColor=colors.HexColor('#666666'))

        story = []
        story.append(Paragraph('Golf Booking Database', title_style))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#3b82f6')))
        story.append(Spacer(1, 6))

        page_width = letter[0] - 1.2*inch

        def add_field(label, value):
            data = [[Paragraph(f'<b>{label}</b>', label_style), Paragraph(str(value or '—'), normal_style)]]
            t = Table(data, colWidths=[1.4*inch, page_width - 1.4*inch])
            t.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 1),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ]))
            story.append(t)

        def add_field_pair(label1, value1, label2, value2):
            half = page_width / 2
            data = [[
                Paragraph(f'<b>{label1}</b>', label_style),
                Paragraph(str(value1 or '—'), normal_style),
                Paragraph(f'<b>{label2}</b>', label_style),
                Paragraph(str(value2 or '—'), normal_style),
            ]]
            t = Table(data, colWidths=[1.1*inch, half - 1.1*inch, 1.1*inch, half - 1.1*inch])
            t.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 1),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ]))
            story.append(t)

        story.append(Paragraph('Intake Information', heading_style))
        add_field_pair('Intake #', booking['intake_number'], 'BKG Number', booking['bkg_number'])
        add_field_pair('Date of Call', booking['date_of_call'], 'Year', booking['year'])
        add_field_pair('Group Name', booking['group_name'], 'Golfers', booking['num_golfers'])
        add_field_pair('Contact', booking['contact_name'], 'Phone', booking['contact_phone'])
        add_field('Email', booking['contact_email'])

        story.append(Paragraph('Dates & Preferences', heading_style))
        add_field_pair('Pref. Arrival', booking['preferred_arrival'], 'Pref. Departure', booking['preferred_departure'])
        add_field_pair('2nd Arrival', booking['second_arrival'], '2nd Departure', booking['second_departure'])
        golfed = 'Yes' if booking['golfed_before'] else 'No'
        if booking['golfed_before']:
            add_field_pair('Golfed Before?', golfed, 'Prior Group', booking['prior_group_name'])
        else:
            add_field_pair('Golfed Before?', golfed, '', '')
        add_field_pair('Breakfast', booking['breakfast'], 'Accommodation', booking['accommodation'])

        if booking['jpc']:
            story.append(Paragraph('Courses', heading_style))
            courses = booking['jpc'].split(',')
            course_map = {'J': ('Jones', booking['jones_rounds']), 'P': ('Palmer', booking['palmer_rounds']), 'C': ('Crispin', booking['crispin_rounds'])}
            for code in courses:
                if code in course_map:
                    name, rounds = course_map[code]
                    add_field(name, f"{rounds or '—'} rounds")

        if tee_data:
            story.append(Paragraph('Tee Times', heading_style))
            for td in tee_data:
                day = td['day']
                if day['tee_date']:
                    try:
                        d = datetime.strptime(day['tee_date'], '%Y-%m-%d')
                        date_str = d.strftime('%a, %b %d, %Y')
                    except:
                        date_str = day['tee_date']
                else:
                    date_str = '—'
                slots_parts = []
                for s in td['slots']:
                    part = f"{s['course'] or ''} {s['tee_time'] or ''} {s['ampm'] or ''}"
                    if s['num_holes']:
                        part += f" ({s['num_holes']}h)"
                    if s['slot_notes']:
                        part += f" - {s['slot_notes']}"
                    slots_parts.append(part.strip())
                add_field(date_str, ' | '.join(slots_parts))

        story.append(Paragraph('Additional Details', heading_style))
        add_field_pair('Address', booking['address'], 'Billing', booking['billing_method'])
        add_field_pair('Golfed Last Year', booking['golf_last_year'], 'Budget', booking['budget'])
        add_field('Pickup', booking['pickup'])
        if booking['notes']:
            add_field('Notes', booking['notes'])

        doc.build(story)
        buf.seek(0)
        filename = f"{booking['intake_number'] or 'intake_' + str(booking_id)}.pdf"
        return send_file(buf, as_attachment=True, download_name=filename, mimetype='application/pdf')
    except ImportError:
        flash('PDF generation requires reportlab. Install it with: pip install reportlab', 'danger')
        return redirect(url_for('view_booking', booking_id=booking_id))

# ─── CSV import/export ──────────────────────────────────────────────

CSV_FIELDS = [
    'intake_number', 'bkg_number', 'date_of_call', 'year', 'group_name', 'contact_name',
    'contact_phone', 'contact_email',
    'num_golfers', 'preferred_date', 'second_option_date', 'golfed_before',
    'prior_group_name', 'breakfast', 'accommodation', 'jpc', 'address',
    'billing_method', 'golf_last_year', 'budget', 'pickup', 'notes',
    'jones_rounds', 'palmer_rounds', 'crispin_rounds', 'archived'
]

@app.route('/export/csv')
@login_required
def export_csv():
    db = get_db()
    show_archived = request.args.get('archived', '0') == '1'
    export_all = request.args.get('all', '0') == '1'

    if export_all:
        # Export all records (active + archived)
        if session.get('user_role') == 'admin':
            bookings = db.execute('SELECT * FROM bookings ORDER BY date_of_call DESC').fetchall()
        else:
            bookings = db.execute('SELECT * FROM bookings WHERE created_by=? ORDER BY date_of_call DESC',
                                  (session.get('user_id'),)).fetchall()
        filename_label = 'all'
    else:
        if session.get('user_role') == 'admin':
            bookings = db.execute('SELECT * FROM bookings WHERE archived=? ORDER BY date_of_call DESC',
                                  (1 if show_archived else 0,)).fetchall()
        else:
            bookings = db.execute('SELECT * FROM bookings WHERE archived=? AND created_by=? ORDER BY date_of_call DESC',
                                  (1 if show_archived else 0, session.get('user_id'))).fetchall()
        filename_label = 'archived' if show_archived else 'active'

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDS + ['tee_times'])
    writer.writeheader()
    for b in bookings:
        row = {k: b[k] for k in CSV_FIELDS}
        # Serialize tee times
        tees = db.execute('SELECT * FROM tee_times WHERE booking_id=? ORDER BY sort_order', (b['id'],)).fetchall()
        tee_strs = []
        for t in tees:
            slots = db.execute('SELECT * FROM tee_time_slots WHERE tee_time_id=? ORDER BY sort_order', (t['id'],)).fetchall()
            slot_strs = []
            for s in slots:
                slot_strs.append(f"{s['hour']}:{str(s['minute']).zfill(2) if s['minute'] is not None else '00'}{s['ampm']}({s['num_holes']}holes)")
            tee_strs.append(f"{t['tee_date']}[{';'.join(slot_strs)}]")
        row['tee_times'] = '|'.join(tee_strs)
        writer.writerow(row)

    output.seek(0)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        as_attachment=True,
        download_name=f'golf_bookings_{filename_label}_{timestamp}.csv',
        mimetype='text/csv'
    )

@app.route('/import/csv', methods=['POST'])
@role_required('admin', 'editor')
def import_csv():
    file = request.files.get('csv_file')
    if not file or not file.filename.endswith('.csv'):
        flash('Please upload a valid CSV file.', 'danger')
        return _settings_redirect()

    import_to = request.form.get('import_to', 'active')
    archive_val = 1 if import_to == 'archived' else 0

    db = get_db()
    content = file.read().decode('utf-8')
    reader = csv.DictReader(io.StringIO(content))
    count = 0
    for row in reader:
        try:
            intake_number = generate_intake_number(db)
            cursor = db.execute('''
                INSERT INTO bookings (
                    intake_number, bkg_number, date_of_call, year, group_name, contact_name,
                    contact_phone, contact_email,
                    num_golfers, preferred_date, second_option_date,
                    golfed_before, prior_group_name, breakfast, accommodation,
                    jpc, address, billing_method, golf_last_year, budget, pickup, notes,
                    jones_rounds, palmer_rounds, crispin_rounds,
                    archived, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                intake_number,
                row.get('bkg_number', ''),
                row.get('date_of_call', date.today().isoformat()),
                row.get('year', ''),
                row.get('group_name', ''),
                row.get('contact_name', ''),
                row.get('contact_phone', ''),
                row.get('contact_email', ''),
                int(row.get('num_golfers', 0) or 0),
                row.get('preferred_date', ''),
                row.get('second_option_date', ''),
                int(row.get('golfed_before', 0) or 0),
                row.get('prior_group_name', ''),
                row.get('breakfast', ''),
                row.get('accommodation', ''),
                row.get('jpc', ''),
                row.get('address', ''),
                row.get('billing_method', ''),
                row.get('golf_last_year', ''),
                row.get('budget', ''),
                row.get('pickup', ''),
                row.get('notes', ''),
                row.get('jones_rounds', ''),
                row.get('palmer_rounds', ''),
                row.get('crispin_rounds', ''),
                archive_val,
                session.get('user_id')
            ))
            count += 1
        except Exception as e:
            flash(f'Error importing row: {e}', 'warning')

    db.commit()
    flash(f'Successfully imported {count} intake(s) into {"archive" if archive_val else "active"}.', 'success')
    return _settings_redirect()

# ─── Init & run ─────────────────────────────────────────────────────

with app.app_context():
    os.makedirs(os.path.dirname(app.config['DATABASE']), exist_ok=True)
    init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
