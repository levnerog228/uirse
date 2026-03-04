import cv2
import numpy as np
from matplotlib import pyplot as plt

# Загрузите изображение
image = cv2.imread('1511423832173430647.jpg')

# Конвертируйте изображение в формат RGB (OpenCV использует BGR по умолчанию)
image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

# Шаг 1: Увеличение разрешения с помощью интерполяции Bicubic
height, width = image.shape[:2]
new_width = width * 2  # Увеличиваем ширину в два раза
new_height = height * 2  # Увеличиваем высоту в два раза

# Применяем интерполяцию для увеличения изображения с высоким качеством
resized_image = cv2.resize(image_rgb, (new_width, new_height), interpolation=cv2.INTER_CUBIC)

# Шаг 2: Использование Non-Local Means для улучшения качества изображения
# Этот метод эффективно устраняет шум и восстанавливает детали.
denoised_image = cv2.fastNlMeansDenoisingColored(resized_image, None, 10, 10, 7, 21)

# Шаг 3: Повышение резкости изображения (с использованием ядра)
sharpen_kernel = np.array([[-1, -1, -1],
                           [-1,  9, -1],
                           [-1, -1, -1]])

sharpened_image = cv2.filter2D(denoised_image, -1, sharpen_kernel)

# Отобразим оригинальное и улучшенное изображение
plt.figure(figsize=(10, 5))

# Оригинальное изображение
plt.subplot(1, 2, 1)
plt.imshow(image_rgb)
plt.title('Original Image')
plt.axis('off')

# Изображение с повышенным разрешением и улучшенным качеством
plt.subplot(1, 2, 2)
plt.imshow(sharpened_image)
plt.title('Enhanced Image (Increased Resolution)')
plt.axis('off')

plt.show()

