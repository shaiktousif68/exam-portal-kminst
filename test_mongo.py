import certifi
from pymongo import MongoClient

uri = f'mongodb+srv://shaiktousiff26_db_user:NTcRdQJXRAiJtpps@ecommerce.ljxphk0.mongodb.net/exam_portal?retryWrites=true&w=majority&tlsCAFile={certifi.where()}'

print("Testing MongoDB Connection on PythonAnywhere...")
try:
    # We set a short timeout of 5 seconds so you don't have to wait 30 seconds
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    print("✅ SUCCESS! Connected to MongoDB Atlas.")
except Exception as e:
    print("❌ FAILED TO CONNECT.")
    print("Error Details:")
    print(e)
    print("\nIf you see a Timeout error, the PythonAnywhere firewall is blocking you.")