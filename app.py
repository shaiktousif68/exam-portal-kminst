from datetime import datetime
import pytz
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from config import Config
from database.db import db, login_manager
from models.user import User
from models.exam import Exam, Question, Result
from utils.auth import admin_required

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
login_manager.init_app(app)

# ===== INDIAN STANDARD TIME (IST) CONFIG =====
IST = pytz.timezone('Asia/Kolkata')

@app.template_filter('ist')
def ist_filter(dt):
    """Convert UTC datetime to IST (Indian Standard Time) for display"""
    if dt is None:
        return ''
    # If datetime is naive (no timezone), assume it's UTC
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    return dt.astimezone(IST).strftime('%d-%m-%Y %I:%M %p')

@app.template_filter('ist_date')
def ist_date_filter(dt):
    """Convert UTC datetime to IST date only"""
    if dt is None:
        return ''
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    return dt.astimezone(IST).strftime('%d-%m-%Y')

@app.context_processor
def inject_now():
    """Inject current IST time into all templates"""
    return {'now_ist': datetime.now(IST).strftime('%d-%m-%Y %I:%M %p IST')}


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


# ===== AUTH ROUTES =====

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not username or not email or not password:
            flash('All fields are required.', 'danger')
            return render_template('register.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')

        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return render_template('register.html')

        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return render_template('register.html')

        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        # First user is admin
        if User.query.count() == 1:
            new_user.is_admin = True
            db.session.commit()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


# ===== DASHBOARD =====

@app.route('/dashboard')
@login_required
def dashboard():
    exams = Exam.query.filter_by(is_active=True).all()
    user_results = Result.query.filter_by(user_id=current_user.id).order_by(Result.submitted_at.desc()).all()
    return render_template('dashboard.html', exams=exams, user_results=user_results)


# ===== EXAM ROUTES =====

@app.route('/exam/<int:exam_id>')
@login_required
def take_exam(exam_id):
    exam = Exam.query.get_or_404(exam_id)

    # Check if user already completed this exam
    existing = Result.query.filter_by(user_id=current_user.id, exam_id=exam_id).first()
    if existing:
        flash('You have already taken this exam.', 'warning')
        if current_user.is_admin:
            return redirect(url_for('view_result', result_id=existing.id))
        return redirect(url_for('dashboard'))

    if not exam.is_active:
        flash('This exam is no longer active.', 'danger')
        return redirect(url_for('dashboard'))

    return render_template('exam.html', exam=exam)


@app.route('/exam/<int:exam_id>/submit', methods=['POST'])
@login_required
def submit_exam(exam_id):
    exam = Exam.query.get_or_404(exam_id)

    existing = Result.query.filter_by(user_id=current_user.id, exam_id=exam_id).first()
    if existing:
        return jsonify({'error': 'Already submitted'}), 400

    questions = Question.query.filter_by(exam_id=exam_id).all()
    score = 0
    total = len(questions)

    for question in questions:
        user_answer = request.form.get(f'question_{question.id}')
        if user_answer and user_answer.upper() == question.correct_option:
            score += 1

    percentage = round((score / total) * 100, 2) if total > 0 else 0

    result = Result(
        user_id=current_user.id,
        exam_id=exam_id,
        score=score,
        total_questions=total,
        percentage=percentage
    )
    db.session.add(result)
    db.session.commit()

    if current_user.is_admin:
        flash(f'Exam submitted! You scored {score}/{total} ({percentage}%).', 'success')
        return redirect(url_for('view_result', result_id=result.id))
    else:
        flash('Exam submitted successfully!', 'success')
        return redirect(url_for('dashboard'))


@app.route('/result/<int:result_id>')
@login_required
def view_result(result_id):
    result = Result.query.get_or_404(result_id)

    # Only admin can view results
    if not current_user.is_admin:
        flash('Access denied. Only administrators can view results.', 'danger')
        return redirect(url_for('dashboard'))

    return render_template('result.html', result=result)


# ===== ADMIN ROUTES =====

