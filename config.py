import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'exam-portal-secret-key-2026'

    MONGO_URI = os.environ.get('MONGO_URI') or (
        'mongodb+srv://shaiktousiff26_db_user:NTcRdQJXRAiJtpps@ecommerce.ljxphk0.mongodb.net/exam_portal?retryWrites=true&w=majority'
    )

    # ==========================
    # Gmail Email Configuration
    # ==========================
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False

    MAIL_USERNAME = 'shaiktousiff26@gmail.com'

    # Replace with your 16-character Gmail App Password
    MAIL_PASSWORD = 'xhbcgrklednposak'

    MAIL_DEFAULT_SENDER = (
        'Kminst EP',
        'shaiktousiff26@gmail.com'
    )