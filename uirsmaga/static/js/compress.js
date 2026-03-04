document.addEventListener("DOMContentLoaded", function () {
    const inputFile = document.createElement("input");
    inputFile.type = "file";
    inputFile.accept = "image/*";
    inputFile.style.display = "none";

    const importButton = document.getElementById("import-button");
    const imageDisplay = document.querySelector(".upload-area");
    const resultDisplay = document.querySelector(".result-area");
    const qualitySlider = document.getElementById("contour-range");
    const rangeValueDisplay = document.getElementById("range-value");
    const saveButton = document.getElementById("save-button");

    let debounceTimeout;

    const tooltip = document.createElement("div");
    tooltip.classList.add("custom-tooltip");
    tooltip.textContent = "Нажмите для увеличения изображения";
    document.body.appendChild(tooltip);

    const popup = document.createElement("div");
    popup.classList.add("popup");
    document.body.appendChild(popup);

    const popupContent = document.createElement("div");
    popupContent.classList.add("popup-content");
    popup.appendChild(popupContent);

    const popupClose = document.createElement("span");
    popupClose.classList.add("popup-close");
    popupClose.textContent = "×";
    popupContent.appendChild(popupClose);

    const popupImage = document.createElement("img");
    popupContent.appendChild(popupImage);

    function openPopup() {
        popup.style.display = "flex";
        setTimeout(() => popup.classList.add("show"), 10);
    }

    function closePopup() {
        popup.classList.remove("show");
        setTimeout(() => (popup.style.display = "none"), 300);
    }

    popup.addEventListener("click", function (event) {
        if (!popupContent.contains(event.target)) {
            closePopup();
        }
    });

    popupClose.addEventListener("click", closePopup);

    if (importButton) {
        importButton.addEventListener("click", function () {
            inputFile.click();
        });
    }

    inputFile.addEventListener("change", function (event) {
        const file = event.target.files[0];
        if (file) {
            const fileSize = (file.size / 1024).toFixed(2);
            const img = new Image();
            img.src = URL.createObjectURL(file);

            img.onload = function () {
                document.getElementById("file-size").textContent = `Размер, кб: ${fileSize}`;
                document.getElementById("aspect-ratio").textContent = `Соотношение сторон: ${(img.width / img.height).toFixed(2)}`;
                document.getElementById("resolution").textContent = `Оригинальное разрешение: ${img.width}x${img.height}`;
                document.getElementById("image-format").textContent = `Формат изображения: ${file.type}`;

                imageDisplay.style.backgroundColor = "#FFFFFF";
                imageDisplay.innerHTML = "";
                imageDisplay.appendChild(img);

                img.style.width = "100%";
                img.style.height = "100%";
                img.style.objectFit = "contain";
                img.style.borderRadius = "10px";
                img.style.cursor = "pointer";

                addTooltip(img);

                img.addEventListener("click", function () {
                    popupImage.src = img.src;
                    openPopup();
                });

                updateCompressedImage();
            };
        }
    });

    qualitySlider.addEventListener("input", () => {
        const value = qualitySlider.value;
        const percentage = value + '%';

        // Обновляем заполненную часть ползунка с изменением градиента
        qualitySlider.style.background = `linear-gradient(to right, #4d4d4d 0%, #4d4d4d ${percentage}, #d9d9d9 ${percentage})`;

        // Отображаем текущее значение ползунка
        rangeValueDisplay.textContent = value;

        // Обновляем сжатое изображение с новым значением качества
        updateCompressedImage();
    });

    async function updateCompressedImage() {
        clearTimeout(debounceTimeout);
        debounceTimeout = setTimeout(async () => {
            const file = inputFile.files[0];
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

                const compressedImage = new Image();
                compressedImage.src = imgURL;
                compressedImage.alt = "Сжатое изображение";

                compressedImage.onload = function () {
                    const compressedSize = (blob.size / 1024).toFixed(2);
                    document.getElementById("file-size1").textContent = `Размер, кб: ${compressedSize}`;
                    document.getElementById("aspect-ratio1").textContent = document.getElementById("aspect-ratio").textContent;
                    document.getElementById("resolution1").textContent = document.getElementById("resolution").textContent;
                    document.getElementById("image-format1").textContent = `Формат изображения: ${blob.type || "N/A"}`;

                    resultDisplay.style.backgroundColor = "#FFFFFF";
                    resultDisplay.innerHTML = "";
                    resultDisplay.appendChild(compressedImage);

                    compressedImage.style.width = "100%";
                    compressedImage.style.height = "100%";
                    compressedImage.style.objectFit = "contain";
                    compressedImage.style.borderRadius = "10px";
                    compressedImage.style.cursor = "pointer";

                    addTooltip(compressedImage);

                    compressedImage.addEventListener("click", function () {
                        popupImage.src = compressedImage.src;
                        openPopup();
                    });

                    saveButton.disabled = false;
                    saveButton.addEventListener("click", function () {
                        downloadProcessedImage(compressedImage.src);
                    });
                };
            } catch (error) {
                console.error('Ошибка:', error);
                alert("Ошибка сжатия: " + error.message);
            }
        }, 300);
    }

    function downloadProcessedImage(imageSrc) {
        const link = document.createElement("a");
        link.href = imageSrc;
        link.download = "compressed-image.png";
        link.click();
    }

    function addTooltip(image) {
        image.addEventListener("mouseenter", function (e) {
            tooltip.style.display = "block";
            tooltip.style.opacity = "1";
            positionTooltip(e);
        });

        image.addEventListener("mousemove", positionTooltip);

        image.addEventListener("mouseleave", function () {
            tooltip.style.opacity = "0";
            setTimeout(() => {
                tooltip.style.display = "none";
            }, 300);
        });
    }

    function positionTooltip(event) {
        const tooltipWidth = tooltip.offsetWidth;
        const tooltipHeight = tooltip.offsetHeight;
        const pageX = event.pageX;
        const pageY = event.pageY;

        tooltip.style.left = `${pageX - tooltipWidth / 2}px`;
        tooltip.style.top = `${pageY - tooltipHeight - 10}px`;
    }
});
