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
import hashlib
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, session, Blueprint, \
    current_app
from flask_cors import CORS
from werkzeug.utils import secure_filename
from skimage.morphology import remove_small_objects
import tempfile
import shutil
import psutil
import traceback
from datetime import datetime
import time
from threading import Thread
from collections import deque


# Автоматическое определение базовой директории SAM2
def find_sam2_base():
    """
    Ищет директорию sam2 относительно текущего файла или в стандартных местах
    """
    # Текущая директория файла server.py
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Возможные пути для поиска
    possible_paths = [
        # Относительно текущего файла (server.py находится в uirsmaga)
        os.path.join(os.path.dirname(current_dir), "sam2"),  # Подняться на уровень выше
        os.path.join(current_dir, "sam2"),  # В той же директории
        os.path.join(current_dir, "..", "sam2"),  # На уровень выше
        os.path.join(current_dir, "..", "..", "sam2"),  # На два уровня выше
        os.path.expanduser("~/PycharmProjects/sam2"),  # В домашней директории
        os.path.expanduser("~/sam2"),  # В домашней директории (короткий путь)
        "/app/sam2",  # Для Docker контейнеров
        "/opt/sam2",  # Для серверов
    ]

    # Проверяем каждый путь
    for path in possible_paths:
        normalized_path = os.path.abspath(path)
        # Проверяем наличие ключевых директорий/файлов sam2
        if os.path.exists(normalized_path):
            # Проверяем, что это действительно директория sam2
            if (os.path.exists(os.path.join(normalized_path, "sam2")) or  # Внутри есть папка sam2
                    os.path.exists(os.path.join(normalized_path, "checkpoints")) or  # Или есть папка checkpoints
                    os.path.exists(os.path.join(normalized_path, "sam2", "configs"))):  # Или структура configs
                print(f"[INFO] Found SAM2 base directory: {normalized_path}")
                return normalized_path

    # Если не нашли, возвращаем None и позже вызовем ошибку
    print("[ERROR] Could not find SAM2 base directory automatically")
    return None


# Определяем базовую директорию SAM2
SAM2_BASE = find_sam2_base()

if SAM2_BASE is None:
    # Если не нашли автоматически, пробуем использовать переменную окружения
    SAM2_BASE = os.environ.get('SAM2_BASE')
    if SAM2_BASE and os.path.exists(SAM2_BASE):
        print(f"[INFO] Using SAM2 base from environment variable: {SAM2_BASE}")
    else:
        # Последняя попытка - использовать путь относительно текущего файла
        fallback_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sam2")
        if os.path.exists(fallback_path):
            SAM2_BASE = fallback_path
            print(f"[INFO] Using fallback SAM2 base: {SAM2_BASE}")
        else:
            raise Exception(f"""
            SAM2 base directory not found. 
            Please set SAM2_BASE environment variable or ensure sam2 is in one of these locations:
            {chr(10).join(['- ' + p for p in possible_paths])}
            Current file location: {os.path.abspath(__file__)}
            """)

SAM2_DIR = os.path.join(SAM2_BASE, "sam2")  # Директория с кодом SAM2

# Добавляем путь к папке SAM2 в sys.path
if os.path.exists(SAM2_DIR):
    sys.path.insert(0, SAM2_DIR)
    print(f"[INFO] Added {SAM2_DIR} to sys.path")
else:
    # Если sam2/sam2 не существует, пробуем добавить саму SAM2_BASE
    if os.path.exists(SAM2_BASE):
        sys.path.insert(0, SAM2_BASE)
        print(f"[INFO] Added {SAM2_BASE} to sys.path")
        SAM2_DIR = SAM2_BASE  # Корректируем SAM2_DIR

# Установить переменные окружения ДО импорта SAM2
os.environ['HYDRA_FULL_ERROR'] = '1'


