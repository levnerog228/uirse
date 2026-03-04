// Получаем ссылки на элементы HTML
const qualitySlider = document.getElementById('qualitySlider');
const qualityValue = document.getElementById('qualityValue');
const fileInput = document.getElementById('fileInput');
const originalImageWrapper = document.getElementById('originalImageWrapper');
const compressedImageWrapper = document.getElementById('compressedImageWrapper');
const originalSizeInfo = document.getElementById('originalSize');
const compressedSizeInfo = document.getElementById('compressedSize');
const downloadButton = document.getElementById('downloadButton');
const colorSelect = document.getElementById('colorSelect');
const colorHighlightedImageWrapper = document.getElementById('colorHighlightedImageWrapper');
const finalProcessedImageWrapper = document.getElementById('finalImageWrapper');
const frame1 = document.getElementById('frame1');
let debounceTimeout, debounceTimeoutColor;


// Обновление отображаемого значения ползунка качества
qualitySlider.oninput = function () {
    qualityValue.textContent = this.value;
    updateCompressedImage();
};

// При выборе файла запускаем все процессы обработки
fileInput.onchange = function () {
    loadBlueChannelImage();
    loadRedChannelImage();
    loadGreenChannelImage();
    loadHueImage();
    loadSaturationImage();
    loadValueImage();
    loadLightnessHlsImage();
    displayOriginalImage();
    updateCompressedImage();
    updateColorHighlightedImage();
    updateFinalProcessedImage();
    updateLightnessHLSImage();

};

// Форматируем размер файла в килобайты
function formatSize(sizeInBytes) {
    return (sizeInBytes / 1024).toFixed(2) + ' кБ';
}

// Отображаем оригинальное изображение
async function displayOriginalImage() {
    const file = fileInput.files[0];
    if (file) {
        const originalURL = URL.createObjectURL(file);
        originalImageWrapper.innerHTML = `<img src="${originalURL}" alt="Оригинальное изображение">`;
        originalSizeInfo.textContent = `Размер: ${formatSize(file.size)}`;
    }
}

// Обновляем сжатое изображение
async function updateCompressedImage() {
    clearTimeout(debounceTimeout);
    debounceTimeout = setTimeout(async () => {
        const file = fileInput.files[0];
        const quality = qualitySlider.value;

        if (!file) {
            alert("Пожалуйста, выберите файл для загрузки.");
            return;
        }

        const formData = new FormData();
        formData.append('file', file);
        formData.append('quality', quality);

        try {
            const response = await fetch('http://localhost:5000/compress-image', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Ошибка ${response.status}: ${errorText}`);
            }

            const blob = await response.blob();
            const imgURL = URL.createObjectURL(blob);
            compressedImageWrapper.innerHTML = `<img src="${imgURL}" alt="Сжатое изображение">`;
            downloadButton.href = imgURL;
            downloadButton.style.display = 'inline-block';
            compressedSizeInfo.textContent = `Размер: ${formatSize(blob.size)}`;
        } catch (error) {
            console.error('Ошибка:', error);
            alert("Ошибка сжатия: " + error.message);
        }
    }, 300);
}

// Обновляем изображение с выделением цвета
async function updateColorHighlightedImage() {
    clearTimeout(debounceTimeoutColor);
    debounceTimeoutColor = setTimeout(async () => {
        const file = fileInput.files[0];
        const color = colorSelect.value;

        if (!file) {
            alert("Пожалуйста, выберите файл для загрузки.");
            return;
        }

        const formData = new FormData();
        formData.append('file', file);
        formData.append('color', color);

        try {
            const response = await fetch('http://localhost:5000/highlight-color', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Ошибка ${response.status}: ${errorText}`);
            }

            const blob = await response.blob();
            const imgURL = URL.createObjectURL(blob);
            colorHighlightedImageWrapper.innerHTML = `<img src="${imgURL}" alt="Выделенное изображение">`;
        } catch (error) {
            console.error('Ошибка:', error);
            alert("Ошибка обработки цвета: " + error.message);
        }
    }, 300);
}

