import matplotlib.pyplot as plt
import numpy as np

# ----------------------------------
# Параметры
# ----------------------------------
frames = np.arange(1, 101)  # 100 кадров

# Генерация данных для IoU SAM2
np.random.seed(42)
iou_sam2 = np.clip(np.random.normal(loc=0.87, scale=0.03, size=100), 0, 1)

# Вычисление среднего значения
mean_iou_sam2 = np.mean(iou_sam2)

# ----------------------------------
# График IoU для SAM2
# ----------------------------------
plt.figure(figsize=(7,5))
plt.plot(frames, iou_sam2, marker='o', markevery=10, label='SAM2 IoU')

# Горизонтальная линия среднего значения
plt.axhline(mean_iou_sam2, color='blue', linestyle='--', linewidth=1,
            label=f'Среднее SAM2 ({mean_iou_sam2:.2f})')

plt.xlabel('Номер кадра')
plt.ylabel('IoU')
plt.title('Динамика значения IoU во времени (SAM2)')
plt.legend()
plt.grid(True)
plt.show()
