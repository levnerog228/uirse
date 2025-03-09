document.addEventListener("DOMContentLoaded", function () {
    const inputFile = document.createElement("input");
    inputFile.type = "file";
    inputFile.accept = "image/*";
    inputFile.style.display = "none";

    const importButton = document.getElementById("import-button");
    const resultDisplay = document.querySelector(".result-area");

    let canvas, ctx, img = new Image();
    let startX, startY, isDrawing = false;
    let selectedRegions = [];  // Массив для хранения выделенных пользователем областей
    let foundRegions = [];     // Массив для хранения найденных областей

    // Обработчик кнопки очистки всех областей с подтверждением
    document.getElementById('clear-button').addEventListener('click', clearAllRegions);

    function clearAllRegions() {
        // Показываем предупреждение
        const isConfirmed = confirm('Вы уверены, что хотите удалить все области? Это действие нельзя отменить.');
        if (isConfirmed) {
            // Очищаем и пользовательские, и найденные сервером области
            selectedRegions = [];
            foundRegions = [];
            redrawCanvas();  // Перерисовываем холст, чтобы он стал чистым
            alert('Все области очищены!');
        } else {
            alert('Удаление областей отменено.');
        }
    }

    function initCanvas() {
        canvas = document.createElement('canvas');
        canvas.style.maxWidth = "100%";
        canvas.style.maxHeight = "100%";
        resultDisplay.innerHTML = '';
        resultDisplay.appendChild(canvas);
        ctx = canvas.getContext('2d');

        const aspectRatio = img.width / img.height;
        canvas.width = resultDisplay.clientWidth;
        canvas.height = canvas.width / aspectRatio;

        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

        canvas.addEventListener('mousedown', startSelection);
        canvas.addEventListener('mousemove', drawSelection);
        canvas.addEventListener('mouseup', endSelection);
    }

    inputFile.addEventListener("change", function (event) {
        const file = event.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function (e) {
                img.src = e.target.result;
                img.onload = () => {
                    initCanvas();
                    selectedRegions = [];
                    foundRegions = [];
                };
            };
            reader.readAsDataURL(file);
        }
    });

    if (importButton) {
        importButton.addEventListener("click", function () {
            inputFile.click();
        });
    }

    function startSelection(e) {
        const rect = canvas.getBoundingClientRect();
        startX = e.clientX - rect.left;
        startY = e.clientY - rect.top;
        isDrawing = true;
    }

    function drawSelection(e) {
        if (!isDrawing) return;

        const rect = canvas.getBoundingClientRect();
        const currentX = e.clientX - rect.left;
        const currentY = e.clientY - rect.top;

        redrawCanvas();

        const width = currentX - startX;
        const height = currentY - startY;

        ctx.strokeStyle = 'red';
        ctx.lineWidth = 2;
        ctx.strokeRect(startX, startY, width, height);
    }

    function endSelection(e) {
        if (!isDrawing) return;
        isDrawing = false;

        const rect = canvas.getBoundingClientRect();
        const endX = e.clientX - rect.left;
        const endY = e.clientY - rect.top;

        const width = endX - startX;
        const height = endY - startY;

        if (width && height) {
            const newRegion = { startX, startY, width, height, color: getRandomColor() };
            selectedRegions.push(newRegion);
            sendSelectedRegion(newRegion);
        }
    }

    function sendSelectedRegion(region) {
        const scaleX = img.width / canvas.width;
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
            croppedRegion.x, croppedRegion.y,
            croppedRegion.width, croppedRegion.height,
            0, 0,
            croppedRegion.width, croppedRegion.height
        );

        const croppedBase64 = canvasCrop.toDataURL('image/jpeg').split(',')[1];
        const imageBase64 = imageToBase64(img);

        fetch('http://localhost:5000/process_region', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                image: imageBase64,
                template: croppedBase64,
            }),
        })
        .then(response => response.json())
        .then(data => {
            console.log('Похожие области:', data.similarRegions);
            const coloredRegions = data.similarRegions.map(region => ({ ...region, color: region.color || selectedRegions[selectedRegions.length - 1].color }));
            foundRegions = foundRegions.concat(coloredRegions);
            redrawCanvas();
        })
        .catch(error => {
            console.error('Ошибка:', error);
        });
    }

    function redrawCanvas() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

        // Перерисовка выделенных пользователем областей
        selectedRegions.forEach(region => {
            drawRegion(region.startX, region.startY, region.width, region.height, region.color);
        });

        // Перерисовка областей, найденных сервером
        foundRegions.forEach(region => {
            const x = region.x / (img.width / canvas.width);
            const y = region.y / (img.height / canvas.height);
            const width = region.width / (img.width / canvas.width);
            const height = region.height / (img.height / canvas.height);
            drawRegion(x, y, width, height, region.color);
        });
    }

    function drawRegion(x, y, width, height, color) {
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.strokeRect(x, y, width, height);
    }

    function imageToBase64(image) {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        canvas.width = image.width;
        canvas.height = image.height;
        ctx.drawImage(image, 0, 0);
        return canvas.toDataURL('image/jpeg').split(',')[1];
    }

    function getRandomColor() {
        const letters = '0123456789ABCDEF';
        let color = '#';
        for (let i = 0; i < 6; i++) {
            color += letters[Math.floor(Math.random() * 16)];
        }
        return color;
    }
});
