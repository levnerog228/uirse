
    // Глобальные переменные
    let allUploadedImages = []; // Массив для хранения всех загруженных изображений
    let currentSessionId = null;
    let images = {};
    let currentImageIndex = 0;
    let points = [];
    let pointType = 'positive'; // 'positive' или 'negative'
    let canvas = null;
    let ctx = null;
    let currentImage = null;
    let zoom = 1;
    let offsetX = 0;
    let offsetY = 0;
    let isDragging = false;
    let dragStartX = 0;
    let dragStartY = 0;
    let dragOffsetX = 0;
    let dragOffsetY = 0;
    let currentMask = false;
    let currentUploadType = 'single'; // 'single' или 'zip'
    // Глобальные переменные для GSD
    let defaultGSDSettings = {
    height: 100,
    sensorPixel: 0.0024,
    focal: 8,
    unit: 'm2'
};


    let currentMaskAreaGSD = 0; // Площадь в реальных единицах (м²/га/км²)
    let currentGSDUnit = 'm2';

    // Переменные для хранения текущей маски и её площади
    let currentMaskImageData = null;
    let currentMaskArea = 0;

    // Хранилище уже загруженных изображений для предотвращения дублирования
    let loadedImageNames = new Set();

    // Хранилище масок для изображений
    window.masks = {};

    // Хранилище для нескольких масок на одном изображении
    window.multiMasks = {};

    // Кэш загруженных изображений масок для производительности
    window.maskImageCache = {};

    // Текущая временная маска для отображения
    window.currentTempMask = null;

    // Флаг для отслеживания процесса отрисовки
    let isRendering = false;

    // Цвета для разных масок (без прозрачности в основном цвете)
    const maskColors = [
        'rgba(58, 134, 255, 0.6)',   // синий
        'rgba(255, 99, 132, 0.6)',   // розовый
        'rgba(75, 192, 192, 0.6)',   // бирюзовый
        'rgba(255, 205, 86, 0.6)',   // желтый
        'rgba(153, 102, 255, 0.6)',  // фиолетовый
        'rgba(255, 159, 64, 0.6)',   // оранжевый
        'rgba(46, 204, 113, 0.6)',   // зеленый
        'rgba(231, 76, 60, 0.6)',    // красный
        'rgba(52, 152, 219, 0.6)',   // голубой
        'rgba(155, 89, 182, 0.6)',   // пурпурный
        'rgba(26, 188, 156, 0.6)',   // бирюзовый
        'rgba(241, 196, 15, 0.6)',   // желтый
        'rgba(230, 126, 34, 0.6)',   // оранжевый
        'rgba(231, 76, 60, 0.6)',    // красный
        'rgba(149, 165, 166, 0.6)',  // серый
        'rgba(52, 73, 94, 0.6)'      // темно-синий
    ];

    // Toast уведомления
    let loadingToast = null;

    // Переменные для модального окна просмотра изображений
    let currentModalImages = [];
    let currentModalIndex = 0;

    // Инициализация
    document.addEventListener('DOMContentLoaded', () => {
        canvas = document.getElementById('main-canvas');
        ctx = canvas.getContext('2d');

        // Загружаем историю с сервера (если пользователь авторизован)
        //const isGuest = {{ is_guest|tojson }};
        if (!isGuest) {
            loadUserHistory();
        } else {
            // Для гостей показываем пустую историю с сообщением
            renderHistoryFromServer([]);
        }

        // Настройка обработчиков событий
        setupEventListeners();

        // Инициализация превью
        initPreview();

        // Скрываем область площади при старте
        document.getElementById('area-info').style.display = 'none';

        // Создаем модальное окно для просмотра изображений
        createImageModal();

        // Создаем индикатор зума
        createZoomIndicator();
        // Устанавливаем начальный инструмент (рука)
    setTool('hand');
    });

    // Создание индикатора зума
    function createZoomIndicator() {
        const container = document.getElementById('canvas-container');
        if (!container) return;

        const indicator = document.createElement('div');
        indicator.id = 'zoom-indicator';
        indicator.className = 'zoom-indicator';
        indicator.innerHTML = '<i class="fas fa-search"></i> 100%';
        container.appendChild(indicator);
    }

    // Обновление индикатора зума
    function updateZoomIndicator() {
        const indicator = document.getElementById('zoom-indicator');
        if (indicator) {
            const zoomPercent = Math.round(zoom * 100);
            indicator.innerHTML = `<i class="fas fa-search"></i> ${zoomPercent}%`;
        }
    }

    // Создание модального окна для просмотра изображений
    function createImageModal() {
    // Проверяем, существует ли уже модальное окно
    if (document.getElementById('image-view-modal')) return;

    const modal = document.createElement('div');
    modal.id = 'image-view-modal';
    modal.className = 'image-modal';
    modal.innerHTML = `
        <div class="image-modal-content">
            <button class="image-modal-close" onclick="closeImageModal()">
                <i class="fas fa-times"></i>
            </button>
            <button class="image-modal-nav prev" onclick="navigateModalImage(-1)">
                <i class="fas fa-chevron-left"></i>
            </button>
            <img class="image-modal-img" src="" alt="Просмотр изображения">
            <button class="image-modal-nav next" onclick="navigateModalImage(1)">
                <i class="fas fa-chevron-right"></i>
            </button>
            <div class="image-modal-info">
                <span class="image-modal-name"></span>
                <span class="image-modal-area"></span>
            </div>
        </div>
    `;
    document.body.appendChild(modal);

    // Закрытие по клику на фон
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            closeImageModal();
        }
    });

    // Закрытие по клавише Escape
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && modal.classList.contains('active')) {
            closeImageModal();
        }

        // Навигация стрелками
        if (modal.classList.contains('active')) {
            if (e.key === 'ArrowLeft') {
                navigateModalImage(-1);
            } else if (e.key === 'ArrowRight') {
                navigateModalImage(1);
            }
        }
    });
}

    // Функция для открытия модального окна с изображением
    function openImageModal(imageSrc, imageName, imageArea, allImages = null) {
        const modal = document.getElementById('image-view-modal');
        if (!modal) return;

        // Если передан массив всех изображений
        if (allImages && allImages.length > 0) {
            currentModalImages = allImages;
            // Находим индекс текущего изображения
            currentModalIndex = allImages.findIndex(img => img.src === imageSrc);
            if (currentModalIndex === -1) currentModalIndex = 0;

            // Показываем/скрываем кнопки навигации
            const prevBtn = modal.querySelector('.prev');
            const nextBtn = modal.querySelector('.next');
            if (prevBtn && nextBtn) {
                prevBtn.style.display = 'flex';
                nextBtn.style.display = 'flex';
                updateNavButtons();
            }
        } else {
            // Если только одно изображение
            currentModalImages = [{
                src: imageSrc,
                name: imageName,
                area: imageArea
            }];
            currentModalIndex = 0;
            const prevBtn = modal.querySelector('.prev');
            const nextBtn = modal.querySelector('.next');
            if (prevBtn && nextBtn) {
                prevBtn.style.display = 'none';
                nextBtn.style.display = 'none';
            }
        }

        // Устанавливаем текущее изображение
        updateModalImage();

        // Показываем модальное окно
        modal.classList.add('active');

        // Блокируем прокрутку страницы
        document.body.style.overflow = 'hidden';
    }

    // Функция для обновления изображения в модальном окне
    function updateModalImage() {
        const modal = document.getElementById('image-view-modal');
        if (!modal || !currentModalImages.length) return;

        const currentImage = currentModalImages[currentModalIndex];
        const img = modal.querySelector('.image-modal-img');
        const nameSpan = modal.querySelector('.image-modal-name');
        const areaSpan = modal.querySelector('.image-modal-area');

        if (img) img.src = currentImage.src;
        if (nameSpan) nameSpan.textContent = currentImage.name || 'Изображение';

        if (areaSpan) {
            if (currentImage.area) {
                areaSpan.innerHTML = `<i class="fas fa-vector-square"></i> Площадь: ${currentImage.area}`;
            } else {
                areaSpan.innerHTML = '';
            }
        }

        updateNavButtons();
    }

    // Функция для навигации по изображениям
    function navigateModalImage(direction) {
        const newIndex = currentModalIndex + direction;
        if (newIndex >= 0 && newIndex < currentModalImages.length) {
            currentModalIndex = newIndex;
            updateModalImage();
        }
    }

    // Функция для обновления состояния кнопок навигации
    function updateNavButtons() {
        const modal = document.getElementById('image-view-modal');
        if (!modal) return;

        const prevBtn = modal.querySelector('.prev');
        const nextBtn = modal.querySelector('.next');

        if (prevBtn) {
            prevBtn.disabled = currentModalIndex === 0;
        }
        if (nextBtn) {
            nextBtn.disabled = currentModalIndex === currentModalImages.length - 1;
        }
    }

    // Функция для закрытия модального окна
    function closeImageModal() {
    const modal = document.getElementById('image-view-modal');
    if (modal && modal.classList.contains('active')) {
        // Добавляем класс closing для анимации
        modal.classList.add('closing');
        modal.classList.remove('active');

        // Разблокируем прокрутку страницы сразу
        document.body.style.overflow = '';

        // Удаляем класс closing после завершения анимации
        setTimeout(() => {
            modal.classList.remove('closing');
        }, 300); // 300ms соответствует длительности transition
    }
}

    // Toast уведомления
    function showToast(title, message, type = 'info', duration = 3000) {
        const container = document.getElementById('toast-container');

        // Создаем элемент уведомления
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;

        // Выбираем иконку в зависимости от типа
        let icon = 'info-circle';
        if (type === 'success') icon = 'check-circle';
        if (type === 'error') icon = 'exclamation-circle';
        if (type === 'warning') icon = 'exclamation-triangle';

        toast.innerHTML = `
            <div class="toast-icon">
                <i class="fas fa-${icon}"></i>
            </div>
            <div class="toast-content">
                <div class="toast-title">${title}</div>
                <div class="toast-message">${message}</div>
            </div>
            <div class="toast-close" onclick="this.closest('.toast').remove()">
                <i class="fas fa-times"></i>
            </div>
        `;

        container.appendChild(toast);

        // Автоматическое удаление через duration
        setTimeout(() => {
            toast.classList.add('fade-out');
            setTimeout(() => {
                if (toast.parentElement) {
                    toast.remove();
                }
            }, 300);
        }, duration);
    }

    function showLoading(message = 'Загрузка...', showProgress = false) {
        // Если уже есть уведомление о загрузке, обновляем его
        if (loadingToast && loadingToast.parentElement) {
            const messageEl = loadingToast.querySelector('.toast-message');
            if (messageEl) messageEl.textContent = message;
            return;
        }

        const container = document.getElementById('toast-container');

        loadingToast = document.createElement('div');
        loadingToast.className = 'toast info';
        loadingToast.innerHTML = `
            <div class="toast-icon">
                <i class="fas fa-spinner fa-pulse"></i>
            </div>
            <div class="toast-content">
                <div class="toast-title">Обработка</div>
                <div class="toast-message">${message}</div>
            </div>
        `;

        container.appendChild(loadingToast);
    }

    function hideLoading() {
        if (loadingToast && loadingToast.parentElement) {
            loadingToast.classList.add('fade-out');
            setTimeout(() => {
                if (loadingToast && loadingToast.parentElement) {
                    loadingToast.remove();
                    loadingToast = null;
                }
            }, 300);
        }
    }

    // Инициализация превью
    function initPreview() {
        const changeBtn = document.querySelector('.preview-btn:first-of-type');
        const removeBtn = document.querySelector('.preview-btn:last-of-type');

        if (changeBtn) {
            changeBtn.onclick = changeImage;
        }
        if (removeBtn) {
            removeBtn.onclick = removeImage;
        }
    }

    // Функция для показа превью после загрузки изображения
    function showImagePreview(file) {
        const uploadZone = document.getElementById('single-upload-zone');
        const previewDiv = document.getElementById('uploaded-preview');
        const previewImage = document.getElementById('preview-image');
        const previewFilename = document.getElementById('preview-filename');
        const previewDimensions = document.getElementById('preview-dimensions');

        if (file) {
            const reader = new FileReader();

            reader.onload = function(e) {
                previewImage.src = e.target.result;

                // Получаем размеры изображения
                const img = new Image();
                img.onload = function() {
                    previewDimensions.textContent = `${img.width} × ${img.height} пикселей`;
                };
                img.src = e.target.result;

                previewFilename.textContent = file.name;

                // Скрываем зону загрузки и показываем превью
                uploadZone.style.display = 'none';
                previewDiv.style.display = 'block';
                previewDiv.classList.add('fade-in');
            };

            reader.readAsDataURL(file);
        }
    }

    // Функция для изменения изображения
    function changeImage() {
        // Скрываем превью и показываем зону загрузки
        document.getElementById('single-upload-zone').style.display = 'block';
        document.getElementById('uploaded-preview').style.display = 'none';
        document.getElementById('preview-image').src = '';

        // Открываем диалог выбора файла
        document.getElementById('single-file-input').click();
    }

    // Функция для удаления изображения
    function removeImage() {
        document.getElementById('single-upload-zone').style.display = 'block';
        document.getElementById('uploaded-preview').style.display = 'none';
        document.getElementById('preview-image').src = '';

        // Очищаем канвас
        clearCanvas();

        // Очищаем данные сессии
        currentSessionId = null;
        images = {};
        points = [];
        currentImage = null;

        // Очищаем хранилища масок
        window.masks = {};
        window.multiMasks = {};
        window.maskImageCache = {};
        window.currentTempMask = null;

        // Очищаем отображение площади
        clearAreaDisplay();

        // Обновляем интерфейс
        updatePointsList();
        showToast('Информация', 'Изображение удалено', 'info');
    }

    // Функция для очистки канваса
    function clearCanvas() {
        const canvas = document.getElementById('main-canvas');
        const ctx = canvas.getContext('2d');

        ctx.clearRect(0, 0, canvas.width, canvas.height);
        canvas.style.display = 'none';

        document.getElementById('no-image-message').style.display = 'flex';
        document.querySelector('.canvas-controls').style.display = 'none';
        document.querySelector('.point-type-selector').style.display = 'none';
        document.getElementById('image-info').style.display = 'none';

        // Скрываем индикатор зума
        const zoomIndicator = document.getElementById('zoom-indicator');
        if (zoomIndicator) zoomIndicator.style.display = 'none';

        // Деактивируем кнопки
        document.getElementById('generate-btn').disabled = true;
        document.getElementById('undo-btn').disabled = true;
        document.getElementById('propagate-btn').disabled = true;
        document.getElementById('complete-btn').disabled = true;
    }

    // Функция для загрузки истории пользователя с сервера
    async function loadUserHistory() {
        try {
            const response = await fetch('/api/user_images');
            const data = await response.json();

            if (data.success) {
                // Преобразуем данные из БД в формат для отображения
                const historyFromServer = data.images.map(img => ({
                    id: img.id,
                    name: img.filename,
                    thumb: img.url,
                    dataUrl: img.url,
                    date: img.upload_date
                }));

                // Обновляем отображение истории
                renderHistoryFromServer(historyFromServer);
            }
        } catch (error) {
            console.error('Error loading history:', error);
        }
    }

    // Функция для отображения истории с сервера
    function renderHistoryFromServer(historyItems) {
        const grid = document.getElementById('history-grid');
        const emptyMessage = document.getElementById('history-empty');

        if (historyItems.length === 0) {
            emptyMessage.style.display = 'flex';
            return;
        }

        emptyMessage.style.display = 'none';
        grid.innerHTML = '';

        historyItems.forEach((item) => {
            const div = document.createElement('div');
            div.className = 'history-item';
            div.onclick = () => loadFromHistory(item);
            div.innerHTML = `
                <img src="${item.thumb}" class="history-thumb" alt="${item.name}">
                <div class="history-info">
                    <div class="history-name">${item.name}</div>
                    <div class="history-date">${item.date}</div>
                </div>
                <div class="history-remove" onclick="deleteHistoryItem(${item.id}, event)">
                    <i class="fas fa-times"></i>
                </div>
            `;
            grid.appendChild(div);
        });
    }

    // Форматирование даты
    function formatDate(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) return 'только что';
        if (diffMins < 60) return `${diffMins} мин назад`;
        if (diffHours < 24) return `${diffHours} ч назад`;
        if (diffDays < 7) return `${diffDays} дн назад`;

        return date.toLocaleDateString('ru-RU', {
            day: '2-digit',
            month: '2-digit',
            year: '2-digit'
        });
    }

    // Добавление в историю (теперь через сервер)
   async function addToHistory(imageData) {
    // Проверяем, авторизован ли пользователь
    //const isGuest = {{ is_guest|tojson }};

    if (isGuest) {
        showToast('Авторизация', 'Чтобы сохранять изображения в историю, необходимо авторизоваться', 'warning');
        return;
    }

    // Проверяем, не было ли это изображение уже добавлено в текущей сессии
    if (window._lastAddedImage && window._lastAddedImage === imageData.name) {
        console.log('Изображение уже добавлено в историю в этой сессии:', imageData.name);
        return;
    }

    showLoading('Сохранение в историю...');

    try {
        // Отправляем изображение на сервер для сохранения в БД
        const formData = new FormData();

        // Преобразуем dataUrl в blob
        const response = await fetch(imageData.dataUrl);
        const blob = await response.blob();
        const file = new File([blob], imageData.name, { type: 'image/jpeg' });

        formData.append('image', file);

        const serverResponse = await fetch('/api/images/save', {
            method: 'POST',
            body: formData
        });

        const result = await serverResponse.json();

        if (result.success) {
            // Запоминаем, что это изображение уже добавлено
            window._lastAddedImage = imageData.name;

            showToast('Успех', 'Изображение сохранено в историю', 'success');
            // Загружаем историю с сервера
            await loadUserHistory();
        } else {
            throw new Error(result.message || 'Ошибка сохранения');
        }
    } catch (error) {
        console.error('Error saving to history:', error);
        showToast('Ошибка', 'Не удалось сохранить изображение в историю', 'error');
    } finally {
        hideLoading();
    }
}

    // Функция для удаления из истории на сервере
    async function deleteHistoryItem(imageId, event) {
        event.stopPropagation();

        if (!confirm('Удалить изображение из истории?')) return;

        try {
            const response = await fetch(`/delete_image/${imageId}`, {
                method: 'DELETE'
            });

            const result = await response.json();

            if (result.success) {
                showToast('Успех', 'Изображение удалено из истории', 'success');
                // Перезагружаем историю
                await loadUserHistory();
            } else {
                throw new Error(result.message || 'Ошибка удаления');
            }
        } catch (error) {
            console.error('Error deleting image:', error);
            showToast('Ошибка', error.message, 'error');
        }
    }

    // Очистка истории
    function clearHistory() {
        // Проверяем, авторизован ли пользователь
        //const isGuest = {{ is_guest|tojson }};

        if (isGuest) {
            showToast('Авторизация', 'Чтобы очищать историю, необходимо авторизоваться', 'warning');
            return;
        }

        if (confirm('Вы уверены, что хотите очистить историю загрузок?')) {
            // Здесь можно добавить API для очистки всей истории
            showToast('Информация', 'Функция очистки всей истории в разработке', 'info');
        }
    }

    // Загрузка из истории (исправленная версия)