# Используем абсолютные пути для надежности
def find_checkpoint_and_config(sam2_base):
    """
    Ищет файлы checkpoint и config в различных возможных местах
    """
    # Возможные пути для checkpoint
    checkpoint_paths = [
        os.path.join(sam2_base, "checkpoints/sam2.1_hiera_large.pt"),
        os.path.join(sam2_base, "sam2/checkpoints/sam2.1_hiera_large.pt"),
        os.path.join(sam2_base, "models/sam2.1_hiera_large.pt"),
        os.path.join(sam2_base, "weights/sam2.1_hiera_large.pt"),
        os.path.join(sam2_base, "sam2.1_hiera_large.pt"),
    ]

    # Возможные пути для config
    config_paths = [
        os.path.join(sam2_base, "sam2/configs/sam2.1/sam2.1_hiera_l.yaml"),
        os.path.join(sam2_base, "configs/sam2.1/sam2.1_hiera_l.yaml"),
        os.path.join(sam2_base, "sam2/configs/sam2.1_hiera_l.yaml"),
        os.path.join(sam2_base, "configs/sam2.1_hiera_l.yaml"),
    ]

    # Находим существующий checkpoint
    ckpt_path = None
    for path in checkpoint_paths:
        if os.path.exists(path):
            ckpt_path = path
            print(f"[INFO] Found checkpoint at: {ckpt_path}")
            break

    # Находим существующий config
    cfg_path = None
    for path in config_paths:
        if os.path.exists(path):
            cfg_path = path
            print(f"[INFO] Found config at: {cfg_path}")
            break

    return ckpt_path, cfg_path


# Поиск файлов модели
CKPT_PATH, CFG_PATH = find_checkpoint_and_config(SAM2_BASE)

# Проверка существования файлов
print(f"[DEBUG] SAM2_BASE = {SAM2_BASE}")
print(f"[DEBUG] SAM2_DIR = {SAM2_DIR}")
print(f"[DEBUG] Checking checkpoint at: {CKPT_PATH}")
print(f"[DEBUG] Checking config at: {CFG_PATH}")
print(f"[DEBUG] Checkpoint exists: {os.path.exists(CKPT_PATH) if CKPT_PATH else False}")
print(f"[DEBUG] Config exists: {os.path.exists(CFG_PATH) if CFG_PATH else False}")

if not CKPT_PATH or not os.path.exists(CKPT_PATH):
    raise FileNotFoundError(f"Could not find SAM2 checkpoint file in {SAM2_BASE}")

if not CFG_PATH or not os.path.exists(CFG_PATH):
    raise FileNotFoundError(f"Could not find SAM2 config file in {SAM2_BASE}")

MASK_THRESHOLD = 0.2
SCORE_THRESHOLD = 0.32
MIN_AREA = 10
USE_SAM_REFINEMENT = True

# Импортируем функции для работы с БД
import database
from database import get_db_connection

# Импортируем маршруты из routes.py
from routes import pages_bp

# Проверяем и создаем папку для загрузок
UPLOAD_FOLDER = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.secret_key = 'p98rnv4@sd!#Kf'  # Секретный ключ
CORS(app, supports_credentials=True)

# Конфигурация
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['TEMP_FOLDER'] = tempfile.mkdtemp()
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200MB
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# Инициализация модели (один раз при запуске)
device = "cuda" if torch.cuda.is_available() else "cpu"
sam2 = None
predictor = None

# Импорт SAM2 модулей (после установки путей)
try:
    from sam2.build_sam import build_sam2
    from sam2.sam2_image_predictor import SAM2ImagePredictor
