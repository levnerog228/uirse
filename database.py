import pymysql
from flask import jsonify, request
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session
import hashlib
from datetime import datetime, date  # Добавляем импорт date

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '12345678',
    'database': 'Process_image',
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


def split_full_name(full_name):
    """Разбивает полное имя на фамилию, имя и отчество"""
    parts = full_name.split()
    last_name = parts[0] if len(parts) > 0 else ''
    first_name = parts[1] if len(parts) > 1 else ''
    middle_name = parts[2] if len(parts) > 2 else ''
    return last_name, first_name, middle_name

def update_user_profile(user_id, field, value):
    """Обновляет данные профиля пользователя"""
    conn = None
    try:
        # Проверяем, что поле разрешено для обновления
        allowed_fields = ['first_name', 'last_name', 'email', 'phone', 'birth_date']
        if field not in allowed_fields:
            return False, "Недопустимое поле для обновления"

        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Для email проверяем уникальность
            if field == 'email':
                cursor.execute("SELECT id FROM users WHERE email = %s AND id != %s", (value, user_id))
                if cursor.fetchone():
                    return False, "Пользователь с таким email уже существует"

            sql = f"UPDATE users SET {field} = %s WHERE id = %s"
            cursor.execute(sql, (value, user_id))
            conn.commit()
            return True, "Данные успешно обновлены"
    except Exception as e:
        return False, str(e)
    finally:
        if conn:
            conn.close()

def login():
    conn = None
    try:
        data = request.form
        email = data.get('username')  # Здесь ожидается email (поле переименовано в форме)
        password = data.get('password')

        if not email or not password:
            return False, "Missing credentials", None

        conn = get_db_connection()
        if not conn:
            return False, "Database connection error", None

        with conn.cursor() as cursor:
            hashed_password = hashlib.sha256(password.encode()).hexdigest()

            sql = """SELECT id, \
                            first_name, \
                            last_name, \
                            middle_name,
                            CONCAT(last_name, ' ', first_name, ' ', IFNULL(middle_name, '')) AS full_name,
                            email, \
                            phone, \
                            birth_date, \
                            registration_date,
                            avatar_url, \
                            position, \
                            access_rights
                     FROM users
                     WHERE email = %s \
                       AND password_hash = %s"""
            cursor.execute(sql, (email, hashed_password))
            user = cursor.fetchone()

            if user:
                if user.get('birth_date'):
                    user['birth_date'] = user['birth_date'].strftime('%d.%m.%Y')
                if user.get('registration_date'):
                    user['registration_date'] = user['registration_date'].strftime('%d.%m.%Y')

                # Проверяем, является ли пользователь администратором
                if user.get('access_rights') == 'admin':
                    return True, "Admin login successful", user
                else:
                    return True, "Login successful", user
            else:
                return False, "Invalid credentials", None
    except Exception as e:
        return False, str(e), None
    finally:
        if conn:
            conn.close()


def add_user():
    conn = None
    try:
        data = request.json
        full_name = data.get('full_name')
        password = data.get('password')
        position = data.get('position')
        email = data.get('email')
        phone = data.get('phone', '')
        birth_date = data.get('birth_date', None)
        access_rights = data.get('access_rights', 'user')  # По умолчанию 'user'

        # Разбиваем ФИО на компоненты
        last_name, first_name, middle_name = split_full_name(full_name)

        # Валидация обязательных полей
        required_fields = {
            'full_name': full_name,
            'password': password,
            'email': email,
            'position': position
        }

        missing_fields = [field for field, value in required_fields.items() if not value]
        if missing_fields:
            return jsonify({
                "success": False,
                "message": f"Заполните все обязательные поля: {', '.join(missing_fields)}"
            }), 400

        # Преобразование даты рождения в формат MySQL
        if birth_date:
            try:
                birth_date = datetime.strptime(birth_date, '%d.%m.%Y').strftime('%Y-%m-%d')
            except ValueError:
                return jsonify({
                    "success": False,
                    "message": "Неверный формат даты рождения. Используйте ДД.ММ.ГГГГ"
                }), 400

        registration_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        conn = get_db_connection()
        if not conn:
            return jsonify({"success": False, "message": "Ошибка подключения к БД"}), 500

        with conn.cursor() as cursor:
            # Проверка уникальности email
            cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                return jsonify({
                    "success": False,
                    "message": "Пользователь с таким email уже существует"
                }), 400

            sql = """
                  INSERT INTO users (last_name, \
                                     first_name, \
                                     middle_name, \
                                     password_hash, \
                                     email, \
                                     phone, \
                                     birth_date, \
                                     registration_date, \
                                     position, \
                                     access_rights) \
                  VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) \
                  """
            cursor.execute(sql, (
                last_name,
                first_name,
                middle_name,
                hashed_password,
                email,
                phone,
                birth_date,
                registration_date,
                position,
                access_rights
            ))
            conn.commit()

            # Получаем данные нового пользователя
            cursor.execute("""
                           SELECT id,
                                  first_name,
                                  last_name,
                                  middle_name,
                                  CONCAT(last_name, ' ', first_name, ' ', IFNULL(middle_name, '')) AS full_name,
                                  email,
                                  phone,
                                  birth_date,
                                  registration_date,
                                  position,
                                  access_rights
                           FROM users
                           WHERE email = %s
                           """, (email,))
            new_user = cursor.fetchone()

            # Форматирование дат для отображения
            if new_user.get('birth_date'):
                new_user['birth_date'] = new_user['birth_date'].strftime('%d.%m.%Y')
            if new_user.get('registration_date'):
                new_user['registration_date'] = new_user['registration_date'].strftime('%d.%m.%Y')

            return jsonify({
                "success": True,
                "message": "Пользователь успешно добавлен",
                "user": new_user
            }), 201

    except Exception as e:
        print(f"Ошибка при регистрации пользователя: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Ошибка базы данных: {str(e)}"
        }), 500
    finally:
        if conn:
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