async function loadFromHistory(historyItem) {
    // Проверяем, авторизован ли пользователь
    //const isGuest = {{ is_guest|tojson }};

    if (isGuest) {
        showToast('Авторизация', 'Чтобы загружать изображения из истории, необходимо авторизоваться', 'warning');
        return;
    }

    showLoading('Загрузка из истории...');

    try {
        // Проверяем, не загружено ли уже это изображение
        const isAlreadyLoaded = allUploadedImages.some(img => img.name === historyItem.name);
        if (isAlreadyLoaded) {
            showToast('Информация', `Изображение "${historyItem.name}" уже загружено`, 'info');

            // Находим индекс уже загруженного изображения и переключаемся на него
            const existingIndex = allUploadedImages.findIndex(img => img.name === historyItem.name);
            if (existingIndex !== -1) {
                currentImageIndex = existingIndex;
                loadImageFromArray(currentImageIndex);
            }

            hideLoading();
            return;
        }

        // Используем URL изображения напрямую
        const response = await fetch(historyItem.dataUrl);
        const blob = await response.blob();
        const file = new File([blob], historyItem.name, { type: 'image/jpeg' });

        const formData = new FormData();
        formData.append('file', file);

        const serverResponse = await fetch('/upload_single', {
            method: 'POST',
            body: formData
        });

        const contentType = serverResponse.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            const text = await serverResponse.text();
            console.error('Server returned non-JSON response:', text);
            throw new Error('Сервер вернул некорректный ответ');
        }

        const data = await serverResponse.json();

        if (data.success) {
            // СОЗДАЕМ НОВОЕ ИЗОБРАЖЕНИЕ ДЛЯ МАССИВА
            const newImage = {
                name: data.filename,
                dataUrl: data.image_data,
                thumb: data.image_data,
                sessionId: data.session_id,
                uploadDate: new Date()
            };

            // ДОБАВЛЯЕМ В МАССИВ allUploadedImages
            allUploadedImages.push(newImage);

            // Обновляем images для обратной совместимости
            images = {};
            let index = 0;
            allUploadedImages.forEach(img => {
                images[index] = {
                    name: img.name,
                    dataUrl: img.dataUrl,
                    thumb: img.thumb
                };
                index++;
            });

            // Устанавливаем текущую сессию
            currentSessionId = data.session_id;

            // Отображаем загруженное изображение
            const newIndex = allUploadedImages.length - 1;
            displayImagePreview(allUploadedImages[newIndex].dataUrl, allUploadedImages[newIndex].name);
            currentImageIndex = newIndex;

            // Инициализируем хранилище для множественных масок
            const imageName = data.filename;
            if (!window.multiMasks[imageName]) {
                window.multiMasks[imageName] = [];
            }

            // Показываем информацию об изображении
            document.getElementById('image-info').style.display = 'block';

            // Показываем индикатор зума
            const zoomIndicator = document.getElementById('zoom-indicator');
            if (zoomIndicator) zoomIndicator.style.display = 'flex';

            // Обновляем список изображений
            showImageList();

            showToast('Успех', `Изображение "${data.filename}" загружено из истории. Всего загружено: ${allUploadedImages.length}`, 'success');
        } else {
            throw new Error(data.error || 'Ошибка загрузки');
        }
    } catch (error) {
        console.error('Load from history error:', error);
        showToast('Ошибка', error.message, 'error');
    } finally {
        hideLoading();
    }
}

    // Настройка обработчиков событий
    function setupEventListeners() {
    // Переключение вкладок
    setupUploadTab('single');
    setupUploadTab('zip');

    // Обработка перетаскивания для одиночного изображения
    const singleZone = document.getElementById('single-upload-zone');
    setupDragAndDrop(singleZone, handleSingleImageDrop);

    // Обработка перетаскивания для ZIP
    const zipZone = document.getElementById('zip-upload-zone');
    setupDragAndDrop(zipZone, handleZipDrop);

    // Клики по canvas
    canvas.addEventListener('click', handleCanvasClick);
    canvas.addEventListener('mousedown', startDrag);
    canvas.addEventListener('mousemove', handleDrag);
    canvas.addEventListener('mouseup', stopDrag);
    canvas.addEventListener('wheel', handleZoom);

    // ПОЛНАЯ БЛОКИРОВКА контекстного меню на canvas
    canvas.addEventListener('contextmenu', (e) => {
        e.preventDefault();
        e.stopPropagation();
        return false;
    });
    // Добавляем обработчик контекстного меню для предотвращения появления стандартного меню при правом клике
    canvas.addEventListener('contextmenu', preventContextMenu);

    // Добавляем обработчик mouseleave на случай, если мышь уйдет за пределы canvas во время перетаскивания
    canvas.addEventListener('mouseleave', stopDrag);

    // Изменение размера окна
    window.addEventListener('resize', resizeCanvas);
}

// Добавляем глобальную переменную для отслеживания режима перетаскивания
let dragMode = null; // 'left' или 'right'

    // Настройка drag and drop для зоны
    function setupDragAndDrop(zone, handler) {
        zone.addEventListener('dragover', (e) => {
            e.preventDefault();
            zone.classList.add('drag-over');
        });

        zone.addEventListener('dragleave', () => {
            zone.classList.remove('drag-over');
        });

        zone.addEventListener('drop', (e) => {
            e.preventDefault();
            zone.classList.remove('drag-over');
            handler(e.dataTransfer.files);
        });
    }

    // Настройка вкладки загрузки
    function setupUploadTab(type) {
    const zone = document.getElementById(`${type}-upload-zone`);
    const fileInput = document.getElementById(`${type}-file-input`);

    // Убираем onclick из HTML и добавляем здесь обработчик для кнопки
    if (type === 'zip') {
        const uploadButton = document.getElementById('zip-upload-button');
        if (uploadButton) {
            uploadButton.addEventListener('click', (e) => {
                e.stopPropagation(); // Останавливаем всплытие
                fileInput.click();
            });
        }
    }

    zone.addEventListener('click', (e) => {
        // Проверяем, что кликнули по зоне или по тексту, НЕ по кнопке
        if (e.target === zone ||
            e.target.classList.contains('upload-text') ||
            e.target.classList.contains('upload-subtext') ||
            e.target.classList.contains('upload-icon')) {
            fileInput.click();
        }
    });

    // Обработчик изменения файла (когда пользователь выбрал файл)
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            if (type === 'single') {
                handleSingleImageUpload(e.target.files);
            } else if (type === 'zip') {
                handleZipUpload(e.target.files[0]);
            }
            // Сбрасываем значение инпута, чтобы можно было выбрать тот же файл снова
            e.target.value = '';
        }
    });
}

    // Переключение вкладок загрузки
    function switchUploadTab(tab) {
        // Обновляем активную вкладку
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        event.target.classList.add('active');

        // Показываем соответствующую вкладку
        document.querySelectorAll('.upload-tab-content').forEach(content => {
            content.style.display = 'none';
        });

        document.getElementById(`${tab}-upload-tab`).style.display = 'block';
        currentUploadType = tab;
    }

    // Обработка перетаскивания одиночного изображения
    function handleSingleImageDrop(files) {
        if (files.length > 0) {
            handleSingleImageUpload(files);
        }
    }

    // Обработка перетаскивания ZIP
    function handleZipDrop(files) {
        if (files.length > 0 && files[0].name.endsWith('.zip')) {
            handleZipUpload(files[0]);
        } else {
            showToast('Ошибка', 'Пожалуйста, загрузите ZIP-архив', 'error');
        }
    }


    // ========== ФУНКЦИИ СЖАТИЯ ИЗОБРАЖЕНИЙ (ИСПРАВЛЕННЫЕ) ==========

/**
 * Проверка, является ли объект File или Blob
 */
function isFileObject(obj) {
    return obj instanceof File || obj instanceof Blob;
}

/**
 * Сжатие изображения перед отправкой на сервер
 * @param {File|Blob} file - исходный файл изображения
 * @param {Object} options - настройки сжатия
 * @returns {Promise<File>} - сжатый файл
 */
async function compressImage(file, options = {}) {
    const {
        maxWidth = 1920,
        maxHeight = 1920,
        quality = 0.85,
        maxSizeMB = 5
    } = options;

    return new Promise((resolve, reject) => {
        // Проверяем входные данные
        if (!file) {
            reject(new Error('Файл не предоставлен'));
            return;
        }

        // Получаем размер файла
        const fileSize = file.size || 0;

        // ВСЕГДА сжимаем (для теста)
        console.log("FORCE COMPRESS:", (fileSize / 1024 / 1024).toFixed(2), "MB");

        // Создаем URL для файла
        let objectUrl = null;

        try {
            // Если это Blob или File, создаем URL
            if (isFileObject(file)) {
                objectUrl = URL.createObjectURL(file);
            } else if (typeof file === 'string') {
                objectUrl = file;
            } else {
                reject(new Error('Неподдерживаемый тип файла'));
                return;
            }

            const img = new Image();

            img.onload = function() {
                let width = img.width;
                let height = img.height;

                // Вычисляем новые размеры с сохранением пропорций
                if (width > maxWidth || height > maxHeight) {
                    const ratio = Math.min(maxWidth / width, maxHeight / height);
                    width = Math.floor(width * ratio);
                    height = Math.floor(height * ratio);
                }

                // Создаем canvas для сжатия
                const canvas = document.createElement('canvas');
                canvas.width = width;
                canvas.height = height;

                const ctx = canvas.getContext('2d');
                ctx.drawImage(img, 0, 0, width, height);

                // Определяем формат выходного файла
                let mimeType = file.type || 'image/jpeg';
                if (mimeType === 'image/bmp' || mimeType === 'image/tiff' || mimeType === '') {
                    mimeType = 'image/jpeg';
                }

                // Сжимаем изображение
                canvas.toBlob(function(blob) {
                    // Создаем имя файла
                    const fileName = file.name || `image_${Date.now()}.${mimeType.split('/')[1] || 'jpg'}`;

                    const compressedFile = new File([blob], fileName, {
                        type: mimeType,
                        lastModified: Date.now()
                    });

                    const originalSize = (fileSize / 1024 / 1024).toFixed(2);
                    const compressedSize = (compressedFile.size / 1024 / 1024).toFixed(2);
                    const reduction = ((1 - compressedFile.size / fileSize) * 100).toFixed(1);

                    console.log(`Сжатие ${fileName}: ${originalSize} MB → ${compressedSize} MB (${reduction}%)`);

                    // Показываем уведомление о сжатии
                    if (reduction > 10) {
                        showToast(`Изображение сжато: ${originalSize} MB → ${compressedSize} MB`, 'info');
                    }

                    // Очищаем URL объект
                    if (objectUrl && objectUrl.startsWith('blob:')) {
                        URL.revokeObjectURL(objectUrl);
                    }

                    resolve(compressedFile);
                }, mimeType, quality);
            };

            img.onerror = () => {
                if (objectUrl && objectUrl.startsWith('blob:')) {
                    URL.revokeObjectURL(objectUrl);
                }
                reject(new Error('Не удалось загрузить изображение для сжатия'));
            };

            img.src = objectUrl;

        } catch (error) {
            if (objectUrl && objectUrl.startsWith('blob:')) {
                URL.revokeObjectURL(objectUrl);
            }
            reject(error);
        }
    });
}

/**
 * Безопасная обертка для handleSingleImageUpload с сжатием
 */


/**
 * Получаем текущие настройки сжатия
 */
function getCompressionSettings() {
    const compressEnabled = document.getElementById('compress-toggle')?.checked ?? true;

    if (!compressEnabled) {
        return null;
    }

    return {
        maxWidth: parseInt(document.getElementById('max-width')?.value || 1920),
        maxHeight: parseInt(document.getElementById('max-height')?.value || 1920),
        quality: parseFloat(document.getElementById('compression-quality')?.value || 0.85),
        maxSizeMB: parseFloat(document.getElementById('max-size-mb')?.value || 5)
    };
}

/**
 * Добавляем настройки сжатия в интерфейс
 */
function addCompressionSettings() {
    // Проверяем, не добавлены ли уже настройки
    if (document.querySelector('.compression-settings')) {
        return;
    }

    const settingsHTML = `
        <div class="compression-settings" style="margin-top: 15px; padding: 12px; background: var(--surface-dark); border-radius: var(--radius-sm); border: 1px solid var(--border);">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <i class="fas fa-compress-alt" style="color: var(--primary);"></i>
                    <span style="font-size: 13px; font-weight: 500;">Сжатие изображений</span>
                </div>
                <label class="toggle-switch">
                    <input type="checkbox" id="compress-toggle" checked>
                    <span class="toggle-slider"></span>
                </label>
            </div>
            <div id="compression-options">
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 12px;">
                    <div>
                        <label style="color: var(--text-light); display: block; margin-bottom: 4px;">Макс. ширина:</label>
                        <input type="number" id="max-width" value="1920" step="100" min="640" max="4096"
                               style="width: 100%; padding: 6px 8px; border-radius: 6px; border: 1px solid var(--border); background: var(--surface);">
                    </div>
                    <div>
                        <label style="color: var(--text-light); display: block; margin-bottom: 4px;">Макс. высота:</label>
                        <input type="number" id="max-height" value="1920" step="100" min="640" max="4096"
                               style="width: 100%; padding: 6px 8px; border-radius: 6px; border: 1px solid var(--border); background: var(--surface);">
                    </div>
                    <div>
                        <label style="color: var(--text-light); display: block; margin-bottom: 4px;">Качество:</label>
                        <input type="range" id="compression-quality" min="0.5" max="1.0" step="0.05" value="0.85"
                               style="width: 100%;">
                        <div style="display: flex; justify-content: space-between; margin-top: 2px;">
                            <span style="font-size: 10px;">50%</span>
                            <span id="quality-value" style="font-size: 11px; font-weight: 500;">85%</span>
                            <span style="font-size: 10px;">100%</span>
                        </div>
                    </div>
                    <div>
                        <label style="color: var(--text-light); display: block; margin-bottom: 4px;">Макс. размер:</label>
                        <select id="max-size-mb" style="width: 100%; padding: 6px 8px; border-radius: 6px; border: 1px solid var(--border); background: var(--surface);">
                            <option value="2">2 MB</option>
                            <option value="5" selected>5 MB</option>
                            <option value="10">10 MB</option>
                            <option value="20">20 MB</option>
                        </select>
                    </div>
                </div>
                <div style="margin-top: 10px; padding: 8px; background: var(--primary-light); border-radius: 6px; font-size: 11px; color: var(--primary-dark);">
                    <i class="fas fa-info-circle"></i>
                    Автоматическое сжатие изображений размером более ${document.getElementById('max-size-mb')?.value || 5} MB
                </div>
            </div>
        </div>
    `;

    // Добавляем настройки в панель загрузки
    const currentTab = document.querySelector('.upload-tab-content:not([style*="display: none"])');
    if (currentTab) {
        const uploadZone = currentTab.querySelector('.upload-zone');
        uploadZone.insertAdjacentHTML('afterend', settingsHTML);
    }

    // Добавляем обработчики
    const toggle = document.getElementById('compress-toggle');
    const options = document.getElementById('compression-options');
    const qualitySlider = document.getElementById('compression-quality');
    const qualityValue = document.getElementById('quality-value');
    const maxSizeSelect = document.getElementById('max-size-mb');

    if (toggle && options) {
        toggle.addEventListener('change', (e) => {
            options.style.display = e.target.checked ? 'block' : 'none';
        });
    }

    if (qualitySlider && qualityValue) {
        qualitySlider.addEventListener('input', (e) => {
            const percent = Math.round(e.target.value * 100);
            qualityValue.textContent = `${percent}%`;
        });
    }

    if (maxSizeSelect) {
        maxSizeSelect.addEventListener('change', () => {
            const infoDiv = document.querySelector('.compression-settings .bg-primary-light');
            if (infoDiv) {
                infoDiv.innerHTML = `<i class="fas fa-info-circle"></i> Автоматическое сжатие изображений размером более ${maxSizeSelect.value} MB`;
            }
        });
    }
}

// Инициализация при загрузке страницы
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        setTimeout(() => {
            addCompressionSettings();

        }, 500);
    });
} else {
    setTimeout(() => {
        addCompressionSettings();

    }, 500);
}
    // Загрузка одиночного изображения
