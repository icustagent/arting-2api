// static/script.js
$(document).ready(function() {
    // DOM Elements
    const apiKeyInput = $('#api-key');
    const modelSelect = $('#model-select');
    const loraSelect = $('#lora-select');
    const promptInput = $('#prompt-input');
    const negativePromptInput = $('#negative-prompt-input');
    const samplerSelect = $('#sampler-select');
    const ratioGroup = $('#ratio-group');
    const stepsSlider = $('#steps-slider');
    const stepsValue = $('#steps-value');
    const guidanceSlider = $('#guidance-slider');
    const guidanceValue = $('#guidance-value');
    const loraWeightSlider = $('#lora-weight-slider');
    const loraWeightValue = $('#lora-weight-value');
    const countSlider = $('#count-slider');
    const countValue = $('#count-value');
    const seedInput = $('#seed-input');
    const nsfwToggle = $('#nsfw-toggle');
    const generateBtn = $('#generate-btn');
    const imageGrid = $('#image-grid');
    const spinner = $('#spinner');
    const errorMessage = $('#error-message');
    const placeholder = $('#placeholder');

    // Initialize Select2
    loraSelect.select2({
        placeholder: "选择 LoRA 模型...",
        allowClear: true
    });

    // --- Functions ---
    async function populateModels() {
        modelSelect.prop('disabled', true);
        loraSelect.prop('disabled', true);
        generateBtn.prop('disabled', true);
        hideError();

        const apiKey = apiKeyInput.val().trim();
        if (!apiKey) {
            modelSelect.html('<option>请输入API Key</option>');
            return;
        }

        modelSelect.html('<option>正在加载模型...</option>');

        try {
            const response = await fetch('/v1/models', {
                headers: { 'Authorization': `Bearer ${apiKey}` }
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.detail || '获取模型列表失败。');

            // Populate Base Models
            modelSelect.empty();
            result.base_models.forEach(model => {
                modelSelect.append(new Option(model.name, model.id));
            });

            // Populate LoRA Models
            loraSelect.empty();
            for (const [id, name] of Object.entries(result.lora_models)) {
                loraSelect.append(new Option(name, id));
            }
            loraSelect.trigger('change'); // Notify Select2

            modelSelect.prop('disabled', false);
            loraSelect.prop('disabled', false);
            generateBtn.prop('disabled', false);

        } catch (error) {
            showError(`模型加载失败: ${error.message}. 请检查您的 API Key.`);
            modelSelect.html('<option>加载失败</option>');
        }
    }

    async function handleGenerate() {
        const apiKey = apiKeyInput.val().trim();
        if (!apiKey || !promptInput.val().trim()) {
            showError("请确保 API Key 和提示词都已填写。");
            return;
        }

        setLoading(true);

        const payload = {
            model: modelSelect.val(),
            prompt: promptInput.val().trim(),
            negative_prompt: negativePromptInput.val().trim(),
            lora_ids: (loraSelect.val() || []).join(','),
            lora_weight: parseFloat(loraWeightSlider.val()),
            n: parseInt(countSlider.val(), 10),
            size: ratioGroup.find('.active').data('size'),
            sampler: samplerSelect.val(),
            steps: parseInt(stepsSlider.val(), 10),
            guidance: parseFloat(guidanceSlider.val()),
            seed: parseInt(seedInput.val(), 10),
            is_nsfw: nsfwToggle.is(':checked')
        };

        try {
            const response = await fetch('/v1/images/generations', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${apiKey}`
                },
                body: JSON.stringify(payload)
            });

            const result = await response.json();
            if (!response.ok) throw new Error(result.detail || '生成失败，未知错误。');

            if (result.data && result.data.length > 0) {
                displayImages(result.data);
            } else {
                throw new Error('API 返回了成功状态，但没有图片数据。');
            }
        } catch (error) {
            showError(error.message);
        } finally {
            setLoading(false);
        }
    }

    function displayImages(data) {
        imageGrid.empty();
        data.forEach(item => {
            if (item.url) {
                const imgContainer = $('<div>').addClass('image-container');
                const img = $('<img>').attr('src', item.url).attr('alt', 'Generated Image');
                imgContainer.append(img);
                imageGrid.append(imgContainer);
            }
        });
    }

    function setLoading(isLoading) {
        generateBtn.prop('disabled', isLoading);
        spinner.toggleClass('hidden', !isLoading);
        placeholder.toggleClass('hidden', isLoading || imageGrid.children().length > 0);
        if (isLoading) {
            imageGrid.empty();
            hideError();
        }
    }

    function showError(message) {
        errorMessage.text(message).removeClass('hidden');
        imageGrid.empty();
        placeholder.addClass('hidden');
    }

    function hideError() {
        errorMessage.addClass('hidden');
    }

    // --- Event Listeners ---
    apiKeyInput.on('change', populateModels);
    generateBtn.on('click', handleGenerate);

    stepsSlider.on('input', () => stepsValue.text(stepsSlider.val()));
    guidanceSlider.on('input', () => guidanceValue.text(parseFloat(guidanceSlider.val()).toFixed(1)));
    loraWeightSlider.on('input', () => loraWeightValue.text(parseFloat(loraWeightSlider.val()).toFixed(2)));
    countSlider.on('input', () => countValue.text(countSlider.val()));

    ratioGroup.on('click', 'button', function() {
        ratioGroup.find('.active').removeClass('active');
        $(this).addClass('active');
    });

    // --- Initial Load ---
    populateModels();
});
