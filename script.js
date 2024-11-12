        // Получаем ссылки на элементы HTML
const qualitySlider = document.getElementById('qualitySlider'); // Ползунок для выбора качества сжатия
const qualityValue = document.getElementById('qualityValue'); // Элемент для отображения выбранного качества
const fileInput = document.getElementById('fileInput'); // Элемент для загрузки изображения
const originalImageWrapper = document.getElementById('originalImageWrapper'); // Обертка для оригинального изображения
const compressedImageWrapper = document.getElementById('compressedImageWrapper'); // Обертка для сжатого изображения
const originalSizeInfo = document.getElementById('originalSize'); // Элемент для отображения размера оригинального изображения
const compressedSizeInfo = document.getElementById('compressedSize'); // Элемент для отображения размера сжатого изображения
const downloadButton = document.getElementById('downloadButton'); // Кнопка для скачивания сжатого изображения
const colorSelect = document.getElementById('colorSelect'); // Элемент выбора цвета для выделения
const colorHighlightedImageWrapper = document.getElementById('colorHighlightedImageWrapper'); // Обертка для изображения с выделением цвета
let debounceTimeout, debounceTimeoutColor; // Переменные для дебаунсинга, чтобы уменьшить количество запросов

// При изменении ползунка качества обновляем отображаемое значение и запускаем обновление сжатого изображения
qualitySlider.oninput = function() {
    qualityValue.textContent = this.value; // Обновляем отображение значения ползунка
    updateCompressedImage(); // Обновляем сжатое изображение
};

// При изменении выбранного файла отображаем оригинальное изображение, обновляем сжатое изображение и выделение цвета
fileInput.onchange = function() {
    displayOriginalImage(); // Отображаем оригинальное изображение
    updateCompressedImage(); // Обновляем сжатое изображение
    updateColorHighlightedImage(); // Обновляем выделение цвета
};

// Функция для форматирования размера файла в килобайты
function formatSize(sizeInBytes) {
    return (sizeInBytes / 1024).toFixed(2) + ' кБ'; // Преобразуем байты в килобайты и форматируем до двух знаков
}

// Функция для отображения оригинального изображения
async function displayOriginalImage() {
    const file = fileInput.files[0]; // Получаем выбранное изображение
    if (file) {
        const originalURL = URL.createObjectURL(file); // Создаем URL для изображения
        originalImageWrapper.innerHTML = `<img src="${originalURL}" alt="Оригинальное изображение">`; // Отображаем изображение
        originalSizeInfo.textContent = `Размер: ${formatSize(file.size)}`; // Отображаем размер изображения
    }
}

// Функция для обновления сжатого изображения
async function updateCompressedImage() {
    clearTimeout(debounceTimeout); // Очищаем предыдущий таймаут для предотвращения частых запросов
    debounceTimeout = setTimeout(async () => {
        const file = fileInput.files[0]; // Получаем выбранное изображение
        const quality = qualitySlider.value; // Получаем значение качества сжатия

        if (!file) { // Если файл не выбран, показываем ошибку
            alert("Пожалуйста, выберите файл для загрузки.");
            return;
        }

        const formData = new FormData(); // Создаем объект FormData для отправки данных
        formData.append('file', file); // Добавляем файл в данные
        formData.append('quality', quality); // Добавляем качество сжатия

        try {
            // Отправляем запрос на сервер для сжатия изображения
            const response = await fetch('http://localhost:5000/compress-image', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) { // Если сервер вернул ошибку
                const errorText = await response.text();
                throw new Error(`Ошибка ${response.status}: ${errorText}`);
            }

            const blob = await response.blob(); // Получаем изображение в виде Blob
            const imgURL = URL.createObjectURL(blob); // Создаем URL для сжатого изображения
            compressedImageWrapper.innerHTML = `<img src="${imgURL}" alt="Сжатое изображение">`; // Отображаем сжатое изображение

            // Обновляем ссылку для скачивания
            downloadButton.href = imgURL;
            downloadButton.style.display = 'inline-block'; // Делаем кнопку скачивания видимой

            // Обновляем размер сжатого изображения
            const compressedSize = blob.size;
            compressedSizeInfo.textContent = `Размер: ${formatSize(compressedSize)}`;
        } catch (error) {
            console.error('Ошибка:', error);
            alert("Произошла ошибка при загрузке изображения: " + error.message); // Показываем ошибку пользователю
        }
    }, 300); // Устанавливаем задержку перед запросом (debounce)
}

// Функция для обновления изображения с выделением цвета
async function updateColorHighlightedImage() {
    clearTimeout(debounceTimeoutColor); // Очищаем предыдущий таймаут для предотвращения частых запросов
    debounceTimeoutColor = setTimeout(async () => {
        const file = fileInput.files[0]; // Получаем выбранное изображение
        const color = colorSelect.value; // Получаем выбранный цвет для выделения

        if (!file) { // Если файл не выбран, показываем ошибку
            alert("Пожалуйста, выберите файл для загрузки.");
            return;
        }

        const formData = new FormData(); // Создаем объект FormData для отправки данных
        formData.append('file', file); // Добавляем файл в данные
        formData.append('color', color); // Добавляем выбранный цвет

        try {
            // Отправляем запрос на сервер для обработки изображения с выделением цвета
            const response = await fetch('http://localhost:5000/highlight-color', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) { // Если сервер вернул ошибку
                const errorText = await response.text();
                throw new Error(`Ошибка ${response.status}: ${errorText}`);
            }

            const blob = await response.blob(); // Получаем изображение в виде Blob
            const imgURL = URL.createObjectURL(blob); // Создаем URL для обработанного изображения
            colorHighlightedImageWrapper.innerHTML = `<img src="${imgURL}" alt="Выделенное изображение">`; // Отображаем изображение с выделением
        } catch (error) {
            console.error('Ошибка:', error);
            alert("Произошла ошибка при обработке изображения: " + error.message); // Показываем ошибку пользователю
        }
    }, 300); // Устанавливаем задержку перед запросом (debounce)
}