async function handleSingleImageUpload(files) {
    if (!files || files.length === 0) return;

   let file = files[0];

    console.log("FILE BEFORE:", file.name, file.size);

    // СЖАТИЕ
    try {
        const settings = getCompressionSettings();

        console.log("START COMPRESS");

        const compressed = await compressImage(file, settings);

        console.log("FILE AFTER:", compressed.name, compressed.size);

        file = compressed;

    } catch (err) {
        console.error("COMPRESS ERROR:", err);
    }

    // Проверка формата файла
    const validFormats = ['.png', '.jpg', '.jpeg', '.bmp', '.tiff'];
    const isValidFormat = validFormats.some(format =>
        file.name.toLowerCase().endsWith(format)
    );

    if (!isValidFormat) {
        showToast('Ошибка', 'Неподдерживаемый формат файла. Используйте PNG, JPG, JPEG, BMP или TIFF.', 'error');
        return;
    }

    // Показываем превью сразу после выбора файла
    showImagePreview(file);

    showLoading('Загрузка изображения...');

    try {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch('/upload_single', {
            method: 'POST',
            body: formData
        });

        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            const text = await response.text();
            console.error('Server returned non-JSON response:', text);
            throw new Error('Сервер вернул некорректный ответ');
        }

        const data = await response.json();

        if (data.success) {
            // СОХРАНЯЕМ ВСЕ ИЗОБРАЖЕНИЯ В МАССИВ
            const newImage = {
                name: data.filename,
                dataUrl: data.image_data,
                thumb: data.image_data,
                sessionId: data.session_id,
                uploadDate: new Date()
            };

            allUploadedImages.push(newImage);

            // Обновляем images для обратной совместимости (текущее изображение)
            images = {};
            let index = 0;
            allUploadedImages.forEach(img => {
                images[index] = {
                    name: img.name,
                    dataUrl: img.dataUrl,
                    thumb: img.thumb
                };
                index++;
            });

            // Устанавливаем текущую сессию как последнюю загруженную
            currentSessionId = data.session_id;

            // Отображаем последнее загруженное изображение
            const lastIndex = allUploadedImages.length - 1;
            displayImagePreview(allUploadedImages[lastIndex].dataUrl, allUploadedImages[lastIndex].name);
            currentImageIndex = lastIndex;

            // Инициализируем хранилище для множественных масок
            const imageName = data.filename;
            if (!window.multiMasks[imageName]) {
                window.multiMasks[imageName] = [];
            }

            // Показываем информацию об изображении
            document.getElementById('image-info').style.display = 'block';

            // Показываем индикатор зума
            const zoomIndicator = document.getElementById('zoom-indicator');
            if (zoomIndicator) zoomIndicator.style.display = 'flex';

            showToast('Успех', `Изображение "${data.filename}" успешно загружено. Всего загружено: ${allUploadedImages.length}`, 'success');

            // Сохраняем изображение в БД для авторизованных пользователей
           // const isGuest = {{ is_guest|tojson }};
            if (!isGuest) {
                await saveUploadedImageToDB(file);
            }

            // Обновляем список изображений
            showImageList();
        } else {
            throw new Error(data.error || 'Ошибка загрузки');
        }
    } catch (error) {
        console.error('Upload error:', error);
        showToast('Ошибка', error.message, 'error');
    } finally {
        hideLoading();
    }
}

// Новая функция для сохранения загруженного изображения в БД
async function saveUploadedImageToDB(file) {
    console.log('СОХРАНЕНИЕ В БД вызвано для файла:', file.name);
    console.trace(); // Покажет стек вызовов - кто вызвал эту функцию
    try {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch('/api/images/save_uploaded', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (result.success) {
            console.log('Изображение сохранено в БД:', result.filename);
            // Обновляем историю
            await loadUserHistory();
        } else {
            console.error('Ошибка сохранения в БД:', result.message);
        }
    } catch (error) {
        console.error('Error saving to database:', error);
    }
}

    // Функция для отображения предпросмотра изображения
function displayImagePreview(imageData, filename) {
    // Скрываем сообщение об отсутствии изображения
    document.getElementById('no-image-message').style.display = 'none';

    // Показываем canvas
    const canvas = document.getElementById('main-canvas');
    canvas.style.display = 'block';

    // Показываем элементы управления
    document.querySelector('.canvas-controls').style.display = 'flex';
    document.querySelector('.point-type-selector').style.display = 'flex';

    // Показываем индикатор зума
    const zoomIndicator = document.getElementById('zoom-indicator');
    if (zoomIndicator) zoomIndicator.style.display = 'flex';

    // Загружаем изображение на canvas
    const img = new Image();
    img.onload = () => {
        currentImage = img;

        // Вычисляем оптимальный масштаб для вписывания изображения в canvas
        resizeCanvas();

        // Сбрасываем позицию и вычисляем оптимальный зум
        offsetX = 0;
        offsetY = 0;

        // Вычисляем масштаб, чтобы изображение вписалось в canvas с минимальными отступами
        const containerWidth = canvas.width;
        const containerHeight = canvas.height;

        const scaleX = containerWidth / img.width;
        const scaleY = containerHeight / img.height;

        // Берем минимальный масштаб, чтобы изображение полностью вписалось
        zoom = Math.min(scaleX, scaleY) * 1.2;

        // Дополнительная проверка: если изображение меньше canvas, не увеличиваем его
        if (zoom > 1) {
            zoom = 1; // Не увеличиваем изображение, если оно уже маленькое
        }

        renderCanvas();

        // Обновляем информацию об изображении
        document.getElementById('image-name-display').textContent = filename;
        document.getElementById('image-dimensions').textContent =
            `${img.width} × ${img.height} пикселей`;

        // Активируем кнопки
        document.getElementById('generate-btn').disabled = false;
        document.getElementById('undo-btn').disabled = false;

        // Показываем список изображений (только одно)
        showImageList();

        // Показываем информационное сообщение
        showToast('Информация', 'Изображение загружено. Используйте колесико мыши для масштабирования.', 'info');
    };
    img.onerror = () => {
        console.error('Ошибка загрузки изображения:', filename);
        showToast('Ошибка', 'Не удалось загрузить изображение', 'error');
    };
    img.src = imageData;
}

    // Загрузка ZIP - ИСПРАВЛЕННАЯ ВЕРСИЯ
async function handleZipUpload(file) {
    if (!file) return;

    showLoading('Загрузка ZIP-архива...');

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });

        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            const text = await response.text();
            console.error('Server returned non-JSON response:', text);
            throw new Error('Сервер вернул некорректный ответ');
        }

        const data = await response.json();

        if (!data.success) throw new Error(data.error || 'Ошибка загрузки');

        currentSessionId = data.session_id;
        console.log('ZIP Session ID set:', currentSessionId);

        // ОЧИЩАЕМ ПРЕДЫДУЩИЕ ДАННЫЕ
        images = {};
        loadedImageNames.clear();

        // ВАЖНО: ОЧИЩАЕМ allUploadedImages ПРИ ЗАГРУЗКЕ НОВОГО ZIP
        allUploadedImages = [];

        if (!data.image_keys || !data.images) {
            console.error('Invalid server response format:', data);
            throw new Error('Неверный формат ответа от сервера');
        }

        const compressionSettings = getCompressionSettings();

        let index = 0;
        for (const key of data.image_keys) {
            if (!data.images[key]) {
                console.warn(`No image data for key: ${key}`);
                continue;
            }

            let fileName = key;
            try {
                fileName = decodeURIComponent(key);
            } catch (e) {
                console.warn('Could not decode filename:', key);
            }

            let dataUrl = data.images[key];

            // Сжатие включено?
            if (compressionSettings) {
                try {
                    const blob = await (async () => {
                        const res = await fetch(dataUrl);
                        return await res.blob();
                    })();

                    const type = blob.type === 'image/png' ? 'image/jpeg' : blob.type;
                    const compressedFile = await compressImage(new File([blob], fileName, { type }), compressionSettings);

                    dataUrl = await new Promise(resolve => {
                        const reader = new FileReader();
                        reader.onload = e => resolve(e.target.result);
                        reader.readAsDataURL(compressedFile);
                    });

                    if (blob.type === 'image/png') {
                        fileName = fileName.replace(/\.png$/i, '.jpg');
                    }

                    console.log(`Изображение ${fileName} сжато и конвертировано`);
                } catch (err) {
                    console.error(`Ошибка сжатия изображения ${fileName}:`, err);
                }
            }

            // СОХРАНЯЕМ В ОБА МАССИВА
            images[index] = {
                name: fileName,
                dataUrl: dataUrl,
                thumb: dataUrl
            };

            // ДОБАВЛЯЕМ В allUploadedImages
            allUploadedImages.push({
                name: fileName,
                dataUrl: dataUrl,
                thumb: dataUrl,
                sessionId: currentSessionId,
                uploadDate: new Date()
            });

            if (!window.multiMasks[fileName]) {
                window.multiMasks[fileName] = [];
            }

            index++;
        }

        if (allUploadedImages.length > 0) {
            // Обновляем images для обратной совместимости
            images = {};
            let idx = 0;
            allUploadedImages.forEach(img => {
                images[idx] = {
                    name: img.name,
                    dataUrl: img.dataUrl,
                    thumb: img.thumb
                };
                idx++;
            });

            // Отображаем первое изображение
            displayImagePreview(allUploadedImages[0].dataUrl, allUploadedImages[0].name);
            currentImageIndex = 0;

            // ПОКАЗЫВАЕМ СПИСОК ИЗОБРАЖЕНИЙ
            showImageList();

            showToast('Успех', `Архив успешно загружен. Загружено ${allUploadedImages.length} изображений`, 'success');



            if (!isGuest) {
                showToast('Информация', 'Изображения из ZIP будут сохранены при создании маски', 'info');
                if (typeof loadUserHistory === 'function') await loadUserHistory();
            }
        } else {
            showToast('Предупреждение', 'В архиве не найдено подходящих изображений', 'warning');
        }
    } catch (error) {
        console.error('ZIP upload error:', error);
        showToast('Ошибка', error.message, 'error');
    } finally {
        hideLoading();
    }
}

    // Загрузка примера
    async function loadExampleData() {
        showLoading('Загрузка примеров...');

        try {
            // Здесь можно добавить предопределенные примеры
            showToast('Информация', 'Функция загрузки примеров в разработке', 'info');
        } catch (error) {
            showToast('Ошибка', error.message, 'error');
        } finally {
            hideLoading();
        }
    }

    // Функция для загрузки и отображения маски
    function loadMaskForCurrentImage(maskDataUrl) {
        return new Promise((resolve, reject) => {
            const maskImg = new Image();
            maskImg.onload = () => {
                window.currentMaskImage = maskImg;
                currentMask = true; // Указываем, что маска есть

                // Вычисляем площадь маски
                calculateMaskAreaFromImage(maskImg).then(area => {
                    currentMaskArea = area;
                    updateAreaDisplay(area);
                    renderCanvas(); // Перерисовываем canvas с маской
                    resolve();
                }).catch(error => {
                    console.error('Ошибка вычисления площади:', error);
                    renderCanvas();
                    resolve();
                });
            };
            maskImg.onerror = () => {
                console.error('Ошибка загрузки маски');
                reject();
            };
            maskImg.src = maskDataUrl;
        });
    }

    // Загрузка изображения
async function loadImage(index) {
    if (!images[index]) return;

    const img = new Image();
    img.onload = () => {
        currentImage = img;

        // Загружаем сохраненные маски для этого изображения, если они есть
        const imageName = images[index].name;
        if (window.multiMasks && window.multiMasks[imageName] && window.multiMasks[imageName].length > 0) {
            // Устанавливаем флаг, что маски есть
            currentMask = true;
        } else {
            currentMask = false;
            window.currentMaskImage = null;
            window.currentTempMask = null;
            currentMaskArea = 0;
            updateAreaDisplay(0);
        }

        // Вычисляем оптимальный масштаб
        resizeCanvas();

        // Сбрасываем позицию и вычисляем оптимальный зум
        offsetX = 0;
        offsetY = 0;

        // Вычисляем масштаб, чтобы изображение вписалось в canvas
        const containerWidth = canvas.width;
        const containerHeight = canvas.height;

        const scaleX = containerWidth / img.width;
        const scaleY = containerHeight / img.height;

        // Берем минимальный масштаб, чтобы изображение полностью вписалось
        zoom = Math.min(scaleX, scaleY) * 0.95; // 0.95 для небольшого отступа от краев

        renderCanvas();

        updateImageSelection(index);
        updateImageInfo();

        // Показываем canvas и скрываем сообщение
        document.getElementById('main-canvas').style.display = 'block';
        document.getElementById('no-image-message').style.display = 'none';
        document.querySelector('.canvas-controls').style.display = 'flex';
        document.querySelector('.point-type-selector').style.display = 'flex';

        // Показываем индикатор зума
        const zoomIndicator = document.getElementById('zoom-indicator');
        if (zoomIndicator) zoomIndicator.style.display = 'flex';

        document.getElementById('generate-btn').disabled = false;
        document.getElementById('image-info').style.display = 'block';

        // Активируем кнопку завершения маски, если есть точки
        document.getElementById('complete-btn').disabled = points.length === 0;
    };
    img.onerror = () => {
        console.error('Ошибка загрузки изображения:', images[index].name);
        showToast('Ошибка', 'Не удалось загрузить изображение', 'error');
    };
    img.src = images[index].dataUrl;
}

    // Обновление информации об изображении
    function updateImageInfo() {
        if (!currentImage) return;

        document.getElementById('image-name-display').textContent =
            images[currentImageIndex]?.name || 'Изображение';
        document.getElementById('image-dimensions').textContent =
            `${currentImage.width} × ${currentImage.height} пикселей`;
    }

    // Навигация по изображениям
    function nextImage() {
        if (currentImageIndex < Object.keys(images).length - 1) {
            currentImageIndex++;
            loadImage(currentImageIndex);
        }
    }

    function prevImage() {
        if (currentImageIndex > 0) {
            currentImageIndex--;
            loadImage(currentImageIndex);
        }
    }

    // Функция для предварительной загрузки изображения маски в кэш
    function loadMaskImage(dataUrl) {
        return new Promise((resolve) => {
            if (window.maskImageCache[dataUrl]) {
                resolve(window.maskImageCache[dataUrl]);
            } else {
                const img = new Image();
                img.onload = () => {
                    window.maskImageCache[dataUrl] = img;
                    resolve(img);
                };
                img.src = dataUrl;
            }
        });
    }

    // ИСПРАВЛЕННАЯ функция отрисовки canvas
async function renderCanvas() {
    if (!currentImage || !canvas) return;

    if (isRendering) {
        setTimeout(() => renderCanvas(), 50);
        return;
    }

    isRendering = true;

    try {
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        ctx.save();
        ctx.translate(canvas.width / 2, canvas.height / 2);
        ctx.scale(zoom, zoom);
        ctx.translate(offsetX, offsetY);

        const x = -currentImage.width / 2;
        const y = -currentImage.height / 2;

        // 1. Рисуем оригинальное изображение
        ctx.drawImage(currentImage, x, y, currentImage.width, currentImage.height);

        const currentImageName = images[currentImageIndex].name;

        // 2. Рисуем ВСЕ сохраненные маски (просто как есть, с прозрачностью)
        if (window.multiMasks && window.multiMasks[currentImageName] && window.multiMasks[currentImageName].length > 0) {
            for (let i = 0; i < window.multiMasks[currentImageName].length; i++) {
                const mask = window.multiMasks[currentImageName][i];

                try {
                    const maskImg = await loadMaskImage(mask.dataUrl);

                    if (maskImg && maskImg.width > 0 && maskImg.height > 0) {
                        ctx.save();

                        // Просто рисуем маску поверх с прозрачностью
                        ctx.globalAlpha = 0.6;
                        ctx.globalCompositeOperation = 'source-over';
                        ctx.drawImage(maskImg, x, y, currentImage.width, currentImage.height);

                        ctx.restore();
                    }
                } catch (maskError) {
                    console.error('Ошибка при отрисовке сохраненной маски:', maskError);
                }
            }
        }

        // 3. Рисуем ВРЕМЕННУЮ маску (просто как есть, с прозрачностью)
        if (window.currentTempMask) {
            try {
                const maskImg = await loadMaskImage(window.currentTempMask);

                if (maskImg && maskImg.width > 0 && maskImg.height > 0) {
                    ctx.save();

                    // Просто рисуем маску поверх с прозрачностью
                    ctx.globalAlpha = 0.6;
                    ctx.globalCompositeOperation = 'source-over';
                    ctx.drawImage(maskImg, x, y, currentImage.width, currentImage.height);

                    ctx.restore();
                }
            } catch (maskError) {
                console.error('Ошибка при отрисовке временной маски:', maskError);
            }
        }

        // 4. Рисуем точки поверх всего
        ctx.globalAlpha = 1.0;
        ctx.globalCompositeOperation = 'source-over';
        ctx.shadowBlur = 0;
        ctx.shadowColor = 'transparent';

        // Базовый размер точки (в пикселях при zoom = 1)
        const basePointSize = 10;
        // Минимальный и максимальный размер точки
        const minPointSize = 1;
        const maxPointSize = 20;

        // Вычисляем размер точки с учетом зума
        // Чем больше зум, тем меньше точка относительно изображения, но абсолютный размер не становится слишком маленьким
        let pointSize = basePointSize / Math.sqrt(zoom); // Используем квадратный корень для более плавного изменения

        // Ограничиваем размер точки
        pointSize = Math.max(minPointSize, Math.min(maxPointSize, pointSize));

        // Размер внешнего свечения (пропорционален размеру точки)
        const glowSize = pointSize * 1.5;
        const highlightSize = pointSize * 0.4;

        points.forEach(point => {
    const pointX = point.x - currentImage.width / 2;
    const pointY = point.y - currentImage.height / 2;

    ctx.save();

    // Внешнее свечение
    ctx.shadowColor = point.type === 'positive' ? 'rgba(56, 176, 0, 0.5)' : 'rgba(255, 0, 110, 0.5)';
    ctx.shadowBlur = 15 / zoom; // Тень тоже масштабируем
    ctx.shadowOffsetX = 0;
    ctx.shadowOffsetY = 0;

    ctx.beginPath();
    ctx.arc(pointX, pointY, glowSize, 0, Math.PI * 2);
    ctx.fillStyle = point.type === 'positive' ? 'rgba(56, 176, 0, 0.3)' : 'rgba(255, 0, 110, 0.3)';
    ctx.fill();

    // Основная точка
    ctx.shadowBlur = 10 / zoom;
    ctx.beginPath();
    ctx.arc(pointX, pointY, pointSize, 0, Math.PI * 2);
    ctx.fillStyle = point.type === 'positive' ? '#38b000' : '#ff006e';
    ctx.fill();

    // Блик
    ctx.shadowBlur = 5 / zoom;
    ctx.beginPath();
    ctx.arc(pointX - pointSize * 0.15, pointY - pointSize * 0.15, highlightSize, 0, Math.PI * 2);
    ctx.fillStyle = 'white';
    ctx.fill();

    ctx.restore();
});

        ctx.restore();
        updateZoomIndicator();

    } catch (error) {
        console.error('Ошибка при отрисовке:', error);
    } finally {
        isRendering = false;
    }
}

