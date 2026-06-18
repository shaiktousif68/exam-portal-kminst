from datetime import datetime, timedelta
import random
import pytz
from bson import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from flask_mail import Mail, Message
from config import Config
from database.db import mongo, login_manager, get_users_collection, get_exams_collection, get_questions_collection, get_results_collection
from models.user import User
from models.exam import Exam, Question, Result
from utils.auth import admin_required

app = Flask(__name__)
app.config.from_object(Config)

mongo.init_app(app)
login_manager.init_app(app)
mail = Mail(app)

# ===== INDIAN STANDARD TIME (IST) CONFIG =====
IST = pytz.timezone('Asia/Kolkata')


@app.template_filter('ist')
def ist_filter(dt):
    """Convert UTC datetime to IST (Indian Standard Time) for display"""
    if dt is None:
        return ''
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            dt = pytz.utc.localize(dt)
        return dt.astimezone(IST).strftime('%d-%m-%Y %I:%M %p')
    return str(dt)


@app.template_filter('ist_date')
def ist_date_filter(dt):
    """Convert UTC datetime to IST date only"""
    if dt is None:
        return ''
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            dt = pytz.utc.localize(dt)
        return dt.astimezone(IST).strftime('%d-%m-%Y')
    return str(dt)


@app.context_processor
def inject_now():
    """Inject current IST time into all templates"""
    return {'now_ist': datetime.now(IST).strftime('%d-%m-%Y %I:%M %p IST')}


@login_manager.user_loader
def load_user(user_id):
    users_collection = get_users_collection()
    try:
        # Try to load by ObjectId (new MongoDB format)
        user_data = users_collection.find_one({'_id': ObjectId(user_id)})
        if user_data:
            return User(user_data)
    except Exception:
        # Invalid ObjectId (e.g. old session with numeric ID) — force re-login
        return None
    return None


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

        users_collection = get_users_collection()

        if users_collection.find_one({'username': username}):
            flash('Username already exists.', 'danger')
            return render_template('register.html')

        if users_collection.find_one({'email': email}):
            flash('Email already registered.', 'danger')
            return render_template('register.html')

        new_user_id = ObjectId()

        # First registered user becomes admin (only if no admin exists yet)
        existing_admin = users_collection.find_one({'is_admin': True})
        is_admin = not existing_admin

        user_doc = {
            '_id': new_user_id,
            'username': username,
            'email': email,
            'password_hash': generate_password_hash(password),
            'is_admin': is_admin,
            'created_at': datetime.utcnow()
        }

        users_collection.insert_one(user_doc)

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
        role = request.form.get('role', 'user')

        users_collection = get_users_collection()
        user_data = users_collection.find_one({'username': username})

        if user_data:
            user = User(user_data)
            if user.check_password(password):
                # === ROLE ENFORCEMENT ===
                # Only admin email "shaiktousiff26@gmail.com" can login as admin
                # Everyone else is forced to be student
                is_admin_email = (user_data.get('email') == 'shaiktousiff26@gmail.com')
                
                if role == 'admin':
                    if not is_admin_email:
                        flash('Access denied. Only the admin can login as admin.', 'danger')
                        return render_template('login.html')
                else:
                    # Student login - allowed for anyone
                    pass
                
                login_user(user)
                next_page = request.args.get('next')
                flash(f'Welcome back, {user.username}!', 'success')
                
                if role == 'admin' and is_admin_email:
                    return redirect(url_for('admin_panel'))
                return redirect(next_page) if next_page else redirect(url_for('dashboard'))

        flash('Invalid username or password.', 'danger')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


# ===== FORGOT PASSWORD / OTP FEATURE =====

