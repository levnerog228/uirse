from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import numpy as np
from PIL import Image
import io
import cv2
from scipy import ndimage
import base64
import json
import immodus_bib_1l as imb
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier
import joblib
import warnings
import time
import os
from matplotlib.path import Path

warnings.filterwarnings('ignore')

app = Flask(__name__)
CORS(app)


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
            'adaptive_threshold': True,
            'multi_scale_analysis': True,
            'edge_preservation': True,
            'region_refinement': True,
            'confidence_threshold': 0.8,
            'color_variance_weight': 0.1,
            'spatial_compactness': 0.2,
            'boundary_sensitivity': 0.7,
        }

        self.image_array = None
        self.H_array = None
        self.S_array = None
        self.L_array = None
        self.edge_map = None
        self.gradient_magnitude = None
        self.confidence_map = None

        self.learning_system = ImprovedLearningSystem()

    def load_image_from_bytes(self, image_bytes):
        """Точная загрузка изображения как в изначальной версии"""
        image = Image.open(io.BytesIO(image_bytes))
        self.image_array = np.array(image)
        height, width, _ = self.image_array.shape

        print("🔄 Точная конвертация RGB в HSL...")
        self.H_array = np.zeros((height, width), dtype=np.float32)
        self.S_array = np.zeros((height, width), dtype=np.float32)
        self.L_array = np.zeros((height, width), dtype=np.float32)

        # ТОЧНАЯ КОНВЕРТАЦИЯ КАК В ИЗНАЧАЛЬНОЙ ВЕРСИИ
        for y in range(height):
            for x in range(width):
                r, g, b = self.image_array[y, x, :3]
                hsl = imb.RGBtoHSL(r, g, b)
                self.H_array[y, x] = hsl[0, 0]
                self.S_array[y, x] = hsl[0, 1]
                self.L_array[y, x] = hsl[0, 2]

        self.analyze_image_characteristics()
        self.precompute_accuracy_maps()
        self.enhance_arrays()

        return height, width

    def analyze_image_characteristics(self):
        """Анализ характеристик изображения как в изначальной версии"""
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

    def find_dominant_hue_ranges(self, hue_data, n_ranges=3):
        """Находит доминирующие диапазоны тонов как в изначальной версии"""
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

    def precompute_accuracy_maps(self):
        """Точный расчет карт как в изначальной версии"""
        print("🔄 Расчет карт для точного поиска...")

        gray_image = cv2.cvtColor(self.image_array, cv2.COLOR_RGB2GRAY)
        self.edge_map = cv2.Canny(gray_image, 50, 150)

        sobelx = cv2.Sobel(gray_image, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray_image, cv2.CV_64F, 0, 1, ksize=3)
        self.gradient_magnitude = np.sqrt(sobelx ** 2 + sobely ** 2)

        if self.gradient_magnitude.max() > 0:
            self.gradient_magnitude = self.gradient_magnitude / self.gradient_magnitude.max()

    def enhance_arrays(self):
        """Улучшенная обработка массивов как в изначальной версии"""
        if self.params['fast_mode']:
            size = 2
        else:
            size = 3

        self.H_array = ndimage.median_filter(self.H_array, size=size)
        self.S_array = ndimage.median_filter(self.S_array, size=size)
        self.L_array = ndimage.median_filter(self.L_array, size=size)
        self.H_array = np.mod(self.H_array, 360)

    def circular_std(self, hues):
        """Точное вычисление стандартного отклонения для циклических данных"""
        if len(hues) == 0:
            return 0.0

        hues_rad = np.radians(hues)
        mean_cos = np.mean(np.cos(hues_rad))
        mean_sin = np.mean(np.sin(hues_rad))
        R = np.sqrt(mean_cos ** 2 + mean_sin ** 2)

        if R < 1e-10:
            return 180.0

        return np.sqrt(-2 * np.log(R)) * 180 / np.pi

    def enhanced_color_similarity(self, color1, color2, spatial_distance=1, edge_weight=1.0):
        """Точная метрика цветового сходства как в изначальной версии"""
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
        """Точное создание адаптивной маски как в изначальной версии"""
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
        """Точное уточнение маски как в изначальной версии"""
        mask_uint8 = (mask * 255).astype(np.uint8)

        kernel = np.ones((3, 3), np.uint8)
        mask_cleaned = cv2.morphologyEx(mask_uint8, cv2.MORPH_OPEN, kernel)
        mask_cleaned = cv2.morphologyEx(mask_cleaned, cv2.MORPH_CLOSE, kernel)

        high_confidence_mask = confidence_map > self.params['confidence_threshold']
        mask_combined = np.logical_or(mask_cleaned > 0, high_confidence_mask)

        return mask_combined

    def multi_scale_region_growing(self, seed_mask, thresholds):
        """Многоуровневый рост регионов как в изначальной версии"""
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
        """Точное уточнение границ региона как в изначальной версии"""
        mask = region['mask']
        contour_points = region['contour_points']

        contour_mask = np.zeros_like(mask, dtype=np.uint8)
        if len(contour_points) > 0:
            contour_array = np.array(contour_points, dtype=np.int32).reshape(-1, 1, 2)
            cv2.drawContours(contour_mask, [contour_array], 0, 255, 2)

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
            new_contour = self.extract_contour(refined_mask)
            if new_contour is not None:
                region['contour_points'] = new_contour
            region['size'] = np.sum(refined_mask)
            region['quality_score'] = self.assess_region_quality_from_mask(refined_mask, main_color)

            return region

        return None

    def extract_contour(self, mask):
        """Точное извлечение контура как в изначальной версии"""
        mask_uint8 = (mask * 255).astype(np.uint8)
        contours, _ = cv2.findContours(mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if contours:
            main_contour = max(contours, key=cv2.contourArea)
            epsilon = 0.002 * cv2.arcLength(main_contour, True)
            smoothed_contour = cv2.approxPolyDP(main_contour, epsilon, True)

            contour_points = []
            for point in smoothed_contour:
                if len(point) > 0:
                    x = int(point[0][0])
                    y = int(point[0][1])
                    contour_points.append([x, y])

            return contour_points if contour_points else None
        return None

    def assess_region_quality_from_mask(self, mask, main_color):
        """Точная оценка качества региона как в изначальной версии"""
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
        """Получение граничных пикселей региона как в изначальной версии"""
        kernel = np.ones((3, 3), np.uint8)
        eroded = cv2.erode(mask.astype(np.uint8), kernel, iterations=1)
        boundary = mask.astype(np.uint8) - eroded
        return boundary > 0

    def create_selection_mask(self, vertices, image_shape):
        """Создание маски выделения как в изначальной версии"""
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
        """Точный анализ выбранной области как в изначальной версии"""
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

    def get_dominant_colors(self, mask, n_colors=3):
        """Точное определение доминантных цветов как в изначальной версии"""
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
        """Создание маски похожих областей как в изначальной версии"""
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
        """Постобработка маски как в изначальной версии"""
        mask_uint8 = mask.astype(np.uint8) * 255

        if not self.params['fast_mode']:
            kernel = np.ones((3, 3), np.uint8)
            mask_uint8 = cv2.morphologyEx(mask_uint8, cv2.MORPH_OPEN, kernel)
            mask_uint8 = cv2.morphologyEx(mask_uint8, cv2.MORPH_CLOSE, kernel)

        return mask_uint8 > 0

    def extract_regions(self, mask, thresholds, source_analysis):
        """Точное извлечение регионов как в изначальной версии"""
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
                        contour_points = self.extract_contour(region_mask)

                        if contour_points is not None:
                            quality_score = self.assess_region_quality(hues, sats, lights,
                                                                       region_mask, source_analysis)

                            if quality_score > 0.3:
                                region_info = {
                                    'mask': region_mask,
                                    'contour_points': contour_points,
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
        """Вычисление компактности региона как в изначальной версии"""
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
        """Извлечение признаков региона для машинного обучения"""
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
        """Точная оценка качества региона как в изначальной версии"""
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

    def find_similar_regions(self, mask, params):
        """ТОЧНЫЙ поиск похожих областей как в изначальной версии"""
        print("\n🔍 Запуск ТОЧНОГО поиска...")
        start_time = time.time()

        # ОБНОВЛЯЕМ ПАРАМЕТРЫ ДЛЯ ТОЧНОСТИ
        self.params.update(params)
        self.params['fast_mode'] = False  # ВСЕГДА ВЫКЛЮЧАЕМ БЫСТРЫЙ РЕЖИМ
        self.params['multi_scale_analysis'] = True  # ВСЕГДА ВКЛЮЧАЕМ
        self.params['region_refinement'] = True  # ВСЕГДА ВКЛЮЧАЕМ

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

        # ВСЕГДА ИСПОЛЬЗУЕМ МНОГОУРОВНЕВЫЙ АНАЛИЗ
        if self.params['multi_scale_analysis']:
            regions = self.multi_scale_region_growing(mask, thresholds)
        else:
            similarity_mask = self.create_adaptive_similarity_mask(thresholds, mask)
            similarity_mask = self.post_process_mask(similarity_mask)
            regions = self.extract_regions(similarity_mask, thresholds, region_analysis)

        # ВСЕГДА ИСПОЛЬЗУЕМ УТОЧНЕНИЕ ГРАНИЦ
        if self.params['region_refinement'] and regions:
            print("🔄 Уточнение границ регионов...")
            refined_regions = []
            for region in regions:
                refined_region = self.refine_region_boundaries(region, thresholds)
                if refined_region:
                    refined_regions.append(refined_region)
            regions = refined_regions

        # ЗАПОЛНЕНИЕ ПРОМЕЖУТКОВ
        if self.params['fill_gaps'] and regions:
            print("🔄 Заполнение промежутков...")
            combined_mask = self.create_combined_mask(regions)
            filled_mask = self.fill_gaps_between_regions(combined_mask)

            if filled_mask is not None:
                filled_regions = self.extract_regions_from_filled_mask(filled_mask, regions)
                all_regions = regions + filled_regions
                unique_regions = self.remove_overlapping_regions(all_regions)
                regions = unique_regions

        # ПРИМЕНЕНИЕ МАШИННОГО ОБУЧЕНИЯ
        if self.learning_system.is_trained():
            regions = self.apply_learning_filter(regions)

        elapsed_time = time.time() - start_time
        print(f"✅ Найдено {len(regions)} областей за {elapsed_time:.2f} сек")

        return regions, thresholds

    def create_combined_mask(self, regions):
        """Создание объединенной маски"""
        if not regions:
            return None

        height, width = self.H_array.shape
        combined_mask = np.zeros((height, width), dtype=bool)

        for region in regions:
            combined_mask = np.logical_or(combined_mask, region['mask'])

        return combined_mask

    def fill_gaps_between_regions(self, combined_mask):
        """Заполнение промежутков между регионами"""
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
        """Извлечение регионов из заполненной маски"""
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
                        contour_points = self.extract_contour(region_mask)
                        if contour_points is not None:
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
                                'contour_points': contour_points,
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
        """Удаление перекрывающихся регионов"""
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
        """Применение обученной модели для фильтрации регионов"""
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
        """Преобразование признаков в вектор для модели"""
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
        """Добавление обратной связи для обучения"""
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

    def get_hsv_analysis(self):
        """Анализ HSV характеристик изображения"""
        hue_flat = self.H_array.flatten()
        hue_flat = hue_flat[hue_flat >= 0]
        saturation_flat = self.S_array.flatten()
        lightness_flat = self.L_array.flatten()

        analysis = {
            'hue': {
                'mean': float(np.mean(hue_flat)),
                'std': float(self.circular_std(hue_flat)),
                'contrast': float(np.percentile(hue_flat, 95) - np.percentile(hue_flat, 5))
            },
            'saturation': {
                'mean': float(np.mean(saturation_flat)),
                'std': float(np.std(saturation_flat)),
                'vibrance': float(np.percentile(saturation_flat, 75)),
                'muted_level': float(np.percentile(saturation_flat, 25))
            },
            'lightness': {
                'mean': float(np.mean(lightness_flat)),
                'std': float(np.std(lightness_flat)),
                'brightness': float(np.percentile(lightness_flat, 75)),
                'darkness': float(np.percentile(lightness_flat, 25)),
                'contrast': float(np.percentile(lightness_flat, 95) - np.percentile(lightness_flat, 5))
            }
        }
        return analysis

    def create_hsv_visualization(self, component):
        """Создание визуализации HSV компонент"""
        height, width = self.H_array.shape
        vis_array = np.zeros((height, width, 3), dtype=np.uint8)

        if component == 'hue':
            for y in range(height):
                for x in range(width):
                    hue = self.H_array[y, x]
                    rgb = self.hsl_to_rgb(hue, 100, 50)
                    vis_array[y, x] = [rgb[0], rgb[1], rgb[2]]
        elif component == 'saturation':
            sat_normalized = (self.S_array / 100 * 255).astype(np.uint8)
            vis_array = np.stack([sat_normalized, sat_normalized, sat_normalized], axis=2)
        elif component == 'lightness':
            light_normalized = (self.L_array / 100 * 255).astype(np.uint8)
            vis_array = np.stack([light_normalized, light_normalized, light_normalized], axis=2)

        return vis_array

    def hsl_to_rgb(self, h, s, l):
        """Конвертация HSL в RGB"""
        h = h % 360
        s = max(0, min(100, s))
        l = max(0, min(100, l))

        s = s / 100.0
        l = l / 100.0

        if s == 0:
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

    def serialize_regions(self, regions):
        """Сериализация регионов для JSON"""
        serialized = []
        for region in regions:
            serialized_region = region.copy()
            if 'mask' in serialized_region:
                del serialized_region['mask']
            if 'features' in serialized_region:
                del serialized_region['features']
            if 'pixels' in serialized_region:
                del serialized_region['pixels']

            # Заменяем contour_points на contour для совместимости с фронтендом
            if 'contour_points' in serialized_region:
                contour_points = serialized_region['contour_points']
                serialized_contour = []
                for point in contour_points:
                    if len(point) == 2:
                        serialized_contour.append([[float(point[0]), float(point[1])]])
                serialized_region['contour'] = serialized_contour
                del serialized_region['contour_points']

            # Преобразование типов
            for key, value in serialized_region.items():
                if isinstance(value, (np.integer, np.int64)):
                    serialized_region[key] = int(value)
                elif isinstance(value, (np.floating, np.float64)):
                    serialized_region[key] = float(value)
                elif isinstance(value, np.ndarray):
                    serialized_region[key] = value.tolist()

            serialized.append(serialized_region)
        return serialized


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
        """Обучение модели"""
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


# Глобальный экземпляр детектора
detector = ImprovedRegionDetector()


def serialize_thresholds(thresholds):
    """Сериализация thresholds для JSON"""
    serialized = {}
    for key, value in thresholds.items():
        if key == 'main_color':
            serialized[key] = {
                'hue': float(value['hue']),
                'saturation': float(value['saturation']),
                'lightness': float(value['lightness']),
                'proportion': float(value.get('proportion', 1.0))
            }
        else:
            if isinstance(value, (np.integer, np.int64)):
                serialized[key] = int(value)
            elif isinstance(value, (np.floating, np.float64)):
                serialized[key] = float(value)
            else:
                serialized[key] = value
    return serialized


@app.route('/')
def index():
    """Главная страница"""
    return send_file('templates/MainPage.html')


@app.route('/api/upload-image', methods=['POST'])
def upload_image():
    """Загрузка изображения"""
    try:
        if 'file' not in request.files:
            return jsonify({'status': 'error', 'detail': 'Файл не найден'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'status': 'error', 'detail': 'Файл не выбран'}), 400

        contents = file.read()
        height, width = detector.load_image_from_bytes(contents)

        # Загружаем модель если существует
        detector.learning_system.load_model()

        # Конвертируем изображение в base64
        img_base64 = base64.b64encode(contents).decode('utf-8')

        return jsonify({
            "status": "success",
            "message": f"Изображение загружено: {width}x{height} пикселей",
            "image_data": f"data:{file.content_type};base64,{img_base64}",
            "dimensions": {"width": int(width), "height": int(height)}
        })
    except Exception as e:
        return jsonify({'status': 'error', 'detail': f'Ошибка загрузки: {str(e)}'}), 500


@app.route('/api/analyze-selection', methods=['POST'])
def analyze_selection():
    """Анализ выбранной области"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'detail': 'Нет данных'}), 400

        vertices = data.get('vertices', [])
        params = data.get('params', {})

        # ВСЕГДА ИСПОЛЬЗУЕМ ТОЧНЫЙ РЕЖИМ
        params['fast_mode'] = False
        params['multi_scale_analysis'] = True
        params['region_refinement'] = True

        mask = detector.create_selection_mask(vertices, detector.H_array.shape)
        regions, thresholds = detector.find_similar_regions(mask, params)

        return jsonify({
            "status": "success",
            "regions": detector.serialize_regions(regions),
            "thresholds": serialize_thresholds(thresholds),
            "regions_count": len(regions)
        })
    except Exception as e:
        return jsonify({'status': 'error', 'detail': f'Ошибка анализа: {str(e)}'}), 500


@app.route('/api/hsv-analysis', methods=['GET'])
def get_hsv_analysis():
    """Получение HSV анализа"""
    try:
        analysis = detector.get_hsv_analysis()
        return jsonify({
            "status": "success",
            "analysis": analysis
        })
    except Exception as e:
        return jsonify({'status': 'error', 'detail': f'Ошибка анализа: {str(e)}'}), 500


@app.route('/api/hsv-component/<component>', methods=['GET'])
def get_hsv_component(component):
    """Получение визуализации HSV компоненты"""
    try:
        if component not in ['hue', 'saturation', 'lightness']:
            return jsonify({'status': 'error', 'detail': 'Неверная компонента'}), 400

        vis_array = detector.create_hsv_visualization(component)

        # Конвертируем в base64
        pil_img = Image.fromarray(vis_array)
        img_io = io.BytesIO()
        pil_img.save(img_io, 'PNG')
        img_io.seek(0)
        img_base64 = base64.b64encode(img_io.getvalue()).decode('utf-8')

        return jsonify({
            "status": "success",
            "component": component,
            "image_data": f"data:image/png;base64,{img_base64}"
        })
    except Exception as e:
        return jsonify({'status': 'error', 'detail': f'Ошибка визуализации: {str(e)}'}), 500


@app.route('/api/feedback', methods=['POST'])
def add_feedback():
    """Добавление обратной связи"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'detail': 'Нет данных'}), 400

        regions = data.get('regions', [])
        is_positive = data.get('is_positive', True)

        # Добавляем обратную связь в систему обучения
        detector.add_feedback(regions, is_positive)

        # Сохраняем модель после обучения
        detector.learning_system.save_model()

        feedback_type = "положительной" if is_positive else "отрицательной"
        return jsonify({
            "status": "success",
            "message": f"Добавлена {feedback_type} обратная связь для {len(regions)} регионов"
        })
    except Exception as e:
        return jsonify({'status': 'error', 'detail': f'Ошибка обратной связи: {str(e)}'}), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """Проверка здоровья сервера"""
    return jsonify({"status": "healthy", "service": "Image Uniformity Analyzer"})


@app.route('/api/settings', methods=['GET', 'POST'])
def handle_settings():
    """Управление настройками"""
    if request.method == 'GET':
        settings = {}
        for key, value in detector.params.items():
            if isinstance(value, (np.integer, np.int64)):
                settings[key] = int(value)
            elif isinstance(value, (np.floating, np.float64)):
                settings[key] = float(value)
            else:
                settings[key] = value

        return jsonify({
            "status": "success",
            "settings": settings
        })
    else:
        try:
            data = request.get_json()
            detector.params.update(data.get('settings', {}))
            return jsonify({
                "status": "success",
                "message": "Настройки обновлены"
            })
        except Exception as e:
            return jsonify({'status': 'error', 'detail': f'Ошибка обновления настроек: {str(e)}'}), 500


@app.route('/api/model/save', methods=['POST'])
def save_model():
    """Сохранение модели"""
    try:
        if detector.learning_system.save_model():
            return jsonify({
                "status": "success",
                "message": "Модель сохранена"
            })
        else:
            return jsonify({'status': 'error', 'detail': 'Не удалось сохранить модель'}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'detail': f'Ошибка сохранения модели: {str(e)}'}), 500


@app.route('/api/model/load', methods=['POST'])
def load_model():
    """Загрузка модели"""
    try:
        if detector.learning_system.load_model():
            return jsonify({
                "status": "success",
                "message": "Модель загружена"
            })
        else:
            return jsonify({'status': 'error', 'detail': 'Не удалось загрузить модель'}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'detail': f'Ошибка загрузки модели: {str(e)}'}), 500


if __name__ == '__main__':
    os.makedirs('templates', exist_ok=True)
    app.run(host='0.0.0.0', port=8000, debug=True)