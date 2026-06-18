from flask_pymongo import PyMongo
from flask_login import LoginManager

mongo = PyMongo()
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'


def get_users_collection():
    return mongo.db.users


def get_exams_collection():
    return mongo.db.exams


def get_questions_collection():
    return mongo.db.questions


def get_results_collection():
    return mongo.db.results