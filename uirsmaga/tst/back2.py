import os
import sys
import zipfile
import io
import cv2
import torch
import numpy as np
from PIL import Image
import base64
import json
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
from skimage.morphology import remove_small_objects
import tempfile
import shutil

# Определяем базовую директорию SAM2
SAM2_BASE = "/Users/user/PycharmProjects/PycharmProjects/sam2"
SAM2_DIR = os.path.join(SAM2_BASE, "sam2")  # Директория с кодом SAM2

# Добавляем путь к папке SAM2 в sys.path
sys.path.insert(0, SAM2_DIR)

# Установить переменные окружения ДО импорта SAM2
os.environ['HYDRA_FULL_ERROR'] = '1'

# Используем абсолютные пути для надежности
CKPT_PATH = os.path.join(SAM2_BASE, "checkpoints/sam2_1_hiera_tiny.pt")
CFG_PATH = os.path.join(SAM2_BASE, "sam2/configs/sam2.1/sam2.1_hiera_t.yaml")

# Проверка существования файлов
print(f"[DEBUG] Checking checkpoint at: {CKPT_PATH}")
print(f"[DEBUG] Checking config at: {CFG_PATH}")
print(f"[DEBUG] Checkpoint exists: {os.path.exists(CKPT_PATH)}")
print(f"[DEBUG] Config exists: {os.path.exists(CFG_PATH)}")

MASK_THRESHOLD = 0.5
SCORE_THRESHOLD = 0.9
MIN_AREA = 100
USE_SAM_REFINEMENT = True

# Инициализация модели (один раз при запуске)
device = "cuda" if torch.cuda.is_available() else "cpu"
sam2 = None
predictor = None

# Импорт SAM2 модулей (после установки путей)
from sam2.build_sam import build_sam2
from sam2.sam2_image_predictor import SAM2ImagePredictor

app = Flask(__name__)
CORS(app)
app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200MB


def init_sam():
    """Инициализация модели SAM2"""
    global sam2, predictor

    if sam2 is None:
        try:
            print(f"[INFO] Initializing SAM2 on {device}...")
            print(f"[INFO] Checkpoint path: {CKPT_PATH}")
            print(f"[INFO] Config path: {CFG_PATH}")

            # Проверяем наличие checkpoint файла
            if not os.path.exists(CKPT_PATH):
                print(f"[ERROR] Checkpoint not found: {CKPT_PATH}")
                raise FileNotFoundError(f"Checkpoint not found at {CKPT_PATH}")

            # Проверяем наличие config файла
            if not os.path.exists(CFG_PATH):
                print(f"[ERROR] Config not found: {CFG_PATH}")
                raise FileNotFoundError(f"Config not found at {CFG_PATH}")

            # Инициализируем Hydra вручную перед вызовом build_sam2
            import hydra
            from hydra.core.global_hydra import GlobalHydra

            # Очищаем GlobalHydra если уже инициализирована
            if GlobalHydra.instance().is_initialized():
                GlobalHydra.instance().clear()

            # Инициализируем Hydra с правильным config_path
            config_dir = os.path.join(SAM2_BASE, "sam2/configs")
            print(f"[INFO] Initializing Hydra with config_dir: {config_dir}")

            # Проверяем существование config директории
            if not os.path.exists(config_dir):
                print(f"[ERROR] Config directory not found: {config_dir}")
                raise FileNotFoundError(f"Config directory not found: {config_dir}")

            # Инициализируем Hydra
            hydra.initialize_config_dir(
                version_base="1.3",
                config_dir=config_dir,
                job_name="sam2_init"
            )

            # Теперь вызываем build_sam2
            sam2 = build_sam2(
                config_file="sam2.1/sam2.1_hiera_t.yaml",
                ckpt_path=CKPT_PATH,
                device=device,
                mode="eval"
            )

            sam2.eval()
            predictor = SAM2ImagePredictor(sam2)
            print(f"[SUCCESS] SAM2 initialized via Hydra on {device}")

        except Exception as e:
            print(f"[ERROR] Failed to initialize SAM2: {e}")
            print("[ERROR] Traceback:", file=sys.stderr)
            import traceback
            traceback.print_exc()
            raise



def load_images_from_zip(zip_path):
    """Загрузка изображений из ZIP-архива"""
    images = {}
    with zipfile.ZipFile(zip_path, 'r') as z:
        for name in z.namelist():
            # Пропускаем системные файлы
            if name.startswith("__MACOSX") or name.startswith("._"):
                continue

            if name.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff')):
                try:
                    data = z.read(name)
                    img = Image.open(io.BytesIO(data))
                    img = img.convert("RGB")
                    images[name] = np.array(img)
                except Exception as e:
                    print(f"[WARN] Skipping {name}: {e}")
    return images