// Обновляем итоговое обработанное изображение
async function updateFinalProcessedImage() {
    const file = fileInput.files[0];

    if (!file) {
        alert("Пожалуйста, выберите файл для загрузки.");
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('http://localhost:5000/segment-image', {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Ошибка ${response.status}: ${errorText}`);
        }

        const blob = await response.blob();
        const imgURL = URL.createObjectURL(blob);
        finalProcessedImageWrapper.innerHTML = `<img src="${imgURL}" alt="Итоговое обработанное изображение">`;
    } catch (error) {
        console.error('Ошибка:', error);
        alert("Ошибка итоговой обработки: " + error.message);
    }
}

// универсальная функция для загрузки чистых оттенков, яркости и чистоты цвета
async function loadChannelImage(route, frameElement) {
    const file = fileInput.files[0]; // Получаем выбранный файл

    if (!file) {
        alert("Пожалуйста, выберите файл для загрузки.");
        return;
    }

    const formData = new FormData();
    formData.append('file', file); // Отправляем файл на сервер

    try {
        // Отправляем POST-запрос на сервер
        const response = await fetch(`http://localhost:5000/${route}`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Ошибка ${response.status}: ${errorText}`);
        }

        // Получаем изображение из ответа
        const blob = await response.blob();
        const imgURL = URL.createObjectURL(blob);

        // Вставляем изображение в указанный контейнер
        frameElement.innerHTML = `<img src="${imgURL}" alt="${route} результат">`;

    } catch (error) {
        console.error('Ошибка:', error);
        alert("Ошибка загрузки изображения: " + error.message);
    }
}
// Функция для загрузки синего канала
async function loadBlueChannelImage() {
    await loadChannelImage('blue-channel', frame1);
}

// Функция для загрузки красного канала
async function loadRedChannelImage() {
    await loadChannelImage('red-channel', frame2);
}

// Функция для загрузки зеленого канала
async function loadGreenChannelImage() {
    await loadChannelImage('green-channel', frame3);
}

// Функция для загрузки оттенков (Hue)
async function loadHueImage() {
    await loadChannelImage('hue', frame4);
}

// Функция для загрузки насыщенности (Saturation)
async function loadSaturationImage() {
    await loadChannelImage('saturation', frame5);
}

// Функция для загрузки яркости (Value)
async function loadValueImage() {
    await loadChannelImage('value', frame6);
}

// Функция для загрузки Lightness в HLS
async function loadLightnessHlsImage() {
    await loadChannelImage('lightness-hls', frame7);
}

document.getElementById('fileInput').addEventListener('change', handleImageUpload);
const additionalImageWrapper = document.getElementById('additionalImageWrapper');
let canvas, ctx;
let img = new Image();
let startX, startY, isDrawing = false;
let selectedRegion;

// Инициализация холста
function initCanvas() {
    // Создаем новый холст
    canvas = document.createElement('canvas');

    // Устанавливаем пропорции для правильного отображения изображения
    const aspectRatio = img.width / img.height;
    canvas.width = additionalImageWrapper.clientWidth;  // Ширина контейнера
    canvas.height = canvas.width / aspectRatio;  // Вычисляем высоту на основе пропорции изображения

    canvas.style.maxWidth = '100%';
    canvas.style.maxHeight = '100%';
    canvas.style.display = 'block';
    ctx = canvas.getContext('2d');

    additionalImageWrapper.innerHTML = '';  // Очистить предыдущий контент
    additionalImageWrapper.appendChild(canvas); // Добавить новый холст

    // Подключаем обработчики событий для рисования области
    canvas.addEventListener('mousedown', startSelection);
    canvas.addEventListener('mousemove', drawSelection);
    canvas.addEventListener('mouseup', endSelection);

    // Рисуем изображение на холсте с учетом пропорций
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
}

// Обработка загрузки изображения
function handleImageUpload(event) {
    const file = event.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function (e) {
            img.src = e.target.result;
            img.onload = () => {
                initCanvas();  // Инициализируем холст после загрузки изображения
            };
        };
        reader.readAsDataURL(file);
    }
}

// Начало рисования области
function startSelection(e) {
    const rect = canvas.getBoundingClientRect();
    startX = e.clientX - rect.left;
    startY = e.clientY - rect.top;
    isDrawing = true;
    selectedRegion = null;
}