def send_otp_email(to_email, otp):
    """Send OTP via Gmail"""
    try:
        msg = Message(
            subject='🔐 Kminst EP - Password Reset OTP',
            recipients=[to_email],
            body=f'''Hello,

You requested to reset your password for Kminst EP.

Your One-Time Password (OTP) is: {otp}

This OTP is valid for 10 minutes only.

If you did not request this, please ignore this email.

- Kminst EP Team
'''
        )
        mail.send(msg)
        return True
    except Exception as e:
        import traceback

        print("\n========== EMAIL ERROR ==========")
        print("Error Type:", type(e).__name__)
        print("Error:", str(e))
        traceback.print_exc()
        print("=================================\n")

        return False


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        
        if not email:
            flash('Please enter your email address.', 'danger')
            return render_template('forgot_password.html')
        
        users_collection = get_users_collection()
        user_data = users_collection.find_one({'email': email})
        
        if not user_data:
            flash('No account found with this email address.', 'danger')
            return render_template('forgot_password.html')
        
        # Generate 6-digit OTP
        otp = str(random.randint(100000, 999999))
        
        # Store OTP in the database with a 10-minute expiry
        users_collection.update_one(
            {'_id': user_data['_id']},
            {'$set': {'reset_otp': otp, 'reset_otp_expiry': datetime.utcnow() + timedelta(minutes=10)}}
        )
        
        # Send OTP via email
        sent = send_otp_email(email, otp)
        
        if not sent:
            flash('⚠️ Email could not be sent. Please check that the Gmail App Password is configured correctly.', 'warning')
            flash('For testing, your OTP is: ' + otp, 'info')
        else:
            flash('✅ OTP sent to your email! Check your inbox.', 'success')
        
        return render_template('verify_otp.html', email=email)
    
    return render_template('forgot_password.html')


@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    email = request.form.get('email', '').strip()
    otp_input = request.form.get('otp', '').strip()
    
    if not email or not otp_input:
        flash('Missing email or OTP.', 'danger')
        return redirect(url_for('forgot_password'))
    
    users_collection = get_users_collection()
    user_data = users_collection.find_one({'email': email})
    
    if not user_data or 'reset_otp' not in user_data:
        flash('Invalid request or OTP expired. Please request a new one.', 'danger')
        return redirect(url_for('forgot_password'))
    
    # Check OTP validity (10 minutes)
    expiry = user_data.get('reset_otp_expiry')
    if not expiry or datetime.utcnow() > expiry:
        users_collection.update_one({'_id': user_data['_id']}, {'$unset': {'reset_otp': '', 'reset_otp_expiry': ''}})
        flash('OTP expired (10 minutes). Please request a new one.', 'danger')
        return redirect(url_for('forgot_password'))
    
    if user_data['reset_otp'] != otp_input:
        flash('Invalid OTP. Please try again.', 'danger')
        return render_template('verify_otp.html', email=email)
    
    # OTP verified - proceed to reset password
    users_collection.update_one({'_id': user_data['_id']}, {'$unset': {'reset_otp': '', 'reset_otp_expiry': ''}})
    flash('✅ OTP verified! Please set your new password.', 'success')
    return render_template('reset_password.html', email=email)


@app.route('/reset-password', methods=['POST'])
def reset_password():
    email = request.form.get('email', '').strip()
    new_password = request.form.get('new_password', '').strip()
    confirm_password = request.form.get('confirm_password', '').strip()
    
    if not email or not new_password:
        flash('Missing fields.', 'danger')
        return redirect(url_for('forgot_password'))
    
    if new_password != confirm_password:
        flash('Passwords do not match.', 'danger')
        return render_template('reset_password.html', email=email)
    
    if len(new_password) < 4:
        flash('Password must be at least 4 characters.', 'danger')
        return render_template('reset_password.html', email=email)
    
    users_collection = get_users_collection()
    user_data = users_collection.find_one({'email': email})
    
    if not user_data:
        flash('Account not found.', 'danger')
        return redirect(url_for('forgot_password'))
    
    # Update password
    new_hash = generate_password_hash(new_password)
    users_collection.update_one(
        {'_id': user_data['_id']},
        {'$set': {'password_hash': new_hash}}
    )
    
    flash('✅ Password reset successfully! You can now login with your new password.', 'success')
    return redirect(url_for('login'))


# ===== DASHBOARD =====