def estimate_homography(img1, img2):
    """Оценка гомографии между двумя изображениями"""
    g1 = cv2.cvtColor(img1, cv2.COLOR_RGB2GRAY)
    g2 = cv2.cvtColor(img2, cv2.COLOR_RGB2GRAY)

    sift = cv2.SIFT_create(4000)
    kp1, d1 = sift.detectAndCompute(g1, None)
    kp2, d2 = sift.detectAndCompute(g2, None)

    if d1 is None or d2 is None:
        return None

    matches = cv2.BFMatcher().knnMatch(d1, d2, k=2)
    good = [m for m, n in matches if m.distance < 0.75 * n.distance]

    if len(good) < 10:
        return None

    src = np.float32([kp1[m.queryIdx].pt for m in good])
    dst = np.float32([kp2[m.trainIdx].pt for m in good])

    H, _ = cv2.findHomography(src, dst, cv2.RANSAC, 5.0)
    return H


def warp_mask(mask, H, shape):
    """Трансформация маски с помощью гомографии"""
    h, w = shape[:2]
    warped = cv2.warpPerspective(
        (mask.astype(np.uint8) * 255), H, (w, h)
    )
    return warped > 127


def numpy_to_base64(image_array):
    """Конвертация numpy массива в base64 строку"""
    img_pil = Image.fromarray(image_array.astype('uint8'))
    buffer = io.BytesIO()
    img_pil.save(buffer, format='PNG')
    img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return f"data:image/png;base64,{img_str}"


