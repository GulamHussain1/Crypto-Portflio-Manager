from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os # Add this import

app = Flask(__name__)
app.secret_key = 'your_super_secret_key_here' 

# Point to the new database location
DB_PATH = os.path.join('data', 'users.db')

def get_db_connection():
    # Update the connection to use DB_PATH
    conn = sqlite3.connect(DB_PATH) 
    conn.row_factory = sqlite3.Row
    return conn

# ... (The rest of your routes remain exactly the same) ...

def init_db():
    """Creates the users table in the data folder."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"User database initialized successfully at: {DB_PATH}")

if __name__ == '__main__':
    init_db()