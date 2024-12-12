from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from PIL import Image
import io
import pymysql
from bcrypt import checkpw
import cv2
from datetime import datetime
import numpy as np
# DB_CONFIG = {
#     'host': 'localhost',        # Имя хоста
#     'user': 'root',             # Пользователь MySQL
#     'password': '123',          # Пароль MySQL
#     'database': 'site_users',   # Имя базы данных
# }
# Инициализация Flask приложения
app = Flask(__name__)
CORS(app)  # Разрешаем CORS для всех запросов



# Подключение к базе данных


# def get_db_connection():
#     return pymysql.connect(
#         host=DB_CONFIG['host'],
#         user=DB_CONFIG['user'],
#         password=DB_CONFIG['password'],
#         database=DB_CONFIG['database'],
#         charset='utf8mb4',
#         cursorclass=pymysql.cursors.DictCursor
#     )
#
# # Маршрут для проверки логина
#
# @app.route('/login', methods=['POST'])
# def login():
#     try:
#         data = request.json
#         username = data.get('username')
#         password = data.get('password')
#
#         if not username or not password:
#             return jsonify({"success": False, "message": "Missing credentials"}), 400
#
#         conn = get_db_connection()
#         if not conn:
#             return jsonify({"success": False, "message": "Database connection error"}), 500
#
#         try:
#             with conn.cursor() as cursor:
#                 sql = "SELECT * FROM users WHERE username = %s AND password_hash = %s"
#                 cursor.execute(sql, (username, password))
#                 user = cursor.fetchone()
#
#                 if user:
#                     return jsonify({"success": True}), 200
#                 else:
#                     return jsonify({"success": False, "message": "Invalid credentials"}), 401
#         except Exception as e:
#             print("Database query error:", e)  # Выводим подробную ошибку
#             return jsonify({"success": False, "message": str(e)}), 500
#         finally:
#             conn.close()
#     except Exception as e:
#         print("General error:", e)  # Выводим ошибку общего уровня
#         return jsonify({"success": False, "message": str(e)}), 500
#
# @app.route('/add_user', methods=['POST'])
# def add_user():
#     try:
#         data = request.json
#         username = data.get('username')
#         password = data.get('password')
#         position = data.get('position')
#         access_rights = data.get('accessRights')
#
#         if not username or not password or not position or not access_rights:
#             return jsonify({"success": False, "message": "Заполните все поля"}), 400
#
#         registration_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Форматируем дату
#
#         conn = get_db_connection()
#         if not conn:
#             return jsonify({"success": False, "message": "Ошибка подключения к БД"}), 500
#
#         try:
#             with conn.cursor() as cursor:
#                 # Проверяем, существует ли пользователь
#                 cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
#                 if cursor.fetchone():
#                     return jsonify({"success": False, "message": "Пользователь уже существует"}), 400
#
#                 # Добавляем нового пользователя
#                 sql = """
#                     INSERT INTO users (username, password_hash, registration_date, position, access_rights)
#                     VALUES (%s, %s, %s, %s, %s)
#                 """
#                 cursor.execute(sql, (username, password, registration_date, position, access_rights))
#                 conn.commit()
#
#                 return jsonify({"success": True, "message": "Пользователь успешно добавлен"}), 201
#         except Exception as e:
#             print("Ошибка при добавлении пользователя:", e)
#             return jsonify({"success": False, "message": "Ошибка базы данных"}), 500
#         finally:
#             conn.close()
#     except Exception as e:
#         print("Общая ошибка:", e)
#         return jsonify({"success": False, "message": str(e)}), 500
#
# @app.route('/log_action', methods=['POST'])
# def log_action():
#     try:
#         data = request.json
#         username = data.get('username')
#         action = data.get('action')
#         page = data.get('page')
#         timestamp = data.get('timestamp')
#
#         if not username or not action or not page or not timestamp:
#             return jsonify({"success": False, "message": "Missing required fields"}), 400
#
#
#         timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).strftime('%Y-%m-%d %H:%M:%S')
#         # Подключаемся к базе данных
#         conn = get_db_connection()
#         if not conn:
#             return jsonify({"success": False, "message": "Database connection error"}), 500
#
#         try:
#             with conn.cursor() as cursor:
#                 # Вставляем данные о действии в таблицу
#                 sql = """
#                     INSERT INTO user_action (username, action, page, timestamp)
#                     VALUES (%s, %s, %s, %s)
#                 """
#                 cursor.execute(sql, (username, action, page, timestamp))
#                 conn.commit()
#                 return jsonify({"success": True, "message": "Action logged successfully"}), 200
#         except Exception as e:
#             print("Error logging action:", e)
#             return jsonify({"success": False, "message": "Database error"}), 500
#         finally:
#             conn.close()
#
#     except Exception as e:
#         print("Error:", e)
#         return jsonify({"success": False, "message": "Server error"}), 500
# @app.route('/get_users', methods=['GET'])
# def get_users():
#     try:
#         conn = get_db_connection()
#         if not conn:
#             return jsonify([]), 500
#
#         with conn.cursor() as cursor:
#             cursor.execute("SELECT username, position, registration_date, access_rights FROM users")
#             users = cursor.fetchall()
#             return jsonify(users), 200
#     except Exception as e:
#         print("Ошибка получения пользователей:", e)
#         return jsonify([]), 500
#
# @app.route('/get_user_actions', methods=['GET'])
# def get_user_actions():
#     try:
#         conn = get_db_connection()
#         if not conn:
#             return jsonify([]), 500
#
#         with conn.cursor() as cursor:
#             cursor.execute("SELECT username, action, page, timestamp FROM user_action ORDER BY timestamp DESC")
#             actions = cursor.fetchall()
#             return jsonify(actions), 200
#     except Exception as e:
#         print("Ошибка получения действий:", e)
#         return jsonify([]), 500
# Функция для сжатия изображения в буфер
def compress_image_to_buffer(image, quality):
    buffer = io.BytesIO()  # Создаем буфер в памяти
    image.save(buffer, format="JPEG", quality=quality)  # Сохраняем изображение в буфер с указанным качеством
    buffer.seek(0)  # Перемещаем указатель на начало буфера
    return buffer

