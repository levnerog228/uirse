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