// Функция для принудительного обновления отображения маски
async function forceUpdateMaskDisplay() {
    if (!currentImage) return;

    // Сбрасываем кэш для текущей временной маски
    if (window.currentTempMask) {
        // Удаляем из кэша, чтобы загрузить заново
        delete window.maskImageCache[window.currentTempMask];
    }

    await renderCanvas();
}
    // Исправленная функция обработки кликов по canvas
   function handleCanvasClick(e) {
    if (!currentImage) return;

    // Игнорируем клики правой кнопкой (они используются для перемещения)
    if (e.button === 2) {
        e.preventDefault();
        return;
    }

    // В режиме руки игнорируем клики левой кнопкой (только перетаскивание)
    if (currentTool === 'hand') {
        return;
    }

    // В режиме точек обрабатываем клики левой кнопкой как добавление точек
    const rect = canvas.getBoundingClientRect();

    // Получаем координаты клика относительно canvas
    const canvasX = e.clientX - rect.left;
    const canvasY = e.clientY - rect.top;

    // Преобразуем координаты canvas в координаты изображения
    const transformedX = (canvasX - canvas.width / 2) / zoom - offsetX;
    const transformedY = (canvasY - canvas.height / 2) / zoom - offsetY;

    // Затем преобразуем в координаты изображения
    const imgX = transformedX + currentImage.width / 2;
    const imgY = transformedY + currentImage.height / 2;

    // Проверяем, что клик внутри изображения
    if (imgX >= 0 && imgX < currentImage.width &&
        imgY >= 0 && imgY < currentImage.height) {

        points.push({
            x: imgX,
            y: imgY,
            type: pointType
        });

        updatePointsList();
        renderCanvas();

        document.getElementById('undo-btn').disabled = false;
        document.getElementById('complete-btn').disabled = false;
    }
}

    // Исправленная функция для начала перетаскивания
   function startDrag(e) {
    if (!currentImage) return;

    // Проверяем, что нажата правая кнопка мыши (button === 2)
    // Или левая кнопка в режиме руки, или с зажатым модификатором
    const isRightButton = e.button === 2;

    if (isRightButton) {
        // Правая кнопка всегда включает режим перемещения
        e.preventDefault(); // Предотвращаем появление контекстного меню
        isDragging = true;
        dragMode = 'right'; // Запоминаем, что тащим правой кнопкой
    }
    // Левая кнопка работает в зависимости от режима
    else if (currentTool === 'hand' || e.ctrlKey || e.shiftKey) {
        isDragging = true;
        dragMode = 'left';
    } else {
        return; // В режиме точек без модификатора не начинаем перетаскивание
    }

    // Сохраняем начальную позицию мыши в координатах canvas
    const rect = canvas.getBoundingClientRect();
    dragStartX = e.clientX - rect.left;
    dragStartY = e.clientY - rect.top;

    // Сохраняем текущие offset для последующего расчета
    dragOffsetX = offsetX;
    dragOffsetY = offsetY;

    // Добавляем класс для изменения курсора
    canvas.style.cursor = 'grabbing';
    canvas.parentElement.classList.add('dragging');
}

    function blockContextMenu(e) {
    // Блокируем для всех типов кликов (левая, правая, средняя кнопка)
    e.preventDefault();
    e.stopPropagation();
    return false;
}
    // Исправленная функция для перетаскивания
    function handleDrag(e) {
    if (!isDragging || !currentImage) return;

    e.preventDefault(); // Предотвращаем выделение текста и другие действия

    const rect = canvas.getBoundingClientRect();
    const currentX = e.clientX - rect.left;
    const currentY = e.clientY - rect.top;

    // Вычисляем смещение мыши в пикселях canvas
    const dx = currentX - dragStartX;
    const dy = currentY - dragStartY;

    // Преобразуем смещение в координаты изображения с учетом текущего зума
    offsetX = dragOffsetX + dx / zoom;
    offsetY = dragOffsetY + dy / zoom;

    renderCanvas();
}

    function stopDrag(e) {
    if (!isDragging) return;

    isDragging = false;
    dragMode = null;

    // Возвращаем курсор в зависимости от текущего инструмента
    if (currentTool === 'hand') {
        canvas.style.cursor = 'grab';
    } else {
        canvas.style.cursor = 'crosshair';
    }
    canvas.parentElement.classList.remove('dragging');
}
function setTool(tool) {
    currentTool = tool;

    // Обновляем стили кнопок
    document.getElementById('tool-hand-btn').classList.toggle('active', tool === 'hand');
    document.getElementById('tool-point-btn').classList.toggle('active', tool === 'point');

    // Меняем курсор в зависимости от инструмента
    if (canvas) {
        if (tool === 'hand') {
            canvas.style.cursor = 'grab';
        } else {
            canvas.style.cursor = 'crosshair';
        }
    }

    showToast('Информация', `Режим: ${tool === 'hand' ? 'перемещение' : 'разметка точками'}`, 'info', 1500);
}
    // Исправленная функция для зума
    function handleZoom(e) {
        if (!currentImage) return;

        e.preventDefault();

        const rect = canvas.getBoundingClientRect();

        // Получаем позицию курсора относительно canvas
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;

        // Преобразуем позицию курсора в координаты изображения до зума
        const worldX = (mouseX - canvas.width / 2) / zoom - offsetX;
        const worldY = (mouseY - canvas.height / 2) / zoom - offsetY;

        // Изменяем зум
        const zoomFactor = 0.1;
        if (e.deltaY < 0) {
            zoom *= (1 + zoomFactor);
        } else {
            zoom /= (1 + zoomFactor);
        }
        zoom = Math.max(0.1, Math.min(10, zoom));

        // Вычисляем новые offset так, чтобы точка под курсором осталась на месте
        offsetX = (mouseX - canvas.width / 2) / zoom - worldX;
        offsetY = (mouseY - canvas.height / 2) / zoom - worldY;

        renderCanvas();
    }

    // Исправленная функция zoomIn
    function zoomIn() {
        if (!currentImage) return;

        // Центр canvas
        const centerX = canvas.width / 2;
        const centerY = canvas.height / 2;

        // Точка в центре в координатах изображения
        const worldX = (centerX - canvas.width / 2) / zoom - offsetX;
        const worldY = (centerY - canvas.height / 2) / zoom - offsetY;

        // Увеличиваем зум
        zoom *= 1.2;
        zoom = Math.min(10, zoom);

        // Корректируем offset, чтобы центр оставался на месте
        offsetX = (centerX - canvas.width / 2) / zoom - worldX;
        offsetY = (centerY - canvas.height / 2) / zoom - worldY;

        renderCanvas();
    }

    // Исправленная функция zoomOut
    function zoomOut() {
        if (!currentImage) return;

        // Центр canvas
        const centerX = canvas.width / 2;
        const centerY = canvas.height / 2;

        // Точка в центре в координатах изображения
        const worldX = (centerX - canvas.width / 2) / zoom - offsetX;
        const worldY = (centerY - canvas.height / 2) / zoom - offsetY;

        // Уменьшаем зум
        zoom /= 1.2;
        zoom = Math.max(0.1, zoom);

        // Корректируем offset, чтобы центр оставался на месте
        offsetX = (centerX - canvas.width / 2) / zoom - worldX;
        offsetY = (centerY - canvas.height / 2) / zoom - worldY;

        renderCanvas();
    }

    // Исправленная функция сброса вида
    function resetView() {
        if (!currentImage) return;

        zoom = 1;
        offsetX = 0;
        offsetY = 0;
        renderCanvas();

        showToast('Информация', 'Вид сброшен', 'info');
    }

    // Изменение размера canvas
    function resizeCanvas() {
    if (!canvas) return;

    const container = canvas.parentElement;
    const oldWidth = canvas.width;
    const oldHeight = canvas.height;

    canvas.width = container.clientWidth;
    canvas.height = container.clientHeight;

    // Если есть изображение и размеры контейнера изменились,
    // пересчитываем масштаб для оптимального отображения
    if (currentImage && (oldWidth !== canvas.width || oldHeight !== canvas.height)) {
        // Сохраняем текущий относительный центр изображения
        if (zoom > 0) {
            // Пересчитываем масштаб для нового размера контейнера
            const scaleX = canvas.width / currentImage.width;
            const scaleY = canvas.height / currentImage.height;

            // Если изображение было вписано полностью (zoom < 1), пересчитываем
            if (zoom < 1) {
                zoom = Math.min(scaleX, scaleY) * 0.95;
            }
            // Если было увеличено, сохраняем масштаб
        }

        renderCanvas();
    } else if (currentImage) {
        renderCanvas();
    }
}

    // Функции для работы с площадью
    function updateAreaDisplay(area) {
        const areaInfo = document.getElementById('area-info');
        const areaValue = document.getElementById('area-value');

        if (area > 0) {
            areaInfo.style.display = 'block';
            areaValue.textContent = area.toLocaleString();

            // Добавляем анимацию обновления
            areaValue.classList.add('updated');
            setTimeout(() => {
                areaValue.classList.remove('updated');
            }, 300);
        } else {
            areaInfo.style.display = 'none';
            areaValue.textContent = '0';
        }
    }

    function clearAreaDisplay() {
        currentMaskImageData = null;
        currentMaskArea = 0;
        updateAreaDisplay(0);
    }

    async function calculateMaskAreaFromImage(maskImage) {
        return new Promise((resolve, reject) => {
            try {
                // Создаем временный canvas для анализа маски
                const tempCanvas = document.createElement('canvas');
                tempCanvas.width = maskImage.width;
                tempCanvas.height = maskImage.height;
                const tempCtx = tempCanvas.getContext('2d');

                // Рисуем маску на canvas
                tempCtx.drawImage(maskImage, 0, 0, maskImage.width, maskImage.height);

                // Получаем данные пикселей
                const imageData = tempCtx.getImageData(0, 0, maskImage.width, maskImage.height);
                const data = imageData.data;

                // Подсчитываем количество пикселей в маске
                let area = 0;
                for (let i = 0; i < data.length; i += 4) {
                    // Проверяем, является ли пиксель частью маски (яркий пиксель)
                    if (data[i] > 200 || data[i + 1] > 200 || data[i + 2] > 200) {
                        area++;
                    }
                }

                resolve(area);
            } catch (error) {
                console.error('Ошибка вычисления площади:', error);
                reject(error);
            }
        });
    }

    function addAreaToResult(area, imageName, maskIndex = 0) {
        const resultsGrid = document.getElementById('results-grid');
        if (resultsGrid) {
            // Ищем результат с соответствующим именем и индексом маски
            const resultItems = resultsGrid.querySelectorAll('.result-item');
            let foundItem = null;

            for (let item of resultItems) {
                const nameDiv = item.querySelector('.result-name');
                const maskIndexEl = item.querySelector('.result-mask-index');
                const itemMaskIndex = maskIndexEl ? parseInt(maskIndexEl.textContent) : 0;

                if (nameDiv && nameDiv.textContent.includes(imageName) && itemMaskIndex === maskIndex) {
                    foundItem = item;
                    break;
                }
            }

            if (foundItem) {
                // Обновляем или создаем бейдж с площадью
                let areaBadge = foundItem.querySelector('.result-area-badge');
                if (!areaBadge) {
                    areaBadge = document.createElement('div');
                    areaBadge.className = 'result-area-badge';
                    areaBadge.innerHTML = `
                        <i class="fas fa-vector-square"></i>
                        <span class="area-value">0</span>
                        <span class="area-unit">px²</span>
                    `;
                    foundItem.appendChild(areaBadge);
                }

                const areaValue = areaBadge.querySelector('.area-value');
                areaValue.textContent = area.toLocaleString('ru-RU');
                areaBadge.style.display = 'flex';
                areaBadge.title = `Точная площадь: ${area} пикселей`;
            }
        }
    }

    // ИСПРАВЛЕННАЯ функция создания маски - маска появляется сразу
    async function generateMask() {
    if (points.length === 0) {
        showToast('Ошибка', 'Добавьте точки для сегментации', 'error');
        return;
    }

    if (!currentSessionId) {
        showToast('Ошибка', 'Сессия не найдена. Пожалуйста, загрузите изображение заново.', 'error');
        return;
    }

    console.log('Current session ID:', currentSessionId);
    console.log('Points:', points);

    showLoading('Создание маски...');

    // Подготавливаем данные в формате, который ожидает сервер
    const pointsArray = points.map(p => [p.x, p.y]);
    const labelsArray = points.map(p => p.type === 'positive' ? 1 : 0);

    const payload = {
        session_id: currentSessionId,
        points: pointsArray,
        labels: labelsArray
    };

    console.log('Sending to server:', JSON.stringify(payload, null, 2));

    try {
        const response = await fetch('/sam2/set_points', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        console.log('Response status:', response.status);

        const responseText = await response.text();
        console.log('Response text:', responseText);

        let data;
        try {
            data = JSON.parse(responseText);
        } catch (e) {
            console.error('Failed to parse JSON:', e);
            throw new Error('Сервер вернул некорректный ответ: ' + responseText.substring(0, 100));
        }

        if (response.ok && data.success) {
            // Сохраняем маску во временное хранилище и сразу отображаем
            if (data.mask_image) {
                window.currentTempMask = data.mask_image;

                // Удаляем из кэша, если там была старая версия
                if (window.maskImageCache) {
                    delete window.maskImageCache[data.mask_image];
                }

                // Принудительно перерисовываем canvas
                await forceUpdateMaskDisplay();

                showToast('Успех', 'Маска создана. Нажмите "Завершить маску" для сохранения.', 'success');

                // Активируем кнопку завершения
                document.getElementById('complete-btn').disabled = false;
                document.getElementById('propagate-btn').disabled = false;
            }
        } else {
            throw new Error(data.error || `Ошибка ${response.status}: ${responseText}`);
        }
    } catch (error) {
        console.error('Generate mask error:', error);
        showToast('Ошибка', error.message, 'error');
    } finally {
        hideLoading();
    }
}

    // ИСПРАВЛЕННАЯ функция для завершения маски (сохранение текущей маски)
   async function completeMask() {
    if (!window.currentTempMask) {
        showToast('Ошибка', 'Сначала создайте маску', 'error');
        return;
    }

    const currentImageName = images[currentImageIndex].name;

    // Инициализируем хранилище для этого изображения, если нужно
    if (!window.multiMasks[currentImageName]) {
        window.multiMasks[currentImageName] = [];
    }

    // Определяем цвет для новой маски
    const maskColor = maskColors[window.multiMasks[currentImageName].length % maskColors.length];

    // СОЗДАЕМ БИНАРНУЮ (ЧЕРНО-БЕЛУЮ) МАСКУ СРАЗУ
    const binaryMaskDataUrl = await createBinaryMask(window.currentTempMask);

    // ★★★ ВЫЧИСЛЯЕМ ПЛОЩАДЬ МАСКИ В ПИКСЕЛЯХ ★★★
    const pixelArea = await calculateMaskAreaFromDataUrl(window.currentTempMask);

    // ★★★ ПОЛУЧАЕМ ТЕКУЩИЕ НАСТРОЙКИ GSD ★★★
    const gsdHeight = parseFloat(document.getElementById('gsd-height-input')?.value) || 100;
    const gsdSensor = parseFloat(document.getElementById('gsd-sensor-input')?.value) || 0.0024;
    const gsdFocal = parseFloat(document.getElementById('gsd-focal-input')?.value) || 8;
    const gsdUnit = document.getElementById('gsd-unit-select')?.value || 'm2';

    // ★★★ РАССЧИТЫВАЕМ РЕАЛЬНУЮ ПЛОЩАДЬ ★★★
    const gsd = (gsdHeight * gsdSensor) / gsdFocal;
    const pixelAreaM2 = Math.pow(gsd, 2);
    let realArea = pixelArea * pixelAreaM2;

    // Конвертируем в выбранную единицу
    let formattedArea = '';
    switch (gsdUnit) {
        case 'ha':
            realArea = realArea / 10000;
            formattedArea = realArea.toLocaleString('ru-RU', { minimumFractionDigits: 4, maximumFractionDigits: 4 }) + ' га';
            break;
        case 'km2':
            realArea = realArea / 1000000;
            formattedArea = realArea.toLocaleString('ru-RU', { minimumFractionDigits: 6, maximumFractionDigits: 6 }) + ' км²';
            break;
        default:
            formattedArea = realArea.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' м²';
    }

    // Сохраняем маски
    const maskData = {
        dataUrl: window.currentTempMask,           // Цветная маска (для отображения)
        binaryDataUrl: binaryMaskDataUrl,          // Бинарная маска (для скачивания)
        color: maskColor,
        index: window.multiMasks[currentImageName].length,
        points: [...points],
        pixelArea: pixelArea,                       // ★★★ ПЛОЩАДЬ В ПИКСЕЛЯХ ★★★
        realArea: realArea,                         // ★★★ РЕАЛЬНАЯ ПЛОЩАДЬ ★★★
        formattedArea: formattedArea,               // ★★★ ФОРМАТИРОВАННАЯ СТРОКА ★★★
        gsdSettings: {
            height: gsdHeight,
            sensorPixel: gsdSensor,
            focal: gsdFocal,
            unit: gsdUnit
        },
        createdAt: new Date().toISOString()
    };

    const calcBtn = document.getElementById('calc-area-btn');
    if (calcBtn) calcBtn.disabled = false;

    window.multiMasks[currentImageName].push(maskData);

    // Обновляем отображение в результатах
    updateResultsWithAllMasks();

    // Очищаем временную маску
    window.currentTempMask = null;

    // Очищаем точки для следующей маски
    points = [];
    updatePointsList();

    // Перерисовываем canvas со всеми сохраненными масками
    await renderCanvas();

    // Деактивируем кнопки
    document.getElementById('undo-btn').disabled = true;
    document.getElementById('complete-btn').disabled = true;

    showToast('Успех',
        `Маска #${window.multiMasks[currentImageName].length} сохранена. Площадь: ${formattedArea} (${pixelArea.toLocaleString()} px²)`,
        'success'
    );
}
// Функция расчета реальной площади по GSD
function calculateRealArea(pixelArea, gsdSettings) {
    const { height, sensorPixel, focal, unit } = gsdSettings;

    // Расчет GSD в метрах на пиксель
    const gsd = (height * sensorPixel) / focal;

    // Площадь одного пикселя в м²
    const pixelAreaM2 = Math.pow(gsd, 2);

    // Итоговая площадь в м²
    let areaM2 = pixelArea * pixelAreaM2;

    // Конвертация в нужную единицу
    switch (unit) {
        case 'ha':
            return areaM2 / 10000;
        case 'km2':
            return areaM2 / 1000000;
        default:
            return areaM2;
    }
}

// Функция форматирования площади с единицей измерения
function formatAreaWithUnit(area, unit) {
    let formattedValue;

    switch (unit) {
        case 'ha':
            formattedValue = area.toLocaleString('ru-RU', {
                minimumFractionDigits: 4,
                maximumFractionDigits: 4
            });
            return `${formattedValue} га`;
        case 'km2':
            formattedValue = area.toLocaleString('ru-RU', {
                minimumFractionDigits: 6,
                maximumFractionDigits: 6
            });
            return `${formattedValue} км²`;
        default:
            // Для м²
            if (area >= 10000) {
                formattedValue = area.toLocaleString('ru-RU', {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2
                });
            } else if (area >= 1) {
                formattedValue = area.toLocaleString('ru-RU', {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2
                });
            } else {
                formattedValue = area.toLocaleString('ru-RU', {
                    minimumFractionDigits: 4,
                    maximumFractionDigits: 4
                });
            }
            return `${formattedValue} м²`;
    }
}

// Функция обновления площади для существующей маски по новым GSD параметрам
function updateMaskAreaWithGSD(imageName, maskIndex, gsdSettings) {
    if (!window.multiMasks[imageName] || !window.multiMasks[imageName][maskIndex]) {
        return false;
    }

    const mask = window.multiMasks[imageName][maskIndex];
    const pixelArea = mask.pixelArea || 0;

    if (pixelArea === 0) return false;

    // Пересчитываем реальную площадь
    const realArea = calculateRealArea(pixelArea, gsdSettings);
    const formattedArea = formatAreaWithUnit(realArea, gsdSettings.unit);

    // Обновляем данные маски
    mask.realArea = realArea;
    mask.areaUnit = gsdSettings.unit;
    mask.formattedArea = formattedArea;
    mask.gsdSettings = { ...gsdSettings };

    return true;
}
// Вспомогательная функция для вычисления площади из dataUrl
async function calculateMaskAreaFromDataUrl(dataUrl) {
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => {
            // Создаем canvas для анализа
            const canvas = document.createElement('canvas');
            canvas.width = img.width;
            canvas.height = img.height;
            const ctx = canvas.getContext('2d');

            ctx.drawImage(img, 0, 0);

            const imageData = ctx.getImageData(0, 0, img.width, img.height);
            const data = imageData.data;

            let area = 0;
            for (let i = 0; i < data.length; i += 4) {
                // Проверяем, является ли пиксель частью маски (яркий пиксель)
                if (data[i] > 200 || data[i+1] > 200 || data[i+2] > 200) {
                    area++;
                }
            }

            resolve(area);
        };
        img.onerror = () => {
            reject(new Error('Не удалось загрузить маску для вычисления площади'));
        };
        img.src = dataUrl;
    });
}
// Функция для создания бинарной маски из цветной
async function createBinaryMask(colorMaskDataUrl) {
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => {
            // Создаем canvas для обработки
            const canvas = document.createElement('canvas');
            canvas.width = img.width;
            canvas.height = img.height;
            const ctx = canvas.getContext('2d');

            // Рисуем исходную маску
            ctx.drawImage(img, 0, 0, img.width, img.height);

            // Получаем данные пикселей
            const imageData = ctx.getImageData(0, 0, img.width, img.height);
            const data = imageData.data;

            // Конвертируем в черно-белое (бинарное) изображение
            for (let i = 0; i < data.length; i += 4) {
                // Проверяем, является ли пиксель частью маски
                const isMaskPixel = data[i] > 200 || data[i+1] > 200 || data[i+2] > 200;

                if (isMaskPixel) {
                    // Белый цвет для маски
                    data[i] = 255;     // R
                    data[i+1] = 255;   // G
                    data[i+2] = 255;   // B
                    data[i+3] = 255;   // A - полностью непрозрачный
                } else {
                    // Черный цвет для фона
                    data[i] = 0;       // R
                    data[i+1] = 0;     // G
                    data[i+2] = 0;     // B
                    data[i+3] = 255;   // A - полностью непрозрачный
                }
            }

            // Обновляем canvas с бинарным изображением
            ctx.putImageData(imageData, 0, 0);

            // Конвертируем в data URL
            const binaryMaskDataUrl = canvas.toDataURL('image/png');
            resolve(binaryMaskDataUrl);
        };

        img.onerror = () => {
            console.error('Ошибка создания бинарной маски');
            reject(new Error('Не удалось создать бинарную маску'));
        };

        img.src = colorMaskDataUrl;
    });
}

    // Обновленная функция для отображения всех масок из multiMasks