# Функция для выделения цветов из изображения
def extract_color_tones(image, color):
    image_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)  # Преобразуем изображение в формат OpenCV
    image_hsv = cv2.cvtColor(image_cv, cv2.COLOR_BGR2HSV)  # Преобразуем изображение в цветовое пространство HSV

    # Определяем диапазоны для разных цветов
    color_ranges = {
        'red': [(0, 100, 100), (10, 255, 255), (160, 100, 100), (179, 255, 255)],  # Диапазоны для красного
        'blue': [(100, 150, 0), (140, 255, 255)],  # Диапазоны для синего
        'green': [(40, 50, 50), (80, 255, 255)],  # Диапазоны для зеленого
        # Можно добавить другие цвета
    }

    # Если цвет не поддерживается, возвращаем ошибку
    if color not in color_ranges:
        return "Цвет не поддерживается", 400

    # Создаем маску для выбранного цвета
    ranges = color_ranges[color]
    if len(ranges) == 2:
        mask = cv2.inRange(image_hsv, ranges[0], ranges[1])  # Для одного диапазона
    else:
        mask1 = cv2.inRange(image_hsv, ranges[0], ranges[1])  # Для первого диапазона
        mask2 = cv2.inRange(image_hsv, ranges[2], ranges[3])  # Для второго диапазона
        mask = cv2.bitwise_or(mask1, mask2)  # Объединяем маски

    # Применяем маску к изображению
    highlighted = cv2.bitwise_and(image_cv, image_cv, mask=mask)
    highlighted_rgb = cv2.cvtColor(highlighted, cv2.COLOR_BGR2RGB)  # Конвертируем обратно в RGB
    return Image.fromarray(highlighted_rgb)

# Маршрут для сжатия изображения
@app.route("/compress-image", methods=["POST"])
def compress_image():
    # Проверка наличия файла в запросе
    if 'file' not in request.files:
        return "Нет файла", 400

    file = request.files['file']
    if file.filename == '':  # Если файл не выбран
        return "Файл не выбран", 400

    try:
        # Получаем качество сжатия из формы (по умолчанию 75)
        quality = int(request.form.get('quality', 75))
        img = Image.open(file.stream)  # Открываем изображение
        compressed_buffer = compress_image_to_buffer(img, quality=quality)  # Сжимаем изображение
        return send_file(compressed_buffer, mimetype="image/jpeg")  # Отправляем сжатое изображение
    except Exception as e:
        return str(e), 500  # Ошибка сервера

# Маршрут для выделения цветов из изображения
@app.route("/highlight-color", methods=["POST"])
def extract_color():
    # Проверка наличия файла в запросе
    if 'file' not in request.files:
        return "Нет файла", 400

    file = request.files['file']
    color = request.form.get('color', 'red')  # Получаем цвет из формы, по умолчанию 'red'

    if file.filename == '':  # Если файл не выбран
        return "Файл не выбран", 400

    try:
        img = Image.open(file.stream)  # Открываем изображение
        color_img = extract_color_tones(img, color)  # Выделяем выбранный цвет
        buffer = io.BytesIO()  # Создаем буфер для сохранения изображения
        color_img.save(buffer, format="JPEG")  # Сохраняем в буфер
        buffer.seek(0)  # Перемещаем указатель на начало буфера
        return send_file(buffer, mimetype="image/jpeg")  # Отправляем изображение с выделенным цветом
    except Exception as e:
        return str(e), 500  # Ошибка сервера

 #Функция для обработки изображений