@app.route('/dashboard')
@login_required
def dashboard():
    exams_collection = get_exams_collection()
    results_collection = get_results_collection()

    exams_data = exams_collection.find({'is_active': True}).sort('created_at', -1)
    exams = []
    for ed in exams_data:
        exam_obj = Exam(ed)
        # Attach questions count
        questions_collection = get_questions_collection()
        q_count = questions_collection.count_documents({'exam_id': exam_obj.id})
        exam_obj.exam_data['questions_count'] = q_count
        exam_obj.exam_data['_questions'] = []
        exams.append(exam_obj)

    user_results_data = results_collection.find({'user_id': current_user.id}).sort('submitted_at', -1)
    user_results = [Result(rd) for rd in user_results_data]

    return render_template('dashboard.html', exams=exams, user_results=user_results)


# ===== EXAM ROUTES =====

@app.route('/exam/<exam_id>')
@login_required
def take_exam(exam_id):
    exams_collection = get_exams_collection()
    exam_data = exams_collection.find_one({'_id': ObjectId(exam_id)})

    if not exam_data:
        flash('Exam not found.', 'danger')
        return redirect(url_for('dashboard'))

    exam = Exam(exam_data)

    # Check if user already completed this exam
    results_collection = get_results_collection()
    existing = results_collection.find_one({'user_id': current_user.id, 'exam_id': exam_id})
    if existing:
        flash('You have already taken this exam.', 'warning')
        if current_user.is_admin:
            return redirect(url_for('view_result', result_id=str(existing['_id'])))
        return redirect(url_for('dashboard'))

    if not exam.is_active:
        flash('This exam is no longer active.', 'danger')
        return redirect(url_for('dashboard'))

    # Load questions for this exam and attach to exam object
    questions_collection = get_questions_collection()
    questions_data = questions_collection.find({'exam_id': exam_id})
    questions = [Question(qd) for qd in questions_data]
    # Attach questions to exam data so template can access exam.questions
    exam.exam_data['questions'] = questions

    return render_template('exam.html', exam=exam, questions=questions)


@app.route('/exam/<exam_id>/submit', methods=['POST'])
@login_required
def submit_exam(exam_id):
    exams_collection = get_exams_collection()
    exam_data = exams_collection.find_one({'_id': ObjectId(exam_id)})

    if not exam_data:
        return jsonify({'error': 'Exam not found'}), 404

    results_collection = get_results_collection()
    existing = results_collection.find_one({'user_id': current_user.id, 'exam_id': exam_id})
    if existing:
        return jsonify({'error': 'Already submitted'}), 400

    questions_collection = get_questions_collection()
    questions_data = questions_collection.find({'exam_id': exam_id})
    questions = [Question(qd) for qd in questions_data]

    score = 0
    total = len(questions)

    for question in questions:
        user_answer = request.form.get(f'question_{question.id}')
        if user_answer and user_answer.upper() == question.correct_option:
            score += 1

    percentage = round((score / total) * 100, 2) if total > 0 else 0

    result_doc = {
        '_id': ObjectId(),
        'user_id': current_user.id,
        'exam_id': exam_id,
        'score': score,
        'total_questions': total,
        'percentage': percentage,
        'submitted_at': datetime.utcnow()
    }
    results_collection.insert_one(result_doc)

    if current_user.is_admin:
        flash(f'Exam submitted! You scored {score}/{total} ({percentage}%).', 'success')
        return redirect(url_for('view_result', result_id=str(result_doc['_id'])))
    else:
        flash('Exam submitted successfully!', 'success')
        return redirect(url_for('dashboard'))


@app.route('/result/<result_id>')
@login_required
def view_result(result_id):
    results_collection = get_results_collection()
    result_data = results_collection.find_one({'_id': ObjectId(result_id)})

    if not result_data:
        flash('Result not found.', 'danger')
        return redirect(url_for('dashboard'))

    # Only admin can view results
    if not current_user.is_admin:
        flash('Access denied. Only administrators can view results.', 'danger')
        return redirect(url_for('dashboard'))

    # Attach user and exam info
    users_collection = get_users_collection()
    user_data = users_collection.find_one({'_id': ObjectId(result_data['user_id'])})
    if user_data:
        result_data['_user'] = User(user_data)

    exams_collection = get_exams_collection()
    exam_data = exams_collection.find_one({'_id': ObjectId(result_data['exam_id'])})
    if exam_data:
        result_data['_exam'] = Exam(exam_data)

    result = Result(result_data)
    return render_template('result.html', result=result)