// Обновленная функция для отображения всех масок из multiMasks
function updateResultsWithAllMasks() {
    const resultsGrid = document.getElementById('results-grid');
    if (!resultsGrid) return;

    resultsGrid.innerHTML = '';

    const modalImages = [];

    Object.keys(window.multiMasks).forEach(imageName => {
        const masks = window.multiMasks[imageName];

        if (!masks || masks.length === 0) return;

        masks.forEach((mask, maskIndex) => {
            const maskId = `${imageName}_mask_${maskIndex + 1}`;

            const div = document.createElement('div');
            div.className = 'result-item';
            div.setAttribute('data-image', imageName);
            div.setAttribute('data-mask-index', maskIndex);

            const badgeColor = mask.color || maskColors[maskIndex % maskColors.length];

            // ★★★ ПОЛУЧАЕМ ФОРМАТИРОВАННУЮ ПЛОЩАДЬ ★★★
            // Если есть реальная площадь - показываем её, иначе показываем пиксели
            let areaDisplayText = '';
            let areaTitle = '';

            if (mask.realArea !== undefined && mask.formattedArea) {
                areaDisplayText = mask.formattedArea;
                areaTitle = `Площадь: ${areaDisplayText} | В пикселях: ${(mask.pixelArea || 0).toLocaleString()} px²`;
            } else if (mask.pixelArea) {
                areaDisplayText = `${mask.pixelArea.toLocaleString()} px²`;
                areaTitle = `Площадь в пикселях: ${mask.pixelArea.toLocaleString()} px²`;
            } else {
                areaDisplayText = 'Вычисляется...';
                areaTitle = 'Площадь не вычислена';
            }

            div.innerHTML = `
                <img src="${mask.dataUrl}" class="result-thumb" alt="${imageName} - маска ${maskIndex + 1}">
                <div class="result-name">${imageName} (маска ${maskIndex + 1})${mask.propagated ? ' 🔄' : ''}</div>
                <div class="result-mask-index" style="display: none;">${maskIndex}</div>
                <div class="result-area-badge" style="display: flex; border-left: 4px solid ${badgeColor}" title="${areaTitle}">
                    <i class="fas fa-vector-square"></i>
                    <span class="area-value">${areaDisplayText}</span>
                </div>
                <button class="result-delete-btn" onclick="deleteResultItem(this)" title="Удалить">
                    <i class="fas fa-times"></i>
                </button>
            `;

            resultsGrid.appendChild(div);

            // Если нет реальной площади, но есть пиксельная - пытаемся пересчитать
            if (mask.pixelArea && !mask.realArea) {
                // Пытаемся пересчитать с текущими GSD настройками
                const currentGSDSettings = {
                    height: parseFloat(document.getElementById('gsd-height-input')?.value) || defaultGSDSettings.height,
                    sensorPixel: parseFloat(document.getElementById('gsd-sensor-input')?.value) || defaultGSDSettings.sensorPixel,
                    focal: parseFloat(document.getElementById('gsd-focal-input')?.value) || defaultGSDSettings.focal,
                    unit: document.getElementById('gsd-unit-select')?.value || defaultGSDSettings.unit
                };

                const realArea = calculateRealArea(mask.pixelArea, currentGSDSettings);
                const formattedArea = formatAreaWithUnit(realArea, currentGSDSettings.unit);

                mask.realArea = realArea;
                mask.areaUnit = currentGSDSettings.unit;
                mask.formattedArea = formattedArea;
                mask.gsdSettings = { ...currentGSDSettings };

                // Обновляем отображение
                const areaBadge = div.querySelector('.result-area-badge');
                const areaValueSpan = areaBadge.querySelector('.area-value');
                areaValueSpan.textContent = formattedArea;
                areaBadge.title = `Площадь: ${formattedArea} | В пикселях: ${mask.pixelArea.toLocaleString()} px²`;
            }

            // Добавляем в массив для модального окна
            modalImages.push({
                src: mask.dataUrl,
                name: `${imageName} (маска ${maskIndex + 1})${mask.propagated ? ' - распространенная' : ''}`,
                area: mask.formattedArea || (mask.pixelArea ? `${mask.pixelArea.toLocaleString()} px²` : 'Вычисляется...')
            });
        });
    });

    // Добавляем обработчики кликов
    setTimeout(() => {
        const resultItems = resultsGrid.querySelectorAll('.result-item');
        resultItems.forEach((item) => {
            if (item.clickHandler) {
                item.removeEventListener('click', item.clickHandler);
            }

            item.clickHandler = function(e) {
                if (!e.target.closest('.result-delete-btn') && !e.target.closest('.result-area-badge')) {
                    const img = this.querySelector('.result-thumb');
                    const name = this.querySelector('.result-name').textContent;
                    const areaBadge = this.querySelector('.area-value');
                    const area = areaBadge ? areaBadge.textContent : '0';

                    openImageModal(
                        img.src,
                        name,
                        area,
                        modalImages.length > 0 ? modalImages : null
                    );
                }
            };

            item.addEventListener('click', item.clickHandler);
        });
    }, 100);

    if (resultsGrid.children.length > 0) {
        document.getElementById('results-panel').style.display = 'block';
    } else {
        document.getElementById('results-panel').style.display = 'none';
    }
}

    // Распространение масок - доступно всем
    // Исправленная функция распространения масок с сохранением в multiMasks
async function propagateMasks() {
    if (!currentSessionId) {
        showToast('Ошибка', 'Сессия не найдена', 'error');
        return;
    }

    showLoading('Распространение масок...', true);

    const payload = {
        session_id: currentSessionId
    };

    try {
        let response = await fetch('/propagate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (response.status === 400) {
            response = await fetch('/sam2/propagate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
        }

        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            const text = await response.text();
            throw new Error('Сервер вернул некорректный ответ');
        }

        const data = await response.json();

        if (data.success) {
            if (!window.multiMasks) window.multiMasks = {};

            const imageNames = Object.keys(data.visualizations);

            // ★★★ ПОЛУЧАЕМ ТЕКУЩИЕ GSD НАСТРОЙКИ ★★★
            const currentGSDSettings = {
                height: parseFloat(document.getElementById('gsd-height-input')?.value) || 100,
                sensorPixel: parseFloat(document.getElementById('gsd-sensor-input')?.value) || 0.0024,
                focal: parseFloat(document.getElementById('gsd-focal-input')?.value) || 8,
                unit: document.getElementById('gsd-unit-select')?.value || 'm2'
            };

            for (let i = 0; i < imageNames.length; i++) {
                const imageName = imageNames[i];
                const maskDataUrl = data.visualizations[imageName];

                if (!window.multiMasks[imageName]) {
                    window.multiMasks[imageName] = [];
                }

                const maskColor = maskColors[window.multiMasks[imageName].length % maskColors.length];

                try {
                    const maskResponse = await fetch(maskDataUrl);
                    const colorMaskBlob = await maskResponse.blob();

                    const binaryMaskBlob = await convertToBinaryMask(colorMaskBlob);
                    const binaryMaskDataUrl = URL.createObjectURL(binaryMaskBlob);

                    // ★★★ ВЫЧИСЛЯЕМ ПЛОЩАДЬ В ПИКСЕЛЯХ ★★★
                    const pixelArea = await calculateMaskAreaFromBlob(binaryMaskBlob);

                    // ★★★ РАССЧИТЫВАЕМ РЕАЛЬНУЮ ПЛОЩАДЬ ★★★
                    const realArea = calculateRealArea(pixelArea, currentGSDSettings);
                    const formattedArea = formatAreaWithUnit(realArea, currentGSDSettings.unit);

                    const maskData = {
                        dataUrl: maskDataUrl,
                        binaryDataUrl: binaryMaskDataUrl,
                        color: maskColor,
                        index: window.multiMasks[imageName].length,
                        propagated: true,
                        points: [],
                        pixelArea: pixelArea,                       // ★★★ ПЛОЩАДЬ В ПИКСЕЛЯХ ★★★
                        realArea: realArea,                         // ★★★ РЕАЛЬНАЯ ПЛОЩАДЬ ★★★
                        formattedArea: formattedArea,               // ★★★ ФОРМАТИРОВАННАЯ СТРОКА ★★★
                        gsdSettings: { ...currentGSDSettings },     // ★★★ СОХРАНЯЕМ ПАРАМЕТРЫ GSD ★★★
                        createdAt: new Date().toISOString()
                    };

                    window.multiMasks[imageName].push(maskData);

                    console.log(`Маска для "${imageName}" сохранена. Площадь: ${formattedArea} (${pixelArea} px²)`);

                } catch (maskError) {
                    console.error(`Ошибка при обработке маски для ${imageName}:`, maskError);

                    // В случае ошибки сохраняем хотя бы цветную маску
                    const maskData = {
                        dataUrl: maskDataUrl,
                        binaryDataUrl: null,
                        color: maskColor,
                        index: window.multiMasks[imageName].length,
                        propagated: true,
                        points: [],
                        pixelArea: 0,
                        realArea: 0,
                        formattedArea: 'Ошибка',
                        error: true,
                        createdAt: new Date().toISOString()
                    };
                    window.multiMasks[imageName].push(maskData);
                }
            }

            // ★★★ АКТИВИРУЕМ КНОПКУ "РАСЧЕТ ПЛОЩАДИ" ★★★
            const calcAreaBtn = document.getElementById('calc-area-btn');
            if (calcAreaBtn) {
                calcAreaBtn.disabled = false;
            }

            // Обновляем отображение результатов
            updateResultsWithAllMasks();

            const currentImageName = images[currentImageIndex]?.name || allUploadedImages[currentImageIndex]?.name;
            if (currentImageName && window.multiMasks[currentImageName] && window.multiMasks[currentImageName].length > 0) {
                currentMask = true;
                await renderCanvas();
            }

            const totalMasks = Object.values(window.multiMasks).reduce((sum, masks) => sum + masks.length, 0);
            showToast('Успех',
                `Распространение завершено! Создано масок: ${totalMasks} для ${Object.keys(window.multiMasks).length} изображений`,
                'success'
            );

        } else {
            throw new Error(data.error || 'Ошибка распространения');
        }
    } catch (error) {
        console.error('Propagate masks error:', error);
        showToast('Ошибка', error.message, 'error');
    } finally {
        hideLoading();
    }
}

    // Утилиты
    function setPointType(type) {
        pointType = type;
        document.querySelectorAll('.point-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`.point-btn.${type}`).classList.add('active');
    }

    function undoLastPoint() {
        if (points.length > 0) {
            points.pop();
            updatePointsList();
            renderCanvas();
            document.getElementById('undo-btn').disabled = points.length === 0;
            document.getElementById('complete-btn').disabled = points.length === 0;
        }
    }

    function clearPoints() {
        points = [];
        currentMask = false;
        window.currentMaskImage = null;
        window.currentTempMask = null;
        currentMaskArea = 0;
        updateAreaDisplay(0);
        updatePointsList();
        renderCanvas();
        document.getElementById('undo-btn').disabled = true;
        document.getElementById('generate-btn').disabled = false;
        document.getElementById('propagate-btn').disabled = true;
        document.getElementById('complete-btn').disabled = true;
    }

    function updatePointsList() {
        const container = document.getElementById('points-list');
        const countElement = document.getElementById('points-count');

        container.innerHTML = '';
        points.forEach((point, index) => {
            const div = document.createElement('div');
            div.className = 'point-item';
            div.innerHTML = `
                <div class="point-marker ${point.type}"></div>
                <div class="point-coords">(${Math.round(point.x)}, ${Math.round(point.y)})</div>
                <div class="point-remove" onclick="removePoint(${index})">
                    <i class="fas fa-times"></i>
                </div>
            `;
            container.appendChild(div);
        });

        countElement.textContent = points.length;
        document.getElementById('points-container').style.display = points.length > 0 ? 'block' : 'none';
    }
    function getImageDimensions(dataUrl) {
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => resolve({
            width: img.width,
            height: img.height
        });
        img.onerror = reject;
        img.src = dataUrl;
    });
}
    function removePoint(index) {
        points.splice(index, 1);
        updatePointsList();
        renderCanvas();
        document.getElementById('undo-btn').disabled = points.length === 0;
        document.getElementById('complete-btn').disabled = points.length === 0;
    }

    function showImageList() {
    const container = document.getElementById('image-list');
    const countElement = document.getElementById('image-count');

    container.innerHTML = '';

    // Используем allUploadedImages вместо images
    allUploadedImages.forEach((img, index) => {
        const div = document.createElement('div');
        div.className = `image-item ${index === currentImageIndex ? 'active' : ''}`;
        div.onclick = () => loadImageFromArray(index);
        div.innerHTML = `
            <img src="${img.thumb}" class="image-thumb" alt="${img.name}">
            <div class="image-name">${img.name}</div>
        `;
        container.appendChild(div);
    });

    countElement.textContent = allUploadedImages.length;
    document.getElementById('image-list-container').style.display = allUploadedImages.length > 0 ? 'block' : 'none';
}
function loadImageFromArray(index) {
    if (!allUploadedImages[index]) return;

    const img = new Image();
    img.onload = () => {
        currentImage = img;

        // Обновляем images для обратной совместимости
        images = {};
        let idx = 0;
        allUploadedImages.forEach(imgData => {
            images[idx] = {
                name: imgData.name,
                dataUrl: imgData.dataUrl,
                thumb: imgData.thumb
            };
            idx++;
        });

        currentImageIndex = index;

        // Загружаем сохраненные маски для этого изображения
        const imageName = allUploadedImages[index].name;
        if (window.multiMasks && window.multiMasks[imageName] && window.multiMasks[imageName].length > 0) {
            currentMask = true;
        } else {
            currentMask = false;
            window.currentMaskImage = null;
            window.currentTempMask = null;
            currentMaskArea = 0;
            updateAreaDisplay(0);
        }

        // Вычисляем оптимальный масштаб
        resizeCanvas();

        // Сбрасываем позицию
        offsetX = 0;
        offsetY = 0;

        // Вычисляем масштаб, чтобы изображение вписалось в canvas
        const containerWidth = canvas.width;
        const containerHeight = canvas.height;
        const scaleX = containerWidth / img.width;
        const scaleY = containerHeight / img.height;
        zoom = Math.min(scaleX, scaleY) * 0.95;

        renderCanvas();

        updateImageSelection(index);
        updateImageInfo();

        // Показываем canvas
        document.getElementById('main-canvas').style.display = 'block';
        document.getElementById('no-image-message').style.display = 'none';
        document.querySelector('.canvas-controls').style.display = 'flex';
        document.querySelector('.point-type-selector').style.display = 'flex';

        const zoomIndicator = document.getElementById('zoom-indicator');
        if (zoomIndicator) zoomIndicator.style.display = 'flex';

        document.getElementById('generate-btn').disabled = false;
        document.getElementById('image-info').style.display = 'block';
        document.getElementById('complete-btn').disabled = points.length === 0;
    };

    img.onerror = () => {
        console.error('Ошибка загрузки изображения:', allUploadedImages[index].name);
        showToast('Ошибка', 'Не удалось загрузить изображение', 'error');
    };

    img.src = allUploadedImages[index].dataUrl;
}
    function updateImageSelection(index) {
        document.querySelectorAll('.image-item').forEach(item => {
            item.classList.remove('active');
        });
        document.querySelectorAll('.image-item')[index]?.classList.add('active');
    }

    function showResults(visualizations) {
    const grid = document.getElementById('results-grid');
    grid.innerHTML = '';

    // Создаем массив данных для модального окна
    const modalImages = [];

    Object.keys(visualizations).forEach(key => {
        const div = document.createElement('div');
        div.className = 'result-item';
        div.setAttribute('data-image', key);
        div.setAttribute('data-mask-index', '0');

        // Создаем контейнер для информации о площади (будет заполнен позже)
        div.innerHTML = `
            <img src="${visualizations[key]}" class="result-thumb" alt="${key}">
            <div class="result-name">${key}</div>
            <div class="result-mask-index" style="display: none;">0</div>
            <div class="result-area-badge" style="display: none;">
                <i class="fas fa-vector-square"></i>
                <span class="area-value">0</span>
                <span class="area-unit">px²</span>
            </div>
        `;

        grid.appendChild(div);

        // Вычисляем площадь для этой маски асинхронно
        const img = new Image();
        img.onload = async () => {
            const area = await calculateMaskAreaFromImage(img);
            const areaBadge = div.querySelector('.result-area-badge');
            const areaValue = areaBadge.querySelector('.area-value');

            // Форматируем число с пробелами как разделителями
            areaValue.textContent = area.toLocaleString('ru-RU');
            areaBadge.style.display = 'flex';
            areaBadge.title = `Точная площадь: ${area} пикселей`;

            // Добавляем в массив для модального окна
            modalImages.push({
                src: visualizations[key],
                name: key,
                area: area.toLocaleString('ru-RU') + ' px²'
            });
        };
        img.src = visualizations[key];
    });

    // Добавляем обработчики кликов на все элементы результатов
    setTimeout(() => {
        const resultItems = grid.querySelectorAll('.result-item');
        resultItems.forEach((item, index) => {
            item.addEventListener('click', function(e) {
                // Проверяем, что клик не по бейджу (чтобы не конфликтовать)
                if (!e.target.closest('.result-area-badge')) {
                    const img = this.querySelector('.result-thumb');
                    const name = this.querySelector('.result-name').textContent;
                    const areaBadge = this.querySelector('.area-value');
                    const area = areaBadge ? areaBadge.textContent + ' px²' : '0 px²';

                    openImageModal(
                        img.src,
                        name,
                        area,
                        modalImages.length > 0 ? modalImages : null
                    );
                }
            });
        });
    }, 100);

    document.getElementById('results-panel').style.display = 'block';
}

    // Функция для извлечения маски по красному цвету из изображения
