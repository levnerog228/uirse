import cv2
import matplotlib.pyplot as plt

# 1. Загрузка изображения
image = cv2.imread('3.png')  # замените на путь к вашему файлу
image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)  # OpenCV загружает в BGR, конвертируем в RGB

# Преобразование в HSV
hsv_image = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
h, s, v = cv2.split(hsv_image)

# Создаем фигуру
fig, axs = plt.subplots(2, 2, figsize=(10, 8))

# Верхний ряд: H и S
axs[0, 0].imshow(h, cmap='hsv')
axs[0, 0].set_title('Hue (H)')
axs[0, 0].axis('off')

axs[0, 1].imshow(s, cmap='gray')
axs[0, 1].set_title('Saturation (S)')
axs[0, 1].axis('off')

# Нижний ряд: V по центру
axs[1, 0].axis('off')  # пустой левый
axs[1, 1].imshow(v, cmap='gray')
axs[1, 1].set_title('Value (V)')
axs[1, 1].axis('off')

plt.tight_layout()
plt.show()