# ===== ADMIN ROUTES =====

@app.route('/admin')
@login_required
@admin_required
def admin_panel():
    exams_collection = get_exams_collection()
    users_collection = get_users_collection()
    results_collection = get_results_collection()
    questions_collection = get_questions_collection()

    exams_data = exams_collection.find().sort('created_at', -1)
    exams = []
    for ed in exams_data:
        exam_obj = Exam(ed)
        q_count = questions_collection.count_documents({'exam_id': exam_obj.id})
        exam_obj.exam_data['_questions'] = []
        exam_obj.exam_data['questions_count'] = q_count
        exams.append(exam_obj)

    users_data = users_collection.find()
    users = [User(ud) for ud in users_data]

    results_data = results_collection.find().sort('submitted_at', -1)
    results_with_details = []
    for rd in results_data:
        result_obj = Result(rd)
        # Attach user
        u_data = users_collection.find_one({'_id': ObjectId(rd['user_id'])})
        if u_data:
            result_obj.user = User(u_data)
        # Attach exam
        e_data = exams_collection.find_one({'_id': ObjectId(rd['exam_id'])})
        if e_data:
            result_obj.exam = Exam(e_data)
        results_with_details.append(result_obj)

    return render_template('dashboard.html', exams=exams, users=users, results=results_with_details, admin_view=True, results_with_details=results_with_details)


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

        exams_collection = get_exams_collection()
        exam_doc = {
            '_id': ObjectId(),
            'title': title,
            'description': description,
            'duration_minutes': int(duration),
            'created_by': current_user.id,
            'created_at': datetime.utcnow(),
            'is_active': True
        }
        exams_collection.insert_one(exam_doc)

        flash(f'Exam "{title}" created successfully! Now add questions.', 'success')
        return redirect(url_for('create_questions', exam_id=str(exam_doc['_id'])))

    return render_template('dashboard.html', create_exam_form=True)


@app.route('/admin/exam/<exam_id>/questions', methods=['GET', 'POST'])
@login_required
@admin_required
def create_questions(exam_id):
    exams_collection = get_exams_collection()
    exam_data = exams_collection.find_one({'_id': ObjectId(exam_id)})

    if not exam_data:
        flash('Exam not found.', 'danger')
        return redirect(url_for('admin_panel'))

    exam = Exam(exam_data)

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

        questions_collection = get_questions_collection()
        question_doc = {
            '_id': ObjectId(),
            'exam_id': exam_id,
            'question_text': question_text,
            'option_a': option_a,
            'option_b': option_b,
            'option_c': option_c,
            'option_d': option_d,
            'correct_option': correct_option
        }
        questions_collection.insert_one(question_doc)

        flash('Question added successfully!', 'success')
        return redirect(url_for('create_questions', exam_id=exam_id))

    questions_collection = get_questions_collection()
    questions_data = questions_collection.find({'exam_id': exam_id})
    questions = [Question(qd) for qd in questions_data]

    return render_template('create_questions.html', exam=exam, questions=questions)