async function extractMaskByRedColor(imageBlob, originalFilename, maskIndex) {
   return new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => {
            // Создаем canvas для анализа
            const canvas = document.createElement('canvas');
            canvas.width = img.width;
            canvas.height = img.height;
            const ctx = canvas.getContext('2d');

            // Рисуем исходное изображение
            ctx.drawImage(img, 0, 0);

            // Получаем данные пикселей
            const imageData = ctx.getImageData(0, 0, img.width, img.height);
            const data = imageData.data;

            // Создаем бинарную маску (черно-белую)
            const maskCanvas = document.createElement('canvas');
            maskCanvas.width = img.width;
            maskCanvas.height = img.height;
            const maskCtx = maskCanvas.getContext('2d');
            const maskImageData = maskCtx.createImageData(img.width, img.height);
            const maskData = maskImageData.data;

            let redPixelCount = 0;

            // Строгое определение чистого красного цвета
            for (let i = 0; i < data.length; i += 4) {
                const r = data[i];
                const g = data[i+1];
                const b = data[i+2];
                const a = data[i+3];

                // Строго чистый красный цвет: R = 255, G = 0, B = 0
                // Допускаем небольшое отклонение для сглаживания, но строго по заданию
                const isPureRed = (r === 255 && g === 0 && b === 0);

                if (isPureRed) {
                    // Белый цвет для маски (область выделения)
                    maskData[i] = 255;     // R
                    maskData[i+1] = 255;   // G
                    maskData[i+2] = 255;   // B
                    maskData[i+3] = 255;   // A - непрозрачный
                    redPixelCount++;
                } else {
                    // Черный цвет для фона
                    maskData[i] = 0;       // R
                    maskData[i+1] = 0;     // G
                    maskData[i+2] = 0;     // B
                    maskData[i+3] = 255;   // A - непрозрачный
                }
            }

            // Применяем маску
            maskCtx.putImageData(maskImageData, 0, 0);

            // Конвертируем в PNG blob
            maskCanvas.toBlob((blob) => {
                console.log(`Маска #${maskIndex} извлечена. Найдено красных пикселей (255,0,0): ${redPixelCount}`);
                resolve({
                    blob: blob,
                    width: img.width,
                    height: img.height,
                    pixelCount: redPixelCount
                });
            }, 'image/png');
        };

        img.onerror = () => {
            reject(new Error(`Не удалось загрузить изображение: ${originalFilename}`));
        };

        img.src = URL.createObjectURL(imageBlob);
    });
}


