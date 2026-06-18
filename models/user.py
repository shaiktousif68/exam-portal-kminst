from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId


class User(UserMixin):
    """MongoDB-based User model for Flask-Login"""

    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.user_data = user_data

    @property
    def username(self):
        return self.user_data.get('username', '')

    @property
    def email(self):
        return self.user_data.get('email', '')

    @property
    def password_hash(self):
        return self.user_data.get('password_hash', '')

    @property
    def is_admin(self):
        return self.user_data.get('is_admin', False)

    @property
    def created_at(self):
        return self.user_data.get('created_at')

    def set_password(self, password):
        self.user_data['password_hash'] = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return self.id

    def to_dict(self):
        """Return user data suitable for MongoDB insertion"""
        return self.user_data

    def __repr__(self):
        return f"<User {self.username}>"