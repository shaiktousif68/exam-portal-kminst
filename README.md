# Kminst EP

A web-based exam management system built with Flask. Allows students to register, take exams, and view results. Admins can create exams, add questions, and manage users.

## Features

- **User Authentication**: Register, login, logout with password hashing
- **Exam Taking**: Timed exams with auto-submit when time expires
- **Results**: Instant scoring with percentage and visual feedback
- **Admin Panel**: Create exams, add MCQ questions, manage users
- **Responsive Design**: Works on desktop and mobile devices
- **REST API**: JSON endpoint for exam data

## Tech Stack

- **Backend**: Python 3, Flask, Flask-SQLAlchemy, Flask-Login
- **Database**: SQLite (default), easily switchable to PostgreSQL/MySQL
- **Frontend**: HTML5, CSS3 (with CSS Variables), Vanilla JavaScript

## Project Structure

```
exam-portal/
├── app.py                 # Main Flask application
├── config.py              # Application configuration
├── requirements.txt       # Python dependencies
├── README.md
├── database/
│   └── db.py              # Database & login manager setup
├── models/
│   ├── user.py            # User model
│   └── exam.py            # Exam, Question, Result models
├── utils/
│   └── auth.py            # Admin decorator
├── templates/
│   ├── base.html          # Base template
│   ├── login.html         # Login page
│   ├── register.html      # Registration page
│   ├── dashboard.html     # Dashboard (student & admin views)
│   ├── exam.html          # Exam taking page
│   ├── result.html        # Exam result page
│   ├── create_questions.html  # Add questions to exam
│   └── manage_users.html  # User management (admin)
└── static/
    ├── css/style.css      # Stylesheet
    └── js/script.js       # JavaScript
```

## Installation & Setup

### 1. Clone / Navigate to the project

```bash
cd exam-portal
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the application

```bash
python app.py
```

### 4. Open in browser

Navigate to `http://127.0.0.1:5000`

## First-Time Setup

1. **Register** a new account at `/register` - the first registered user automatically becomes an **admin**.
2. **Login** with your new account.
3. As admin, go to **Admin Panel** and click **"+ Create New Exam"**.
4. Add questions to the exam with 4 options and mark the correct answer.
5. **Activate** the exam so students can take it.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Home - redirects to login/dashboard |
| GET/POST | `/login` | User login |
| GET/POST | `/register` | User registration |
| GET | `/logout` | Logout |
| GET | `/dashboard` | User dashboard |
| GET | `/exam/<id>` | Take an exam |
| POST | `/exam/<id>/submit` | Submit exam answers |
| GET | `/result/<id>` | View exam result |
| GET | `/admin` | Admin panel |
| GET/POST | `/admin/exam/create` | Create new exam |
| GET/POST | `/admin/exam/<id>/questions` | Add questions |
| POST | `/admin/exam/<id>/toggle` | Activate/deactivate exam |
| GET | `/admin/users` | Manage users |
| GET | `/api/exams` | JSON API for active exams |

## License

MIT License