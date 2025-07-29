document.addEventListener("DOMContentLoaded", function () {
    const inputFile = document.createElement("input");
    inputFile.type = "file";
    inputFile.accept = "image/*";
    inputFile.style.display = "none";

    const importButton = document.getElementById("import-button");
    const drawModeButton = document.getElementById("draw-mode-button");
    const resultDisplay = document.querySelector(".result-area");

    let canvas, ctx, img = new Image();
    let isDrawing = false;
    let drawMode = false;
    let currentPolygon = [];
    let selectedPolygons = [];
    let foundRegions = [];

    let scale = 1;
    let originX = 0;
    let originY = 0;

    let isDragging = false;
    let dragStartX = 0;
    let dragStartY = 0;

    document.getElementById('save-button').addEventListener('click', saveCanvas);
    document.getElementById('clear-button').addEventListener('click', clearAllRegions);

    drawModeButton.addEventListener("click", () => {
        drawMode = !drawMode;
        drawModeButton.textContent = drawMode ? "Выключить рисование" : "Включить рисование";
        if (canvas) {
            canvas.style.cursor = drawMode ? "crosshair" : "grab";
        }
    });

    async function saveCanvas() {
    if (!canvas) {
        alert('Нет изображения для сохранения!');
        return;
    }

    const progressContainer = document.getElementById('progress-container');
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');

    try {
        // Показываем индикатор прогресса
        progressContainer.style.display = 'block';
        progressBar.style.width = '0%';
        progressText.textContent = 'Сохранение...';

        // 1. Сохраняем изображение локально на компьютер пользователя
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const localFilename = `processed-image-${timestamp}.png`;

        // Создаем временную ссылку для скачивания
        const link = document.createElement('a');
        link.download = localFilename;
        link.href = canvas.toDataURL('image/png');
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        // 2. Отправляем копию на сервер (если пользователь авторизован)
        try {
            const blob = await new Promise(resolve => {
                canvas.toBlob(resolve, 'image/png', 0.9);
            });

            const formData = new FormData();
            formData.append('image', blob, 'processed_image.png');

            const response = await fetch('/save_image', {
                method: 'POST',
                body: formData,
                credentials: 'include'
            });

            if (!response.ok) {
                throw new Error(await response.text());
            }

            const result = await response.json();

            progressBar.style.width = '100%';
            progressText.textContent = 'Сохранено локально и на сервере!';

            // Обновляем список изображений на сервере
            if (result.success) {
                updateImageList();
            }
        } catch (serverError) {
            console.error('Ошибка сохранения на сервере:', serverError);
            progressBar.style.width = '100%';
            progressText.style.color = 'orange';
            progressText.textContent = 'Сохранено локально, но ошибка сервера';
        }

        setTimeout(() => {
            progressContainer.style.display = 'none';
            progressText.style.color = '';
        }, 3000);

    } catch (error) {
        console.error('Ошибка сохранения:', error);
        if (progressBar && progressText) {
            progressBar.style.backgroundColor = '#ff3333';
            progressText.textContent = 'Ошибка сохранения';
        }
    }
}
    async function updateImageList() {
    try {
        const response = await fetch('/get_user_images', {
            credentials: 'include' // Важно для передачи сессии
        });

        if (!response.ok) {
            throw new Error('Ошибка при загрузке изображений');
        }

        const images = await response.json();
        const imagesGrid = document.querySelector('.images-grid');

        if (!imagesGrid) return;

        imagesGrid.innerHTML = '';

        if (images.length === 0) {
            imagesGrid.innerHTML = '<p>Вы еще не сохраняли изображений</p>';
            return;
        }

        images.forEach(image => {
            const imageCard = document.createElement('div');
            imageCard.className = 'image-card';
            imageCard.innerHTML = `
                <img src="/static/uploads/${image.filename}" 
                     alt="Обработанное изображение" class="image-thumbnail">
                <div class="image-info">
                    <div class="image-date">${image.upload_date}</div>
                    <div class="image-actions">
                        <button onclick="viewImage('/static/uploads/${image.filename}')">
                            Просмотр
                        </button>
                        <button onclick="deleteImage(${image.id})">Удалить</button>
                    </div>
                </div>
            `;
            imagesGrid.appendChild(imageCard);
        });
    } catch (error) {
        console.error('Ошибка загрузки изображений:', error);
    }
}

    function clearAllRegions() {
        if (!confirm('Удалить все области?')) return;
        selectedPolygons = [];
        currentPolygon = [];
        foundRegions = [];
        redrawCanvas();
    }

    function initCanvas() {
        canvas = document.createElement('canvas');
        canvas.style.width = "100%";
        canvas.style.height = "auto";
        canvas.style.display = "block";
        canvas.style.cursor = drawMode ? "crosshair" : "grab";

        resultDisplay.innerHTML = '';
        resultDisplay.appendChild(canvas);
        ctx = canvas.getContext('2d');

        canvas.width = img.naturalWidth;
        canvas.height = img.naturalHeight;

        scale = 1;
        originX = 0;
        originY = 0;

        drawImage();

        canvas.addEventListener('mousedown', onMouseDown);
        canvas.addEventListener('mousemove', onMouseMove);
        canvas.addEventListener('mouseup', onMouseUp);
        canvas.addEventListener('mouseleave', onMouseLeave);
        canvas.addEventListener('dblclick', onDoubleClick);
        canvas.addEventListener('wheel', handleZoom);
    }

    function getCanvasCoordinates(clientX, clientY) {
        const rect = canvas.getBoundingClientRect();
        const scaleX = canvas.width / rect.width;
        const scaleY = canvas.height / rect.height;

        const screenX = (clientX - rect.left) * scaleX;
        const screenY = (clientY - rect.top) * scaleY;

        const x = (screenX - originX) / scale;
        const y = (screenY - originY) / scale;

        return { x, y };
    }

    function onMouseDown(e) {
        const { x, y } = getCanvasCoordinates(e.clientX, e.clientY);

        if (drawMode) {
            if (currentPolygon.length > 2 && isCloseToFirstPoint(x, y)) {
                closeCurrentPolygon();
            } else {
                currentPolygon.push({ x, y });
                isDrawing = true;
            }
            redrawCanvas();
        } else {
            isDragging = true;
            dragStartX = e.clientX;
            dragStartY = e.clientY;
            canvas.style.cursor = "grabbing";
        }
    }

    function onMouseMove(e) {
        const { x, y } = getCanvasCoordinates(e.clientX, e.clientY);

        if (!canvas) return;

        if (drawMode && isDrawing && currentPolygon.length > 0) {
            redrawCanvas();

            ctx.beginPath();
            ctx.moveTo(currentPolygon[0].x, currentPolygon[0].y);

            for (let i = 1; i < currentPolygon.length; i++) {
                ctx.lineTo(currentPolygon[i].x, currentPolygon[i].y);
            }

            ctx.lineTo(x, y);

            if (currentPolygon.length > 2 && isCloseToFirstPoint(x, y)) {
                ctx.strokeStyle = 'green';
            } else {
                ctx.strokeStyle = 'blue';
            }

            ctx.lineWidth = 2 / scale;
            ctx.stroke();
        } else if (isDragging) {
            originX += (e.clientX - dragStartX);
            originY += (e.clientY - dragStartY);
            dragStartX = e.clientX;
            dragStartY = e.clientY;
            drawImage();
        }
    }

    function onMouseUp() {
        isDragging = false;
        canvas.style.cursor = drawMode ? "crosshair" : "grab";
    }

    function onMouseLeave() {
        isDragging = false;
        canvas.style.cursor = drawMode ? "crosshair" : "grab";
    }

    function onDoubleClick() {
        if (drawMode && currentPolygon.length >= 3) {
            closeCurrentPolygon();
        }
    }

    function closeCurrentPolygon() {
        if (currentPolygon.length < 3) return;

        currentPolygon.push({...currentPolygon[0]});
        selectedPolygons.push([...currentPolygon]);
        sendSelectedRegion(currentPolygon);
        currentPolygon = [];
        isDrawing = false;
        redrawCanvas();
    }

    function isCloseToFirstPoint(x, y) {
        if (currentPolygon.length === 0) return false;
        const firstPoint = currentPolygon[0];
        const distance = Math.sqrt(Math.pow(x - firstPoint.x, 2) + Math.pow(y - firstPoint.y, 2));
        return distance < 10 / scale;
    }

    function handleZoom(event) {
        event.preventDefault();
        const delta = event.deltaY < 0 ? 1.1 : 0.9;

        const { x: mouseX, y: mouseY } = getCanvasCoordinates(event.clientX, event.clientY);

        const previousScale = scale;
        scale *= delta;
        scale = Math.min(Math.max(0.1, scale), 10);

        const scaleDiff = scale / previousScale;
        originX = mouseX - (mouseX - originX) * scaleDiff;
        originY = mouseY - (mouseY - originY) * scaleDiff;

        drawImage();
    }

    function drawImage() {
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        ctx.setTransform(scale, 0, 0, scale, originX, originY);
        ctx.drawImage(img, 0, 0);

        drawPolygons();
        drawFoundRegions();
    }

    function drawPolygons() {
        ctx.save();
        ctx.beginPath();
        ctx.strokeStyle = 'red';
        ctx.lineWidth = 2 / scale;

        selectedPolygons.forEach(polygon => {
            if (polygon.length > 0) {
                ctx.moveTo(polygon[0].x, polygon[0].y);
                for (let i = 1; i < polygon.length; i++) {
                    ctx.lineTo(polygon[i].x, polygon[i].y);
                }
                ctx.closePath();
            }
        });

        ctx.stroke();
        ctx.restore();
    }

    function drawFoundRegions() {
    if (foundRegions.length === 0) return;

    ctx.save();
    ctx.strokeStyle = 'green';
    ctx.lineWidth = 2 / scale;
    ctx.fillStyle = 'rgba(0, 255, 0, 0.2)';

    // Сначала рисуем все контуры
    foundRegions.forEach(region => {
        if (region.contour && region.contour.length > 2) {
            ctx.beginPath();
            ctx.moveTo(region.contour[0].x, region.contour[0].y);
            for (let i = 1; i < region.contour.length; i++) {
                ctx.lineTo(region.contour[i].x, region.contour[i].y);
            }
            ctx.closePath();
            ctx.fill();
        }
    });

    // Затем обводим контуры, чтобы они были видны поверх заливки
    foundRegions.forEach(region => {
        if (region.contour && region.contour.length > 2) {
            ctx.beginPath();
            ctx.moveTo(region.contour[0].x, region.contour[0].y);
            for (let i = 1; i < region.contour.length; i++) {
                ctx.lineTo(region.contour[i].x, region.contour[i].y);
            }
            ctx.closePath();
            ctx.stroke();
        }
    });

    ctx.restore();
}

    function groupAdjacentRegions(regions, maxGap = 5) {
        const groups = [];
        const used = new Array(regions.length).fill(false);

        for (let i = 0; i < regions.length; i++) {
            if (!used[i]) {
                const queue = [regions[i]];
                used[i] = true;
                const currentGroup = [regions[i]];

                while (queue.length > 0) {
                    const current = queue.shift();

                    for (let j = 0; j < regions.length; j++) {
                        if (!used[j] && areRegionsAdjacent(current, regions[j], maxGap)) {
                            used[j] = true;
                            currentGroup.push(regions[j]);
                            queue.push(regions[j]);
                        }
                    }
                }

                groups.push(currentGroup);
            }
        }

        return groups;
    }

    function areRegionsAdjacent(a, b, maxGap) {
        return !(
            a.x + a.width + maxGap < b.x ||
            b.x + b.width + maxGap < a.x ||
            a.y + a.height + maxGap < b.y ||
            b.y + b.height + maxGap < a.y
        );
    }

    function computeConvexHull(points) {
        if (points.length <= 1) return points;

        points.sort((a, b) => a.x - b.x || a.y - b.y);

        const lower = [];
        for (const point of points) {
            while (lower.length >= 2 && cross(lower[lower.length - 2], lower[lower.length - 1], point) <= 0) {
                lower.pop();
            }
            lower.push(point);
        }

        const upper = [];
        for (let i = points.length - 1; i >= 0; i--) {
            const point = points[i];
            while (upper.length >= 2 && cross(upper[upper.length - 2], upper[upper.length - 1], point) <= 0) {
                upper.pop();
            }
            upper.push(point);
        }

        lower.pop();
        upper.pop();

        return lower.concat(upper);
    }

    function cross(o, a, b) {
        return (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x);
    }

    function redrawCanvas() {
        drawImage();
    }

    function sendSelectedRegion(polygon) {
    const progressContainer = document.getElementById('progress-container');
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');

    // Показываем индикатор прогресса
    progressContainer.style.display = 'block';
    progressBar.style.width = '0%';
    progressText.textContent = '0%';
    progressBar.style.backgroundColor = '#4CAF50';

    // Имитация прогресса (будет перезаписана реальным прогрессом)
    const progressInterval = setInterval(() => {
        const currentWidth = parseInt(progressBar.style.width);
        if (currentWidth < 90) {
            const newWidth = currentWidth + 10;
            progressBar.style.width = newWidth + '%';
            progressText.textContent = newWidth + '%';
        }
    }, 300);

    // Создаем временный canvas для вырезания ROI
    const tempCanvas = document.createElement('canvas');
    const tempCtx = tempCanvas.getContext('2d');

    // Вычисляем границы полигона
    const minX = Math.min(...polygon.map(p => p.x));
    const minY = Math.min(...polygon.map(p => p.y));
    const maxX = Math.max(...polygon.map(p => p.x));
    const maxY = Math.max(...polygon.map(p => p.y));
    const width = maxX - minX;
    const height = maxY - minY;

    // Настраиваем временный canvas
    tempCanvas.width = width;
    tempCanvas.height = height;

    // Вырезаем ROI с учетом полигона
    tempCtx.save();
    tempCtx.beginPath();
    tempCtx.moveTo(polygon[0].x - minX, polygon[0].y - minY);
    for (let i = 1; i < polygon.length; i++) {
        tempCtx.lineTo(polygon[i].x - minX, polygon[i].y - minY);
    }
    tempCtx.closePath();
    tempCtx.clip();

    // Рисуем изображение в вырезанной области
    tempCtx.drawImage(img, minX, minY, width, height, 0, 0, width, height);
    tempCtx.restore();

    // Получаем ROI в base64
    const roiBase64 = tempCanvas.toDataURL('image/jpeg');

    // Подготавливаем данные для отправки
    const requestData = {
        image: imageToBase64(img),
        roi: roiBase64,
        polygon: polygon.map(p => ({ x: p.x, y: p.y })),
        return_contours: true // Запрашиваем точные контуры у сервера
    };

    // Отправляем запрос на сервер
    fetch('http://127.0.0.1:5000/process_region', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData),
    })
    .then(response => {
        if (!response.ok) throw new Error('Network response was not ok');
        return response.json();
    })
    .then(data => {
        clearInterval(progressInterval);
        progressBar.style.width = '100%';
        progressText.textContent = '100%';

        setTimeout(() => {
            progressContainer.style.display = 'none';
        }, 1000);

        // Обрабатываем ответ сервера
        if (data.similarRegions) {
            // Преобразуем данные регионов для удобства использования
            foundRegions = data.similarRegions.map(region => {
                // Если сервер вернул контур, используем его
                if (region.contour && region.contour.length > 0) {
                    return {
                        ...region,
                        contour: region.contour.map(p => ({ x: p.x, y: p.y }))
                    };
                }
                // Иначе создаем прямоугольный контур
                return {
                    ...region,
                    contour: [
                        { x: region.x, y: region.y },
                        { x: region.x + region.width, y: region.y },
                        { x: region.x + region.width, y: region.y + region.height },
                        { x: region.x, y: region.y + region.height }
                    ]
                };
            });

            // Перерисовываем canvas с новыми регионами
            redrawCanvas();

            // Показываем цветовые компоненты, если они есть
            if (data.hComponent && data.sComponent && data.vComponent) {
                showHSComponents(data.hComponent, data.sComponent, data.vComponent);
            }
        }

        // Показываем превью выбранной области
        const previewContainer = document.getElementById("preview-container");
        const previewImage = document.getElementById("preview-image");
        previewContainer.style.display = "block";
        previewImage.src = roiBase64;

        // Добавляем информацию о найденных регионах
        const infoPanel = document.getElementById("region-info") || document.querySelector(".image-info");
        if (infoPanel) {
            const regionsInfo = foundRegions.length > 0 ? `
                <h3>Найдено регионов: ${foundRegions.length}</h3>
                <p>Первый регион: X=${foundRegions[0].x}, Y=${foundRegions[0].y}</p>
                <p>Размер: ${foundRegions[0].width}×${foundRegions[0].height}</p>
            ` : '<p>Однородные регионы не найдены</p>';

            infoPanel.innerHTML = regionsInfo;
            }
    })
    .catch(error => {
        clearInterval(progressInterval);
        progressBar.style.backgroundColor = '#ff3333';
        progressText.textContent = 'Ошибка: ' + error.message;
        console.error('Error:', error);

        // Показываем сообщение об ошибке пользователю
        const errorDisplay = document.createElement('div');
        errorDisplay.className = 'error-message';
        errorDisplay.textContent = 'Произошла ошибка: ' + error.message;
        resultDisplay.appendChild(errorDisplay);

        setTimeout(() => {
            errorDisplay.remove();
        }, 5000);
    });
}

