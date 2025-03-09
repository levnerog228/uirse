import pymysql
from flask import jsonify, request
from datetime import datetime

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '12345678',
    'database': 'site_users',
}

def get_db_connection():
    return pymysql.connect(
        host=DB_CONFIG['host'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password'],
        database=DB_CONFIG['database'],
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

def login():
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({"success": False, "message": "Missing credentials"}), 400

        conn = get_db_connection()
        if not conn:
            return jsonify({"success": False, "message": "Database connection error"}), 500

        with conn.cursor() as cursor:
            sql = "SELECT * FROM users WHERE username = %s AND password_hash = %s"
            cursor.execute(sql, (username, password))
            user = cursor.fetchone()

            if user:
                return jsonify({"success": True}), 200
            else:
                return jsonify({"success": False, "message": "Invalid credentials"}), 401
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()

def add_user():
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        position = data.get('position')
        access_rights = data.get('accessRights')

        if not username or not password or not position or not access_rights:
            return jsonify({"success": False, "message": "Заполните все поля"}), 400

        registration_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        conn = get_db_connection()
        if not conn:
            return jsonify({"success": False, "message": "Ошибка подключения к БД"}), 500

        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                return jsonify({"success": False, "message": "Пользователь уже существует"}), 400

            sql = """
                INSERT INTO users (username, password_hash, registration_date, position, access_rights)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (username, password, registration_date, position, access_rights))
            conn.commit()

            return jsonify({"success": True, "message": "Пользователь успешно добавлен"}), 201
    except Exception as e:
        return jsonify({"success": False, "message": "Ошибка базы данных"}), 500
    finally:
        conn.close()

def get_users():
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify([]), 500

        with conn.cursor() as cursor:
            cursor.execute("SELECT username, position, registration_date, access_rights FROM users")
            users = cursor.fetchall()
            return jsonify(users), 200
    except Exception as e:
        return jsonify([]), 500
    finally:
        conn.close()

def get_user_actions():
    try:
        conn = get_db_connection()
        if not conn:
            return jsonify([]), 500

        with conn.cursor() as cursor:
            cursor.execute("SELECT username, action, page, timestamp FROM user_action ORDER BY timestamp DESC")
            actions = cursor.fetchall()
            return jsonify(actions), 200
    except Exception as e:
        return jsonify([]), 500
    finally:
        conn.close()
