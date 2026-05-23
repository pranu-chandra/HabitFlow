from flask import Flask, render_template, request, redirect, session, url_for, send_file, jsonify, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
from datetime import datetime, timedelta, date
import csv
import random
from io import StringIO, BytesIO
import json
 
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'habitflow_secret_2024')
 
DB_PATH = os.environ.get('DB_PATH', '/tmp/habit_data.db')
 
QUOTES = [
    {"text": "Success is the sum of small efforts repeated daily.", "author": "Robert Collier"},
    {"text": "Don't watch the clock; do what it does. Keep going.", "author": "Sam Levenson"},
    {"text": "The secret to getting ahead is getting started.", "author": "Mark Twain"},
    {"text": "Discipline is choosing between what you want now and what you want most.", "author": "Abraham Lincoln"},
    {"text": "Small daily improvements lead to stunning results.", "author": "Robin Sharma"},
    {"text": "Consistency is more important than perfection.", "author": "Unknown"},
    {"text": "We are what we repeatedly do. Excellence is not an act but a habit.", "author": "Aristotle"},
    {"text": "Motivation gets you going, but discipline keeps you growing.", "author": "John C. Maxwell"},
    {"text": "The only way to do great work is to love what you do.", "author": "Steve Jobs"},
    {"text": "Push yourself because no one else is going to do it for you.", "author": "Unknown"},
    {"text": "It's not about having time. It's about making time.", "author": "Unknown"},
    {"text": "Your future is created by what you do today, not tomorrow.", "author": "Robert Kiyosaki"},
    {"text": "Dream big, start small, act now.", "author": "Robin Sharma"},
    {"text": "Every master was once a disaster.", "author": "T. Harv Eker"},
]
 
CATEGORIES = ["Health", "Fitness", "Learning", "Mindfulness", "Productivity", "Social", "Finance", "Creative", "Other"]
FREQUENCIES = ["Daily", "Weekly", "Weekdays", "Weekends"]
COLORS = ["#6EE7B7", "#93C5FD", "#F9A8D4", "#FCD34D", "#A78BFA", "#FB923C", "#34D399", "#60A5FA"]
 
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
 