// Вспомогательная функция для преобразования изображения в base64
function imageToBase64(image) {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    canvas.width = image.width;
    canvas.height = image.height;
    ctx.drawImage(image, 0, 0);
    return canvas.toDataURL('image/jpeg').split(',')[1];
}

    function showHSComponents(hBase64, sBase64, vBase64) {
        const hsContainer = document.getElementById('hs-components');

        hsContainer.innerHTML = `
            <div class="hs-header">
                <h3>Анализ цветовых компонент (HSV)</h3>
                <p>Нажмите на изображение для увеличения</p>
            </div>
            <div class="hs-grid">
                <div class="hs-item" data-component="h">
                    <img src="data:image/jpeg;base64,${hBase64}" alt="H-компонента (Цветовой тон)" class="hs-image">
                    <div class="hs-label">H-компонента (Цветовой тон)</div>
                </div>
                <div class="hs-item" data-component="s">
                    <img src="data:image/jpeg;base64,${sBase64}" alt="S-компонента (Насыщенность)" class="hs-image">
                    <div class="hs-label">S-компонента (Насыщенность)</div>
                </div>
                <div class="hs-item" data-component="v">
                    <img src="data:image/jpeg;base64,${vBase64}" alt="V-компонента (Яркость)" class="hs-image">
                    <div class="hs-label">V-компонента (Яркость)</div>
                </div>
            </div>
        `;

        hsContainer.style.display = 'block';

        const hsItems = document.querySelectorAll('.hs-item');
        hsItems.forEach(item => {
            item.addEventListener('click', function() {
                const img = this.querySelector('img');
                const label = this.querySelector('.hs-label').textContent;

                const popup = document.createElement('div');
                popup.className = 'hs-popup';
                popup.style.position = 'fixed';
                popup.style.top = '0';
                popup.style.left = '0';
                popup.style.width = '100%';
                popup.style.height = '100%';
                popup.style.backgroundColor = 'rgba(0,0,0,0.9)';
                popup.style.display = 'flex';
                popup.style.justifyContent = 'center';
                popup.style.alignItems = 'center';
                popup.style.zIndex = '10000';

                popup.innerHTML = `
                    <div class="hs-popup-content" style="position:relative; background:#fff; padding:10px; border-radius:10px; max-width:90%; max-height:90%;">
                        <span class="hs-popup-close" style="position:absolute; top:10px; right:15px; font-size:30px; color:#676767; cursor:pointer; background:none; border:none;">&times;</span>
                        <img src="${img.src}" alt="${img.alt}" style="max-width:80vw; max-height:70vh; object-fit:contain;">
                        <div style="margin-top:15px; font-size:1.2rem; color:#676767; font-weight:bold; text-align:center;">${label}</div>
                    </div>
                `;

                document.body.appendChild(popup);

                const closeBtn = popup.querySelector('.hs-popup-close');
                closeBtn.addEventListener('click', () => {
                    popup.remove();
                });

                popup.addEventListener('click', (e) => {
                    if (e.target === popup) {
                        popup.remove();
                    }
                });

                const popupContent = popup.querySelector('.hs-popup-content');
                popupContent.addEventListener('click', (e) => {
                    e.stopPropagation();
                });
            });
        });
    }

    function imageToBase64(image) {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        canvas.width = image.width;
        canvas.height = image.height;
        ctx.drawImage(image, 0, 0);
        return canvas.toDataURL('image/jpeg').split(',')[1];
    }

    inputFile.addEventListener("change", function (event) {
        const file = event.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function (e) {
                img.src = e.target.result;
                img.onload = () => {
                    initCanvas();
                    selectedPolygons = [];
                    foundRegions = [];

                    const fileSize = (file.size / 1024).toFixed(2);
                    const aspectRatio = (img.width / img.height).toFixed(2);
                    const resolution = `${img.width}x${img.height}`;
                    const imageFormat = file.type.split('/')[1].toUpperCase();

                    document.getElementById("file-size").textContent = `Размер, кб: ${fileSize}`;
                    document.getElementById("aspect-ratio").textContent = `Соотношение сторон: ${aspectRatio}`;
                    document.getElementById("resolution").textContent = `Оригинальное разрешение: ${resolution}`;
                    document.getElementById("image-format").textContent = `Формат изображения: ${imageFormat}`;
                };
            };
            reader.readAsDataURL(file);
            document.querySelector('.result-area').classList.add('auto-height');
        }
    });

    document.getElementById('reset-button').addEventListener('click', resetImage);

    let resetAnimationFrame;
    let resetStartTime = 0;
    const resetDuration = 300;

    function resetImage() {
        const startScale = scale;
        const startOriginX = originX;
        const startOriginY = originY;

        resetStartTime = performance.now();
        cancelAnimationFrame(resetAnimationFrame);
        animateReset(startScale, startOriginX, startOriginY);
    }

    function animateReset(startScale, startOriginX, startOriginY) {
        const currentTime = performance.now();
        const elapsedTime = currentTime - resetStartTime;
        const progress = Math.min(elapsedTime / resetDuration, 1);

        scale = startScale + (1 - startScale) * progress;
        originX = startOriginX + (0 - startOriginX) * progress;
        originY = startOriginY + (0 - startOriginY) * progress;

        drawImage();

        if (progress < 1) {
            resetAnimationFrame = requestAnimationFrame(() => animateReset(startScale, startOriginX, startOriginY));
        }
    }

    if (importButton) {
        importButton.addEventListener("click", function () {
            inputFile.click();
        });
    }
});