# ============== Функции для работы с изображениями ==============
def save_user_image(user_id, filename):
    """Сохраняет информацию о изображении пользователя в БД"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = """INSERT INTO user_images (user_id, filename, upload_date)
                     VALUES (%s, %s, NOW())"""
            cursor.execute(sql, (user_id, filename))
            conn.commit()
            return True
    except Exception as e:
        print(f"Ошибка при сохранении изображения: {str(e)}")
        return False
    finally:
        if conn:
            conn.close()


def get_all_users():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                           SELECT 
                    id,
                    first_name,
                    last_name, 
                    middle_name,
                    email,
                    phone,
                    birth_date,
                    position, 
                    registration_date, 
                    access_rights
                FROM users
                ORDER BY last_name, first_name
            """)
            users = cursor.fetchall()

            # Преобразуем даты в строки и формируем полное имя
            for user in users:
                if user.get('registration_date') and isinstance(user['registration_date'], datetime):
                    user['registration_date'] = user['registration_date'].strftime('%d.%m.%Y %H:%M:%S')

                if user.get('birth_date'):
                    try:
                        # Вариант 1: если приходит datetime.date
                        if isinstance(user['birth_date'], date):
                            user['birth_date'] = user['birth_date'].strftime('%d.%m.%Y')
                    except Exception as e:
                        print(f"Ошибка форматирования birth_date: {e}")
                        user['birth_date'] = 'Некорректная дата'

                # Формируем полное имя
                user[
                    'full_name'] = f"{user['last_name']} {user['first_name']} {user['middle_name'] if user['middle_name'] else ''}".strip()

            return users
    except Exception as e:
        print(f"Ошибка при получении пользователей: {str(e)}")
        return []
    finally:
        conn.close()

def get_user_images(user_id):
    """Получает все изображения пользователя"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = """SELECT id, filename, upload_date
                     FROM user_images
                     WHERE user_id = %s
                     ORDER BY upload_date DESC"""
            cursor.execute(sql, (user_id,))
            images = cursor.fetchall()

            # Преобразуем даты в строки
            for img in images:
                if img.get('upload_date'):
                    img['upload_date'] = img['upload_date'].strftime('%d.%m.%Y')
            return images
    except Exception as e:
        print(f"Ошибка при получении изображений: {str(e)}")
        return []
    finally:
        if conn:
            conn.close()


def delete_user_image(image_id, user_id):
    """Удаляет изображение пользователя"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Сначала получаем имя файла
            sql = """SELECT filename \
                     FROM user_images
                     WHERE id = %s \
                       AND user_id = %s"""
            cursor.execute(sql, (image_id, user_id))
            image = cursor.fetchone()

            if not image:
                return False, "Изображение не найдено или доступ запрещен"

            # Удаляем запись из БД
            sql = """DELETE \
                     FROM user_images
                     WHERE id = %s \
                       AND user_id = %s"""
            cursor.execute(sql, (image_id, user_id))
            conn.commit()

            return True, image['filename']
    except Exception as e:
        print(f"Ошибка при удалении изображения: {str(e)}")
        return False, str(e)
    finally:
        if conn:
            conn.close()


def get_image_by_id(image_id, user_id):
    """Получает информацию о конкретном изображении"""
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = """SELECT id, filename, upload_date
                     FROM user_images
                     WHERE id = %s \
                       AND user_id = %s"""
            cursor.execute(sql, (image_id, user_id))
            image = cursor.fetchone()

            if image and image.get('upload_date'):
                image['upload_date'] = image['upload_date'].strftime('%d.%m.%Y')
            return image
    except Exception as e:
        print(f"Ошибка при получении изображения: {str(e)}")
        return None
    finally:
        if conn:
            conn.close()

def get_current_user():
    user_id = session.get('user_id')
    if not user_id:
        return None
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, first_name, last_name, email, phone, birth_date, avatar_url
                FROM users WHERE id = %s
            """, (user_id,))
            return cursor.fetchone()
    finally:
        conn.close()

