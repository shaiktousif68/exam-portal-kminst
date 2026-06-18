import sys
sys.path.insert(0, '.')
from datetime import datetime
from bson import ObjectId
from app import app
from database.db import get_users_collection
from werkzeug.security import generate_password_hash

with app.app_context():
    users_collection = get_users_collection()
    admin_email = "shaiktousiff26@gmail.com"
    new_password = "AdminPassword123!"
    new_hash = generate_password_hash(new_password)
    
    user = users_collection.find_one({"email": admin_email})
    if user:
        users_collection.update_one({"_id": user["_id"]}, {"$set": {"password_hash": new_hash, "is_admin": True}})
        print(f"✅ Success! Admin password for {admin_email} has been reset to: {new_password}")
        print(f"👤 Your Username is: '{user.get('username')}'")
    else:
        # Create the admin user if they don't exist
        user_doc = {'_id': ObjectId(), 'username': 'admin', 'email': admin_email, 'password_hash': new_hash, 'is_admin': True, 'created_at': datetime.utcnow()}
        users_collection.insert_one(user_doc)
        print(f"✅ Success! Admin account was missing, so it has been created.")
        print(f"👤 Username: 'admin'")
        print(f"🔑 Password: '{new_password}'")