async function downloadResults() {
    //const isGuest = {{ is_guest|tojson }};

    if (isGuest) {
        showToast('Авторизация', 'Для скачивания результатов необходимо авторизоваться', 'warning');
        return;
    }

    if (!window.multiMasks || Object.keys(window.multiMasks).length === 0) {
        showToast('Ошибка', 'Нет масок для скачивания', 'error');
        return;
    }

    let totalMasks = 0;
    for (const imageName in window.multiMasks) {
        totalMasks += window.multiMasks[imageName].length;
    }

    if (totalMasks === 0) {
        showToast('Ошибка', 'Нет масок для скачивания', 'error');
        return;
    }

    showLoading('Подготовка архива...');

    try {
        const zip = new JSZip();

        const originalsFolder = zip.folder("originals");
        const masksFolder = zip.folder("masks");
        const overlaysFolder = zip.folder("overlays");
        const metadataFolder = zip.folder("metadata");

        const metadataMap = new Map();

        function normalizeFilename(filename) {
            return filename.replace(/[\\/:*?"<>|]/g, '_');
        }

        function isSameImageName(name1, name2) {
            const name1WithoutExt = name1.replace(/\.[^/.]+$/, '');
            const name2WithoutExt = name2.replace(/\.[^/.]+$/, '');
            const normalized1 = normalizeFilename(name1WithoutExt);
            const normalized2 = normalizeFilename(name2WithoutExt);
            return normalized1 === normalized2;
        }

        async function extractMaskFromOverlay(overlayBlob) {
            return new Promise((resolve, reject) => {
                const img = new Image();
                img.onload = () => {
                    const canvas = document.createElement('canvas');
                    canvas.width = img.width;
                    canvas.height = img.height;
                    const ctx = canvas.getContext('2d');

                    ctx.drawImage(img, 0, 0);

                    const imageData = ctx.getImageData(0, 0, img.width, img.height);
                    const data = imageData.data;

                    const maskCanvas = document.createElement('canvas');
                    maskCanvas.width = img.width;
                    maskCanvas.height = img.height;
                    const maskCtx = maskCanvas.getContext('2d');
                    const maskImageData = maskCtx.createImageData(img.width, img.height);
                    const maskData = maskImageData.data;

                    for (let i = 0; i < data.length; i += 4) {
                        const r = data[i];
                        const g = data[i+1];
                        const b = data[i+2];

                        const isMaskPixel = (r >= 250 && g <= 5 && b <= 5);

                        if (isMaskPixel) {
                            maskData[i] = 255;
                            maskData[i+1] = 255;
                            maskData[i+2] = 255;
                            maskData[i+3] = 255;
                        } else {
                            maskData[i] = 0;
                            maskData[i+1] = 0;
                            maskData[i+2] = 0;
                            maskData[i+3] = 255;
                        }
                    }

                    maskCtx.putImageData(maskImageData, 0, 0);

                    maskCanvas.toBlob((blob) => {
                        resolve(blob);
                    }, 'image/png');
                };

                img.onerror = reject;
                img.src = URL.createObjectURL(overlayBlob);
            });
        }

        function getImageDimensionsFromBlob(blob) {
            return new Promise((resolve, reject) => {
                const img = new Image();
                img.onload = () => {
                    resolve({
                        width: img.width,
                        height: img.height
                    });
                    URL.revokeObjectURL(img.src);
                };
                img.onerror = reject;
                img.src = URL.createObjectURL(blob);
            });
        }

        // ========== ОСНОВНОЙ ПОДХОД ==========
        for (let i = 0; i < allUploadedImages.length; i++) {
            const image = allUploadedImages[i];
            const imageName = image.name;

            let foundMasks = null;
            let matchedMaskKey = null;

            for (const maskKey of Object.keys(window.multiMasks)) {
                if (isSameImageName(maskKey, imageName)) {
                    foundMasks = window.multiMasks[maskKey];
                    matchedMaskKey = maskKey;
                    break;
                }
            }

            if (!foundMasks || foundMasks.length === 0) {
                console.log(`Нет масок для изображения: ${imageName}`);
                continue;
            }

            const imageNumber = i + 1;
            const paddedNumber = imageNumber.toString().padStart(3, '0');

            const originalResponse = await fetch(image.dataUrl);
            const originalBlob = await originalResponse.blob();
            const fileExt = image.name.split('.').pop() || 'png';
            const cleanImageName = normalizeFilename(image.name.replace(/\.[^/.]+$/, ''));
            const imgDimensions = await getImageDimensionsFromBlob(originalBlob);

            const imageData = {
                original: {
                    name: image.name,
                    blob: originalBlob,
                    width: imgDimensions.width,
                    height: imgDimensions.height,
                    size: originalBlob.size,
                    imageNumber: imageNumber,
                    paddedNumber: paddedNumber,
                    cleanName: cleanImageName,
                    extension: fileExt
                },
                masks: [],
                imageNumber: imageNumber,
                paddedNumber: paddedNumber,
                cleanName: cleanImageName
            };

            for (let maskIndex = 0; maskIndex < foundMasks.length; maskIndex++) {
                const mask = foundMasks[maskIndex];
                const maskNumber = maskIndex + 1;

                try {
                    // ★★★ СОХРАНЯЕМ ОБЕ ПЛОЩАДИ ★★★
                    const pixelArea = mask.pixelArea || 0;

                    let realArea = 0;
                    let realAreaUnit = 'px²';
                    let realAreaDisplay = '';

                    if (mask.realArea !== undefined && mask.realArea > 0) {
                        realArea = mask.realArea;
                        realAreaUnit = mask.areaUnit || 'м²';
                        realAreaDisplay = formatAreaWithUnit(realArea, realAreaUnit);
                    } else if (pixelArea > 0) {
                        // Если нет реальной площади, но есть пиксельная
                        realArea = pixelArea;
                        realAreaUnit = 'px²';
                        realAreaDisplay = `${pixelArea.toLocaleString()} px²`;
                    } else {
                        realAreaDisplay = 'не вычислена';
                    }

                    // Получаем цветной overlay
                    let overlayBlob;
                    if (mask.dataUrl.startsWith('blob:')) {
                        const overlayResponse = await fetch(mask.dataUrl);
                        overlayBlob = await overlayResponse.blob();
                    } else if (mask.dataUrl.startsWith('data:')) {
                        const overlayResponse = await fetch(mask.dataUrl);
                        overlayBlob = await overlayResponse.blob();
                    } else {
                        overlayBlob = await (await fetch(mask.dataUrl)).blob();
                    }

                    const maskBlob = await extractMaskFromOverlay(overlayBlob);

                    imageData.masks.push({
                        index: maskNumber,
                        pixelArea: pixelArea,                    // ★★★ ПЛОЩАДЬ В ПИКСЕЛЯХ ★★★
                        realArea: realArea,                      // ★★★ РЕАЛЬНАЯ ПЛОЩАДЬ ★★★
                        realAreaUnit: realAreaUnit,              // ★★★ ЕДИНИЦА ИЗМЕРЕНИЯ ★★★
                        realAreaDisplay: realAreaDisplay,        // ★★★ ФОРМАТИРОВАННАЯ СТРОКА ★★★
                        maskBlob: maskBlob,
                        overlayBlob: overlayBlob,
                        propagated: mask.propagated || false,
                        gsdSettings: mask.gsdSettings || null
                    });

                    console.log(`Маска ${maskNumber} для ${imageName}: пикселей = ${pixelArea}, реальная = ${realAreaDisplay}`);

                } catch (maskError) {
                    console.error(`Ошибка обработки маски ${maskNumber}:`, maskError);
                }
            }

            if (imageData.masks.length > 0) {
                metadataMap.set(image.name, imageData);
            }
        }

        // ========== АЛЬТЕРНАТИВНЫЙ ПОДХОД ==========
        if (metadataMap.size === 0) {
            console.log('Пробуем альтернативный подход...');

            let altIndex = 0;
            const maskKeys = Object.keys(window.multiMasks);

            for (const maskKey of maskKeys) {
                const masks = window.multiMasks[maskKey];
                if (!masks || masks.length === 0) continue;

                let foundImage = null;
                for (const img of allUploadedImages) {
                    if (isSameImageName(img.name, maskKey)) {
                        foundImage = img;
                        break;
                    }
                }

                if (!foundImage) {
                    console.log(`Не найдено изображение для маски: ${maskKey}`);
                    continue;
                }

                altIndex++;
                const paddedNumber = altIndex.toString().padStart(3, '0');
                const cleanImageName = normalizeFilename(maskKey.replace(/\.[^/.]+$/, ''));

                const originalResponse = await fetch(foundImage.dataUrl);
                const originalBlob = await originalResponse.blob();
                const fileExt = foundImage.name.split('.').pop() || 'png';
                const imgDimensions = await getImageDimensionsFromBlob(originalBlob);

                const imageData = {
                    original: {
                        name: foundImage.name,
                        blob: originalBlob,
                        width: imgDimensions.width,
                        height: imgDimensions.height,
                        size: originalBlob.size,
                        imageNumber: altIndex,
                        paddedNumber: paddedNumber,
                        cleanName: cleanImageName,
                        extension: fileExt
                    },
                    masks: [],
                    imageNumber: altIndex,
                    paddedNumber: paddedNumber,
                    cleanName: cleanImageName
                };

                for (let maskIndex = 0; maskIndex < masks.length; maskIndex++) {
                    const mask = masks[maskIndex];
                    const maskNumber = maskIndex + 1;

                    try {
                        const pixelArea = mask.pixelArea || 0;

                        let realArea = 0;
                        let realAreaUnit = 'px²';
                        let realAreaDisplay = '';

                        if (mask.realArea !== undefined && mask.realArea > 0) {
                            realArea = mask.realArea;
                            realAreaUnit = mask.areaUnit || 'м²';
                            realAreaDisplay = formatAreaWithUnit(realArea, realAreaUnit);
                        } else if (pixelArea > 0) {
                            realArea = pixelArea;
                            realAreaUnit = 'px²';
                            realAreaDisplay = `${pixelArea.toLocaleString()} px²`;
                        } else {
                            realAreaDisplay = 'не вычислена';
                        }

                        let overlayBlob = await (await fetch(mask.dataUrl)).blob();
                        const maskBlob = await extractMaskFromOverlay(overlayBlob);

                        imageData.masks.push({
                            index: maskNumber,
                            pixelArea: pixelArea,
                            realArea: realArea,
                            realAreaUnit: realAreaUnit,
                            realAreaDisplay: realAreaDisplay,
                            maskBlob: maskBlob,
                            overlayBlob: overlayBlob,
                            propagated: mask.propagated || false,
                            gsdSettings: mask.gsdSettings || null
                        });

                        console.log(`Альт. Маска ${maskNumber} для ${maskKey}: пикселей = ${pixelArea}, реальная = ${realAreaDisplay}`);

                    } catch (err) {
                        console.error(`Ошибка обработки маски ${maskKey}:`, err);
                    }
                }

                if (imageData.masks.length > 0) {
                    metadataMap.set(foundImage.name, imageData);
                }
            }
        }

        if (metadataMap.size === 0) {
            throw new Error('Не найдено данных для сохранения (нет масок)');
        }

        // Сохраняем файлы в архив
        for (const [imageName, data] of metadataMap.entries()) {
            const paddedNum = data.paddedNumber;
            const cleanName = data.cleanName;

            console.log(`Сохранение в архив: ${imageName}, масок: ${data.masks.length}`);

            const originalFileName = `${paddedNum}_${cleanName}_original.${data.original.extension}`;
            originalsFolder.file(originalFileName, data.original.blob);

            for (const mask of data.masks) {
                const binaryFileName = `${paddedNum}_${cleanName}_mask_${mask.index}.png`;
                masksFolder.file(binaryFileName, mask.maskBlob);

                const overlayFileName = `${paddedNum}_${cleanName}_mask_${mask.index}_overlay.png`;
                overlaysFolder.file(overlayFileName, mask.overlayBlob);

                console.log(`  - Сохранена маска ${mask.index}: ${binaryFileName} (пикселей: ${mask.pixelArea}, реальная: ${mask.realAreaDisplay})`);
            }
        }

        // Создаем метаданные
        const globalMetadata = {
            generation_date: new Date().toISOString(),
            generation_date_formatted: new Date().toLocaleString('ru-RU'),
            total_images: metadataMap.size,
            total_masks: Array.from(metadataMap.values()).reduce((sum, data) => sum + data.masks.length, 0),
            images: []
        };

        for (const [imageName, data] of metadataMap.entries()) {
            const paddedNum = data.paddedNumber;
            const cleanName = data.cleanName;
            const totalPixels = data.original.width * data.original.height;

            const imageMetadata = {
                image_number: data.imageNumber,
                padded_number: paddedNum,
                original_filename: imageName,
                new_filename: `${paddedNum}_${cleanName}_original.${data.original.extension}`,
                width: data.original.width,
                height: data.original.height,
                file_size_bytes: data.original.size,
                file_size_formatted: formatFileSize(data.original.size),
                total_pixels: totalPixels,
                masks: data.masks.map(mask => {
                    // ★★★ ФОРМИРУЕМ МЕТАДАННЫЕ С ОБЕИМИ ПЛОЩАДЯМИ ★★★
                    const maskMetadata = {
                        mask_index: mask.index,
                        area_pixels: mask.pixelArea,                    // Площадь в пикселях
                        area_real: mask.realArea,                       // Реальная площадь
                        area_unit: mask.realAreaUnit,                   // Единица измерения
                        area_display: mask.realAreaDisplay,             // Форматированная строка
                        binary_mask_filename: `${paddedNum}_${cleanName}_mask_${mask.index}.png`,
                        overlay_filename: `${paddedNum}_${cleanName}_mask_${mask.index}_overlay.png`,
                        propagated: mask.propagated || false
                    };

                    // Добавляем GSD параметры, если есть
                    if (mask.gsdSettings) {
                        maskMetadata.gsd_settings = {
                            height: mask.gsdSettings.height,
                            sensor_pixel: mask.gsdSettings.sensorPixel,
                            focal: mask.gsdSettings.focal,
                            unit: mask.gsdSettings.unit
                        };
                    }

                    return maskMetadata;
                })
            };

            globalMetadata.images.push(imageMetadata);
            metadataFolder.file(`${paddedNum}_${cleanName}_metadata.json`, JSON.stringify(imageMetadata, null, 2));
        }

        // Сохраняем общие метаданные
        metadataFolder.file('all_metadata.json', JSON.stringify(globalMetadata, null, 2));

        // Создаем CSV с обеими площадями
        const csvRows = [
            ['Image #', 'Padded #', 'Original Filename', 'New Filename', 'Width', 'Height',
             'Total Pixels', 'File Size (Bytes)', 'File Size', 'Mask #',
             'Area (pixels)', 'Area (real)', 'Area Unit', 'Area Display',
             'Propagated', 'Mask File', 'Overlay File', 'GSD Height', 'GSD Sensor', 'GSD Focal']
        ];

        globalMetadata.images.forEach(img => {
            img.masks.forEach(mask => {
                csvRows.push([
                    img.image_number,
                    img.padded_number,
                    `"${img.original_filename}"`,
                    `"${img.new_filename}"`,
                    img.width,
                    img.height,
                    img.total_pixels,
                    img.file_size_bytes,
                    `"${img.file_size_formatted}"`,
                    mask.mask_index,
                    mask.area_pixels,                                    // Площадь в пикселях
                    mask.area_real,                                      // Реальная площадь
                    `"${mask.area_unit}"`,                               // Единица измерения
                    `"${mask.area_display}"`,                            // Форматированная строка
                    mask.propagated ? 'Yes' : 'No',
                    `"${mask.binary_mask_filename}"`,
                    `"${mask.overlay_filename}"`,
                    mask.gsd_settings?.height || '',
                    mask.gsd_settings?.sensor_pixel || '',
                    mask.gsd_settings?.focal || ''
                ]);
            });
        });

        metadataFolder.file('all_masks_info.csv', csvRows.map(row => row.join(',')).join('\n'));

        // Создаем отдельный CSV только с площадями для быстрого анализа
        const areaSummaryRows = [
            ['Image #', 'Image Name', 'Mask #', 'Area (pixels)', 'Area (real)', 'Area Unit', 'GSD Used']
        ];

        globalMetadata.images.forEach(img => {
            img.masks.forEach(mask => {
                areaSummaryRows.push([
                    img.image_number,
                    `"${img.original_filename}"`,
                    mask.mask_index,
                    mask.area_pixels,
                    mask.area_real,
                    `"${mask.area_unit}"`,
                    mask.gsd_settings ? `H=${mask.gsd_settings.height}, S=${mask.gsd_settings.sensor_pixel}, F=${mask.gsd_settings.focal}` : 'No GSD'
                ]);
            });
        });

        metadataFolder.file('areas_summary.csv', areaSummaryRows.map(row => row.join(',')).join('\n'));

        // README
        const readmeContent = `# Результаты сегментации
Дата генерации: ${globalMetadata.generation_date_formatted}

## Структура архива:
📁 originals/ - Оригинальные изображения
📁 masks/ - Бинарные черно-белые маски
📁 overlays/ - Цветные наложения масок
📁 metadata/ - Метаданные

## Информация о площадях:
Для каждой маски сохраняются два значения площади:
1. **Area (pixels)** - площадь в пикселях (количество пикселей в маске)
2. **Area (real)** - реальная площадь, рассчитанная по GSD

Формула расчета:
- GSD = (H × S) / F
- Реальная площадь = Площадь в пикселях × GSD²

## Статистика:
Всего изображений: ${globalMetadata.total_images}
Всего масок: ${globalMetadata.total_masks}

## Файлы метаданных:
- all_metadata.json - полные метаданные в JSON формате
- all_masks_info.csv - подробная информация о масках
- areas_summary.csv - краткая сводка по площадям

## Детальная информация:
${globalMetadata.images.map(img => `
### ${img.padded_number}: ${img.original_filename}
- Размер: ${img.width}×${img.height} (${img.total_pixels.toLocaleString()} px)
- Масок: ${img.masks.length}
${img.masks.map(mask => `  - Маска ${mask.mask_index}: ${mask.area_display} (${mask.area_pixels.toLocaleString()} px²) ${mask.propagated ? '🔄 распространенная' : '✍️ ручная'}`).join('\n')}
`).join('\n')}

## Примечания:
- 🔄 - распространенная маска (создана автоматически)
- ✍️ - ручная маска (создана пользователем)
- Для масок с GSD параметрами площадь рассчитана по формуле GSD = (H × S) / F
- Площадь в пикселях всегда доступна, даже если GSD не заданы
`;
        metadataFolder.file('README.txt', readmeContent);

        // Генерируем архив
        const finalZipBlob = await zip.generateAsync({
            type: 'blob',
            compression: 'DEFLATE',
            compressionOptions: { level: 6 }
        });

        const url = window.URL.createObjectURL(finalZipBlob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `segmentation_results_${new Date().toISOString().slice(0,19).replace(/:/g, '-')}.zip`;
        document.body.appendChild(a);
        a.click();

        setTimeout(() => {
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        }, 100);

        showToast('Успех', `Архив готов! ${globalMetadata.total_images} изобр., ${globalMetadata.total_masks} масок`, 'success');

    } catch (error) {
        console.error('Download error:', error);
        showToast('Ошибка', error.message, 'error');
    } finally {
        hideLoading();
    }
}
// Функция для отладки - показывает содержимое multiMasks
function debugMasks() {
    console.log('=== DEBUG: window.multiMasks ===');
    if (!window.multiMasks || Object.keys(window.multiMasks).length === 0) {
        console.log('Нет масок в multiMasks');
        return;
    }

    let totalMasks = 0;
    for (const imageName in window.multiMasks) {
        const masks = window.multiMasks[imageName];
        console.log(`\n📁 ${imageName}:`);
        console.log(`   Масок: ${masks.length}`);
        masks.forEach((mask, idx) => {
            console.log(`   Маска ${idx + 1}:`);
            console.log(`     - dataUrl: ${mask.dataUrl ? mask.dataUrl.substring(0, 50) + '...' : 'null'}`);
            console.log(`     - binaryDataUrl: ${mask.binaryDataUrl ? mask.binaryDataUrl.substring(0, 50) + '...' : 'null'}`);
            console.log(`     - propagated: ${mask.propagated || false}`);
            console.log(`     - area: ${mask.area || 'не вычислена'}`);
        });
        totalMasks += masks.length;
    }
    console.log(`\n📊 Всего масок: ${totalMasks}`);

    // Показываем уведомление
    showToast('Отладка', `Найдено масок: ${totalMasks} в ${Object.keys(window.multiMasks).length} изображениях`, 'info', 5000);
}

// Добавляем кнопку отладки в интерфейс (можно добавить в HTML или вызвать из консоли)
// Для удобства можно добавить глобальную функцию
window.debugMasks = debugMasks;
// Вспомогательная функция для получения размеров изображения из Blob
function getImageDimensionsFromBlob(blob) {
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => {
            resolve({
                width: img.width,
                height: img.height
            });
            URL.revokeObjectURL(img.src);
        };
        img.onerror = reject;
        img.src = URL.createObjectURL(blob);
    });
}

// Функция для форматирования размера файла
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}
// Функция для конвертации цветной маски в черно-белую (бинарную)
// Белый = маска, Черный = фон
async function convertToBinaryMask(colorMaskBlob) {
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => {
            const canvas = document.createElement('canvas');
            canvas.width = img.width;
            canvas.height = img.height;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(img, 0, 0, img.width, img.height);

            const imageData = ctx.getImageData(0, 0, img.width, img.height);
            const data = imageData.data;

            for (let i = 0; i < data.length; i += 4) {
                const r = data[i];
                const g = data[i+1];
                const b = data[i+2];
                const a = data[i+3];

                // ★ ИЗМЕНЯЕМ УСЛОВИЕ: ищем КРАСНЫЕ пиксели (R > 200, G < 50, B < 50)
                const isMaskPixel = (a > 0) && (r > 200) && (g < 50) && (b < 50);

                if (isMaskPixel) {
                    data[i] = 255;     // R
                    data[i+1] = 255;   // G
                    data[i+2] = 255;   // B
                    data[i+3] = 255;   // A
                } else {
                    data[i] = 0;
                    data[i+1] = 0;
                    data[i+2] = 0;
                    data[i+3] = 255;
                }
            }

            ctx.putImageData(imageData, 0, 0);
            canvas.toBlob((blob) => {
                resolve(blob);
            }, 'image/png');
        };

        img.onerror = reject;
        img.src = URL.createObjectURL(colorMaskBlob);
    });
}
// Вспомогательная функция для форматирования размера файла
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}
async function calculateMaskAreaFromBlob(blob) {
    return new Promise((resolve, reject) => {
        const img = new Image();

        img.onload = () => {
            const canvas = document.createElement('canvas');
            canvas.width = img.width;
            canvas.height = img.height;

            const ctx = canvas.getContext('2d');
            ctx.drawImage(img, 0, 0);

            const imageData = ctx.getImageData(0, 0, img.width, img.height);
            const data = imageData.data;

            let area = 0;

            for (let i = 0; i < data.length; i += 4) {
                // считаем белые пиксели маски
                if (data[i] > 200 || data[i + 1] > 200 || data[i + 2] > 200) {
                    area++;
                }
            }

            resolve(area);
        };

        img.onerror = reject;
        img.src = URL.createObjectURL(blob);
    });
}
// Функция для генерации читаемого текстового файла с метаданными
function generateReadableMetadata(metadata) {
    const lines = [];
    lines.push('='.repeat(60));
    lines.push('МЕТАДАННЫЕ ИЗОБРАЖЕНИЯ');
    lines.push('='.repeat(60));
    lines.push('');
    lines.push(`Номер изображения: ${metadata.image_number}`);
    lines.push(`Оригинальный файл: ${metadata.original_filename}`);
    lines.push(`Новый файл: ${metadata.new_filename}`);
    lines.push(`Размер изображения: ${metadata.width} × ${metadata.height} пикселей`);
    lines.push(`Общее количество пикселей: ${metadata.total_pixels.toLocaleString()}`);
    lines.push(`Размер файла: ${metadata.file_size_formatted} (${metadata.file_size_bytes.toLocaleString()} байт)`);
    lines.push('');
    lines.push('МАСКИ:');
    lines.push('-'.repeat(40));

    metadata.masks.forEach(mask => {
        lines.push('');
        lines.push(`Маска #${mask.mask_index}:`);
        lines.push(`  Площадь выделенной области: ${mask.area_pixels.toLocaleString()} пикселей`);
        lines.push(`  Процент от всего изображения: ${mask.area_percentage}%`);
        lines.push(`  Файл маски: ${mask.mask_filename}`);
        lines.push(`  Файл с наложением: ${mask.overlay_filename}`);
    });

    lines.push('');
    lines.push('='.repeat(60));
    lines.push(`Дата генерации: ${new Date().toLocaleString('ru-RU')}`);
    lines.push('='.repeat(60));

    return lines.join('\n');
}

// Функция для генерации глобального читаемого файла
function generateGlobalReadableMetadata(globalMetadata) {
    const lines = [];
    lines.push('='.repeat(70));
    lines.push('ОБЩИЙ ОТЧЕТ ПО СЕГМЕНТАЦИИ');
    lines.push('='.repeat(70));
    lines.push('');
    lines.push(`Дата генерации: ${new Date(globalMetadata.generation_date).toLocaleString('ru-RU')}`);
    lines.push(`ID сессии: ${globalMetadata.session_id}`);
    lines.push(`Всего изображений: ${globalMetadata.total_images}`);
    lines.push(`Всего масок: ${globalMetadata.total_masks}`);
    lines.push('');
    lines.push('ДЕТАЛЬНАЯ ИНФОРМАЦИЯ:');
    lines.push('='.repeat(70));

    globalMetadata.images.forEach((img, idx) => {
        lines.push('');
        lines.push(`ИЗОБРАЖЕНИЕ ${img.image_number}: ${img.original_filename}`);
        lines.push(`Новый файл: ${img.new_filename}`);
        lines.push('-'.repeat(40));
        lines.push(`Размер: ${img.width} × ${img.height} (${img.total_pixels.toLocaleString()} пикселей)`);
        lines.push(`Размер файла: ${img.file_size_formatted}`);
        lines.push('');
        lines.push('Маски:');

        img.masks.forEach(mask => {
            lines.push(`  #${mask.mask_index}: Площадь = ${mask.area_pixels.toLocaleString()} px (${mask.area_percentage}%)`);
            lines.push(`    Файл маски: ${mask.mask_filename}`);
            lines.push(`    Файл наложения: ${mask.overlay_filename}`);
        });
    });

    lines.push('');
    lines.push('='.repeat(70));
    lines.push('КОНЕЦ ОТЧЕТА');
    lines.push('='.repeat(70));

    return lines.join('\n');
}