@app.route('/admin')
@login_required
@admin_required
def admin_panel():
    exams = Exam.query.all()
    users = User.query.all()
    results = Result.query.all()
    
    # Get results with student names and exam titles for display
    from sqlalchemy.orm import joinedload
    results_with_details = Result.query.options(
        joinedload(Result.user),
        joinedload(Result.exam)
    ).order_by(Result.submitted_at.desc()).all()
    
    return render_template('dashboard.html', exams=exams, users=users, results=results, admin_view=True, results_with_details=results_with_details)


@app.route('/admin/exam/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_exam():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        duration = request.form.get('duration', 30)

        if not title:
            flash('Exam title is required.', 'danger')
            return render_template('dashboard.html', create_exam_form=True)

        exam = Exam(
            title=title,
            description=description,
            duration_minutes=int(duration),
            created_by=current_user.id
        )
        db.session.add(exam)
        db.session.commit()

        flash(f'Exam "{title}" created successfully! Now add questions.', 'success')
        return redirect(url_for('create_questions', exam_id=exam.id))

    return render_template('dashboard.html', create_exam_form=True)


@app.route('/admin/exam/<int:exam_id>/questions', methods=['GET', 'POST'])
@login_required
@admin_required
def create_questions(exam_id):
    exam = Exam.query.get_or_404(exam_id)

    if request.method == 'POST':
        question_text = request.form.get('question_text')
        option_a = request.form.get('option_a')
        option_b = request.form.get('option_b')
        option_c = request.form.get('option_c')
        option_d = request.form.get('option_d')
        correct_option = request.form.get('correct_option', '').upper()

        if not all([question_text, option_a, option_b, option_c, option_d, correct_option]):
            flash('All fields are required for each question.', 'danger')
            return redirect(url_for('create_questions', exam_id=exam_id))

        if correct_option not in ['A', 'B', 'C', 'D']:
            flash('Correct option must be A, B, C, or D.', 'danger')
            return redirect(url_for('create_questions', exam_id=exam_id))

        question = Question(
            exam_id=exam_id,
            question_text=question_text,
            option_a=option_a,
            option_b=option_b,
            option_c=option_c,
            option_d=option_d,
            correct_option=correct_option
        )
        db.session.add(question)
        db.session.commit()

        flash('Question added successfully!', 'success')
        return redirect(url_for('create_questions', exam_id=exam_id))

    questions = Question.query.filter_by(exam_id=exam_id).all()
    return render_template('create_questions.html', exam=exam, questions=questions)


@app.route('/admin/exam/<int:exam_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_exam(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    title = exam.title

    # Delete all related results first
    Result.query.filter_by(exam_id=exam_id).delete()

    # Delete all questions (though cascade should handle this too)
    Question.query.filter_by(exam_id=exam_id).delete()

    db.session.delete(exam)
    db.session.commit()
    flash(f'Exam "{title}" has been deleted successfully.', 'success')
    return redirect(url_for('admin_panel'))


@app.route('/admin/exam/<int:exam_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_exam(exam_id):
    exam = Exam.query.get_or_404(exam_id)
    exam.is_active = not exam.is_active
    db.session.commit()
    status = 'activated' if exam.is_active else 'deactivated'
    flash(f'Exam "{exam.title}" {status}.', 'success')
    return redirect(url_for('admin_panel'))


@app.route('/admin/users')
@login_required
@admin_required
def manage_users():
    users = User.query.all()
    return render_template('manage_users.html', users=users)


# ===== API ENDPOINTS =====

@app.route('/api/exams')
def api_exams():
    exams = Exam.query.filter_by(is_active=True).all()
    return jsonify([{
        'id': e.id,
        'title': e.title,
        'description': e.description,
        'duration_minutes': e.duration_minutes,
        'questions_count': len(e.questions)
    } for e in exams])


# ===== ERROR HANDLERS =====

@app.errorhandler(404)
def not_found(e):
    return render_template('base.html', error='404 - Page Not Found'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('base.html', error='500 - Internal Server Error'), 500


# ===== INIT DATABASE =====
with app.app_context():
    db.create_all()


if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=(os.environ.get('DEBUG', 'True') == 'True'))