def segment_and_find_contours(image):
    # Преобразуем PIL изображение в OpenCV формат
    image_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

    # Конвертируем изображение в оттенки серого
    gray_image = cv2.cvtColor(image_cv, cv2.COLOR_BGR2GRAY)

    # Применяем пороговую сегментацию
    _, binary_mask = cv2.threshold(gray_image, 128, 255, cv2.THRESH_BINARY)

    # Находим контуры
    contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Создаем изображение для отображения контуров
    contour_image = np.zeros_like(image_cv)
    cv2.drawContours(contour_image, contours, -1, (0, 255, 0), 2)  # Зеленые контуры

    # Преобразуем обратно в формат PIL
    contour_image_rgb = cv2.cvtColor(contour_image, cv2.COLOR_BGR2RGB)
    return Image.fromarray(contour_image_rgb)

# Новый маршрут для автоматической сегментации изображений
@app.route("/segment-image", methods=["POST"])
def segment_image():
    if 'file' not in request.files:
        return "Нет файла", 400

    file = request.files['file']
    if file.filename == '':
        return "Файл не выбран", 400

    try:
        img = Image.open(file.stream)  # Открываем изображение
        segmented_img = segment_and_find_contours(img)  # Выполняем сегментацию

        # Сохраняем изображение с контурами в буфер
        buffer = io.BytesIO()
        segmented_img.save(buffer, format="JPEG")
        buffer.seek(0)

        return send_file(buffer, mimetype="image/jpeg")  # Отправляем результат клиенту
    except Exception as e:
        return str(e), 500  # Ошибка сервера
def calculate_homogeneity(image_channels):
    """ Рассчитать однородность структуры как стандартное отклонение для каждого канала. """
    return [np.std(channel) for channel in image_channels]

# Обработка красного канала
def process_red_channel(image):
    red_channel = np.zeros_like(image)
    red_channel[:, :, 2] = image[:, :, 2]  # Красный
    return red_channel

# Обработка зеленого канала
def process_green_channel(image):
    green_channel = np.zeros_like(image)
    green_channel[:, :, 1] = image[:, :, 1]  # Зеленый
    return green_channel

# Обработка синего канала
def process_blue_channel(image):
    blue_channel = np.zeros_like(image)
    blue_channel[:, :, 0] = image[:, :, 0]  # Синий
    return blue_channel

# Обработка оттенков (Hue)
def process_hue(image):
    hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    h, _, _ = cv2.split(hsv_image)
    return cv2.merge([h, h, h])  # Преобразуем обратно в 3-канальное изображение

# Обработка насыщенности (Saturation)
def process_saturation(image):
    hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    _, s, _ = cv2.split(hsv_image)
    return cv2.merge([s, s, s])  # Преобразуем обратно в 3-канальное изображение

# Обработка яркости (Value)
def process_value(image):
    hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    _, _, v = cv2.split(hsv_image)
    return cv2.merge([v, v, v])  # Преобразуем обратно в 3-канальное изображение

# Обработка яркости (Lightness) в HLS
def process_lightness_hls(image):
    hls_image = cv2.cvtColor(image, cv2.COLOR_BGR2HLS)
    _, l, _ = cv2.split(hls_image)
    return cv2.merge([l, l, l])  # Преобразуем обратно в 3-канальное изображение
# Маршрут для обработки красного канала
def handle_channel_processing(file, processing_function):
    try:
        # Читаем изображение из файла
        file_bytes = np.frombuffer(file.read(), np.uint8)
        image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

        # Применяем обработку
        processed_image = processing_function(image)

        # Кодируем изображение обратно в JPEG
        _, buffer = cv2.imencode('.jpg', processed_image)

        return send_file(
            io.BytesIO(buffer),
            mimetype="image/jpeg"
        )
    except Exception as e:
        return str(e), 500
@app.route("/red-channel", methods=["POST"])
def red_channel():
    if 'file' not in request.files:
        return "Нет файла", 400
    return handle_channel_processing(request.files['file'], process_red_channel)

@app.route("/green-channel", methods=["POST"])
def green_channel():
    if 'file' not in request.files:
        return "Нет файла", 400
    return handle_channel_processing(request.files['file'], process_green_channel)

@app.route("/blue-channel", methods=["POST"])
def blue_channel():
    if 'file' not in request.files:
        return "Нет файла", 400
    return handle_channel_processing(request.files['file'], process_blue_channel)

@app.route("/hue", methods=["POST"])
def hue():
    if 'file' not in request.files:
        return "Нет файла", 400
    return handle_channel_processing(request.files['file'], process_hue)

@app.route("/saturation", methods=["POST"])
def saturation():
    if 'file' not in request.files:
        return "Нет файла", 400
    return handle_channel_processing(request.files['file'], process_saturation)

@app.route("/value", methods=["POST"])
def value():
    if 'file' not in request.files:
        return "Нет файла", 400
    return handle_channel_processing(request.files['file'], process_value)

@app.route("/lightness-hls", methods=["POST"])
def lightness_hls():
    if 'file' not in request.files:
        return "Нет файла", 400
    return handle_channel_processing(request.files['file'], process_lightness_hls)




# Запуск приложения
if __name__ == "__main__":
    app.run(debug=True)  # Запускаем сервер в режиме отладки
