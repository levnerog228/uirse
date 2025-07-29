from flask import Blueprint, render_template, request, redirect, url_for, session
import database

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login_user')
def login_page():
    return render_template('login.html')


@auth_bp.route('/login', methods=['POST'])
def login():
    success, message, user = database.login()
    if success:
        session['user'] = user
        print("Логин успешен, сессия установлена для", user)

        # Проверяем, является ли пользователь администратором
        if user.get('access_rights') == 'admin':
            return redirect(url_for('pages.administration'))
        else:
            return redirect(url_for('pages.find_area'))
    else:
        print("Ошибка входа:", message)
        return render_template('login.html', error=message)

@auth_bp.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('pages.find_area'))
