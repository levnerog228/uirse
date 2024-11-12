from flask import Flask, request, send_file
from flask_cors import CORS
from PIL import Image
import io
import cv2
import numpy as np

# Инициализация Flask приложения
app = Flask(__name__)
CORS(app)  # Разрешаем CORS для всех запросов

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

# Запуск приложения
if __name__ == "__main__":
    app.run(debug=True)  # Запускаем сервер в режиме отладки
