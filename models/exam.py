from datetime import datetime
from bson import ObjectId


class Exam:
    """MongoDB-based Exam model"""

    def __init__(self, exam_data):
        self.exam_data = exam_data

    @property
    def id(self):
        return str(self.exam_data['_id'])

    @property
    def title(self):
        return self.exam_data.get('title', '')

    @property
    def description(self):
        return self.exam_data.get('description', '')

    @property
    def duration_minutes(self):
        return self.exam_data.get('duration_minutes', 30)

    @property
    def created_by(self):
        return self.exam_data.get('created_by', '')

    @property
    def created_at(self):
        return self.exam_data.get('created_at')

    @property
    def is_active(self):
        return self.exam_data.get('is_active', True)

    @property
    def questions(self):
        return self.exam_data.get('questions', [])

    @questions.setter
    def questions(self, q_list):
        self.exam_data['questions'] = q_list

    def to_dict(self):
        return self.exam_data

    def __repr__(self):
        return f"<Exam {self.title}>"


class Question:
    """MongoDB-based Question model"""

    def __init__(self, question_data):
        self.question_data = question_data

    @property
    def id(self):
        return str(self.question_data['_id'])

    @property
    def exam_id(self):
        return self.question_data.get('exam_id', '')

    @property
    def question_text(self):
        return self.question_data.get('question_text', '')

    @property
    def option_a(self):
        return self.question_data.get('option_a', '')

    @property
    def option_b(self):
        return self.question_data.get('option_b', '')

    @property
    def option_c(self):
        return self.question_data.get('option_c', '')

    @property
    def option_d(self):
        return self.question_data.get('option_d', '')

    @property
    def correct_option(self):
        return self.question_data.get('correct_option', '')

    def to_dict(self):
        return self.question_data

    def __repr__(self):
        return f"<Question {self.id}: {self.question_text[:50]}>"


class Result:
    """MongoDB-based Result model"""

    def __init__(self, result_data):
        self.result_data = result_data

    @property
    def id(self):
        return str(self.result_data['_id'])

    @property
    def user_id(self):
        return self.result_data.get('user_id', '')

    @property
    def exam_id(self):
        return self.result_data.get('exam_id', '')

    @property
    def score(self):
        return self.result_data.get('score', 0)

    @property
    def total_questions(self):
        return self.result_data.get('total_questions', 0)

    @property
    def percentage(self):
        return self.result_data.get('percentage', 0.0)

    @property
    def submitted_at(self):
        return self.result_data.get('submitted_at')

    @property
    def user(self):
        return self.result_data.get('_user')

    @user.setter
    def user(self, user_obj):
        self.result_data['_user'] = user_obj

    @property
    def exam(self):
        return self.result_data.get('_exam')

    @exam.setter
    def exam(self, exam_obj):
        self.result_data['_exam'] = exam_obj

    def to_dict(self):
        return self.result_data

    def __repr__(self):
        return f"<Result User:{self.user_id} Exam:{self.exam_id} Score:{self.score}/{self.total_questions}>"