from flask import Blueprint, render_template, session, redirect, url_for, current_app, request, jsonify
from database import *
import os
import psutil
import hashlib

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


def split_full_name(full_name):
    """Разделяет полное имя на фамилию, имя и отчество"""
    parts = full_name.strip().split()
    if len(parts) >= 3:
        return parts[0], parts[1], parts[2]
    elif len(parts) == 2:
        return parts[0], parts[1], ''
    else:
        return parts[0] if parts else '', '', ''


def get_user_images(user_id):
    """Получает все изображения пользователя из БД"""
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
                    if hasattr(img['upload_date'], 'strftime'):
                        img['upload_date'] = img['upload_date'].strftime('%d.%m.%Y %H:%M')
                    else:
                        img['upload_date'] = str(img['upload_date'])

                # Добавляем URL для доступа к изображению
                img['url'] = f"/static/uploads/{img['filename']}"

            return images
    except Exception as e:
        print(f"Ошибка при получении изображений: {str(e)}")
        return []
    finally:
        if conn:
            conn.close()


@pages_bp.before_request
def before_request():
    """Обновляем сессию перед каждым запросом, но не требуем авторизацию"""
    if 'user' in session:
        refresh_user_session()


@pages_bp.route('/')
def home():
    """Корневой маршрут - перенаправляет на главную страницу"""
    return redirect(url_for('pages.sam2_design'))


@pages_bp.route('/sam2_design')
def sam2_design():
    """Главная страница дизайна SAM2 - доступна всем, включая гостей"""
    # Для гостей создаем специальную сессию или просто передаем user=None
    guest_user = {
        'id': None,
        'first_name': 'Гость',
        'last_name': '',
        'access_rights': 'guest'
    }

    # Если пользователь авторизован, используем его данные
    if 'user' in session:
        user = session['user']
    else:
        user = guest_user

    return render_template('sam2_design.html', user=user, is_guest=('user' not in session))


@pages_bp.route('/administration')
def administration():
    """Страница администратора - только для админов"""
    if 'user' not in session:
        return redirect(url_for('auth.login_page'))

    user = session['user']
    if user.get('access_rights') != 'admin':
        return redirect(url_for('pages.sam2_design'))

    # Получаем список всех пользователей
    all_users = get_all_users()

    return render_template('administration.html', user=user, users=all_users)


@pages_bp.route('/profile')
def profile():
    """Страница профиля пользователя - только для авторизованных"""
    if 'user' not in session:
        return redirect(url_for('auth.login_page'))

    refresh_user_session()

    # Получаем ВСЕ изображения пользователя
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, filename, upload_date
                FROM user_images
                WHERE user_id = %s
                ORDER BY upload_date DESC
            """, (session['user']['id'],))
            images = cursor.fetchall()

            # Преобразуем даты в строки прямо здесь
            for img in images:
                if img.get('upload_date'):
                    if hasattr(img['upload_date'], 'strftime'):
                        img['upload_date'] = img['upload_date'].strftime('%d.%m.%Y')
                    else:
                        # Если уже строка, оставляем как есть
                        img['upload_date'] = str(img['upload_date'])
    finally:
        conn.close()

    return render_template("profile.html", user=session['user'], images=images)


@pages_bp.route('/stats')
def stats():
    """Страница статистики - только для авторизованных"""
    if 'user' not in session:
        return redirect(url_for('auth.login_page'))
    refresh_user_session()
    return render_template('stats.html', user=session['user'])


@pages_bp.route('/test')
def test():
    """Тестовая страница - доступна всем"""
    guest_user = {
        'id': None,
        'first_name': 'Гость',
        'last_name': '',
        'access_rights': 'guest'
    }

    if 'user' in session:
        user = session['user']
    else:
        user = guest_user

    return render_template('test.html', user=user)


@pages_bp.route('/delete_image/<int:image_id>', methods=['DELETE'])
def delete_image(image_id):
    """Удаление изображения - только для авторизованных"""
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
                WHERE id = %s AND user_id = %s
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
    """Обновление профиля пользователя - только для авторизованных"""
    if 'user' not in session:
        return jsonify({"success": False, "message": "Требуется авторизация"}), 401

    data = request.get_json()
    user_id = data.get('user_id')

    if not user_id:
        return jsonify({"success": False, "message": "Не указан ID пользователя"}), 400

    current_user = session['user']
    if current_user.get('access_rights') != 'admin' and str(current_user.get('id')) != str(user_id):
        return jsonify({"success": False, "message": "Недостаточно прав"}), 403

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            update_fields = []
            update_values = []

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


@pages_bp.route('/api/user_images')
def api_user_images():
    """API для получения всех изображений пользователя"""
    if 'user' not in session:
        return jsonify({"success": False, "message": "Необходима авторизация"}), 401

    refresh_user_session()
    user_id = session['user']['id']

    images = get_user_images(user_id)

    return jsonify({
        "success": True,
        "images": images
    })


@pages_bp.route('/image/<int:image_id>')
def view_image(image_id):
    """Просмотр конкретного изображения"""
    if 'user' not in session:
        return redirect(url_for('auth.login_page'))

    refresh_user_session()
    user_id = session['user']['id']

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, filename, upload_date
                FROM user_images
                WHERE id = %s AND user_id = %s
            """, (image_id, user_id))
            image = cursor.fetchone()

            if not image:
                return redirect(url_for('pages.profile'))

            if image.get('upload_date') and hasattr(image['upload_date'], 'strftime'):
                image['upload_date'] = image['upload_date'].strftime('%d.%m.%Y %H:%M')

            image['url'] = f"/static/uploads/{image['filename']}"

            return render_template("view_image.html",
                                   user=session['user'],
                                   image=image)
    except Exception as e:
        print(f"Ошибка при получении изображения: {e}")
        return redirect(url_for('pages.profile'))
    finally:
        conn.close()


@pages_bp.route('/api/system_stats')
def system_stats():
    """API для получения статистики системы - только для админов"""
    if 'user' not in session or session['user'].get('access_rights') != 'admin':
        return jsonify({"error": "Unauthorized"}), 401

    try:
        cpu_usage = psutil.cpu_percent(interval=1)
        memory_usage = psutil.virtual_memory().percent
        disk_usage = psutil.disk_usage('/').percent

        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                processes.append({
                    'pid': proc.info['pid'],
                    'name': proc.info['name'],
                    'cpu': proc.info['cpu_percent'] or 0,
                    'memory': proc.info['memory_percent'] or 0
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        processes = sorted(processes, key=lambda p: p['cpu'], reverse=True)[:10]

        return jsonify({
            'cpu_usage': cpu_usage,
            'memory_usage': memory_usage,
            'disk_usage': disk_usage,
            'processes': processes
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500