// Функция для генерации CSV файла
function generateCSVMetadata(globalMetadata) {
    // Заголовки CSV
    const headers = [
        'Image Number',
        'Original Filename',
        'New Filename',
        'Image Width',
        'Image Height',
        'Total Pixels',
        'File Size (Bytes)',
        'File Size (Formatted)',
        'Mask Index',
        'Mask Area (px)',
        'Mask Area (%)',
        'Mask Filename',
        'Overlay Filename'
    ];

    const rows = [headers.join(',')];

    globalMetadata.images.forEach(img => {
        if (img.masks.length === 0) {
            // Если нет масок, добавляем строку только с информацией об изображении
            const row = [
                img.image_number,
                `"${img.original_filename}"`,
                `"${img.new_filename}"`,
                img.width,
                img.height,
                img.total_pixels,
                img.file_size_bytes,
                `"${img.file_size_formatted}"`,
                '',
                '',
                '',
                '',
                ''
            ];
            rows.push(row.join(','));
        } else {
            // Для каждой маски создаем отдельную строку
            img.masks.forEach(mask => {
                const row = [
                    img.image_number,
                    `"${img.original_filename}"`,
                    `"${img.new_filename}"`,
                    img.width,
                    img.height,
                    img.total_pixels,
                    img.file_size_bytes,
                    `"${img.file_size_formatted}"`,
                    mask.mask_index,
                    mask.area_pixels,
                    mask.area_percentage,
                    `"${mask.mask_filename}"`,
                    `"${mask.overlay_filename}"`
                ];
                rows.push(row.join(','));
            });
        }
    });

    return rows.join('\n');
}

// Вспомогательная функция для создания изображения с наложенной маской
async function createOverlayImage(originalImageUrl, maskImageUrl, imageName, maskIndex) {
    return new Promise((resolve, reject) => {
        try {
            // Создаем canvas для наложения
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');

            // Загружаем оригинальное изображение
            const originalImg = new Image();
            originalImg.crossOrigin = 'Anonymous';

            originalImg.onload = () => {
                canvas.width = originalImg.width;
                canvas.height = originalImg.height;

                // Рисуем оригинальное изображение
                ctx.drawImage(originalImg, 0, 0, canvas.width, canvas.height);

                // Загружаем маску
                const maskImg = new Image();
                maskImg.crossOrigin = 'Anonymous';

                maskImg.onload = () => {
                    // Рисуем маску поверх с хорошей прозрачностью
                    ctx.globalAlpha = 0.5;
                    ctx.globalCompositeOperation = 'source-over';
                    ctx.drawImage(maskImg, 0, 0, canvas.width, canvas.height);

                    // Добавляем красную обводку вокруг маски для лучшей видимости
                    ctx.globalAlpha = 1.0;
                    ctx.strokeStyle = '#ff4444';
                    ctx.lineWidth = 2;

                    // Получаем данные пикселей для определения границ маски
                    // Создаем временный canvas для анализа маски
                    const tempCanvas = document.createElement('canvas');
                    tempCanvas.width = canvas.width;
                    tempCanvas.height = canvas.height;
                    const tempCtx = tempCanvas.getContext('2d');
                    tempCtx.drawImage(maskImg, 0, 0, canvas.width, canvas.height);

                    const imageData = tempCtx.getImageData(0, 0, canvas.width, canvas.height);
                    const data = imageData.data;

                    // Находим границы маски (упрощенный алгоритм)
                    ctx.beginPath();

                    // Проходим по пикселям и находим границы
                    // Для больших изображений это может быть медленно, поэтому делаем сэмплинг
                    const step = Math.max(1, Math.floor(Math.min(canvas.width, canvas.height) / 500));

                    for (let y = 0; y < canvas.height; y += step) {
                        for (let x = 0; x < canvas.width; x += step) {
                            const index = (y * canvas.width + x) * 4;
                            // Если пиксель маски яркий (принадлежит маске)
                            if (data[index] > 200) {
                                // Проверяем соседние пиксели, чтобы найти границу
                                let isEdge = false;
                                for (let dy = -step; dy <= step && !isEdge; dy += step) {
                                    for (let dx = -step; dx <= step && !isEdge; dx += step) {
                                        if (dx === 0 && dy === 0) continue;

                                        const nx = x + dx;
                                        const ny = y + dy;
                                        if (nx >= 0 && nx < canvas.width && ny >= 0 && ny < canvas.height) {
                                            const nIndex = (ny * canvas.width + nx) * 4;
                                            if (data[nIndex] <= 200) {
                                                isEdge = true;
                                            }
                                        }
                                    }
                                }

                                if (isEdge) {
                                    ctx.fillStyle = '#ff4444';
                                    ctx.fillRect(x, y, step, step);
                                }
                            }
                        }
                    }

                    // Конвертируем canvas в blob
                    canvas.toBlob((blob) => {
                        resolve(blob);
                    }, 'image/png');
                };

                maskImg.onerror = () => {
                    console.error('Ошибка загрузки маски:', maskImageUrl);
                    // В случае ошибки возвращаем оригинальное изображение
                    canvas.toBlob((blob) => {
                        resolve(blob);
                    }, 'image/png');
                };

                maskImg.src = maskImageUrl;
            };

            originalImg.onerror = () => {
                console.error('Ошибка загрузки оригинального изображения:', originalImageUrl);
                reject(new Error('Не удалось загрузить оригинальное изображение'));
            };

            originalImg.src = originalImageUrl;
        } catch (error) {
            console.error('Ошибка создания наложения:', error);
            reject(error);
        }
    });
}

    function clearResults() {
        document.getElementById('results-grid').innerHTML = '';
        document.getElementById('results-panel').style.display = 'none';
    }

    // Функции для навигации
    function showInfo() {
        const infoModal = document.getElementById('info-modal');
        if (infoModal) {
            infoModal.style.display = 'flex';
        }
    }

    function showHelp() {
        const helpModal = document.getElementById('help-modal');
        if (helpModal) {
            helpModal.style.display = 'flex';
        }
    }

    // Функции для закрытия модальных окон
    function hideModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = 'none';
        }
    }

    // Добавьте обработчики для кнопок закрытия в модальных окнах
    document.addEventListener('DOMContentLoaded', function() {
        // Закрытие по клику на крестик
        document.querySelectorAll('.close-button, .modal-actions .action-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const modal = this.closest('.modal');
                if (modal) {
                    modal.style.display = 'none';
                }
            });
        });

        // Закрытие по клику вне модального окна
        window.addEventListener('click', function(event) {
            if (event.target.classList.contains('modal')) {
                event.target.style.display = 'none';
            }
        });
    });

    function showLogin() {
       window.location.href = '/auth/login';
    }

    function showRegister() {
        window.location.href = '/auth/login?register=true';
    }

    function openRegisterModal() {
        showRegister();
    }
    // Функция для удаления отдельного изображения из результатов
function deleteResultItem(element) {
    event.stopPropagation(); // Предотвращаем открытие модального окна

    const resultItem = element.closest('.result-item');
    if (!resultItem) return;

    const imageName = resultItem.querySelector('.result-name').textContent;
    const maskIndex = resultItem.getAttribute('data-mask-index');
    const originalImageName = resultItem.getAttribute('data-image');

    if (confirm(`Удалить "${imageName}" из результатов?`)) {

        // Удаляем маску из хранилища multiMasks
        if (originalImageName && maskIndex !== null) {
            if (window.multiMasks[originalImageName]) {
                // Удаляем конкретную маску по индексу
                window.multiMasks[originalImageName] = window.multiMasks[originalImageName].filter(
                    (mask, idx) => idx !== parseInt(maskIndex)
                );

                // Если масок больше нет, удаляем запись об изображении
                if (window.multiMasks[originalImageName].length === 0) {
                    delete window.multiMasks[originalImageName];
                }
            }
        }

        // Удаляем элемент из DOM
        resultItem.classList.add('fade-out');
        setTimeout(() => {
            resultItem.remove();

            // Проверяем, остались ли еще результаты
            const resultsGrid = document.getElementById('results-grid');
            if (resultsGrid.children.length === 0) {
                document.getElementById('results-panel').style.display = 'none';
            } else {
                // Обновляем индексы масок в оставшихся элементах
                updateMaskIndices();
            }

            // Перерисовываем canvas, если нужно
            renderCanvas();

            showToast('Успех', 'Изображение удалено из результатов', 'success');
        }, 300);
    }
}

// Функция для обновления индексов масок после удаления
function updateMaskIndices() {
    const resultsGrid = document.getElementById('results-grid');
    const resultItems = resultsGrid.querySelectorAll('.result-item');

    // Группируем по имени изображения
    const imageGroups = {};

    resultItems.forEach(item => {
        const imageName = item.getAttribute('data-image');
        if (!imageGroups[imageName]) {
            imageGroups[imageName] = [];
        }
        imageGroups[imageName].push(item);
    });

    // Обновляем индексы для каждой группы
    Object.keys(imageGroups).forEach(imageName => {
        const items = imageGroups[imageName];
        items.sort((a, b) => {
            const idxA = parseInt(a.getAttribute('data-mask-index') || '0');
            const idxB = parseInt(b.getAttribute('data-mask-index') || '0');
            return idxA - idxB;
        });

        items.forEach((item, newIndex) => {
            const nameDiv = item.querySelector('.result-name');
            const originalName = item.getAttribute('data-image');
            nameDiv.textContent = `${originalName} (маска ${newIndex + 1})`;
            item.setAttribute('data-mask-index', newIndex);

            // Обновляем индекс в хранилище multiMasks
            if (window.multiMasks[originalName] && window.multiMasks[originalName][newIndex]) {
                window.multiMasks[originalName][newIndex].index = newIndex;
            }
        });
    });
}
// Принудительная инициализация модального окна
window.addEventListener('load', function() {
    console.log('Window loaded, checking for modal...');
    if (!document.getElementById('image-view-modal')) {
        createImageModal();
    }
});
// Функция для открытия GSD модального окна
function openGSDPopup() {
    console.log('=== openGSDPopup called ===');

    // Загружаем сохраненные настройки GSD из localStorage (если есть)
    const savedSettings = localStorage.getItem('gsd_settings');
    if (savedSettings) {
        try {
            const settings = JSON.parse(savedSettings);
            document.getElementById('gsd-height-input').value = settings.height || 100;
            document.getElementById('gsd-sensor-input').value = settings.sensorPixel || 0.0024;
            document.getElementById('gsd-focal-input').value = settings.focal || 8;
            document.getElementById('gsd-unit-select').value = settings.unit || 'm2';
        } catch(e) {
            console.error('Error loading saved settings:', e);
        }
    } else {
        // Значения по умолчанию
        document.getElementById('gsd-height-input').value = 100;
        document.getElementById('gsd-sensor-input').value = 0.0024;
        document.getElementById('gsd-focal-input').value = 8;
        document.getElementById('gsd-unit-select').value = 'm2';
    }

    // ★★★ УБИРАЕМ ПРОВЕРКУ НА НАЛИЧИЕ ИЗОБРАЖЕНИЯ ★★★
    // Просто показываем информацию о маске, если она есть
    const currentImageName = images[currentImageIndex]?.name || allUploadedImages[currentImageIndex]?.name;
    let pixelArea = 0;
    let maskExists = false;

    if (currentImageName && window.multiMasks && window.multiMasks[currentImageName]) {
        const masks = window.multiMasks[currentImageName];
        if (masks && masks.length > 0) {
            maskExists = true;
            const activeMask = masks[masks.length - 1];
            pixelArea = activeMask.pixelArea || 0;

            // Если в маске есть сохраненные GSD параметры, загружаем их
            if (activeMask.gsdSettings && activeMask.gsdSettings.height) {
                document.getElementById('gsd-height-input').value = activeMask.gsdSettings.height;
                document.getElementById('gsd-sensor-input').value = activeMask.gsdSettings.sensorPixel;
                document.getElementById('gsd-focal-input').value = activeMask.gsdSettings.focal;
                document.getElementById('gsd-unit-select').value = activeMask.gsdSettings.unit;
            }
        }
    }

    // Отображаем информацию о маске (если есть)
    const pixelCountSpan = document.getElementById('gsd-modal-pixel-count');
    const pxAreaSpan = document.getElementById('gsd-modal-px-area');
    const pixelInfoBlock = pixelCountSpan?.parentElement?.parentElement;

    if (!currentImageName) {
        // Нет загруженных изображений
        if (pixelInfoBlock) {
            pixelInfoBlock.style.opacity = '0.5';
        }
        pixelCountSpan.textContent = 'Нет загруженных изображений';
        pxAreaSpan.textContent = '—';
    } else if (pixelArea > 0) {
        if (pixelInfoBlock) {
            pixelInfoBlock.style.opacity = '1';
        }
        pixelCountSpan.textContent = pixelArea.toLocaleString('ru-RU');
        pxAreaSpan.textContent = pixelArea.toLocaleString('ru-RU');
    } else if (maskExists) {
        if (pixelInfoBlock) {
            pixelInfoBlock.style.opacity = '0.7';
        }
        pixelCountSpan.textContent = '0 (маска создана, но площадь не вычислена)';
        pxAreaSpan.textContent = '0';
    } else if (currentImageName) {
        if (pixelInfoBlock) {
            pixelInfoBlock.style.opacity = '0.5';
        }
        pixelCountSpan.textContent = 'Нет маски для текущего изображения';
        pxAreaSpan.textContent = '—';
    }

    // Сохраняем текущую площадь
    window.currentPixelArea = pixelArea;

    // Скрываем результаты предыдущего расчета
    const resultsDiv = document.getElementById('gsd-results');
    if (resultsDiv) {
        resultsDiv.style.display = 'none';
    }

    // Показываем модальное окно
    const modal = document.getElementById('gsd-modal');
    if (modal) {
        modal.style.display = 'flex';
        console.log('GSD modal opened');
    } else {
        console.error('GSD modal element not found');
        showToast('Ошибка', 'Не удалось открыть окно расчета площади', 'error');
    }
}

// Функция для расчета площади по GSD
function calculateGSDArea() {
    const height = parseFloat(document.getElementById('gsd-height-input').value);
    const sensorPixel = parseFloat(document.getElementById('gsd-sensor-input').value);
    const focal = parseFloat(document.getElementById('gsd-focal-input').value);
    const unit = document.getElementById('gsd-unit-select').value;

    if (isNaN(height) || height <= 0 || isNaN(sensorPixel) || sensorPixel <= 0 || isNaN(focal) || focal <= 0) {
        showToast('Ошибка', 'Введите корректные параметры', 'error');
        return;
    }

    const pixelArea = window.currentPixelArea || 0;
    if (pixelArea === 0) {
        showToast('Ошибка', 'Площадь маски не определена', 'error');
        return;
    }

    const gsdSettings = { height, sensorPixel, focal, unit };
    const realArea = calculateRealArea(pixelArea, gsdSettings);
    const formattedArea = formatAreaWithUnit(realArea, unit);

    // Обновляем отображение в модальном окне
    const gsd = (height * sensorPixel) / focal;
    const pixelAreaM2 = Math.pow(gsd, 2);

    document.getElementById('gsd-result-value').textContent = gsd.toFixed(6) + ' м/пикс';
    document.getElementById('gsd-pixel-area').textContent = pixelAreaM2.toFixed(6) + ' м²';
    document.getElementById('gsd-final-area').textContent = formattedArea;
    document.getElementById('gsd-results').style.display = 'block';

    // ★★★ ОБНОВЛЯЕМ ТОЛЬКО ТЕКУЩЕЕ ИЗОБРАЖЕНИЕ ★★★
    const currentImageName = window.currentGSDActiveImage || images[currentImageIndex]?.name;

    if (currentImageName && window.multiMasks[currentImageName]) {
        // Сохраняем GSD настройки для этого изображения
        if (!window.imageGSDSettings) window.imageGSDSettings = {};
        window.imageGSDSettings[currentImageName] = { ...gsdSettings };

        // Обновляем все маски этого изображения
        let updatedCount = 0;
        for (let i = 0; i < window.multiMasks[currentImageName].length; i++) {
            const mask = window.multiMasks[currentImageName][i];
            if (mask.pixelArea) {
                const newRealArea = calculateRealArea(mask.pixelArea, gsdSettings);
                mask.realArea = newRealArea;
                mask.areaUnit = unit;
                mask.formattedArea = formatAreaWithUnit(newRealArea, unit);
                mask.gsdSettings = { ...gsdSettings };
                updatedCount++;
            }
        }

        if (updatedCount > 0) {
            updateResultsWithAllMasks();
            showToast('Успех',
                `Площадь обновлена для ${updatedCount} масок изображения "${currentImageName}". ${formattedArea}`,
                'success'
            );
        }
    }

    // Сохраняем последние настройки для нового изображения по умолчанию
    localStorage.setItem('gsd_settings', JSON.stringify(gsdSettings));

    updateAreaDisplayWithGSD(realArea, unit);
}

// Функция для обновления отображения площади с учетом GSD
function updateAreaDisplayWithGSD(areaValue, unit) {
    const areaInfo = document.getElementById('area-info');
    const areaValueElement = document.getElementById('area-value');
    const areaUnitElement = document.getElementById('area-unit');

    if (areaValue > 0) {
        areaInfo.style.display = 'block';

        // Если есть элемент для отображения единицы измерения, обновляем его
        if (areaUnitElement) {
            areaUnitElement.textContent = unit;
        } else {
            // Если элемента нет, создаем его или обновляем существующий
            const parentElement = areaValueElement.parentElement;
            if (parentElement) {
                let unitSpan = parentElement.querySelector('.area-unit');
                if (!unitSpan) {
                    unitSpan = document.createElement('span');
                    unitSpan.className = 'area-unit';
                    unitSpan.style.fontSize = '14px';
                    unitSpan.style.marginLeft = '2px';
                    unitSpan.style.color = 'var(--text-light)';
                    parentElement.appendChild(unitSpan);
                }
                unitSpan.textContent = unit;
            }
        }

        areaValueElement.textContent = areaValue.toLocaleString('ru-RU', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });

        // Добавляем анимацию обновления
        areaValueElement.classList.add('updated');
        setTimeout(() => {
            areaValueElement.classList.remove('updated');
        }, 300);
    }
}

// Функция для закрытия GSD модального окна
function closeGSDPopup() {
    const modal = document.getElementById('gsd-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