except ImportError as e:
    print(f"[ERROR] Failed to import SAM2 modules: {e}")
    print(f"[ERROR] sys.path: {sys.path}")
    # Пробуем альтернативный импорт
    try:
        import sam2
        from sam2.build_sam import build_sam2
        from sam2.sam2_image_predictor import SAM2ImagePredictor

        print("[INFO] Successfully imported SAM2 modules (alternative method)")
    except ImportError as e2:
        print(f"[ERROR] Alternative import also failed: {e2}")
        raise


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
            config_dir = os.path.dirname(CFG_PATH)
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

            # Получаем имя конфиг файла относительно config_dir
            config_file = os.path.basename(CFG_PATH)

            # Теперь вызываем build_sam2
            sam2 = build_sam2(
                config_file=config_file,
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


def refresh_user_session(user_id=None):
    """Обновляет данные пользователя в сессии из БД"""
    if user_id is None:
        user_id = session.get('user', {}).get('id')

    if not user_id:
        return False

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            user_data = cursor.fetchone()
            if user_data:
                session['user'] = dict(user_data)
                session.modified = True
                return True
    except Exception as e:
        print(f"Ошибка при обновлении сессии: {e}")
    finally:
        conn.close()
    return False


def split_full_name(full_name):
    """Разделяет полное имя на фамилию, имя и отчество"""
    parts = full_name.strip().split()
    if len(parts) >= 3:
        return parts[0], parts[1], parts[2]
    elif len(parts) == 2:
        return parts[0], parts[1], ''
    else:
        return parts[0] if parts else '', '', ''


# ==================== СОЗДАНИЕ БЛЮПРИНТОВ ====================

# Создаем Blueprint для API
api_bp = Blueprint('api', __name__)

@api_bp.route('/add_user', methods=['POST'])
def add_user():
    return database.add_user()

@api_bp.route('/get_users', methods=['GET'])
def get_users():
    return database.get_users()

@api_bp.route('/get_user_actions', methods=['GET'])
def get_user_actions():
    return database.get_user_actions()


# Создаем Blueprint для аутентификации
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login_user')
def login_page():
    # Если пользователь уже авторизован, перенаправляем на главную
    if 'user' in session:
        return redirect(url_for('pages.sam2_design'))
    return render_template('login.html')


@auth_bp.route('/login', methods=['POST'])
def login():
    success, message, user = database.login()
    if success:
        session['user'] = user
        print("Логин успешен, сессия установлена для", user)

        # Проверяем, является ли пользователь администратором
        if user.get('access_rights') == 'admin':
            return redirect(url_for('pages.administration'))
        else:
            return redirect(url_for('pages.sam2_design'))
    else:
        print("Ошибка входа:", message)
        return render_template('login.html', error=message)


@auth_bp.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('pages.sam2_design'))


# ==================== РЕГИСТРАЦИЯ БЛЮПРИНТОВ ====================
# Важно: сначала регистрируем auth_bp для правильной обработки авторизации
app.register_blueprint(auth_bp)
app.register_blueprint(api_bp)
app.register_blueprint(pages_bp)  # pages_bp регистрируем последним


# ==================== МАРШРУТЫ ДЛЯ РАБОТЫ С SAM2 ====================
@app.route('/sam2')
def sam2_index():
    """Главная страница SAM2"""
    if 'user' not in session:
        return redirect(url_for('auth.login_page'))
    return render_template('sam2_index.html', user=session['user'])


