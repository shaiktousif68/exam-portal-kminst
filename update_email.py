"""Run this script to update admin email"""
import sys
sys.path.insert(0, '.')
from app import app
from database.db import get_users_collection

with app.app_context():
    users = get_users_collection()
    result = users.update_one(
        {'username': 'jon'},
        {'$set': {'email': 'shaiktousiff26@gmail.com'}}
    )
    print(f"Updated {result.modified_count} user(s)")
    
    # Verify
    user = users.find_one({'username': 'jon'})
    if user:
        print(f"Username: {user['username']}")
        print(f"Email now: {user['email']}")
    else:
        print("User 'jon' not found")