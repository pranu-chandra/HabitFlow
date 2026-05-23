# HabitFlow — Advanced Habit Tracker

A beautiful, full-featured habit tracking web app built with Flask.

## Features

- 🔐 Secure user auth (register/login)
- ✅ One-click habit check-off with instant feedback
- 🔥 Streak tracking per habit
- 📊 Analytics: weekly bar chart, category donut, mood trend
- 🗓️ GitHub-style activity heatmap (full year)
- 🎨 Custom icons & colors per habit
- 📁 CSV export
- 💬 Daily motivational quotes
- 📱 Mobile responsive

---

## Run Locally

```bash
# 1. Navigate to project folder
cd habitflow

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
python app.py
```

Visit: http://localhost:5000

---

## Deploy FREE on Render

1. **Push to GitHub**
   - Create a new repo at github.com
   - Upload all files in this folder to it

2. **Deploy on Render** (render.com — free tier)
   - Sign up at render.com
   - Click "New +" → "Web Service"
   - Connect your GitHub repo
   - Settings:
     - **Runtime**: Python 3
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `gunicorn app:app`
   - Under "Environment Variables", add:
     - `SECRET_KEY` = any random long string
   - Click "Deploy"!

Your app will be live at `https://habitflow-xxxx.onrender.com` in ~2 minutes.

---

## Deploy FREE on Railway

1. Go to railway.app
2. "New Project" → "Deploy from GitHub"
3. Connect your repo
4. Add env var: `SECRET_KEY=your_secret`
5. Railway auto-detects Python and deploys!

---

## Project Structure

```
habitflow/
├── app.py              # Main Flask app + all routes
├── requirements.txt    # Dependencies
├── Procfile            # For Render/Heroku
├── render.yaml         # Render auto-config
├── templates/
│   ├── base.html       # Shared nav + styles
│   ├── login.html      # Login page
│   ├── register.html   # Registration page
│   ├── dashboard.html  # Main dashboard
│   └── analytics.html  # Analytics & charts
└── static/             # (optional) custom assets
```

---

## Notes

- SQLite database (`habit_data.db`) is created automatically on first run
- For production, consider upgrading to PostgreSQL (free on Neon.tech or Supabase)
- The `render.yaml` file makes Render auto-configure everything