@app.route('/sam2/upload', methods=['POST'])
def sam2_upload_file():
    """Загрузка ZIP-архива с изображениями для SAM2"""
    if 'user' not in session:
        return jsonify({'error': 'Authentication required'}), 401

    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if not file.filename.lower().endswith('.zip'):
        return jsonify({'error': 'File must be a ZIP archive'}), 400

    try:
        # Сохраняем временный файл
        temp_dir = tempfile.mkdtemp(dir=app.config['TEMP_FOLDER'])
        zip_path = os.path.join(temp_dir, secure_filename(file.filename))
        file.save(zip_path)

        # Загружаем изображения
        images = load_images_from_zip(zip_path)

        if len(images) == 0:
            shutil.rmtree(temp_dir)
            return jsonify({'error': 'No valid images found in ZIP'}), 400

        # Конвертируем все изображения в base64 для отправки на фронтенд
        images_base64 = {}
        for key, img_array in images.items():
            images_base64[key] = numpy_to_base64(img_array)

        # Сохраняем numpy массивы во временный файл
        npz_path = os.path.join(temp_dir, 'images.npz')
        np.savez_compressed(npz_path, **{k: v for k, v in images.items()})

        session_id = os.path.basename(temp_dir)

        print(f"[INFO] ZIP uploaded: {len(images)} images, session_id: {session_id}")
        print(f"[INFO] Image keys: {list(images.keys())}")

        return jsonify({
            'success': True,
            'session_id': session_id,
            'image_keys': list(images.keys()),
            'images': images_base64
        })

    except Exception as e:
        print(f"[ERROR] ZIP upload error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/sam2/set_points', methods=['POST'])
def sam2_set_points():
    """Обработка точек для создания маски"""
    try:
        data = request.json
        points = data.get('points', [])
        labels = data.get('labels', [])
        session_id = data.get('session_id')

        if not session_id:
            return jsonify({'error': 'No session ID'}), 400

        temp_dir = os.path.join(app.config['TEMP_FOLDER'], session_id)
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

            # Сохраняем маску как изображение для визуализации
            viz_path = os.path.join(temp_dir, 'ref_viz.png')
            viz_img = Image.fromarray(visualization)
            viz_img.save(viz_path)

            # Создаем словарь с результатами для всех изображений (пока только референсное)
            all_masks = {ref_key: mask}
            masks_path = os.path.join(temp_dir, 'all_masks.npz')
            np.savez_compressed(masks_path, **all_masks)

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
        print(f"[ERROR] set_points failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/sam2/propagate', methods=['POST'])
def sam2_propagate_mask():
    """Распространение маски на все изображения"""
    try:
        data = request.json
        session_id = data.get('session_id')

        if not session_id:
            return jsonify({'error': 'No session ID'}), 400

        temp_dir = os.path.join(app.config['TEMP_FOLDER'], session_id)
        npz_path = os.path.join(temp_dir, 'images.npz')
        mask_path = os.path.join(temp_dir, 'ref_mask.npy')

        if not os.path.exists(npz_path):
            return jsonify({'error': 'Session expired'}), 400

        if not os.path.exists(mask_path):
            return jsonify({'error': 'No mask created yet'}), 400

        # Загружаем изображения и маску
        with np.load(npz_path, allow_pickle=True) as data_np:
            images = {k: data_np[k] for k in data_np.files}

        ref_mask = np.load(mask_path)
        ref_key = list(images.keys())[0]
        ref_img = images[ref_key]

        # Инициализируем SAM2 если еще не инициализирован
        init_sam()

        results = {}
        visualizations = {}

        # Проходим по всем изображениям
        for i, (key, img) in enumerate(images.items()):
            if i == 0:
                # Референсное изображение - используем уже созданную маску
                results[key] = ref_mask

                # Создаем визуализацию
                viz = img.copy()
                viz[ref_mask] = [255, 0, 0]
                visualizations[key] = numpy_to_base64(viz)
                continue

            # Оцениваем гомографию
            H = estimate_homography(ref_img, img)

            if H is None:
                print(f"[WARN] Cannot match {key}")
                # Используем пустую маску для нераспознанных изображений
                results[key] = np.zeros(img.shape[:2], dtype=bool)
                viz = img.copy()
                visualizations[key] = numpy_to_base64(viz)
                continue

            # Трансформируем маску
            warped = warp_mask(ref_mask, H, img.shape)

            # Опциональное уточнение через SAM
            if USE_SAM_REFINEMENT and warped.sum() > 50:
                try:
                    ys, xs = np.where(warped)
                    cx, cy = xs.mean(), ys.mean()

                    predictor.set_image(img)
                    masks, scores, _ = predictor.predict(
                        point_coords=np.array([[cx, cy]]),
                        point_labels=np.array([1]),
                        multimask_output=False
                    )

                    warped = masks[0] > MASK_THRESHOLD
                except Exception as e:
                    print(f"[WARN] SAM refinement failed for {key}: {e}")

            results[key] = warped

            # Создаем визуализацию
            viz = img.copy()
            viz[warped] = [255, 0, 0]
            visualizations[key] = numpy_to_base64(viz)

        # Сохраняем все маски
        masks_path = os.path.join(temp_dir, 'all_masks.npz')
        np.savez_compressed(masks_path, **results)

        # Сохраняем визуализации для быстрого доступа
        viz_dir = os.path.join(temp_dir, 'visualizations')
        os.makedirs(viz_dir, exist_ok=True)

        for key, viz_data in visualizations.items():
            # Извлекаем base64 данные
            if viz_data.startswith('data:image/png;base64,'):
                base64_data = viz_data.split(',')[1]
                img_data = base64.b64decode(base64_data)

                # Создаем безопасное имя файла
                safe_name = sanitize_filename(key)
                viz_path = os.path.join(viz_dir, f"{safe_name}.png")

                with open(viz_path, 'wb') as f:
                    f.write(img_data)

        # Если пользователь авторизован, сохраняем результаты в БД
        if 'user' in session:
            try:
                conn = get_db_connection()
                with conn.cursor() as cursor:
                    for key, mask in results.items():
                        # Конвертируем маску в изображение для сохранения
                        mask_img = (mask * 255).astype(np.uint8)
                        img_pil = Image.fromarray(mask_img)

                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        safe_key = sanitize_filename(key)
                        filename = f"mask_{session['user']['id']}_{timestamp}_{safe_key}.png"
                        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

                        # Сохраняем файл
                        img_pil.save(filepath)

                        # Сохраняем запись в БД
                        cursor.execute("""
                            INSERT INTO user_images (user_id, filename, upload_date)
                            VALUES (%s, %s, NOW())
                        """, (session['user']['id'], filename))

                    conn.commit()
                    print(f"[INFO] Saved {len(results)} images to database for user {session['user']['id']}")
            except Exception as e:
                print(f"[ERROR] Failed to save images to DB: {e}")
            finally:
                if conn:
                    conn.close()

        return jsonify({
            'success': True,
            'visualizations': visualizations,
            'processed_count': len(results)
        })

    except Exception as e:
        print(f"[ERROR] propagate failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/sam2/download', methods=['GET'])
def sam2_download_results():
    """Скачивание результатов"""
    try:
        session_id = request.args.get('session_id')
        if not session_id:
            return jsonify({'error': 'No session ID'}), 400

        temp_dir = os.path.join(app.config['TEMP_FOLDER'], session_id)

        # Проверяем наличие визуализаций
        viz_dir = os.path.join(temp_dir, 'visualizations')

        # Если есть папка с визуализациями, используем её
        if os.path.exists(viz_dir) and os.listdir(viz_dir):
            memory_file = io.BytesIO()

            with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for filename in os.listdir(viz_dir):
                    if filename.lower().endswith('.png'):
                        file_path = os.path.join(viz_dir, filename)
                        zipf.write(file_path, filename)

            memory_file.seek(0)

            date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            zip_filename = f"masks_{date_str}.zip"

            return send_file(
                memory_file,
                mimetype='application/zip',
                as_attachment=True,
                download_name=zip_filename
            )

        # Если нет визуализаций, пробуем использовать all_masks.npz
        masks_path = os.path.join(temp_dir, 'all_masks.npz')

        if not os.path.exists(masks_path):
            return jsonify({'error': 'No results available'}), 400

        # Создаем ZIP архив в памяти
        memory_file = io.BytesIO()

        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            with np.load(masks_path, allow_pickle=True) as data:
                for key in data.files:
                    mask = data[key]
                    # Конвертируем маску в изображение
                    mask_img = (mask * 255).astype(np.uint8)
                    img_pil = Image.fromarray(mask_img)

                    # Сохраняем во временный байтовый поток
                    img_buffer = io.BytesIO()
                    img_pil.save(img_buffer, format='PNG')

                    # Создаем безопасное имя файла
                    safe_name = sanitize_filename(key)
                    filename = f"mask_{safe_name}.png"

                    # Добавляем в ZIP
                    zipf.writestr(filename, img_buffer.getvalue())

        memory_file.seek(0)

        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"masks_{date_str}.zip"

        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=zip_filename
        )

    except Exception as e:
        print(f"[ERROR] Download failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


def sanitize_filename(filename):
    """Очищает имя файла от проблемных символов"""
    if not filename:
        return "unknown"

    # Убираем путь к директории
    basename = os.path.basename(filename)

    # Убираем расширение, если оно есть
    name_without_ext = os.path.splitext(basename)[0]

    # Пробуем декодировать, если это байты
    if isinstance(name_without_ext, bytes):
        try:
            name_without_ext = name_without_ext.decode('utf-8')
        except:
            name_without_ext = name_without_ext.decode('latin-1', errors='ignore')

    # Заменяем проблемные символы на подчеркивание
    safe_chars = []
    for c in name_without_ext:
        if c.isalnum() or c in ' ._-':
            safe_chars.append(c)
        else:
            safe_chars.append('_')

    safe_name = ''.join(safe_chars)

    # Убираем множественные подчеркивания
    while '__' in safe_name:
        safe_name = safe_name.replace('__', '_')

    # Убираем пробелы в начале и конце
    safe_name = safe_name.strip()

    # Если имя пустое, генерируем новое
    if not safe_name or safe_name.isspace():
        import hashlib
        import time
        hash_obj = hashlib.md5(str(time.time()).encode())
        safe_name = f"mask_{hash_obj.hexdigest()[:8]}"

    return safe_name
@app.route('/sam2/cleanup', methods=['POST'])
def sam2_cleanup():
    """Очистка временных файлов"""
    try:
        session_id = request.json.get('session_id')
        if session_id:
            temp_dir = os.path.join(app.config['TEMP_FOLDER'], session_id)
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== МАРШРУТЫ ДЛЯ ЗАГРУЗКИ ОДИНОЧНЫХ ИЗОБРАЖЕНИЙ ====================
@app.route('/upload_single', methods=['POST'])
def upload_single():
    """Загрузка одиночного изображения для предпросмотра"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400

        # Проверка формата файла
        allowed_extensions = {'png', 'jpg', 'jpeg', 'bmp', 'tiff'}
        if not '.' in file.filename or file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
            return jsonify({'error': 'Invalid file format'}), 400

        # Читаем изображение
        img_bytes = file.read()
        img = Image.open(io.BytesIO(img_bytes))
        img = img.convert('RGB')
        img_array = np.array(img)

        # Конвертируем в base64 для отправки на фронтенд
        img_base64 = numpy_to_base64(img_array)

        # Создаем временную сессию для предпросмотра
        temp_dir = tempfile.mkdtemp(dir=app.config['TEMP_FOLDER'])
        session_id = os.path.basename(temp_dir)  # Убрали префикс "preview_"

        # Сохраняем изображение для возможной дальнейшей работы
        npz_path = os.path.join(temp_dir, 'images.npz')
        np.savez_compressed(npz_path, **{file.filename: img_array})

        return jsonify({
            'success': True,
            'image_data': img_base64,
            'filename': file.filename,
            'session_id': session_id
        })

    except Exception as e:
        print(f"Error in upload_single: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/upload_single_to_session', methods=['POST'])
def upload_single_to_session():
    """Создание полноценной сессии из предпросмотра"""
    try:
        # Создаем новую временную директорию
        temp_dir = tempfile.mkdtemp(dir=app.config['TEMP_FOLDER'])
        session_id = os.path.basename(temp_dir)

        # Здесь нужно перенести данные из предпросмотра в новую сессию
        # Это зависит от того, как вы храните данные предпросмотра

        return jsonify({
            'success': True,
            'session_id': session_id
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/upload', methods=['POST'])
def upload_zip():
    """Загрузка ZIP-архива (алиас для sam2_upload_file)"""
    return sam2_upload_file()


@app.route('/set_points', methods=['POST'])
def set_points():
    """Алиас для sam2_set_points"""
    return sam2_set_points()


@app.route('/propagate', methods=['POST'])
def propagate():
    """Алиас для sam2_propagate_mask"""
    return sam2_propagate_mask()


@app.route('/download', methods=['GET'])
def download():
    """Алиас для sam2_download_results"""
    return sam2_download_results()

# ==================== API МАРШРУТЫ ДЛЯ РАБОТЫ С ИЗОБРАЖЕНИЯМИ ====================



@app.route('/api/images/user', methods=['GET'])
def get_user_images():
    """Получение списка изображений пользователя"""
    if 'user' not in session:
        return jsonify([])

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, filename, upload_date
                FROM user_images
                WHERE user_id = %s
                ORDER BY upload_date DESC
            """, (session['user']['id'],))

            images = cursor.fetchall()
            for img in images:
                img['upload_date'] = img['upload_date'].strftime('%d.%m.%Y %H:%M')
                img['url'] = f"/static/uploads/{img['filename']}"

            return jsonify(images)

    except Exception as e:
        return jsonify([])
    finally:
        if conn:
            conn.close()


# ==================== ВСПОМОГАТЕЛЬНЫЕ МАРШРУТЫ ====================
@app.route('/health', methods=['GET'])
def health_check():
    """Проверка работоспособности сервера"""
    return jsonify({
        'status': 'healthy',
        'sam2_initialized': sam2 is not None,
        'authenticated': 'user' in session
    })


@app.route('/debug/session', methods=['GET'])
def debug_session():
    """Отладка сессии (только для разработки)"""
    print("Текущая сессия:", session)
    print("Пользователь в сессии:", session.get('user'), flush=True)
    return jsonify({
        'session': dict(session),
        'user': session.get('user')
    })

@app.route('/api/images/save_uploaded', methods=['POST'])
def save_uploaded_image():
    """Сохраняет загруженное изображение в БД"""
    if 'user' not in session:
        return jsonify({"success": False, "message": "Необходима авторизация"}), 401

    if 'file' not in request.files:
        return jsonify({"success": False, "message": "Файл не предоставлен"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "message": "Файл не выбран"}), 400

    try:
        # Создаем уникальное имя файла
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = secure_filename(file.filename)
        filename = f"upload_{session['user']['id']}_{timestamp}_{safe_filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        # Сохраняем файл
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        file.save(filepath)

        # Сохраняем запись в БД
        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO user_images (user_id, filename, upload_date)
                    VALUES (%s, %s, NOW())
                """, (session['user']['id'], filename))
                conn.commit()
        finally:
            if conn:
                conn.close()

        return jsonify({
            "success": True,
            "message": "Изображение успешно сохранено",
            "filename": filename
        })

    except Exception as e:
        print(f"Ошибка при сохранении изображения: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Ошибка сервера: {str(e)}"
        }), 500
if __name__ == '__main__':
    # Инициализируем SAM2 при запуске
    try:
        init_sam()
        print("[INFO] SAM2 initialized successfully")
    except Exception as e:
        print(f"[WARNING] SAM2 initialization failed: {e}")
        print("[WARNING] Application will run but mask creation will fail")

    # Создаем необходимые директории
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['TEMP_FOLDER'], exist_ok=True)

    app.run(debug=True, host='0.0.0.0', port=5001)