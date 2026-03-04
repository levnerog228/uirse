import os
import numpy as np
import tensorflow as tf
from tensorflow.keras.preprocessing.image import load_img, img_to_array
import matplotlib.pyplot as plt

# Путь к обученной модели
MODEL_PATH = 'unet_segmentation_model.h5'

# Пути к изображениям для предсказаний
IMAGE_PATH = 'dataset/Tile 2/images/image_part_007.jpg'

# Загружаем модель
model = tf.keras.models.load_model(MODEL_PATH)


def load_image(image_path, target_size=(256, 256)):
    """ Загружает изображение и нормализует его """
    try:
        image = load_img(image_path, target_size=target_size)
        image = img_to_array(image) / 255.0  # Нормализация
        return image
    except Exception as e:
        print(f"Ошибка загрузки изображения: {e}")
        return None


def predict_image(image_path):
    """ Делаем предсказание для одного изображения """
    image = load_image(image_path)
    if image is None:
        print("Ошибка при загрузке изображения!")
        return None

    # Подготавливаем изображение для модели (добавляем batch размерность)
    image_input = np.expand_dims(image, axis=0)  # (1, 256, 256, 3)

    # Получаем предсказания
    pred_mask = model.predict(image_input)

    # Преобразуем выходные данные
    pred_mask = np.argmax(pred_mask, axis=-1)  # Получаем класс для каждого пикселя
    pred_mask = np.squeeze(pred_mask)  # Убираем размерность 1

    return pred_mask


def display_results(image_path, pred_mask):
    """ Показывает оригинальное изображение и результат сегментации """
    # Загружаем изображение
    image = load_img(image_path)

    # Визуализируем оригинальное изображение и предсказанную маску
    fig, axes = plt.subplots(1, 2, figsize=(12, 6))

    axes[0].imshow(image)
    axes[0].set_title("Оригинальное изображение")
    axes[0].axis("off")

    axes[1].imshow(pred_mask, cmap='tab20b')  # Отображаем предсказанную маску с цветовой картой
    axes[1].set_title("Предсказанная маска")
    axes[1].axis("off")

    plt.show()


# Используем модель для предсказания
pred_mask = predict_image(IMAGE_PATH)

if pred_mask is not None:
    display_results(IMAGE_PATH, pred_mask)
