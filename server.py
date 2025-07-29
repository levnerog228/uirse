from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from PIL import Image
import traceback
import io
import base64
import cv2
import numpy as np
from flask import render_template
import os
from werkzeug.utils import secure_filename
from datetime import datetime
from database import get_db_connection
from database import *
from sklearn.metrics.pairwise import cosine_similarity
from flask import Flask, render_template, request, redirect, url_for, session

# Импортируем маршруты страниц
from routes import pages_bp
from auth import auth_bp
from api import api_bp
import psutil
import time
from threading import Thread
from collections import deque

# Проверяем и создаем папку для загрузок
UPLOAD_FOLDER = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.secret_key = 'p98rnv4@sd!#Kf'  # обязательно уникальный и секретный ключ
CORS(app, supports_credentials=True)

# Конфигурация
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# Регистрируем блюпринты
app.register_blueprint(pages_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(api_bp)

@app.route('/save_image', methods=['POST'])
@app.route('/save_image', methods=['POST'])
# Пример использования в роутах Flask
@app.route('/save_image', methods=['POST'])
def save_image():
    # Проверка авторизации и получение user_id из сессии
    if 'user' not in session or not isinstance(session['user'], dict) or 'id' not in session['user']:
        return jsonify({"success": False, "message": "Необходима авторизация"}), 401

    user_id = session['user']['id']  # Получаем ID напрямую из сессии

    conn = None
    try:
        # Проверяем наличие файла
        if 'image' not in request.files:
            return jsonify({"success": False, "message": "Файл не предоставлен"}), 400

        file = request.files['image']
        if file.filename == '':
            return jsonify({"success": False, "message": "Файл не выбран"}), 400

        # Создаем уникальное имя файла
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"processed_{user_id}_{timestamp}.png"
        filepath = os.path.join(UPLOAD_FOLDER, filename)

        # Сохраняем файл
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        file.save(filepath)

        # Сохраняем запись в БД
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                           INSERT INTO user_images (user_id, filename, upload_date)
                           VALUES (%s, %s, NOW())
                           """, (user_id, filename))
            conn.commit()

        return jsonify({
            "success": True,
            "filename": filename,
            "message": "Изображение успешно сохранено"
        })

    except Exception as e:
        print(f"Ошибка при сохранении изображения: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Ошибка сервера: {str(e)}"
        }), 500
    finally:
        if conn:
            conn.close()


@app.route('/get_user_images')
def get_user_images():
    if 'user' not in session:
        return jsonify([])

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Получаем ID пользователя
            cursor.execute("SELECT id FROM users WHERE username = %s", (session['user'],))
            user = cursor.fetchone()
            if not user:
                return jsonify([])

            # Получаем изображения пользователя
            cursor.execute("""
                           SELECT id, filename, upload_date
                           FROM user_images
                           WHERE user_id = %s
                           ORDER BY upload_date DESC
                           """, (user['id'],))

            images = cursor.fetchall()
            for img in images:
                img['upload_date'] = img['upload_date'].strftime('%d.%m.%Y')

            return jsonify(images)
    except Exception as e:
        return jsonify([])
    finally:
        if conn:
            conn.close()

@app.route('/some_route')
def some_route():
    print("Текущая сессия:", session)
    print("Пользователь в сессии:", session.get('user'), flush=True)
    return "Смотри консоль сервера!"

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
    _, binary_mask = cv2.threshold(gray_image, 135, 255, cv2.THRESH_BINARY)

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


# Функция для вычисления цветовых компонент
def generate_h_component(image):
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    h = hsv[:, :, 0]
    return cv2.cvtColor(h, cv2.COLOR_GRAY2BGR)


def generate_s_component(image):
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    s = hsv[:, :, 1]
    return cv2.cvtColor(s, cv2.COLOR_GRAY2BGR)


def generate_v_component(image):
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    v = hsv[:, :, 2]
    return cv2.cvtColor(v, cv2.COLOR_GRAY2BGR)


# Вычисление гистограммы
def compute_histogram(image, mask=None, use_hsv=True):
    if use_hsv:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    channels = cv2.split(image)
    hist = []
    for ch in channels:
        h = cv2.calcHist([ch], [0], mask, [256], [0, 256])
        cv2.normalize(h, h, 0, 1, cv2.NORM_MINMAX)
        hist.append(h)
    return hist


# Сравнение гистограмм
def compare_histograms(hist1, hist2, method=cv2.HISTCMP_BHATTACHARYYA):
    scores = [cv2.compareHist(h1, h2, method) for h1, h2 in zip(hist1, hist2)]
    return sum(scores) / len(scores)


# Вычисление IoU (пересечение над объединением)
def intersection_over_union(box1, box2):
    x1, y1, w1, h1 = box1["x"], box1["y"], box1["width"], box1["height"]
    x2, y2, w2, h2 = box2["x"], box2["y"], box2["width"], box2["height"]

    inter_x1 = max(x1, x2)
    inter_y1 = max(y1, y2)
    inter_x2 = min(x1 + w1, x2 + w2)
    inter_y2 = min(y1 + h1, y2 + h2)

    if inter_x2 <= inter_x1 or inter_y2 <= inter_y1:
        return 0.0

    inter_area = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
    box1_area = w1 * h1
    box2_area = w2 * h2

    return inter_area / float(box1_area + box2_area - inter_area)


# Объединение прямоугольников
def merge_similar_boxes(boxes, iou_threshold=0.3):
    if not boxes:
        return []

    clusters = []
    for box in boxes:
        matched = False
        for cluster in clusters:
            for clustered_box in cluster:
                iou = intersection_over_union(box, clustered_box)
                if iou >= iou_threshold:
                    cluster.append(box)
                    matched = True
                    break
            if matched:
                break
        if not matched:
            clusters.append([box])

    merged_boxes = []
    for cluster in clusters:
        xs = [b["x"] for b in cluster]
        ys = [b["y"] for b in cluster]
        ws = [b["x"] + b["width"] for b in cluster]
        hs = [b["y"] + b["height"] for b in cluster]

        x_min, y_min = min(xs), min(ys)
        x_max, y_max = max(ws), max(hs)

        merged_boxes.append({
            "x": int(x_min),
            "y": int(y_min),
            "width": int(x_max - x_min),
            "height": int(y_max - y_min),
        })

    return merged_boxes


# Нахождение контура региона
def find_region_contour(image, x, y, w, h):
    region = image[y:y + h, x:x + w]
    hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
    h_channel = hsv[:, :, 0]

    _, binary = cv2.threshold(h_channel, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return [
            {"x": int(x), "y": int(y)},
            {"x": int(x + w), "y": int(y)},
            {"x": int(x + w), "y": int(y + h)},
            {"x": int(x), "y": int(y + h)}
        ]

    largest_contour = max(contours, key=cv2.contourArea)
    epsilon = 0.02 * cv2.arcLength(largest_contour, True)
    approx = cv2.approxPolyDP(largest_contour, epsilon, True)

    contour_points = []
    for point in approx:
        px, py = point[0]
        contour_points.append({
            "x": int(x + px),  # Явное преобразование в int
            "y": int(y + py)  # Явное преобразование в int
        })

    return contour_points


# Объединение регионов с учетом контуров
def merge_regions_with_contours(regions, iou_threshold=0.3):
    if not regions:
        return []

    merged_boxes = merge_similar_boxes(regions, iou_threshold)
    final_regions = []

    for box in merged_boxes:
        x, y, w, h = box["x"], box["y"], box["width"], box["height"]

        # Создаем маску для объединенного региона
        mask = np.zeros((h, w), dtype=np.uint8)

        # Добавляем все входящие контуры в маску
        for region in regions:
            if (region["x"] >= x and region["y"] >= y and
                    region["x"] + region["width"] <= x + w and
                    region["y"] + region["height"] <= y + h):

                if "contour" in region:
                    for point in region["contour"]:
                        px, py = point["x"] - x, point["y"] - y
                        if 0 <= px < w and 0 <= py < h:
                            mask[py, px] = 255

        # Находим контур объединенного региона
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if contours:
            largest_contour = max(contours, key=cv2.contourArea)
            epsilon = 0.01 * cv2.arcLength(largest_contour, True)
            approx = cv2.approxPolyDP(largest_contour, epsilon, True)

            contour_points = []
            for point in approx:
                px, py = point[0]
                contour_points.append({"x": x + px, "y": y + py})

            box["contour"] = contour_points

        final_regions.append(box)

    return final_regions


# Поиск похожих регионов с контурами
def find_similar_regions_with_contours(
        image_cv, roi_cv_original,
        threshold=0.3, step_ratio=0.5,
        scales=[0.5, 0.8, 1.0, 1.2, 1.5],
        return_contours=False
):
    similar_regions = []

    for scale in scales:
        roi_cv = cv2.resize(roi_cv_original, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
        roi_hist = compute_histogram(roi_cv)

        roi_h, roi_w = roi_cv.shape[:2]
        step_y = max(1, int(roi_h * step_ratio))
        step_x = max(1, int(roi_w * step_ratio))

        for y in range(0, image_cv.shape[0] - roi_h + 1, step_y):
            for x in range(0, image_cv.shape[1] - roi_w + 1, step_x):
                window = image_cv[y:y + roi_h, x:x + roi_w]
                window_hist = compute_histogram(window)

                score = compare_histograms(roi_hist, window_hist)

                if score < threshold:
                    region = {
                        "x": x,
                        "y": y,
                        "width": roi_w,
                        "height": roi_h,
                        "score": score,
                        "scale": scale
                    }

                    if return_contours:
                        region["contour"] = find_region_contour(image_cv, x, y, roi_w, roi_h)

                    similar_regions.append(region)

    if return_contours:
        return merge_regions_with_contours(similar_regions)
    else:
        return merge_similar_boxes(similar_regions, iou_threshold=0.01)


# Декодирование изображения из base64
def decode_image(image_data):
    image_base64 = image_data.split(",")[1] if "," in image_data else image_data
    image_bytes = base64.b64decode(image_base64)
    image_np = np.frombuffer(image_bytes, dtype=np.uint8)
    return cv2.imdecode(image_np, cv2.IMREAD_COLOR)


# Кодирование изображения в base64
def encode_image(image):
    _, encoded = cv2.imencode('.jpg', image)
    return base64.b64encode(encoded).decode('utf-8')


# Основной обработчик запроса
@app.route('/process_region', methods=['POST'])
def process_region():
    data = request.json
    image_data = data.get('image')
    roi_data = data.get('roi')
    polygon = data.get('polygon')

    try:
        # Декодируем изображения
        image = decode_image(image_data)
        roi = decode_image(roi_data)

        # 1. Анализ выбранной области (ROI)
        roi_hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

        # Вычисляем средние значения и стандартные отклонения
        h_mean, h_std = np.mean(roi_hsv[:, :, 0]), np.std(roi_hsv[:, :, 0])
        s_mean, s_std = np.mean(roi_hsv[:, :, 1]), np.std(roi_hsv[:, :, 1])

        # Определяем диапазоны (с проверкой границ)
        h_low = max(0, int(h_mean - h_std * 2))
        h_high = min(180, int(h_mean + h_std * 2))
        s_low = max(0, int(s_mean - s_std * 2))
        s_high = min(255, int(s_mean + s_std * 2))

        # Создаем границы ОДНОГО ТИПА (np.uint8)
        lower = np.array([h_low, s_low, 0], dtype=np.uint8)
        upper = np.array([h_high, s_high, 255], dtype=np.uint8)

        # 2. Применяем цветовой фильтр
        image_hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(image_hsv, lower, upper)

        # Улучшаем маску
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)

        # 3. Находим контуры
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        similar_regions = []
        min_area = roi.shape[0] * roi.shape[1] * 0.3  # Минимальная площадь региона

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < min_area:
                continue

            # Аппроксимируем контур
            epsilon = 0.02 * cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, epsilon, True)

            # Получаем bounding rect
            x, y, w, h = cv2.boundingRect(cnt)

            # Преобразуем контур в список точек
            contour_points = [{"x": int(point[0][0]), "y": int(point[0][1])} for point in approx]

            similar_regions.append({
                "x": int(x),
                "y": int(y),
                "width": int(w),
                "height": int(h),
                "contour": contour_points,
                "area": int(area)
            })

        # Сортируем регионы по площади
        similar_regions.sort(key=lambda r: r['area'], reverse=True)

        # Генерируем компоненты для визуализации
        h_component = cv2.cvtColor(image_hsv[:, :, 0], cv2.COLOR_GRAY2BGR)
        s_component = cv2.cvtColor(image_hsv[:, :, 1], cv2.COLOR_GRAY2BGR)
        v_component = cv2.cvtColor(image_hsv[:, :, 2], cv2.COLOR_GRAY2BGR)

        return jsonify({
            "similarRegions": similar_regions,
            "hComponent": encode_image(h_component),
            "sComponent": encode_image(s_component),
            "vComponent": encode_image(v_component),
            "colorRange": {
                "h": [int(h_low), int(h_high)],
                "s": [int(s_low), int(s_high)]
            }
        })

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500




if __name__ == "__main__":
    app.run(host='127.0.0.1', debug=True)