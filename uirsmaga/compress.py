from PIL import Image
import io
import os
import matplotlib.pyplot as plt

def compress_image_to_buffer(image_path, quality=10):
    # Открываем изображение и сжимаем его, сохраняя в буфере памяти
    with Image.open(image_path) as img:
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality)
        buffer.seek(0)
        return buffer

# Путь к изображению
input_image = "scale_1200.jpg"  # замените на имя вашего изображения

# Проверка, существует ли изображение
try:
    # Размер оригинального изображения
    original_size = os.path.getsize(input_image)

    # Оригинальное изображение
    original_img = Image.open(input_image)

    # Сжимаем изображение и сохраняем в буфере
    compressed_buffer = compress_image_to_buffer(input_image)
    compressed_img = Image.open(compressed_buffer)

    # Размер сжатого изображения
    compressed_size = compressed_buffer.getbuffer().nbytes

    # Отображаем размеры изображений
    print(f"Размер оригинального изображения: {original_size / 1024:.2f} КБ")
    print(f"Размер сжатого изображения: {compressed_size / 1024:.2f} КБ")

    # Отображаем изображения
    fig, axes = plt.subplots(1, 2, figsize=(12, 6))
    axes[0].imshow(original_img)
    axes[0].set_title("Оригинальное изображение")
    axes[0].axis("off")

    axes[1].imshow(compressed_img)
    axes[1].set_title("Сжатое изображение (из буфера)")
    axes[1].axis("off")

    plt.show()

except FileNotFoundError:
    print(f"Файл {input_image} не найден.")


