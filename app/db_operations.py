import sqlite3
from datetime import datetime

from aiogram.types import User

# Connect to SQLite database (or create it if it doesn't exist)
conn = sqlite3.connect("olx_notify.db")
cur = conn.cursor()

# Create user table
cur.execute('''
CREATE TABLE IF NOT EXISTS user (
    user_telegram_id INTEGER PRIMARY KEY,
    username TEXT,
    full_name TEXT,
    first_name TEXT,
    last_name TEXT,
    is_active BOOLEAN,
    created_at DATETIME
)
''')

# Create checker_query table
cur.execute('''
CREATE TABLE IF NOT EXISTS checker_query (
    query_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_telegram_id INTEGER,
    query_name TEXT,
    query_url TEXT,
    is_active BOOLEAN,
    is_deleted BOOLEAN,
    created_at DATETIME,
    FOREIGN KEY (user_telegram_id) REFERENCES user(user_telegram_id)
)
''')

# Create found_ad table
cur.execute('''
CREATE TABLE IF NOT EXISTS found_ad (
    ad_id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_id INTEGER,
    ad_url TEXT,
    ad_description TEXT,
    ad_price REAL,
    currency TEXT,
    is_active BOOLEAN,
    created_at DATETIME,
    FOREIGN KEY (query_id) REFERENCES checker_query(query_id)
)
''')

# Commit changes and close the connection
conn.commit()
cur.close()


def is_user_registered(user_telegram_id):
    cursor = conn.cursor()

    # Query to select all users based on user_telegram_id
    cursor.execute('''
    SELECT *
    FROM user
    WHERE user_telegram_id = ?
    ''', (user_telegram_id,))

    # Fetch all results
    users_data = cursor.fetchall()

    # Close the connection
    cursor.close()

    return len(users_data) > 0


def register_new_user(user: User):
    cursor = conn.cursor()

    # Get the current timestamp
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Insert a new user into the user table
    cursor.execute('''
        INSERT INTO user (user_telegram_id, username, full_name, first_name, last_name, is_active, 
        created_at)
        VALUES (?, ?, ?, ?, ?, 1, ?)
        ''', (user.id, user.username, user.full_name, user.first_name, user.last_name, created_at))

    # Commit the changes and close the connection
    conn.commit()
    cursor.close()


def create_new_checker_query(user_telegram_id, query_name, query_url):
    cursor = conn.cursor()

    # Get the current timestamp
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Insert a new checker query into the checker_query table
    cursor.execute('''
    INSERT INTO checker_query (user_telegram_id, query_name, query_url, is_active, is_deleted, created_at)
    VALUES (?, ?, ?, 1, 0, ?)
    ''', (user_telegram_id, query_name, query_url, created_at))

    # Commit the changes and close the connection
    conn.commit()
    cursor.close()


def update_checker_query_is_active(query_id, is_active):
    # Convert boolean to integer (1 for True, 0 for False)
    is_active_int = 1 if is_active else 0

    cursor = conn.cursor()

    # Update the 'is_active' status for the given query_id
    cursor.execute('''
        UPDATE checker_query
        SET is_active = ?
        WHERE query_id = ?
        ''', (is_active_int, query_id))

    # Commit the transaction and close the connection
    conn.commit()
    cursor.close()


def set_checker_query_deleted(query_id):
    cursor = conn.cursor()

    # Update the is_deleted field to 0 where the query_id matches
    cursor.execute('''
    UPDATE checker_query
    SET is_deleted = 1
    WHERE query_id = ?
    ''', (query_id,))

    # Commit the transaction and close the connection
    conn.commit()
    cursor.close()


def has_user_active_checker_queries(user_telegram_id):
    cursor = conn.cursor()

    # Execute the query to check for active checker queries
    cursor.execute('''
    SELECT 1
    FROM checker_query
    WHERE user_telegram_id = ? AND is_active = 1 AND is_deleted = 0
    LIMIT 1
    ''', (user_telegram_id,))

    # Fetch the result
    exists = cursor.fetchone() is not None

    # Close the connection
    cursor.close()

    return exists


def count_active_checker_queries(user_telegram_id):
    cursor = conn.cursor()

    # Execute the query to count active checker_query records
    cursor.execute('''
    SELECT COUNT(*)
    FROM checker_query
    WHERE user_telegram_id = ? AND is_active = 1 AND is_deleted = 0
    ''', (user_telegram_id,))

    # Fetch the result
    count = cursor.fetchone()[0]

    # Close the connection
    cursor.close()

    return int(count)


def count_inactive_checker_queries(user_telegram_id):
    cursor = conn.cursor()

    # Execute the query to count active checker_query records
    cursor.execute('''
    SELECT COUNT(*)
    FROM checker_query
    WHERE user_telegram_id = ? AND is_active = 0 AND is_deleted = 0
    ''', (user_telegram_id,))

    # Fetch the result
    count = cursor.fetchone()[0]

    # Close the connection
    cursor.close()

    return int(count)


def check_query_url_exists(user_telegram_id, query_url):
    cursor = conn.cursor()

    # Execute the query to check for existence
    cursor.execute('''
    SELECT 1
    FROM checker_query
    WHERE user_telegram_id = ? AND query_url = ?
    LIMIT 1
    ''', (user_telegram_id, query_url,))

    # Fetch the result
    exists = cursor.fetchone() is not None

    # Close the connection
    cursor.close()

    return exists


def create_new_found_ad(query_id, ad_url, ad_description, ad_price, currency):
    cursor = conn.cursor()

    # Get the current timestamp
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Insert the new record into the 'found_ad' table
    cursor.execute('''
    INSERT INTO found_ad (query_id, ad_url, ad_description, ad_price, currency, is_active, created_at)
    VALUES (?, ?, ?, ?, ?, 1, ?)
    ''', (query_id, ad_url, ad_description, ad_price, currency, created_at))

    # Commit the changes and close the connection
    conn.commit()
    cursor.close()


def update_found_ad_is_active(ad_id, is_active):
    # Convert boolean to integer (1 for True, 0 for False)
    is_active_int = 1 if is_active else 0

    cursor = conn.cursor()

    # Update the 'is_active' status for the given ad_id
    cursor.execute('''
        UPDATE found_ad
        SET is_active = ?
        WHERE ad_id = ?
        ''', (is_active_int, ad_id))

    # Commit the transaction and close the connection
    conn.commit()
    cursor.close()