// Отрисовка области
function drawSelection(e) {
    if (!isDrawing) return;

    const rect = canvas.getBoundingClientRect();
    const currentX = e.clientX - rect.left;
    const currentY = e.clientY - rect.top;

    // Очистить холст и заново отрисовать изображение
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

    const width = currentX - startX;
    const height = currentY - startY;

    ctx.strokeStyle = 'red';
    ctx.lineWidth = 2;
    ctx.strokeRect(startX, startY, width, height);

    selectedRegion = { startX, startY, width, height };
}

// Завершение рисования области
function endSelection() {
    if (isDrawing && selectedRegion) {
        isDrawing = false;
        sendSelectedRegion(selectedRegion);
    }
}

// Функция для конвертации изображения в base64
function imageToBase64(image) {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    canvas.width = image.width;
    canvas.height = image.height;
    ctx.drawImage(image, 0, 0);
    return canvas.toDataURL('image/jpeg').split(',')[1]; // Возвращаем только base64 без префикса
}

// Функция для отправки выделенной области на сервер
function sendSelectedRegion(region) {
    const scaleX = img.width / canvas.width;  // Масштаб для вычисления реальных координат
    const scaleY = img.height / canvas.height;

    const croppedRegion = {
        x: region.startX * scaleX,
        y: region.startY * scaleY,
        width: region.width * scaleX,
        height: region.height * scaleY,
    };

    const canvasCrop = document.createElement('canvas');
    const ctxCrop = canvasCrop.getContext('2d');
    canvasCrop.width = croppedRegion.width;
    canvasCrop.height = croppedRegion.height;

    ctxCrop.drawImage(
        img,
        croppedRegion.x,
        croppedRegion.y,
        croppedRegion.width,
        croppedRegion.height,
        0,
        0,
        croppedRegion.width,
        croppedRegion.height
    );

    const croppedBase64 = imageToBase64(canvasCrop);  // Конвертируем в base64

    const imageBase64 = imageToBase64(img);  // Конвертируем все изображение в base64

    console.log("Cropped region (base64):", croppedBase64);
    // Отправляем запрос на сервер
    fetch('http://localhost:5000/process_region', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            image: imageBase64,
            template: croppedBase64
        }),
    })
    .then(response => response.json())
    .then(data => {
        console.log('Похожие области:', data.similarRegions);

        // Отрисовка полученных координат
        drawRegions(data.similarRegions);
    })
    .catch(error => {
        console.error('Ошибка:', error);
    });
}

// Функция для отрисовки прямоугольников по координатам
function drawRegions(regions) {
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height); // Очистить предыдущие выделения
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height); // Перерисовать изображение

    regions.forEach(region => {
        const x = region.x / (img.width / canvas.width);
        const y = region.y / (img.height / canvas.height);
        const width = region.width / (img.width / canvas.width);
        const height = region.height / (img.height / canvas.height);

        ctx.strokeStyle = 'red';
        ctx.lineWidth = 2;
        ctx.strokeRect(x, y, width, height);
    });
}

// Функция для фильтрации слишком близких прямоугольников
function filterCloseRegions(regions, minDistance) {
    const filteredRegions = [];

    regions.forEach((currentRegion, idx) => {
        let isTooClose = false;

        // Вычисляем центр текущего прямоугольника
        const currentCenterX = currentRegion.x + currentRegion.width / 2;
        const currentCenterY = currentRegion.y + currentRegion.height / 2;

        // Проверяем все уже отфильтрованные области на расстояние
        for (let i = 0; i < filteredRegions.length; i++) {
            const region = filteredRegions[i];

            // Вычисляем центр уже отфильтрованной области
            const regionCenterX = region.x + region.width / 2;
            const regionCenterY = region.y + region.height / 2;

            // Вычисляем расстояние между центрами двух прямоугольников
            const distance = Math.sqrt(
                Math.pow(currentCenterX - regionCenterX, 2) + Math.pow(currentCenterY - regionCenterY, 2)
            );

            // Если расстояние слишком маленькое, то они считаются "слишком близкими"
            if (distance < minDistance) {
                isTooClose = true;
                break; // Выход из цикла
            }
        }

        // Если прямоугольник не слишком близок к другим, добавляем его в отфильтрованные
        if (!isTooClose) {
            filteredRegions.push(currentRegion);
        }
    });

    return filteredRegions;
}

