import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
import cv2
from scipy import ndimage
from aboba import immodus_bibl as imb
import matplotlib.patches as patches
from matplotlib.widgets import Button, Slider, CheckButtons
from matplotlib.path import Path
import os
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier
import joblib
import warnings
import time

warnings.filterwarnings('ignore')


class ImprovedRegionDetector:
    def __init__(self):
        self.params = {
            'hue_threshold': 15,
            'saturation_threshold': 25,
            'lightness_threshold': 30,
            'min_region_size': 10,
            'color_consistency_threshold': 0.6,
            'spatial_coherence_weight': 0.3,
            'edge_awareness': True,
            'texture_weight': 0.2,
            'shape_weight': 0.1,
            'fast_mode': False,
            'similarity_threshold': 0.7,
            'fill_gaps': True,
            'gap_fill_size': 10,
            'morphology_kernel': 3,
            'v_threshold': 40,
            # НОВЫЕ ПАРАМЕТРЫ ДЛЯ ТОЧНОСТИ
            'adaptive_threshold': True,
            'multi_scale_analysis': True,
            'edge_preservation': True,
            'region_refinement': True,
            'confidence_threshold': 0.8,
            'color_variance_weight': 0.1,
            'spatial_compactness': 0.2,
            'boundary_sensitivity': 0.7,
        }

        self.image_path = None
        self.original_image = None
        self.image_array = None
        self.H_array = None
        self.S_array = None
        self.L_array = None

        # НОВЫЕ ПЕРЕМЕННЫЕ ДЛЯ ТОЧНОСТИ
        self.edge_map = None
        self.gradient_magnitude = None
        self.confidence_map = None

        self.color_analysis = None
        self.current_selection = None
        self.selection_vertices = []
        self.current_regions = []
        self.selected_region_index = None
        self.region_patches = []

        self.learning_system = ImprovedLearningSystem()

        self.fig = None
        self.ax1 = None
        self.ax2 = None
        self.delete_mode = False

    def load_and_convert_image(self, image_path):
        """Улучшенная загрузка и конвертация изображения с анализом"""
        print("📁 Загрузка изображения...")
        self.image_path = image_path
        self.original_image = Image.open(image_path)
        self.image_array = np.array(self.original_image)
        height, width, _ = self.image_array.shape

        print("🔄 Конвертация RGB в HSL...")
        self.H_array = np.zeros((height, width), dtype=np.float32)
        self.S_array = np.zeros((height, width), dtype=np.float32)
        self.L_array = np.zeros((height, width), dtype=np.float32)

        for y in range(height):
            for x in range(width):
                r, g, b = self.image_array[y, x, :3]
                hsl = imb.RGBtoHSL(r, g, b)
                self.H_array[y, x] = hsl[0, 0]
                self.S_array[y, x] = hsl[0, 1]
                self.L_array[y, x] = hsl[0, 2]

        # НОВЫЙ АНАЛИЗ ИЗОБРАЖЕНИЯ И ПРЕДОБРАБОТКА
        self.analyze_image_characteristics()
        self.precompute_accuracy_maps()

        self.enhance_arrays()
        print(f"✅ Изображение загружено: {width}x{height} пикселей")
        return height, width

    def precompute_accuracy_maps(self):
        """Предварительный расчет карт для улучшения точности"""
        print("🔄 Расчет карт для точного поиска...")

        # Карта границ с помощью Canny
        gray_image = cv2.cvtColor(self.image_array, cv2.COLOR_RGB2GRAY)
        self.edge_map = cv2.Canny(gray_image, 50, 150)

        # Карта градиентов для сохранения границ
        sobelx = cv2.Sobel(gray_image, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray_image, cv2.CV_64F, 0, 1, ksize=3)
        self.gradient_magnitude = np.sqrt(sobelx ** 2 + sobely ** 2)

        # Нормализуем градиенты
        if self.gradient_magnitude.max() > 0:
            self.gradient_magnitude = self.gradient_magnitude / self.gradient_magnitude.max()

    def analyze_image_characteristics(self):
        """Анализ характеристик изображения по HSV-спектрам"""
        print("📊 Анализ HSV-характеристик изображения...")

        hue_flat = self.H_array.flatten()
        hue_flat = hue_flat[hue_flat >= 0]
        saturation_flat = self.S_array.flatten()
        lightness_flat = self.L_array.flatten()

        self.color_analysis = {
            'hue': {
                'mean': np.mean(hue_flat),
                'std': self.circular_std(hue_flat),
                'dominant_ranges': self.find_dominant_hue_ranges(hue_flat),
                'contrast': np.percentile(hue_flat, 95) - np.percentile(hue_flat, 5)
            },
            'saturation': {
                'mean': np.mean(saturation_flat),
                'std': np.std(saturation_flat),
                'vibrance': np.percentile(saturation_flat, 75),
                'muted_level': np.percentile(saturation_flat, 25)
            },
            'lightness': {
                'mean': np.mean(lightness_flat),
                'std': np.std(lightness_flat),
                'brightness': np.percentile(lightness_flat, 75),
                'darkness': np.percentile(lightness_flat, 25),
                'contrast': np.percentile(lightness_flat, 95) - np.percentile(lightness_flat, 5)
            }
        }

        self.print_image_analysis()

    def find_dominant_hue_ranges(self, hue_data, n_ranges=3):
        """Находит доминирующие диапазоны тонов"""
        if len(hue_data) == 0:
            return []

        hist, bins = np.histogram(hue_data, bins=36, range=(0, 360))

        peaks = []
        for i in range(1, len(hist) - 1):
            if hist[i] > hist[i - 1] and hist[i] > hist[i + 1] and hist[i] > len(hue_data) * 0.01:
                peaks.append((bins[i], hist[i]))

        peaks.sort(key=lambda x: x[1], reverse=True)

        dominant_ranges = []
        for center, count in peaks[:n_ranges]:
            dominant_ranges.append({
                'center': center,
                'range': (max(0, center - 15), min(360, center + 15)),
                'percentage': count / len(hue_data) * 100
            })

        return dominant_ranges

    def print_image_analysis(self):
        """Выводит анализ изображения"""
        analysis = self.color_analysis
        print("\n" + "=" * 60)
        print("📊 АНАЛИЗ ИЗОБРАЖЕНИЯ ПО HSV-СПЕКТРАМ")
        print("=" * 60)

        hue_info = analysis['hue']
        print(f"🎨 ТОН (Hue):")
        print(f"   • Среднее: {hue_info['mean']:.1f}°")
        print(f"   • Контраст: {hue_info['contrast']:.1f}°")
        print(f"   • Стандартное отклонение: {hue_info['std']:.1f}°")

        if hue_info['dominant_ranges']:
            print(f"   • Доминирующие диапазоны:")
            for i, range_info in enumerate(hue_info['dominant_ranges']):
                print(f"     {i + 1}. {range_info['range'][0]:.0f}°-{range_info['range'][1]:.0f}° "
                      f"({range_info['percentage']:.1f}%)")

        sat_info = analysis['saturation']
        print(f"🎯 НАСЫЩЕННОСТЬ (Saturation):")
        print(f"   • Средняя: {sat_info['mean']:.1f}%")
        print(f"   • Яркость цвета: {sat_info['vibrance']:.1f}%")
        print(f"   • Приглушенность: {sat_info['muted_level']:.1f}%")

        light_info = analysis['lightness']
        print(f"💡 ЯРКОСТЬ (Lightness/Value):")
        print(f"   • Средняя: {light_info['mean']:.1f}%")
        print(f"   • Яркие области: {light_info['brightness']:.1f}%")
        print(f"   • Темные области: {light_info['darkness']:.1f}%")
        print(f"   • Контраст: {light_info['contrast']:.1f}%")

        print("\n💡 ВЫВОДЫ:")

        if hue_info['std'] < 30:
            print("   • Изображение имеет ограниченную цветовую гамму")
        elif hue_info['std'] > 90:
            print("   • Изображение имеет широкую цветовую гамму")

        if sat_info['mean'] < 25:
            print("   • Преобладают приглушенные, пастельные тона")
        elif sat_info['mean'] > 60:
            print("   • Яркие, насыщенные цвета")

        if light_info['mean'] < 30:
            print("   • Темное изображение")
        elif light_info['mean'] > 70:
            print("   • Светлое изображение")

        if light_info['contrast'] > 50:
            print("   • Высокий контраст")
        elif light_info['contrast'] < 20:
            print("   • Низкий контраст")

        print("=" * 60)

    def create_hsv_visualizations(self):
        """Создает визуализации изображения в разных HSV-спектрах"""
        print("\n🎨 Создание визуализаций HSV-спектров...")

        fig = plt.figure(figsize=(20, 12))
        fig.suptitle('ВИЗУАЛИЗАЦИЯ ИЗОБРАЖЕНИЯ В РАЗНЫХ ЦВЕТОВЫХ СПЕКТРАХ',
                     fontsize=16, fontweight='bold', y=0.95)

        # 1. Оригинальное изображение
        ax1 = plt.subplot(2, 4, 1)
        ax1.imshow(self.original_image)
        ax1.set_title('🎨 ОРИГИНАЛЬНОЕ ИЗОБРАЖЕНИЕ', fontweight='bold')
        ax1.axis('off')

        # 2. Тон (Hue) - цветовой круг
        ax2 = plt.subplot(2, 4, 2)
        hue_visualization = self.create_hue_visualization()
        ax2.imshow(hue_visualization)
        ax2.set_title('🎯 ТОН (Hue) - Цветовой круг', fontweight='bold')
        ax2.axis('off')

        # 3. Насыщенность (Saturation)
        ax3 = plt.subplot(2, 4, 3)
        sat_visualization = self.create_saturation_visualization()
        im3 = ax3.imshow(sat_visualization, cmap='viridis')
        ax3.set_title('📈 НАСЫЩЕННОСТЬ (Saturation)', fontweight='bold')
        ax3.axis('off')
        plt.colorbar(im3, ax=ax3, fraction=0.046, pad=0.04)

        # 4. Яркость (Lightness/Value)
        ax4 = plt.subplot(2, 4, 4)
        light_visualization = self.create_lightness_visualization()
        im4 = ax4.imshow(light_visualization, cmap='plasma')
        ax4.set_title('💡 ЯРКОСТЬ (Lightness/Value)', fontweight='bold')
        ax4.axis('off')
        plt.colorbar(im4, ax=ax4, fraction=0.046, pad=0.04)

        # 5. Комбинированная HSV визуализация
        ax5 = plt.subplot(2, 4, 5)
        hsv_combined = self.create_hsv_combined_visualization()
        ax5.imshow(hsv_combined)
        ax5.set_title('🌈 КОМБИНИРОВАННАЯ HSV-ВИЗУАЛИЗАЦИЯ', fontweight='bold')
        ax5.axis('off')

        # 6. Доминирующие цвета
        ax6 = plt.subplot(2, 4, 6)
        self.plot_dominant_colors(ax6)
        ax6.set_title('🎨 ДОМИНИРУЮЩИЕ ЦВЕТА', fontweight='bold')
        ax6.axis('off')

        # 7. Карта градиентов (границы)
        ax7 = plt.subplot(2, 4, 7)
        if self.gradient_magnitude is not None:
            im7 = ax7.imshow(self.gradient_magnitude, cmap='hot')
            ax7.set_title('🔄 КАРТА ГРАДИЕНТОВ (Границы)', fontweight='bold')
            ax7.axis('off')
            plt.colorbar(im7, ax=ax7, fraction=0.046, pad=0.04)

        # 8. Статистика распределения цветов
        ax8 = plt.subplot(2, 4, 8)
        self.plot_color_statistics(ax8)
        ax8.set_title('📊 СТАТИСТИКА ЦВЕТОВ', fontweight='bold')

        plt.tight_layout()
        plt.show()

        return fig

    def create_hue_visualization(self):
        """Создает визуализацию тона (Hue) в виде цветового круга"""
        height, width = self.H_array.shape
        hue_vis = np.zeros((height, width, 3), dtype=np.uint8)

        for y in range(height):
            for x in range(width):
                hue = self.H_array[y, x]
                saturation = 100  # Максимальная насыщенность для чистых цветов
                lightness = 50  # Средняя яркость

                # Конвертируем HSL обратно в RGB для визуализации
                rgb = self.hsl_to_rgb(hue, saturation, lightness)
                hue_vis[y, x] = [rgb[0], rgb[1], rgb[2]]

        return hue_vis

    def create_saturation_visualization(self):
        """Создает визуализацию насыщенности"""
        return self.S_array

    def create_lightness_visualization(self):
        """Создает визуализацию яркости"""
        return self.L_array

    def create_hsv_combined_visualization(self):
        """Создает комбинированную HSV визуализацию"""
        height, width = self.H_array.shape
        combined_vis = np.zeros((height, width, 3), dtype=np.uint8)

        for y in range(height):
            for x in range(width):
                hue = self.H_array[y, x]
                saturation = self.S_array[y, x]
                lightness = self.L_array[y, x]

                rgb = self.hsl_to_rgb(hue, saturation, lightness)
                combined_vis[y, x] = [rgb[0], rgb[1], rgb[2]]

        return combined_vis

    def hsl_to_rgb(self, h, s, l):
        """Конвертирует HSL в RGB"""
        # Нормализуем значения
        h = h % 360
        s = max(0, min(100, s))
        l = max(0, min(100, l))

        s = s / 100.0
        l = l / 100.0

        if s == 0:
            # Оттенки серого
            rgb = [int(l * 255), int(l * 255), int(l * 255)]
        else:
            def hue_to_rgb(p, q, t):
                if t < 0: t += 1
                if t > 1: t -= 1
                if t < 1 / 6: return p + (q - p) * 6 * t
                if t < 1 / 2: return q
                if t < 2 / 3: return p + (q - p) * (2 / 3 - t) * 6
                return p

            q = l * (1 + s) if l < 0.5 else l + s - l * s
            p = 2 * l - q
            h_k = h / 360.0

            r = hue_to_rgb(p, q, h_k + 1 / 3)
            g = hue_to_rgb(p, q, h_k)
            b = hue_to_rgb(p, q, h_k - 1 / 3)

            rgb = [int(r * 255), int(g * 255), int(b * 255)]

        return rgb

    def plot_dominant_colors(self, ax):
        """Визуализирует доминирующие цвета изображения"""
        if not self.color_analysis or not self.color_analysis['hue']['dominant_ranges']:
            ax.text(0.5, 0.5, 'Нет данных\nо доминирующих цветах',
                    ha='center', va='center', transform=ax.transAxes)
            return

        dominant_ranges = self.color_analysis['hue']['dominant_ranges']
        n_colors = len(dominant_ranges)

        # Создаем цветовую палитру
        for i, color_info in enumerate(dominant_ranges):
            hue_center = color_info['center']
            percentage = color_info['percentage']

            # Создаем патч с цветом
            color_rgb = self.hsl_to_rgb(hue_center, 80, 50)
            color_normalized = [c / 255.0 for c in color_rgb]

            rect = patches.Rectangle((0.1, i * 0.8 / n_colors), 0.3, 0.6 / n_colors,
                                     facecolor=color_normalized, edgecolor='black')
            ax.add_patch(rect)

            # Подписываем цвет
            ax.text(0.45, (i + 0.5) * 0.8 / n_colors,
                    f'{hue_center:.0f}° ({percentage:.1f}%)',
                    va='center', ha='left', fontsize=10)

        ax.set_xlim(0, 1)
        ax.set_ylim(0, 0.8)

    def plot_color_statistics(self, ax):
        """Строит гистограммы распределения цветов"""
        hue_flat = self.H_array.flatten()
        hue_flat = hue_flat[hue_flat >= 0]
        sat_flat = self.S_array.flatten()
        light_flat = self.L_array.flatten()

        # Гистограмма тонов
        ax.hist(hue_flat, bins=36, range=(0, 360), color='red', alpha=0.7,
                label=f'Hue (μ={np.mean(hue_flat):.1f}°)')

        # Нормализованные гистограммы насыщенности и яркости
        ax2 = ax.twinx()
        sat_normalized = (sat_flat - np.min(sat_flat)) / (np.max(sat_flat) - np.min(sat_flat)) * 360
        light_normalized = (light_flat - np.min(light_flat)) / (np.max(light_flat) - np.min(light_flat)) * 360

        ax2.hist(sat_normalized, bins=50, range=(0, 360), color='green', alpha=0.5,
                 label=f'Sat (μ={np.mean(sat_flat):.1f}%)')
        ax2.hist(light_normalized, bins=50, range=(0, 360), color='blue', alpha=0.5,
                 label=f'Light (μ={np.mean(light_flat):.1f}%)')

        ax.set_xlabel('Значение (нормализованное)')
        ax.set_ylabel('Частота Hue', color='red')
        ax2.set_ylabel('Частота Sat/Light', color='green')

        ax.legend(loc='upper left')
        ax2.legend(loc='upper right')

    def enhance_arrays(self):
        """Улучшенная обработка массивов"""
        if self.params['fast_mode']:
            size = 2
        else:
            size = 3

        self.H_array = ndimage.median_filter(self.H_array, size=size)
        self.S_array = ndimage.median_filter(self.S_array, size=size)
        self.L_array = ndimage.median_filter(self.L_array, size=size)
        self.H_array = np.mod(self.H_array, 360)

    def enhanced_color_similarity(self, color1, color2, spatial_distance=1, edge_weight=1.0):
        """Улучшенная метрика цветового сходства с учетом пространства и границ"""
        hue_diff = min(abs(color1[0] - color2[0]), 360 - abs(color1[0] - color2[0]))
        sat_diff = abs(color1[1] - color2[1])
        light_diff = abs(color1[2] - color2[2])

        hue_threshold = self.params['hue_threshold']
        sat_threshold = self.params['saturation_threshold'] * (1 + color1[1] / 100)
        light_threshold = self.params['lightness_threshold']
        v_threshold = self.params['v_threshold']

        hue_sim = max(0, 1 - hue_diff / hue_threshold)
        sat_sim = max(0, 1 - sat_diff / sat_threshold)
        light_sim = max(0, 1 - light_diff / light_threshold)

        spatial_sim = max(0, 1 - spatial_distance / 10.0)

        base_similarity = (0.4 * hue_sim + 0.3 * sat_sim + 0.3 * light_sim)

        spatial_weight = 0.1
        base_similarity = base_similarity * (1 - spatial_weight) + spatial_sim * spatial_weight

        if self.params['edge_preservation'] and edge_weight < 0.5:
            base_similarity *= 0.7

        v_similarity = 1.0 if light_diff <= v_threshold else 0.5

        return base_similarity * v_similarity

    def create_adaptive_similarity_mask(self, thresholds, mask):
        """Создает адаптивную маску с учетом локальных характеристик"""
        height, width = self.H_array.shape
        similarity_mask = np.zeros((height, width), dtype=bool)
        confidence_map = np.zeros((height, width), dtype=np.float32)

        main_color = thresholds['main_color']

        region_analysis = self.analyze_selection_region(mask)
        if region_analysis:
            local_hue_std = region_analysis['hue_std']
            local_sat_std = region_analysis['saturation_std']
        else:
            local_hue_std = 15
            local_sat_std = 10

        step = 2 if self.params['fast_mode'] else 1

        for y in range(0, height, step):
            for x in range(0, width, step):
                if self.gradient_magnitude is not None and self.gradient_magnitude[y, x] > 0.3:
                    edge_weight = 0.3
                else:
                    edge_weight = 1.0

                current_color = [self.H_array[y, x], self.S_array[y, x], self.L_array[y, x]]

                adaptive_threshold = thresholds['similarity_threshold']
                if self.params['adaptive_threshold']:
                    adaptive_threshold *= max(0.7, 1 - (local_hue_std / 60 + local_sat_std / 40) / 2)

                similarity = self.enhanced_color_similarity(
                    current_color,
                    [main_color['hue'], main_color['saturation'], main_color['lightness']],
                    edge_weight=edge_weight
                )

                confidence_map[y, x] = similarity

                if similarity >= adaptive_threshold:
                    similarity_mask[y, x] = True

        if self.params['region_refinement']:
            similarity_mask = self.refine_similarity_mask(similarity_mask, confidence_map)

        return similarity_mask

    def refine_similarity_mask(self, mask, confidence_map):
        """Уточняет маску на основе карты уверенности"""
        mask_uint8 = (mask * 255).astype(np.uint8)

        kernel = np.ones((3, 3), np.uint8)
        mask_cleaned = cv2.morphologyEx(mask_uint8, cv2.MORPH_OPEN, kernel)
        mask_cleaned = cv2.morphologyEx(mask_cleaned, cv2.MORPH_CLOSE, kernel)

        high_confidence_mask = confidence_map > self.params['confidence_threshold']
        mask_combined = np.logical_or(mask_cleaned > 0, high_confidence_mask)

        return mask_combined

    def multi_scale_region_growing(self, seed_mask, thresholds):
        """Многоуровневый рост регионов для лучшей точности"""
        height, width = self.H_array.shape

        coarse_mask = self.create_similarity_mask(thresholds, seed_mask)
        region_analysis = self.analyze_selection_region(seed_mask)
        coarse_regions = self.extract_regions(coarse_mask, thresholds, region_analysis)

        if not coarse_regions:
            return []

        refined_regions = []
        for coarse_region in coarse_regions:
            refined_region = self.refine_region_boundaries(coarse_region, thresholds)
            if refined_region:
                refined_regions.append(refined_region)

        return refined_regions

    def refine_region_boundaries(self, region, thresholds):
        """Уточняет границы региона"""
        mask = region['mask']
        contour = region['contour']

        contour_mask = np.zeros_like(mask, dtype=np.uint8)
        cv2.drawContours(contour_mask, [contour], 0, 255, 2)

        kernel = np.ones((5, 5), np.uint8)
        boundary_zone = cv2.dilate(contour_mask, kernel, iterations=1)
        boundary_zone = boundary_zone > 0

        boundary_pixels = np.where(boundary_zone)
        main_color = [region['avg_hue'], region['avg_saturation'], region['avg_lightness']]

        refined_mask = mask.copy()
        height, width = mask.shape

        for y, x in zip(boundary_pixels[0], boundary_pixels[1]):
            if mask[y, x]:
                if self.gradient_magnitude is not None and self.gradient_magnitude[y, x] > 0.5:
                    neighbors_similar = 0
                    total_neighbors = 0

                    for dy in [-1, 0, 1]:
                        for dx in [-1, 0, 1]:
                            ny, nx = y + dy, x + dx
                            if (0 <= ny < height and 0 <= nx < width and
                                    not mask[ny, nx] and self.gradient_magnitude[ny, nx] < 0.3):
                                neighbor_color = [self.H_array[ny, nx], self.S_array[ny, nx], self.L_array[ny, nx]]
                                similarity = self.enhanced_color_similarity(neighbor_color, main_color)
                                if similarity > thresholds['similarity_threshold']:
                                    neighbors_similar += 1
                                total_neighbors += 1

                    if total_neighbors > 0 and neighbors_similar / total_neighbors > 0.7:
                        for dy in [-1, 0, 1]:
                            for dx in [-1, 0, 1]:
                                ny, nx = y + dy, x + dx
                                if (0 <= ny < height and 0 <= nx < width and not mask[ny, nx]):
                                    neighbor_color = [self.H_array[ny, nx], self.S_array[ny, nx], self.L_array[ny, nx]]
                                    similarity = self.enhanced_color_similarity(neighbor_color, main_color)
                                    if similarity > thresholds['similarity_threshold']:
                                        refined_mask[ny, nx] = True

            else:
                current_color = [self.H_array[y, x], self.S_array[y, x], self.L_array[y, x]]
                similarity = self.enhanced_color_similarity(current_color, main_color)

                if similarity > thresholds['similarity_threshold']:
                    similar_neighbors = 0
                    for dy in [-1, 0, 1]:
                        for dx in [-1, 0, 1]:
                            ny, nx = y + dy, x + dx
                            if (0 <= ny < height and 0 <= nx < width and mask[ny, nx]):
                                similar_neighbors += 1

                    if similar_neighbors >= 2:
                        refined_mask[y, x] = True

        if np.sum(refined_mask) >= self.params['min_region_size']:
            region['mask'] = refined_mask
            region['contour'] = self.extract_contour(refined_mask)
            region['size'] = np.sum(refined_mask)
            region['quality_score'] = self.assess_region_quality_from_mask(refined_mask, main_color)

            return region

        return None

    def extract_contour(self, mask):
        """Извлекает контур из маски с улучшенной точностью"""
        mask_uint8 = (mask * 255).astype(np.uint8)
        contours, _ = cv2.findContours(mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if contours:
            main_contour = max(contours, key=cv2.contourArea)
            epsilon = 0.002 * cv2.arcLength(main_contour, True)
            smoothed_contour = cv2.approxPolyDP(main_contour, epsilon, True)
            return smoothed_contour

        return None

    def assess_region_quality_from_mask(self, mask, main_color):
        """Оценивает качество региона по маске"""
        H_region = self.H_array[mask]
        S_region = self.S_array[mask]
        L_region = self.L_array[mask]

        if len(H_region) == 0:
            return 0.0

        hue_std = self.circular_std(H_region)
        sat_std = np.std(S_region)

        hue_score = 1.0 - min(hue_std / 60.0, 1.0)
        sat_score = 1.0 - min(sat_std / 40.0, 1.0)
        color_consistency = 0.6 * hue_score + 0.4 * sat_score

        avg_color = [np.median(H_region), np.median(S_region), np.median(L_region)]
        similarity_to_target = self.enhanced_color_similarity(avg_color, main_color)

        shape_score = self.compute_compactness(mask)

        boundary_quality = 1.0
        if self.params['edge_preservation'] and self.gradient_magnitude is not None:
            region_boundary = self.get_region_boundary(mask)
            boundary_gradient = np.mean(self.gradient_magnitude[region_boundary])
            boundary_quality = 1.0 - boundary_gradient * 0.5

        final_score = (0.4 * color_consistency +
                       0.3 * similarity_to_target +
                       0.2 * shape_score +
                       0.1 * boundary_quality)

        return final_score

    def get_region_boundary(self, mask):
        """Получает граничные пиксели региона"""
        kernel = np.ones((3, 3), np.uint8)
        eroded = cv2.erode(mask.astype(np.uint8), kernel, iterations=1)
        boundary = mask.astype(np.uint8) - eroded
        return boundary > 0

    def create_selection_mask(self, vertices, image_shape):
        """Создает маску выделения"""
        height, width = image_shape
        mask = np.zeros((height, width), dtype=bool)

        if len(vertices) < 3:
            return mask

        poly_path = Path(vertices)
        y_coords, x_coords = np.mgrid[0:height, 0:width]
        points = np.vstack([x_coords.ravel(), y_coords.ravel()]).T

        inside_mask = poly_path.contains_points(points)
        mask = inside_mask.reshape(height, width)

        return mask

    def analyze_selection_region(self, mask):
        """Анализирует выбранную область"""
        if np.sum(mask) == 0:
            return None

        H_region = self.H_array[mask]
        S_region = self.S_array[mask]
        L_region = self.L_array[mask]

        analysis = {
            'hue_mean': np.mean(H_region),
            'hue_std': self.circular_std(H_region),
            'saturation_mean': np.mean(S_region),
            'saturation_std': np.std(S_region),
            'lightness_mean': np.mean(L_region),
            'lightness_std': np.std(L_region),
            'size': np.sum(mask),
            'dominant_colors': self.get_dominant_colors(mask)
        }

        return analysis

    def circular_std(self, hues):
        """Вычисление стандартного отклонения для циклических данных"""
        if len(hues) == 0:
            return 0.0

        hues_rad = np.radians(hues)
        mean_cos = np.mean(np.cos(hues_rad))
        mean_sin = np.mean(np.sin(hues_rad))
        R = np.sqrt(mean_cos ** 2 + mean_sin ** 2)

        if R < 1e-10:
            return 180.0

        return np.sqrt(-2 * np.log(R)) * 180 / np.pi

    def get_dominant_colors(self, mask, n_colors=3):
        """Определяет доминантные цвета в области"""
        H_region = self.H_array[mask]
        S_region = self.S_array[mask]
        L_region = self.L_array[mask]

        if len(H_region) == 0:
            return []

        features = np.column_stack([H_region, S_region, L_region])

        n_samples = len(features)
        n_clusters = min(n_colors, max(2, n_samples // 20))

        if n_samples < n_clusters * 10:
            return [{
                'hue': np.mean(H_region),
                'saturation': np.mean(S_region),
                'lightness': np.mean(L_region),
                'proportion': 1.0
            }]

        try:
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=5)
            labels = kmeans.fit_predict(features)

            dominant_colors = []
            for cluster_id in range(n_clusters):
                cluster_mask = labels == cluster_id
                cluster_size = np.sum(cluster_mask)

                if cluster_size > len(labels) * 0.05:
                    dominant_colors.append({
                        'hue': np.median(H_region[cluster_mask]),
                        'saturation': np.median(S_region[cluster_mask]),
                        'lightness': np.median(L_region[cluster_mask]),
                        'proportion': cluster_size / len(labels)
                    })

            dominant_colors.sort(key=lambda x: x['proportion'], reverse=True)
            return dominant_colors[:n_colors]

        except Exception as e:
            print(f"⚠️ Ошибка кластеризации: {e}")
            return [{
                'hue': np.median(H_region),
                'saturation': np.median(S_region),
                'lightness': np.median(L_region),
                'proportion': 1.0
            }]

    def create_similarity_mask(self, thresholds, mask):
        """Создает маску областей, похожих на выбранную"""
        height, width = self.H_array.shape
        similarity_mask = np.zeros((height, width), dtype=bool)
        main_color = thresholds['main_color']

        step = 2 if self.params['fast_mode'] else 1

        for y in range(0, height, step):
            for x in range(0, width, step):
                current_color = [self.H_array[y, x], self.S_array[y, x], self.L_array[y, x]]
                similarity = self.enhanced_color_similarity(current_color,
                                                            [main_color['hue'],
                                                             main_color['saturation'],
                                                             main_color['lightness']])

                if similarity >= thresholds['similarity_threshold']:
                    similarity_mask[y, x] = True

        if step > 1:
            similarity_mask = ndimage.binary_dilation(similarity_mask,
                                                      structure=np.ones((3, 3)))

        return similarity_mask

    def post_process_mask(self, mask):
        """Постобработка маски для улучшения качества"""
        mask_uint8 = mask.astype(np.uint8) * 255

        if not self.params['fast_mode']:
            kernel = np.ones((3, 3), np.uint8)
            mask_uint8 = cv2.morphologyEx(mask_uint8, cv2.MORPH_OPEN, kernel)
            mask_uint8 = cv2.morphologyEx(mask_uint8, cv2.MORPH_CLOSE, kernel)

        return mask_uint8 > 0

    def extract_regions(self, mask, thresholds, source_analysis):
        """Извлекает и анализирует регионы из маски"""
        height, width = mask.shape
        visited = np.zeros((height, width), dtype=bool)
        regions = []

        def flood_fill(start_y, start_x):
            stack = [(start_y, start_x)]
            region_mask = np.zeros((height, width), dtype=bool)
            pixels = []
            hues, sats, lights = [], [], []

            while stack:
                y, x = stack.pop()

                if (y < 0 or y >= height or x < 0 or x >= width or
                        not mask[y, x] or visited[y, x]):
                    continue

                visited[y, x] = True
                region_mask[y, x] = True
                pixels.append((y, x))

                hues.append(self.H_array[y, x])
                sats.append(self.S_array[y, x])
                lights.append(self.L_array[y, x])

                for dy in [-1, 0, 1]:
                    for dx in [-1, 0, 1]:
                        if dy == 0 and dx == 0:
                            continue
                        stack.append((y + dy, x + dx))

            return region_mask, pixels, hues, sats, lights

        step = 2 if self.params['fast_mode'] else 1

        for y in range(0, height, step):
            for x in range(0, width, step):
                if mask[y, x] and not visited[y, x]:
                    region_mask, pixels, hues, sats, lights = flood_fill(y, x)
                    region_size = len(pixels)

                    if region_size >= self.params['min_region_size']:
                        region_uint8 = (region_mask * 255).astype(np.uint8)
                        contours, _ = cv2.findContours(region_uint8, cv2.RETR_EXTERNAL,
                                                       cv2.CHAIN_APPROX_SIMPLE)

                        if contours:
                            main_contour = max(contours, key=cv2.contourArea)
                            epsilon = 0.005 * cv2.arcLength(main_contour, True)
                            smoothed_contour = cv2.approxPolyDP(main_contour, epsilon, True)

                            quality_score = self.assess_region_quality(hues, sats, lights,
                                                                       region_mask, source_analysis)

                            if quality_score > 0.3:
                                region_info = {
                                    'mask': region_mask,
                                    'contour': smoothed_contour,
                                    'size': region_size,
                                    'avg_hue': np.median(hues),
                                    'avg_saturation': np.median(sats),
                                    'avg_lightness': np.median(lights),
                                    'quality_score': quality_score,
                                    'pixels': pixels,
                                    'compactness': self.compute_compactness(region_mask),
                                    'features': self.extract_region_features(region_mask),
                                    'is_filled': False
                                }
                                regions.append(region_info)

        regions.sort(key=lambda x: x['quality_score'], reverse=True)
        return regions

    def compute_compactness(self, mask):
        """Вычисляет компактность региона"""
        region_uint8 = (mask * 255).astype(np.uint8)
        contours, _ = cv2.findContours(region_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if contours:
            contour = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(contour)
            perimeter = cv2.arcLength(contour, True)

            if perimeter > 0:
                return (4 * np.pi * area) / (perimeter ** 2)

        return 0.5

    def extract_region_features(self, mask):
        """Извлекает признаки региона для машинного обучения"""
        H_region = self.H_array[mask]
        if len(H_region) == 0:
            return None

        S_region = self.S_array[mask]
        L_region = self.L_array[mask]

        features = {
            'hue_mean': np.mean(H_region),
            'hue_std': self.circular_std(H_region),
            'saturation_mean': np.mean(S_region),
            'saturation_std': np.std(S_region),
            'lightness_mean': np.mean(L_region),
            'lightness_std': np.std(L_region),
            'region_size': np.sum(mask),
            'compactness': self.compute_compactness(mask)
        }

        return features

    def assess_region_quality(self, hues, sats, lights, region_mask, source_analysis):
        """Оценивает качество региона"""
        if len(hues) == 0:
            return 0.0

        hue_std = self.circular_std(hues)
        sat_std = np.std(sats)

        hue_score = 1.0 - min(hue_std / 60.0, 1.0)
        sat_score = 1.0 - min(sat_std / 40.0, 1.0)
        color_consistency = 0.6 * hue_score + 0.4 * sat_score

        similarity_to_source = self.enhanced_color_similarity(
            [np.median(hues), np.median(sats), np.median(lights)],
            [source_analysis['hue_mean'], source_analysis['saturation_mean'],
             source_analysis['lightness_mean']]
        )

        shape_score = self.compute_compactness(region_mask)

        final_score = (0.5 * color_consistency +
                       0.3 * similarity_to_source +
                       0.2 * shape_score)

        return final_score

    def find_similar_regions(self, mask):
        """Улучшенный поиск похожих областей с повышенной точностью"""
        print("\n🔍 Запуск ТОЧНОГО поиска...")
        start_time = time.time()

        region_analysis = self.analyze_selection_region(mask)
        if not region_analysis:
            print("❌ Не удалось проанализировать выбранную область")
            return [], None

        dominant_colors = region_analysis['dominant_colors']
        if not dominant_colors:
            print("❌ Не удалось определить доминантные цвета")
            return [], None

        main_color = dominant_colors[0]
        thresholds = {
            'hue_threshold': self.params['hue_threshold'],
            'saturation_threshold': self.params['saturation_threshold'],
            'lightness_threshold': self.params['lightness_threshold'],
            'similarity_threshold': self.params['similarity_threshold'],
            'main_color': main_color
        }

        if self.params['multi_scale_analysis']:
            regions = self.multi_scale_region_growing(mask, thresholds)
        else:
            similarity_mask = self.create_adaptive_similarity_mask(thresholds, mask)
            similarity_mask = self.post_process_mask(similarity_mask)
            regions = self.extract_regions(similarity_mask, thresholds, region_analysis)

        if self.params['region_refinement'] and regions:
            print("🔄 Уточнение границ регионов...")
            refined_regions = []
            for region in regions:
                refined_region = self.refine_region_boundaries(region, thresholds)
                if refined_region:
                    refined_regions.append(refined_region)
            regions = refined_regions

        if self.params['fill_gaps'] and regions:
            print("🔄 Заполнение промежутков...")
            combined_mask = self.create_combined_mask(regions)
            filled_mask = self.fill_gaps_between_regions(combined_mask)

            if filled_mask is not None:
                filled_regions = self.extract_regions_from_filled_mask(filled_mask, regions)
                all_regions = regions + filled_regions
                unique_regions = self.remove_overlapping_regions(all_regions)
                regions = unique_regions

        if self.learning_system.is_trained():
            regions = self.apply_learning_filter(regions)

        elapsed_time = time.time() - start_time
        print(f"✅ Найдено {len(regions)} областей за {elapsed_time:.2f} сек")

        return regions, thresholds

    def create_combined_mask(self, regions):
        """Создает объединенную маску из всех регионов"""
        if not regions:
            return None

        height, width = self.H_array.shape
        combined_mask = np.zeros((height, width), dtype=bool)

        for region in regions:
            combined_mask = np.logical_or(combined_mask, region['mask'])

        return combined_mask

    def fill_gaps_between_regions(self, combined_mask):
        """Заполняет промежутки между регионами"""
        if combined_mask is None:
            return None

        mask_uint8 = (combined_mask * 255).astype(np.uint8)
        kernel_size = self.params['morphology_kernel']
        kernel = np.ones((kernel_size, kernel_size), np.uint8)
        closed_mask = cv2.morphologyEx(mask_uint8, cv2.MORPH_CLOSE, kernel)

        if self.params['gap_fill_size'] > 0:
            dilation_kernel = np.ones((self.params['gap_fill_size'],
                                       self.params['gap_fill_size']), np.uint8)
            dilated_mask = cv2.dilate(closed_mask, dilation_kernel, iterations=1)
            filled_mask = dilated_mask > 0
        else:
            filled_mask = closed_mask > 0

        return filled_mask

    def extract_regions_from_filled_mask(self, filled_mask, original_regions):
        """Извлекает регионы из заполненной маски"""
        if filled_mask is None:
            return original_regions

        height, width = filled_mask.shape
        visited = np.zeros((height, width), dtype=bool)
        new_regions = []

        def flood_fill(start_y, start_x):
            stack = [(start_y, start_x)]
            region_mask = np.zeros((height, width), dtype=bool)
            pixels = []
            hues, sats, lights = [], [], []

            while stack:
                y, x = stack.pop()

                if (y < 0 or y >= height or x < 0 or x >= width or
                        not filled_mask[y, x] or visited[y, x]):
                    continue

                visited[y, x] = True
                region_mask[y, x] = True
                pixels.append((y, x))

                hues.append(self.H_array[y, x])
                sats.append(self.S_array[y, x])
                lights.append(self.L_array[y, x])

                for dy in [-1, 0, 1]:
                    for dx in [-1, 0, 1]:
                        if dy == 0 and dx == 0:
                            continue
                        stack.append((y + dy, x + dx))

            return region_mask, pixels, hues, sats, lights

        for y in range(0, height, 2):
            for x in range(0, width, 2):
                if filled_mask[y, x] and not visited[y, x]:
                    region_mask, pixels, hues, sats, lights = flood_fill(y, x)
                    region_size = len(pixels)

                    if region_size >= self.params['min_region_size']:
                        region_uint8 = (region_mask * 255).astype(np.uint8)
                        contours, _ = cv2.findContours(region_uint8, cv2.RETR_EXTERNAL,
                                                       cv2.CHAIN_APPROX_SIMPLE)

                        if contours:
                            main_contour = max(contours, key=cv2.contourArea)
                            epsilon = 0.005 * cv2.arcLength(main_contour, True)
                            smoothed_contour = cv2.approxPolyDP(main_contour, epsilon, True)

                            avg_hue = np.mean(
                                [r['avg_hue'] for r in original_regions]) if original_regions else np.median(hues)
                            avg_saturation = np.mean(
                                [r['avg_saturation'] for r in original_regions]) if original_regions else np.median(
                                sats)
                            avg_lightness = np.mean(
                                [r['avg_lightness'] for r in original_regions]) if original_regions else np.median(
                                lights)

                            quality_score = 0.7

                            region_info = {
                                'mask': region_mask,
                                'contour': smoothed_contour,
                                'size': region_size,
                                'avg_hue': avg_hue,
                                'avg_saturation': avg_saturation,
                                'avg_lightness': avg_lightness,
                                'quality_score': quality_score,
                                'pixels': pixels,
                                'compactness': self.compute_compactness(region_mask),
                                'features': self.extract_region_features(region_mask),
                                'is_filled': True
                            }
                            new_regions.append(region_info)

        return new_regions

    def remove_overlapping_regions(self, regions, overlap_threshold=0.8):
        """Удаляет сильно перекрывающиеся регионы"""
        if len(regions) <= 1:
            return regions

        unique_regions = []
        used_indices = set()

        for i, region1 in enumerate(regions):
            if i in used_indices:
                continue

            is_duplicate = False
            for j, region2 in enumerate(regions):
                if i != j and j not in used_indices:
                    overlap = np.sum(np.logical_and(region1['mask'], region2['mask']))
                    min_size = min(region1['size'], region2['size'])

                    if overlap / min_size > overlap_threshold:
                        if region1['quality_score'] >= region2['quality_score']:
                            used_indices.add(j)
                        else:
                            is_duplicate = True
                            break

            if not is_duplicate:
                unique_regions.append(region1)
                used_indices.add(i)

        return unique_regions

    def apply_learning_filter(self, regions):
        """Применяет обученную модель для фильтрации регионов"""
        if not self.learning_system.is_trained() or not regions:
            return regions

        filtered_regions = []

        for region in regions:
            if region['features'] is not None:
                feature_vector = self.features_to_vector(region['features'])
                prediction = self.learning_system.predict(feature_vector)

                if prediction == 1:
                    filtered_regions.append(region)
            else:
                filtered_regions.append(region)

        print(f"🎓 Модель отфильтровала {len(regions) - len(filtered_regions)} регионов")
        return filtered_regions

    def features_to_vector(self, features):
        """Преобразует признаки в вектор для модели"""
        return np.array([
            features['hue_mean'],
            features['hue_std'],
            features['saturation_mean'],
            features['saturation_std'],
            features['lightness_mean'],
            features['lightness_std'],
            features['region_size'],
            features['compactness']
        ])

    def add_feedback(self, regions, is_positive=True):
        """Добавляет обратную связь для обучения"""
        feedback_type = "положительной" if is_positive else "отрицательной"
        print(f"\n📚 Добавление {feedback_type} обратной связи...")

        count = 0
        for region in regions:
            if region['features'] is not None:
                feature_vector = self.features_to_vector(region['features'])

                if is_positive:
                    self.learning_system.add_positive_example(feature_vector)
                else:
                    self.learning_system.add_negative_example(feature_vector)
                count += 1

        if count > 0:
            success = self.learning_system.train()
            if success:
                print(f"✅ Добавлено {count} {feedback_type} примеров")
            else:
                print("❌ Не удалось обучить модель на новых данных")
        else:
            print("❌ Не удалось извлечь признаки для обучения")

    def delete_region(self, region_index):
        """Удаляет регион и добавляет отрицательную обратную связь"""
        if 0 <= region_index < len(self.current_regions):
            region = self.current_regions[region_index]

            if region['features'] is not None:
                feature_vector = self.features_to_vector(region['features'])
                self.learning_system.add_negative_example(feature_vector)
                self.learning_system.train()

            self.current_regions.pop(region_index)
            print(f"🗑️ Удален регион {region_index + 1}")
            return True

        return False

    def select_region_for_deletion(self, event):
        """Обработчик выбора региона для удаления"""
        if not self.delete_mode or event.inaxes != self.ax2:
            return

        x, y = event.xdata, event.ydata

        for i, region in enumerate(self.current_regions):
            contour = region['contour']
            path = Path(contour[:, 0])
            if path.contains_point([x, y]):
                self.selected_region_index = i
                self.highlight_selected_region(i)
                print(f"🎯 Выбран регион {i + 1} для удаления")
                return

    def highlight_selected_region(self, region_index):
        """Подсвечивает выбранный регион"""
        for patch in self.region_patches:
            patch.set_edgecolor('blue')
            patch.set_linewidth(1)

        if 0 <= region_index < len(self.region_patches):
            self.region_patches[region_index].set_edgecolor('red')
            self.region_patches[region_index].set_linewidth(3)

        self.fig.canvas.draw()

    def display_interactive_results(self, ax, regions, thresholds):
        """Отображает результаты с улучшенной визуализацией"""
        ax.clear()
        ax.imshow(self.original_image)
        self.region_patches = []

        if not regions:
            ax.set_title('❌ Области не найдены')
            self.fig.canvas.draw()
            return

        original_regions = [r for r in regions if not r.get('is_filled', False)]
        filled_regions = [r for r in regions if r.get('is_filled', False)]

        print(f"📊 Оригинальные регионы: {len(original_regions)}, Заполненные: {len(filled_regions)}")

        for i, region in enumerate(original_regions):
            contour = region['contour']
            ax.plot(contour[:, 0, 0], contour[:, 0, 1], linewidth=2, color='green')
            alpha = 0.3 + 0.3 * region['quality_score']
            poly = patches.Polygon(contour[:, 0], alpha=alpha, color='green',
                                   linewidth=2, edgecolor='darkgreen')
            ax.add_patch(poly)
            self.region_patches.append(poly)


        for i, region in enumerate(filled_regions, start=len(original_regions)):
            contour = region['contour']
            ax.plot(contour[:, 0, 0], contour[:, 0, 1], linewidth=1, color='blue', linestyle='--')
            alpha = 0.2
            poly = patches.Polygon(contour[:, 0], alpha=alpha, color='blue',
                                   linewidth=1, edgecolor='blue', linestyle='--')
            ax.add_patch(poly)
            self.region_patches.append(poly)


        model_status = " (с моделью)" if self.learning_system.is_trained() else ""
        fill_status = " (с заполнением)" if self.params['fill_gaps'] else ""
        precision_status = " (высокая точность)" if self.params['multi_scale_analysis'] else ""
        ax.set_title(f'🎯 Найдено {len(regions)} областей{model_status}{fill_status}{precision_status}')
        ax.axis('off')

        self.fig.canvas.draw()
        print(
            f"📊 Отображено {len(regions)} областей ({len(original_regions)} оригинальных + {len(filled_regions)} заполненных)")

    def create_interactive_interface(self):
        """Создает интерактивный интерфейс с улучшенными настройками точности"""
        fig = plt.figure(figsize=(28, 16))
        self.fig = fig

        # Основные subplots
        ax1 = plt.axes([0.05, 0.4, 0.4, 0.55])
        ax2 = plt.axes([0.55, 0.4, 0.4, 0.55])
        self.ax1 = ax1
        self.ax2 = ax2

        # Элементы управления
        ax_slider_hue = plt.axes([0.05, 0.32, 0.2, 0.02])
        ax_slider_sat = plt.axes([0.05, 0.29, 0.2, 0.02])
        ax_slider_light = plt.axes([0.05, 0.26, 0.2, 0.02])
        ax_slider_sim = plt.axes([0.05, 0.23, 0.2, 0.02])
        ax_slider_confidence = plt.axes([0.05, 0.20, 0.2, 0.02])
        ax_slider_gap = plt.axes([0.05, 0.17, 0.2, 0.02])

        # Кнопки
        ax_button_apply = plt.axes([0.3, 0.32, 0.08, 0.04])
        ax_button_clear = plt.axes([0.39, 0.32, 0.08, 0.04])
        ax_button_finish = plt.axes([0.48, 0.32, 0.08, 0.04])

        ax_button_high_precision = plt.axes([0.57, 0.32, 0.12, 0.04])
        ax_button_balanced = plt.axes([0.70, 0.32, 0.12, 0.04])
        ax_button_fast = plt.axes([0.83, 0.32, 0.12, 0.04])

        ax_button_positive = plt.axes([0.57, 0.26, 0.1, 0.04])
        ax_button_negative = plt.axes([0.68, 0.26, 0.1, 0.04])
        ax_button_delete_mode = plt.axes([0.79, 0.26, 0.1, 0.04])
        ax_button_delete_selected = plt.axes([0.90, 0.26, 0.1, 0.04])

        ax_button_save_model = plt.axes([0.57, 0.20, 0.1, 0.04])
        ax_button_delete_all = plt.axes([0.68, 0.20, 0.1, 0.04])
        ax_button_retrain = plt.axes([0.79, 0.20, 0.1, 0.04])
        ax_button_show_analysis = plt.axes([0.90, 0.20, 0.1, 0.04])
        ax_button_show_spectrums = plt.axes([0.57, 0.14, 0.33, 0.04])  # Новая кнопка для спектров

        # Чекбоксы
        ax_checkbox_adaptive = plt.axes([0.3, 0.26, 0.15, 0.04])
        ax_checkbox_multiscale = plt.axes([0.3, 0.20, 0.15, 0.04])
        ax_checkbox_edges = plt.axes([0.3, 0.14, 0.15, 0.04])
        ax_checkbox_refine = plt.axes([0.46, 0.26, 0.15, 0.04])
        ax_checkbox_fast = plt.axes([0.46, 0.20, 0.15, 0.04])
        ax_checkbox_fill = plt.axes([0.46, 0.14, 0.15, 0.04])

        # Отображаем исходное изображение
        ax1.imshow(self.original_image)
        ax1.set_title('🎨 РИСУЙТЕ ФИГУРУ (кликайте для добавления точек)')
        ax1.axis('off')

        ax2.imshow(self.original_image)
        ax2.set_title('Результаты точного поиска - ЗЕЛЕНЫЕ: оригинальные, СИНИЕ: заполненные')
        ax2.axis('off')

        # Создаем элементы управления
        slider_hue = Slider(ax_slider_hue, 'Hue порог', 5, 40, valinit=self.params['hue_threshold'])
        slider_sat = Slider(ax_slider_sat, 'Saturation порог', 10, 50, valinit=self.params['saturation_threshold'])
        slider_light = Slider(ax_slider_light, 'V/Lightness порог', 10, 80, valinit=self.params['lightness_threshold'])
        slider_sim = Slider(ax_slider_sim, 'Порог схожести', 0.3, 0.9, valinit=self.params['similarity_threshold'])
        slider_confidence = Slider(ax_slider_confidence, 'Порог уверенности', 0.5, 0.95,
                                   valinit=self.params['confidence_threshold'])
        slider_gap = Slider(ax_slider_gap, 'Размер заполнения', 1, 20, valinit=self.params['gap_fill_size'])

        # Checkbox'ы
        adaptive_check = CheckButtons(ax_checkbox_adaptive, ['🎯 Адаптивные пороги'],
                                      [self.params['adaptive_threshold']])
        multiscale_check = CheckButtons(ax_checkbox_multiscale, ['📊 Многоуровневый анализ'],
                                        [self.params['multi_scale_analysis']])
        edges_check = CheckButtons(ax_checkbox_edges, ['🔄 Сохранение границ'], [self.params['edge_preservation']])
        refine_check = CheckButtons(ax_checkbox_refine, ['✏️ Уточнение регионов'], [self.params['region_refinement']])
        fast_check = CheckButtons(ax_checkbox_fast, ['🚀 Быстрый режим'], [self.params['fast_mode']])
        fill_check = CheckButtons(ax_checkbox_fill, ['🔄 Заполнить промежутки'], [self.params['fill_gaps']])

        # Создаем кнопки
        button_apply = Button(ax_button_apply, '🔍 Поиск')
        button_clear = Button(ax_button_clear, '🗑️ Очистить')
        button_finish = Button(ax_button_finish, '✅ Завершить')
        button_high_precision = Button(ax_button_high_precision, '🎯 Высокая точность')
        button_balanced = Button(ax_button_balanced, '⚖️ Сбалансировано')
        button_fast = Button(ax_button_fast, '🚀 Быстро')
        button_positive = Button(ax_button_positive, '👍 Все верно')
        button_negative = Button(ax_button_negative, '👎 Все неверно')
        button_delete_mode = Button(ax_button_delete_mode, '🎯 Режим удаления')
        button_delete_selected = Button(ax_button_delete_selected, '🗑️ Удалить выбранный')
        button_save_model = Button(ax_button_save_model, '💾 Сохранить модель')
        button_delete_all = Button(ax_button_delete_all, '🗑️ Удалить все')
        button_retrain = Button(ax_button_retrain, '🔄 Переобучить')
        button_show_analysis = Button(ax_button_show_analysis, '📊 Показать анализ')
        button_show_spectrums = Button(ax_button_show_spectrums, '🌈 ПОКАЗАТЬ HSV-СПЕКТРЫ')  # Новая кнопка

        # Переменные состояния
        self.selection_vertices = []
        self.delete_mode = False
        self.current_regions = []
        self.selected_region_index = None
        self.region_patches = []

        def update_params(val):
            self.params['hue_threshold'] = slider_hue.val
            self.params['saturation_threshold'] = slider_sat.val
            self.params['lightness_threshold'] = slider_light.val
            self.params['similarity_threshold'] = slider_sim.val
            self.params['confidence_threshold'] = slider_confidence.val
            self.params['gap_fill_size'] = int(slider_gap.val)

        def toggle_adaptive_threshold(label):
            self.params['adaptive_threshold'] = not self.params['adaptive_threshold']
            print(f"🎯 Адаптивные пороги: {'ВКЛ' if self.params['adaptive_threshold'] else 'ВЫКЛ'}")

        def toggle_multiscale_analysis(label):
            self.params['multi_scale_analysis'] = not self.params['multi_scale_analysis']
            print(f"📊 Многоуровневый анализ: {'ВКЛ' if self.params['multi_scale_analysis'] else 'ВЫКЛ'}")

        def toggle_edge_preservation(label):
            self.params['edge_preservation'] = not self.params['edge_preservation']
            print(f"🔄 Сохранение границ: {'ВКЛ' if self.params['edge_preservation'] else 'ВЫКЛ'}")

        def toggle_region_refinement(label):
            self.params['region_refinement'] = not self.params['region_refinement']
            print(f"✏️ Уточнение регионов: {'ВКЛ' if self.params['region_refinement'] else 'ВЫКЛ'}")

        def toggle_fast_mode(label):
            self.params['fast_mode'] = not self.params['fast_mode']
            print(f"🚀 Быстрый режим: {'ВКЛ' if self.params['fast_mode'] else 'ВЫКЛ'}")

        def toggle_fill_gaps(label):
            self.params['fill_gaps'] = not self.params['fill_gaps']
            print(f"🔄 Заполнение промежутков: {'ВКЛ' if self.params['fill_gaps'] else 'ВЫКЛ'}")

        def set_high_precision_mode(event):
            self.params.update({
                'adaptive_threshold': True,
                'multi_scale_analysis': True,
                'edge_preservation': True,
                'region_refinement': True,
                'confidence_threshold': 0.8,
                'similarity_threshold': 0.6,
                'fast_mode': False
            })
            slider_sim.set_val(0.6)
            slider_confidence.set_val(0.8)
            print("🎯 Режим ВЫСОКОЙ ТОЧНОСТИ активирован")

        def set_balanced_mode(event):
            self.params.update({
                'adaptive_threshold': True,
                'multi_scale_analysis': True,
                'edge_preservation': True,
                'region_refinement': True,
                'confidence_threshold': 0.7,
                'similarity_threshold': 0.7,
                'fast_mode': False
            })
            slider_sim.set_val(0.7)
            slider_confidence.set_val(0.7)
            print("⚖️ СБАЛАНСИРОВАННЫЙ режим активирован")

        def set_fast_mode(event):
            self.params.update({
                'adaptive_threshold': False,
                'multi_scale_analysis': False,
                'edge_preservation': False,
                'region_refinement': False,
                'confidence_threshold': 0.6,
                'similarity_threshold': 0.8,
                'fast_mode': True
            })
            slider_sim.set_val(0.8)
            slider_confidence.set_val(0.6)
            print("🚀 БЫСТРЫЙ режим активирован")

        def show_analysis(event):
            self.print_image_analysis()

            fig_analysis = plt.figure(figsize=(15, 5))

            ax1 = fig_analysis.add_subplot(131)
            hue_flat = self.H_array.flatten()
            hue_flat = hue_flat[hue_flat >= 0]
            ax1.hist(hue_flat, bins=36, range=(0, 360), color='red', alpha=0.7)
            ax1.set_title('Распределение тонов (Hue)')
            ax1.set_xlabel('Hue (градусы)')
            ax1.set_ylabel('Частота')

            ax2 = fig_analysis.add_subplot(132)
            sat_flat = self.S_array.flatten()
            ax2.hist(sat_flat, bins=50, range=(0, 100), color='green', alpha=0.7)
            ax2.set_title('Распределение насыщенности (Saturation)')
            ax2.set_xlabel('Saturation (%)')
            ax2.set_ylabel('Частота')

            ax3 = fig_analysis.add_subplot(133)
            light_flat = self.L_array.flatten()
            ax3.hist(light_flat, bins=50, range=(0, 100), color='blue', alpha=0.7)
            ax3.set_title('Распределение яркости (Lightness)')
            ax3.set_xlabel('Lightness (%)')
            ax3.set_ylabel('Частота')

            plt.tight_layout()
            plt.show()

        def show_spectrums(event):
            """Показывает визуализации HSV-спектров"""
            self.create_hsv_visualizations()

        def on_click(event):
            if event.inaxes != ax1:
                return

            if event.button == 1:
                x, y = event.xdata, event.ydata
                self.selection_vertices.append([x, y])

                for artist in ax1.collections + ax1.lines:
                    artist.remove()

                if len(self.selection_vertices) > 1:
                    vertices_array = np.array(self.selection_vertices)
                    ax1.plot(vertices_array[:, 0], vertices_array[:, 1], 'ro-', linewidth=2, markersize=4)
                else:
                    ax1.plot(x, y, 'ro', markersize=4)

                fig.canvas.draw()

        def finish_shape(event):
            if len(self.selection_vertices) < 3:
                print("❌ Нужно как минимум 3 точки!")
                return

            if self.selection_vertices[0] != self.selection_vertices[-1]:
                self.selection_vertices.append(self.selection_vertices[0])

            polygon = patches.Polygon(self.selection_vertices, alpha=0.3, color='red')
            ax1.add_patch(polygon)

            vertices_array = np.array(self.selection_vertices)
            ax1.plot(vertices_array[:, 0], vertices_array[:, 1], 'r-', linewidth=2)

            fig.canvas.draw()

            image_shape = self.H_array.shape
            self.current_selection = self.create_selection_mask(self.selection_vertices, image_shape)

            selected_pixels = np.sum(self.current_selection)
            print(f"✅ Фигура завершена! Выделено {selected_pixels} пикселей")

        def apply_search(event):
            if self.current_selection is None:
                print("❌ Сначала создайте фигуру!")
                return

            regions, thresholds = self.find_similar_regions(self.current_selection)
            self.current_regions = regions
            self.display_interactive_results(ax2, regions, thresholds)

        def clear_selection(event):
            self.current_selection = None
            self.selection_vertices = []
            self.current_regions = []
            self.selected_region_index = None
            self.region_patches = []

            for artist in ax1.collections + ax1.lines + ax1.patches:
                artist.remove()

            ax2.clear()
            ax2.imshow(self.original_image)
            ax2.set_title('Результаты поиска - ЗЕЛЕНЫЕ: оригинальные, СИНИЕ: заполненные')
            ax2.axis('off')

            fig.canvas.draw()
            print("🧹 Выделение очищено")

        def activate_delete_mode(event):
            self.delete_mode = True
            print("🎯 Режим удаления активирован. Кликайте на области для выбора.")
            ax2.set_title('РЕЖИМ УДАЛЕНИЯ - кликайте на области для выбора')
            fig.canvas.draw()

        def delete_selected_region(event):
            if self.selected_region_index is None:
                print("❌ Сначала выберите регион для удаления!")
                return

            if self.delete_region(self.selected_region_index):
                self.display_interactive_results(ax2, self.current_regions, None)
                self.selected_region_index = None

        def delete_all_regions(event):
            if not self.current_regions:
                print("❌ Нет регионов для удаления!")
                return

            print(f"🗑️ Удаление всех {len(self.current_regions)} регионов...")
            self.add_feedback(self.current_regions, is_positive=False)
            self.current_regions = []
            self.selected_region_index = None

            ax2.clear()
            ax2.imshow(self.original_image)
            ax2.set_title('Все регионы удалены')
            ax2.axis('off')
            fig.canvas.draw()

        def add_positive_feedback(event):
            if not self.current_regions:
                print("❌ Сначала выполните поиск!")
                return
            self.add_feedback(self.current_regions, is_positive=True)
            print("✅ Положительная обратная связь добавлена!")

        def add_negative_feedback(event):
            if not self.current_regions:
                print("❌ Сначала выполните поиск!")
                return
            self.add_feedback(self.current_regions, is_positive=False)
            print("✅ Отрицательная обратная связь добавлена!")

        def retrain_model(event):
            if self.learning_system.train():
                print("🔄 Модель переобучена!")
            else:
                print("❌ Не удалось переобучить модель")

        def save_model(event):
            if self.learning_system.save_model():
                print("💾 Модель сохранена!")
            else:
                print("❌ Не удалось сохранить модель")

        # Настраиваем взаимодействие
        slider_hue.on_changed(update_params)
        slider_sat.on_changed(update_params)
        slider_light.on_changed(update_params)
        slider_sim.on_changed(update_params)
        slider_confidence.on_changed(update_params)
        slider_gap.on_changed(update_params)

        adaptive_check.on_clicked(toggle_adaptive_threshold)
        multiscale_check.on_clicked(toggle_multiscale_analysis)
        edges_check.on_clicked(toggle_edge_preservation)
        refine_check.on_clicked(toggle_region_refinement)
        fast_check.on_clicked(toggle_fast_mode)
        fill_check.on_clicked(toggle_fill_gaps)

        # Подключаем обработчики
        fig.canvas.mpl_connect('button_press_event', on_click)
        fig.canvas.mpl_connect('button_press_event', self.select_region_for_deletion)

        button_apply.on_clicked(apply_search)
        button_clear.on_clicked(clear_selection)
        button_finish.on_clicked(finish_shape)
        button_high_precision.on_clicked(set_high_precision_mode)
        button_balanced.on_clicked(set_balanced_mode)
        button_fast.on_clicked(set_fast_mode)
        button_positive.on_clicked(add_positive_feedback)
        button_negative.on_clicked(add_negative_feedback)
        button_delete_mode.on_clicked(activate_delete_mode)
        button_delete_selected.on_clicked(delete_selected_region)
        button_save_model.on_clicked(save_model)
        button_delete_all.on_clicked(delete_all_regions)
        button_retrain.on_clicked(retrain_model)
        button_show_analysis.on_clicked(show_analysis)
        button_show_spectrums.on_clicked(show_spectrums)  # Подключаем новую кнопку

        plt.show()


class ImprovedLearningSystem:
    """Улучшенная система машинного обучения"""

    def __init__(self):
        self.model = None
        self.positive_examples = []
        self.negative_examples = []
        self.is_trained_flag = False
        self.model_file = "improved_detector_model.pkl"

    def add_positive_example(self, features):
        self.positive_examples.append(features)

    def add_negative_example(self, features):
        self.negative_examples.append(features)

    def train(self):
        """Обучение модели с улучшенными параметрами"""
        if len(self.positive_examples) < 2 or len(self.negative_examples) < 2:
            print("⚠️ Недостаточно данных для обучения")
            return False

        try:
            X_positive = np.array(self.positive_examples)
            X_negative = np.array(self.negative_examples)

            X = np.vstack([X_positive, X_negative])
            y = np.hstack([np.ones(len(X_positive)), np.zeros(len(X_negative))])

            self.model = RandomForestClassifier(
                n_estimators=50,
                max_depth=10,
                min_samples_split=5,
                random_state=42,
                n_jobs=-1
            )

            self.model.fit(X, y)
            self.is_trained_flag = True

            accuracy = self.model.score(X, y)
            print(f"🎓 Модель обучена! Точность: {accuracy:.3f}")
            print(f"   📊 Примеров: +{len(X_positive)}/-{len(X_negative)}")

            return True

        except Exception as e:
            print(f"❌ Ошибка при обучении: {e}")
            return False

    def predict(self, features):
        if not self.is_trained_flag or self.model is None:
            return 1

        try:
            features_array = np.array(features).reshape(1, -1)
            return self.model.predict(features_array)[0]
        except:
            return 1

    def is_trained(self):
        return self.is_trained_flag

    def save_model(self):
        if not self.is_trained_flag:
            return False

        try:
            joblib.dump({
                'model': self.model,
                'positive_examples': self.positive_examples,
                'negative_examples': self.negative_examples
            }, self.model_file)
            return True
        except Exception as e:
            print(f"❌ Ошибка при сохранении: {e}")
            return False

    def load_model(self):
        try:
            if os.path.exists(self.model_file):
                data = joblib.load(self.model_file)
                self.model = data['model']
                self.positive_examples = data['positive_examples']
                self.negative_examples = data['negative_examples']
                self.is_trained_flag = True
                print(f"✅ Модель загружена! Примеров: +{len(self.positive_examples)}/-{len(self.negative_examples)}")
                return True
        except Exception as e:
            print(f"❌ Ошибка при загрузке: {e}")
        return False


def main():
    """Основная функция программы"""
    IMAGE_PATH = "3.png"

    if not os.path.exists(IMAGE_PATH):
        print(f"❌ Файл {IMAGE_PATH} не найден!")
        return

    try:
        detector = ImprovedRegionDetector()
        detector.load_and_convert_image(IMAGE_PATH)
        detector.learning_system.load_model()

        print("\n" + "=" * 80)
        print("🎯 УЛУЧШЕННАЯ СИСТЕМА ТОЧНОГО ПОИСКА ОДНОРОДНЫХ ОБЛАСТЕЙ")
        print("=" * 80)
        print("ОСНОВНЫЕ УЛУЧШЕНИЯ ТОЧНОСТИ:")
        print("• Адаптивные пороги на основе локальных характеристик")
        print("• Многоуровневый анализ (грубый + точный поиск)")
        print("• Учет границ изображения для сохранения контуров")
        print("• Уточнение границ регионов")
        print("• Карта уверенности для отсева ложных срабатываний")
        print("• Предустановленные режимы: Высокая точность / Сбалансированный / Быстрый")
        print("• Визуализация HSV-спектров для анализа изображения")
        print("=" * 80)
        print("РЕКОМЕНДАЦИИ ПО ИСПОЛЬЗОВАНИЮ:")
        print("1. Для сложных изображений используйте режим '🎯 Высокая точность'")
        print("2. Для четких границ включите '🔄 Сохранение границ'")
        print("3. Используйте '✏️ Уточнение регионов' для точных контуров")
        print("4. Настройте 'Порог уверенности' для контроля ложных срабатываний")
        print("5. Нажмите '🌈 ПОКАЗАТЬ HSV-СПЕКТРЫ' для анализа цветового состава")
        print("=" * 80)

        detector.create_interactive_interface()

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()