def init_db():
    with get_db() as db:
        db.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            timezone TEXT DEFAULT 'UTC'
        )''')
        db.execute('''CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT NOT NULL,
            category TEXT DEFAULT 'Other',
            frequency TEXT DEFAULT 'Daily',
            color TEXT DEFAULT '#6EE7B7',
            icon TEXT DEFAULT '⭐',
            target_days INTEGER DEFAULT 7,
            created_at TEXT DEFAULT (datetime('now')),
            archived INTEGER DEFAULT 0
        )''')
        db.execute('''CREATE TABLE IF NOT EXISTS habit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            habit_id INTEGER,
            user_id INTEGER,
            status TEXT NOT NULL,
            notes TEXT,
            mood INTEGER DEFAULT 3,
            logged_date TEXT NOT NULL,
            logged_at TEXT DEFAULT (datetime('now'))
        )''')
        db.execute('''CREATE TABLE IF NOT EXISTS user_stats (
            user_id INTEGER PRIMARY KEY,
            total_completions INTEGER DEFAULT 0,
            longest_streak INTEGER DEFAULT 0,
            last_active TEXT
        )''')
 
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated
 
def get_random_quote():
    return random.choice(QUOTES)
 
def calculate_habit_streak(habit_id, user_id):
    db = get_db()
    logs = db.execute("""
        SELECT DISTINCT logged_date FROM habit_logs 
        WHERE habit_id=? AND user_id=? AND status='done'
        ORDER BY logged_date DESC
    """, (habit_id, user_id)).fetchall()
 
    if not logs:
        return 0
 
    streak = 0
    today = date.today()
    expected = today
 
    for row in logs:
        log_date = datetime.strptime(row['logged_date'], '%Y-%m-%d').date()
        if log_date == expected or (streak == 0 and log_date == today - timedelta(days=1)):
            if streak == 0 and log_date != today:
                expected = log_date
            streak += 1
            expected = expected - timedelta(days=1)
        else:
            break
 
    return streak
 
def calculate_completion_rate(habit_id, user_id, days=30):
    db = get_db()
    start_date = (date.today() - timedelta(days=days)).strftime('%Y-%m-%d')
    done = db.execute("""
        SELECT COUNT(DISTINCT logged_date) FROM habit_logs
        WHERE habit_id=? AND user_id=? AND status='done' AND logged_date >= ?
    """, (habit_id, user_id, start_date)).fetchone()[0]
    return round((done / days) * 100, 1)
 
def get_heatmap_data(user_id, days=365):
    db = get_db()
    start = (date.today() - timedelta(days=days)).strftime('%Y-%m-%d')
    rows = db.execute("""
        SELECT logged_date, COUNT(*) as count FROM habit_logs
        WHERE user_id=? AND status='done' AND logged_date >= ?
        GROUP BY logged_date
    """, (user_id, start)).fetchall()
    return {row['logged_date']: row['count'] for row in rows}
 
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect('/dashboard')
    return redirect('/login')
 
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip().lower()
        password = request.form['password']
        if len(password) < 6:
            return render_template('register.html', error="Password must be at least 6 characters.")
        db = get_db()
        try:
            hashed = generate_password_hash(password)
            db.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                       (username, email, hashed))
            db.commit()
            return redirect('/login?registered=1')
        except sqlite3.IntegrityError:
            return render_template('register.html', error="Email already registered.")
    return render_template('register.html')
 
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect('/dashboard')
        return render_template('login.html', error="Invalid email or password.")
    registered = request.args.get('registered')
    return render_template('login.html', registered=registered)
 
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')
 
@app.route('/dashboard')
@login_required
def dashboard():
    db = get_db()
    user_id = session['user_id']
    today = date.today().strftime('%Y-%m-%d')
    quote = get_random_quote()
 
    habits = db.execute("""
        SELECT h.*, 
            (SELECT COUNT(*) FROM habit_logs hl WHERE hl.habit_id=h.id AND hl.status='done' AND hl.logged_date=?) as done_today
        FROM habits h WHERE h.user_id=? AND h.archived=0
        ORDER BY h.created_at ASC
    """, (today, user_id)).fetchall()
 
    habit_data = []
    total_streak = 0
    for h in habits:
        streak = calculate_habit_streak(h['id'], user_id)
        rate = calculate_completion_rate(h['id'], user_id)
        total_streak += streak
        habit_data.append({
            'id': h['id'], 'name': h['name'], 'category': h['category'],
            'frequency': h['frequency'], 'color': h['color'], 'icon': h['icon'],
            'done_today': h['done_today'], 'streak': streak, 'rate': rate
        })
 
    total_habits = len(habit_data)
    done_today = sum(1 for h in habit_data if h['done_today'])
    completion_pct = round((done_today / total_habits * 100) if total_habits else 0)
 
    total_done = db.execute("""
        SELECT COUNT(*) FROM habit_logs WHERE user_id=? AND status='done'
    """, (user_id,)).fetchone()[0]
 
    heatmap = get_heatmap_data(user_id, 365)
 
    return render_template('dashboard.html',
        username=session['username'], quote=quote,
        habits=habit_data, total_habits=total_habits,
        done_today=done_today, completion_pct=completion_pct,
        total_done=total_done, total_streak=total_streak,
        heatmap=json.dumps(heatmap), today=today,
        categories=CATEGORIES, colors=COLORS,
        frequencies=FREQUENCIES,
        now_hour=datetime.now().hour
    )
 
@app.route('/habit/add', methods=['POST'])
@login_required
def add_habit():
    db = get_db()
    name = request.form['name'].strip()
    category = request.form.get('category', 'Other')
    frequency = request.form.get('frequency', 'Daily')
    color = request.form.get('color', '#6EE7B7')
    icon = request.form.get('icon', '⭐')
    if name:
        db.execute("""
            INSERT INTO habits (user_id, name, category, frequency, color, icon)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (session['user_id'], name, category, frequency, color, icon))
        db.commit()
    return redirect('/dashboard')
 
@app.route('/habit/log', methods=['POST'])
@login_required
def log_habit():
    db = get_db()
    habit_id = request.form['habit_id']
    status = request.form['status']
    notes = request.form.get('notes', '')
    mood = request.form.get('mood', 3)
    logged_date = request.form.get('logged_date', date.today().strftime('%Y-%m-%d'))
 
    existing = db.execute("""
        SELECT id FROM habit_logs WHERE habit_id=? AND user_id=? AND logged_date=?
    """, (habit_id, session['user_id'], logged_date)).fetchone()
 
    if existing:
        db.execute("""
            UPDATE habit_logs SET status=?, notes=?, mood=? WHERE id=?
        """, (status, notes, mood, existing['id']))
    else:
        db.execute("""
            INSERT INTO habit_logs (habit_id, user_id, status, notes, mood, logged_date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (habit_id, session['user_id'], status, notes, mood, logged_date))
    db.commit()
    return jsonify({'success': True})
 
@app.route('/habit/delete/<int:habit_id>', methods=['POST'])
@login_required
def delete_habit(habit_id):
    db = get_db()
    db.execute("UPDATE habits SET archived=1 WHERE id=? AND user_id=?", (habit_id, session['user_id']))
    db.commit()
    return jsonify({'success': True})
 
@app.route('/analytics')
@login_required
def analytics():
    db = get_db()
    user_id = session['user_id']
 
    habits = db.execute("SELECT * FROM habits WHERE user_id=? AND archived=0", (user_id,)).fetchall()
    habit_stats = []
    for h in habits:
        streak = calculate_habit_streak(h['id'], user_id)
        rate_30 = calculate_completion_rate(h['id'], user_id, 30)
        rate_7 = calculate_completion_rate(h['id'], user_id, 7)
        total = db.execute("SELECT COUNT(*) FROM habit_logs WHERE habit_id=? AND status='done'", (h['id'],)).fetchone()[0]
        habit_stats.append({
            'id': h['id'], 'name': h['name'], 'category': h['category'],
            'color': h['color'], 'icon': h['icon'],
            'streak': streak, 'rate_30': rate_30, 'rate_7': rate_7, 'total': total
        })
 
    # Weekly data (last 8 weeks)
    weekly_data = []
    for i in range(7, -1, -1):
        week_start = (date.today() - timedelta(weeks=i)).strftime('%Y-%m-%d')
        week_end = (date.today() - timedelta(weeks=i) + timedelta(days=6)).strftime('%Y-%m-%d')
        count = db.execute("""
            SELECT COUNT(*) FROM habit_logs WHERE user_id=? AND status='done'
            AND logged_date BETWEEN ? AND ?
        """, (user_id, week_start, week_end)).fetchone()[0]
        weekly_data.append({'week': f"W{8-i}", 'count': count})
 
    # Category breakdown
    cat_data = db.execute("""
        SELECT h.category, COUNT(hl.id) as count
        FROM habits h LEFT JOIN habit_logs hl ON h.id=hl.habit_id AND hl.status='done'
        WHERE h.user_id=? AND h.archived=0
        GROUP BY h.category
    """, (user_id,)).fetchall()
 
    # Mood trend (last 30 days)
    mood_data = db.execute("""
        SELECT logged_date, AVG(mood) as avg_mood FROM habit_logs
        WHERE user_id=? AND logged_date >= ?
        GROUP BY logged_date ORDER BY logged_date
    """, (user_id, (date.today() - timedelta(days=30)).strftime('%Y-%m-%d'))).fetchall()
 
    heatmap = get_heatmap_data(user_id, 365)
 
    return render_template('analytics.html',
        username=session['username'],
        habit_stats=habit_stats,
        weekly_data=json.dumps([{'week': w['week'], 'count': w['count']} for w in weekly_data]),
        cat_data=json.dumps([{'category': r['category'], 'count': r['count']} for r in cat_data]),
        mood_data=json.dumps([{'date': r['logged_date'], 'mood': round(r['avg_mood'], 2)} for r in mood_data]),
        heatmap=json.dumps(heatmap)
    )
 
@app.route('/export')
@login_required
def export():
    db = get_db()
    user_id = session['user_id']
    rows = db.execute("""
        SELECT h.name, h.category, hl.status, hl.notes, hl.mood, hl.logged_date
        FROM habit_logs hl JOIN habits h ON hl.habit_id=h.id
        WHERE hl.user_id=? ORDER BY hl.logged_date DESC
    """, (user_id,)).fetchall()
 
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Habit', 'Category', 'Status', 'Notes', 'Mood (1-5)', 'Date'])
    for r in rows:
        writer.writerow([r['name'], r['category'], r['status'], r['notes'], r['mood'], r['logged_date']])
    output.seek(0)
    return send_file(BytesIO(output.getvalue().encode()), mimetype='text/csv',
                     as_attachment=True, download_name=f'habitflow_export_{date.today()}.csv')
 
@app.route('/api/chart-data')
@login_required
def chart_data():
    db = get_db()
    user_id = session['user_id']
    results = db.execute("""
        SELECT status, COUNT(*) as count FROM habit_logs
        WHERE user_id=? GROUP BY status
    """, (user_id,)).fetchall()
    return jsonify({'labels': [r['status'] for r in results], 'values': [r['count'] for r in results]})
 
@app.route('/api/toggle-habit', methods=['POST'])
@login_required
def toggle_habit():
    data = request.get_json()
    habit_id = data['habit_id']
    today = date.today().strftime('%Y-%m-%d')
    db = get_db()
 
    existing = db.execute("""
        SELECT id, status FROM habit_logs WHERE habit_id=? AND user_id=? AND logged_date=?
    """, (habit_id, session['user_id'], today)).fetchone()
 
    if existing and existing['status'] == 'done':
        db.execute("UPDATE habit_logs SET status='skipped' WHERE id=?", (existing['id'],))
        new_status = 'skipped'
    elif existing:
        db.execute("UPDATE habit_logs SET status='done' WHERE id=?", (existing['id'],))
        new_status = 'done'
    else:
        db.execute("""
            INSERT INTO habit_logs (habit_id, user_id, status, logged_date)
            VALUES (?, ?, 'done', ?)
        """, (habit_id, session['user_id'], today))
        new_status = 'done'
 
    db.commit()
    streak = calculate_habit_streak(habit_id, session['user_id'])
    return jsonify({'success': True, 'status': new_status, 'streak': streak})
 
init_db()
 
if __name__ == '__main__':
    app.run(debug=True)