@app.route('/admin/exam/<exam_id>/questions/bulk', methods=['POST'])
@login_required
@admin_required
def bulk_import_questions(exam_id):
    """Import multiple questions at once from pasted text"""
    exams_collection = get_exams_collection()
    exam_data = exams_collection.find_one({'_id': ObjectId(exam_id)})
    
    if not exam_data:
        flash('Exam not found.', 'danger')
        return redirect(url_for('admin_panel'))
    
    bulk_text = request.form.get('bulk_questions', '').strip()
    
    if not bulk_text:
        flash('Please paste some questions first.', 'danger')
        return redirect(url_for('create_questions', exam_id=exam_id))
    
    lines = bulk_text.strip().split('\n')
    questions_collection = get_questions_collection()
    imported = 0
    errors = []
    
    for i, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue
        
        parts = [p.strip() for p in line.split('|')]
        
        if len(parts) != 6:
            errors.append(f"Line {i}: Expected 6 parts (question | A | B | C | D | correct), got {len(parts)}")
            continue
        
        question_text, option_a, option_b, option_c, option_d, correct_option = parts
        correct_option = correct_option.upper()
        
        if correct_option not in ['A', 'B', 'C', 'D']:
            errors.append(f"Line {i}: Correct answer must be A, B, C, or D (got '{correct_option}')")
            continue
        
        question_doc = {
            '_id': ObjectId(),
            'exam_id': exam_id,
            'question_text': question_text,
            'option_a': option_a,
            'option_b': option_b,
            'option_c': option_c,
            'option_d': option_d,
            'correct_option': correct_option
        }
        questions_collection.insert_one(question_doc)
        imported += 1
    
    msg = f'✅ Successfully imported {imported} question(s)!'
    if errors:
        msg += f' ⚠️ {len(errors)} line(s) had errors (check format).'
    
    flash(msg, 'success' if imported > 0 else 'danger')
    
    if errors:
        error_msg = 'Errors:<br>' + '<br>'.join(errors[:5])
        if len(errors) > 5:
            error_msg += f'<br>...and {len(errors) - 5} more error(s)'
        flash(error_msg, 'warning')
    
    return redirect(url_for('create_questions', exam_id=exam_id))


@app.route('/admin/exam/<exam_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_exam(exam_id):
    exams_collection = get_exams_collection()
    exam_data = exams_collection.find_one({'_id': ObjectId(exam_id)})

    if not exam_data:
        flash('Exam not found.', 'danger')
        return redirect(url_for('admin_panel'))

    title = exam_data['title']

    # Delete all related results
    get_results_collection().delete_many({'exam_id': exam_id})

    # Delete all questions
    get_questions_collection().delete_many({'exam_id': exam_id})

    # Delete the exam
    exams_collection.delete_one({'_id': ObjectId(exam_id)})

    flash(f'Exam "{title}" has been deleted successfully.', 'success')
    return redirect(url_for('admin_panel'))


@app.route('/admin/exam/<exam_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_exam(exam_id):
    exams_collection = get_exams_collection()
    exam_data = exams_collection.find_one({'_id': ObjectId(exam_id)})

    if not exam_data:
        flash('Exam not found.', 'danger')
        return redirect(url_for('admin_panel'))

    new_status = not exam_data.get('is_active', True)
    exams_collection.update_one(
        {'_id': ObjectId(exam_id)},
        {'$set': {'is_active': new_status}}
    )

    status = 'activated' if new_status else 'deactivated'
    flash(f'Exam "{exam_data["title"]}" {status}.', 'success')
    return redirect(url_for('admin_panel'))


@app.route('/admin/users')
@login_required
@admin_required
def manage_users():
    users_collection = get_users_collection()
    users_data = users_collection.find()
    users = [User(ud) for ud in users_data]
    return render_template('manage_users.html', users=users)


@app.route('/admin/users/<user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    if str(current_user.id) == user_id:
        flash('You cannot delete your own admin account.', 'danger')
        return redirect(url_for('manage_users'))
        
    users_collection = get_users_collection()
    
    # Delete user's exam results
    get_results_collection().delete_many({'user_id': user_id})
    
    # Delete the user
    users_collection.delete_one({'_id': ObjectId(user_id)})
    
    flash('User has been deleted successfully.', 'success')
    return redirect(url_for('manage_users'))

# ===== API ENDPOINTS =====

@app.route('/api/exams')
def api_exams():
    exams_collection = get_exams_collection()
    questions_collection = get_questions_collection()
    exams_data = exams_collection.find({'is_active': True})
    result = []
    for ed in exams_data:
        q_count = questions_collection.count_documents({'exam_id': str(ed['_id'])})
        result.append({
            'id': str(ed['_id']),
            'title': ed['title'],
            'description': ed.get('description', ''),
            'duration_minutes': ed.get('duration_minutes', 30),
            'questions_count': q_count
        })
    return jsonify(result)


# ===== ERROR HANDLERS =====

@app.errorhandler(404)
def not_found(e):
    return render_template('base.html', error='404 - Page Not Found'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('base.html', error='500 - Internal Server Error'), 500


if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=(os.environ.get('DEBUG', 'True') == 'True'))