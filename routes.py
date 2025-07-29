from flask import Blueprint, render_template, session, redirect, url_for, current_app, request, jsonify
from database import *
import os

pages_bp = Blueprint('pages', __name__)


def refresh_user_session(user_id=None):
    """Обновляет данные пользователя в сессии из БД"""
    if user_id is None:
        user_id = session.get('user', {}).get('id')

    if not user_id:
        return False

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            user_data = cursor.fetchone()
            if user_data:
                session['user'] = dict(user_data)
                session.modified = True
                return True
    except Exception as e:
        print(f"Ошибка при обновлении сессии: {e}")
    finally:
        conn.close()
    return False


@pages_bp.before_request
def before_request():
    """Обновляем сессию перед каждым запросом"""
    if 'user' in session:
        refresh_user_session()


@pages_bp.route('/compress')
def compress_page():
    if 'user' not in session:
        return redirect(url_for('auth.login_page'))
    refresh_user_session()
    return render_template('compress.html', user=session['user'])


@pages_bp.route('/main')
def main_page():
    if 'user' not in session:
        return redirect(url_for('auth.login_page'))
    refresh_user_session()
    return render_template('main.html', user=session['user'])


@pages_bp.route('/select_area')
def select_area():
    if 'user' not in session:
        return redirect(url_for('auth.login_page'))
    refresh_user_session()
    return render_template('select_area.html', user=session['user'])


@pages_bp.route('/find_area')
def find_area():
    if 'user' not in session:
        return redirect(url_for('auth.login_page'))
    refresh_user_session()
    return render_template("find_area.html", user=session['user'])


@pages_bp.route('/administration')
def administration():
    if 'user' not in session:
        return redirect(url_for('auth.login_page'))

    user = session['user']
    if user.get('access_rights') != 'admin':
        return redirect(url_for('pages.find_area'))

    # Получаем список всех пользователей
    all_users = get_all_users()

    return render_template('administration.html', user=user, users=all_users)

@pages_bp.route('/profile')
def profile():
    if 'user' not in session:
        return redirect(url_for('auth.login_page'))

    refresh_user_session()

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                           SELECT id, filename, upload_date
                           FROM user_images
                           WHERE user_id = %s
                           ORDER BY upload_date DESC LIMIT 4
                           """, (session['user']['id'],))
            images = cursor.fetchall()
    finally:
        conn.close()

    return render_template("profile.html", user=session['user'], images=images)


@pages_bp.route('/test')
def test():
    if 'user' not in session:
        return redirect(url_for('auth.login_page'))
    refresh_user_session()
    return render_template('test.html', user=session['user'])


@pages_bp.route('/')
def home():
    if 'user' in session:
        refresh_user_session()
        return redirect(url_for('pages.find_area'))
    return render_template('login.html')


@pages_bp.route('/delete_image/<int:image_id>', methods=['DELETE'])
def delete_image(image_id):
    if 'user' not in session:
        return jsonify({"success": False, "message": "Необходима авторизация"}), 401

    refresh_user_session()
    user_id = session['user']['id']

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                           SELECT filename
                           FROM user_images
                           WHERE id = %s
                             AND user_id = %s
                           """, (image_id, user_id))
            image = cursor.fetchone()

            if not image:
                return jsonify({"success": False, "message": "Изображение не найдено"}), 404

            try:
                os.remove(os.path.join(current_app.static_folder, 'uploads', image['filename']))
            except OSError as e:
                print(f"Ошибка при удалении файла: {e}")

            cursor.execute("DELETE FROM user_images WHERE id = %s", (image_id,))
            conn.commit()

            return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()


@pages_bp.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user' not in session:
        return jsonify({"success": False, "message": "Требуется авторизация"}), 401

    data = request.get_json()
    user_id = data.get('user_id')

    if not user_id:
        return jsonify({"success": False, "message": "Не указан ID пользователя"}), 400

    # Проверка прав (только админ может редактировать других пользователей)
    current_user = session['user']
    if current_user.get('access_rights') != 'admin' and str(current_user.get('id')) != str(user_id):
        return jsonify({"success": False, "message": "Недостаточно прав"}), 403

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            update_fields = []
            update_values = []

            # Динамически собираем только те поля, которые нужно обновить
            if 'full_name' in data:
                last_name, first_name, middle_name = split_full_name(data['full_name'])
                update_fields.extend(['last_name = %s', 'first_name = %s', 'middle_name = %s'])
                update_values.extend([last_name, first_name, middle_name])

            if 'email' in data:
                update_fields.append('email = %s')
                update_values.append(data['email'])

            if 'password' in data and data['password']:
                hashed_password = hashlib.sha256(data['password'].encode()).hexdigest()
                update_fields.append('password_hash = %s')
                update_values.append(hashed_password)

            if 'position' in data:
                update_fields.append('position = %s')
                update_values.append(data['position'])

            if 'phone' in data:
                update_fields.append('phone = %s')
                update_values.append(data['phone'])

            if 'birth_date' in data:
                update_fields.append('birth_date = %s')
                update_values.append(data['birth_date'])

            if 'access_rights' in data:
                update_fields.append('access_rights = %s')
                update_values.append(data['access_rights'])

            if not update_fields:
                return jsonify({"success": False, "message": "Нет данных для обновления"}), 400

            sql = f"UPDATE users SET {', '.join(update_fields)} WHERE id = %s"
            update_values.append(user_id)
            cursor.execute(sql, update_values)
            conn.commit()

            return jsonify({"success": True, "message": "Данные пользователя обновлены"})

    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if conn:
            conn.close()