@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    """Загрузка ZIP-архива с изображениями"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if not file.filename.lower().endswith('.zip'):
        return jsonify({'error': 'File must be a ZIP archive'}), 400

    try:
        # Сохраняем временный файл
        temp_dir = tempfile.mkdtemp(dir=app.config['UPLOAD_FOLDER'])
        zip_path = os.path.join(temp_dir, secure_filename(file.filename))
        file.save(zip_path)

        # Загружаем изображения
        images = load_images_from_zip(zip_path)

        if len(images) == 0:
            shutil.rmtree(temp_dir)
            return jsonify({'error': 'No valid images found in ZIP'}), 400

        # Возвращаем информацию о первом изображении (референсном)
        first_key = list(images.keys())[0]
        first_image = images[first_key]

        # Конвертируем в base64 для отображения
        image_data = numpy_to_base64(first_image)

        # Сохраняем данные в сессии (в реальном приложении используйте Redis или БД)
        session_data = {
            'temp_dir': temp_dir,
            'zip_path': zip_path,
            'images': {k: numpy_to_base64(v) for k, v in images.items()},
            'image_keys': list(images.keys()),
            'ref_image': image_data,
            'ref_key': first_key
        }

        # Сохраняем numpy массивы во временный файл
        npz_path = os.path.join(temp_dir, 'images.npz')
        np.savez_compressed(npz_path, **{k: v for k, v in images.items()})

        return jsonify({
            'success': True,
            'image_count': len(images),
            'ref_image': image_data,
            'ref_key': first_key,
            'image_keys': list(images.keys()),
            'session_id': os.path.basename(temp_dir)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/set_points', methods=['POST'])
def set_points():
    """Обработка точек для создания маски"""
    try:
        data = request.json
        points = data.get('points', [])
        labels = data.get('labels', [])
        session_id = data.get('session_id')

        if not session_id:
            return jsonify({'error': 'No session ID'}), 400

        temp_dir = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
        npz_path = os.path.join(temp_dir, 'images.npz')

        if not os.path.exists(npz_path):
            return jsonify({'error': 'Session expired or invalid'}), 400

        # Загружаем изображения
        with np.load(npz_path, allow_pickle=True) as data_np:
            images = {k: data_np[k] for k in data_np.files}

        # Инициализируем SAM2 если еще не инициализирован
        init_sam()

        # Берем референсное изображение
        ref_key = list(images.keys())[0]
        ref_img = images[ref_key]

        # Устанавливаем изображение для предсказателя
        predictor.set_image(ref_img)

        # Создаем маску на основе точек
        if len(points) > 0:
            masks, scores, _ = predictor.predict(
                point_coords=np.array(points),
                point_labels=np.array(labels),
                multimask_output=True
            )

            valid = [i for i, s in enumerate(scores) if s >= SCORE_THRESHOLD]
            if not valid:
                valid = [int(np.argmax(scores))]

            best = valid[np.argmax([scores[i] for i in valid])]
            mask = masks[best] > MASK_THRESHOLD
            mask = remove_small_objects(mask, MIN_AREA)

            # Создаем визуализацию маски
            visualization = ref_img.copy()
            visualization[mask] = [255, 0, 0]  # Красный цвет для маски

            # Сохраняем маску для дальнейшего использования
            mask_path = os.path.join(temp_dir, 'ref_mask.npy')
            np.save(mask_path, mask)

            # Конвертируем в base64
            mask_data = numpy_to_base64(visualization)

            return jsonify({
                'success': True,
                'mask_image': mask_data,
                'mask_available': True
            })
        else:
            return jsonify({'error': 'No points provided'}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/propagate', methods=['POST'])
def propagate_mask():
    """Распространение маски на все изображения"""
    try:
        data = request.json
        session_id = data.get('session_id')

        if not session_id:
            return jsonify({'error': 'No session ID'}), 400

        temp_dir = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
        npz_path = os.path.join(temp_dir, 'images.npz')
        mask_path = os.path.join(temp_dir, 'ref_mask.npy')

        if not os.path.exists(npz_path) or not os.path.exists(mask_path):
            return jsonify({'error': 'Session expired or no mask created'}), 400

        # Загружаем изображения и маску
        with np.load(npz_path, allow_pickle=True) as data_np:
            images = {k: data_np[k] for k in data_np.files}

        ref_mask = np.load(mask_path)
        ref_key = list(images.keys())[0]
        ref_img = images[ref_key]

        # Инициализируем SAM2 если еще не инициализирован
        init_sam()

        results = {}

        # Проходим по всем изображениям
        for i, (key, img) in enumerate(images.items()):
            if i == 0:
                # Референсное изображение - используем уже созданную маску
                results[key] = ref_mask
                continue

            # Оцениваем гомографию
            H = estimate_homography(ref_img, img)

            if H is None:
                print(f"[WARN] Cannot match {key}")
                continue

            # Трансформируем маску
            warped = warp_mask(ref_mask, H, img.shape)

            # Опциональное уточнение через SAM
            if USE_SAM_REFINEMENT and warped.sum() > 50:
                ys, xs = np.where(warped)
                cx, cy = xs.mean(), ys.mean()

                predictor.set_image(img)
                masks, scores, _ = predictor.predict(
                    point_coords=np.array([[cx, cy]]),
                    point_labels=np.array([1]),
                    multimask_output=False
                )

                warped = masks[0] > MASK_THRESHOLD

            results[key] = warped

        # Создаем визуализации для всех изображений
        visualizations = {}
        for key, mask in results.items():
            img = images[key].copy()
            img[mask] = [255, 0, 0]  # Красный цвет для маски
            visualizations[key] = numpy_to_base64(img)

        # Сохраняем все маски
        masks_path = os.path.join(temp_dir, 'all_masks.npz')
        np.savez_compressed(masks_path, **results)

        return jsonify({
            'success': True,
            'visualizations': visualizations,
            'processed_count': len(results)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/download', methods=['GET'])
def download_results():
    """Скачивание результатов"""
    try:
        session_id = request.args.get('session_id')
        if not session_id:
            return jsonify({'error': 'No session ID'}), 400

        temp_dir = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
        masks_path = os.path.join(temp_dir, 'all_masks.npz')

        if not os.path.exists(masks_path):
            return jsonify({'error': 'No results available'}), 400

        # Создаем ZIP архив с масками
        output_zip = os.path.join(temp_dir, 'masks.zip')

        with zipfile.ZipFile(output_zip, 'w') as zipf:
            with np.load(masks_path, allow_pickle=True) as data:
                for key in data.files:
                    mask = data[key]
                    # Конвертируем маску в изображение
                    mask_img = (mask * 255).astype(np.uint8)
                    img_pil = Image.fromarray(mask_img)

                    # Сохраняем во временный файл
                    mask_filename = f"mask_{os.path.splitext(key)[0]}.png"
                    temp_mask_path = os.path.join(temp_dir, mask_filename)
                    img_pil.save(temp_mask_path)

                    # Добавляем в ZIP
                    zipf.write(temp_mask_path, mask_filename)

        return send_file(output_zip,
                         as_attachment=True,
                         download_name='masks.zip',
                         mimetype='application/zip')

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/cleanup', methods=['POST'])
def cleanup():
    """Очистка временных файлов"""
    try:
        session_id = request.json.get('session_id')
        if session_id:
            temp_dir = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Инициализируем SAM2 при запуске
    try:
        init_sam()
        print("[INFO] SAM2 initialized successfully")
    except Exception as e:
        print(f"[WARNING] SAM2 initialization failed: {e}")
        print("[WARNING] Application will run but mask creation will fail")

    app.run(debug=True, host='0.0.0.0', port=5001)