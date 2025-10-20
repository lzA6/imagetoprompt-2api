document.addEventListener('DOMContentLoaded', () => {
    const apiKeyInput = document.getElementById('api-key');
    const imageUploader = document.getElementById('image-uploader');
    const imageUploadInput = document.getElementById('image-upload-input');
    const imagePreview = document.getElementById('image-preview');
    const uploadPlaceholder = document.getElementById('upload-placeholder');
    const generateBtn = document.getElementById('generate-btn');
    const btnText = document.getElementById('btn-text');
    const btnSpinner = document.getElementById('btn-spinner');
    const resultPlaceholder = document.getElementById('result-placeholder');
    const resultContainer = document.getElementById('result-container');
    const promptOutput = document.getElementById('prompt-output');
    const copyBtn = document.getElementById('copy-btn');
    const errorMessage = document.getElementById('error-message');
    const languageSelect = document.getElementById('language-select');
    const structuredPromptSelect = document.getElementById('structured-prompt-select');

    let selectedFile = null;

    // --- 语言选项 ---
    const supportedLanguages = {
        "English": "en", "Español": "es", "Deutsch": "de", "Français": "fr",
        "Português": "pt", "简体中文": "zh-CN", "繁體中文": "zh-TW", "العربية": "ar",
        "Русский": "ru", "日本語": "ja", "한국어": "ko"
    };

    // --- 初始化 ---
    function initialize() {
        // 填充语言下拉框
        for (const [name, code] of Object.entries(supportedLanguages)) {
            const option = document.createElement('option');
            option.value = code;
            option.textContent = name;
            if (code === 'en') {
                option.selected = true;
            }
            languageSelect.appendChild(option);
        }
    }

    // --- 事件监听 ---
    imageUploader.addEventListener('click', () => imageUploadInput.click());
    imageUploader.addEventListener('dragover', (e) => {
        e.preventDefault();
        imageUploader.classList.add('dragover');
    });
    imageUploader.addEventListener('dragleave', () => imageUploader.classList.remove('dragover'));
    imageUploader.addEventListener('drop', (e) => {
        e.preventDefault();
        imageUploader.classList.remove('dragover');
        const file = e.dataTransfer.files[0];
        handleFile(file);
    });
    imageUploadInput.addEventListener('change', (e) => handleFile(e.target.files[0]));
    generateBtn.addEventListener('click', handleGenerate);
    copyBtn.addEventListener('click', copyToClipboard);

    // --- 核心函数 ---
    function handleFile(file) {
        if (!file || !file.type.startsWith('image/')) {
            showError("请上传有效的图片文件。");
            return;
        }
        selectedFile = file;
        const reader = new FileReader();
        reader.onload = (e) => {
            imagePreview.src = e.target.result;
            imagePreview.classList.remove('hidden');
            uploadPlaceholder.classList.add('hidden');
            hideError();
        };
        reader.readAsDataURL(file);
    }

    async function handleGenerate() {
        const apiKey = apiKeyInput.value.trim();
        if (!selectedFile) {
            showError("请先上传一张图片。");
            return;
        }
        if (!apiKey) {
            showError("请输入 API Key。");
            return;
        }

        setLoading(true);

        const formData = new FormData();
        formData.append('image', selectedFile);
        formData.append('language', languageSelect.value);
        formData.append('structured_prompt', structuredPromptSelect.value);

        try {
            const response = await fetch('/api/generate-from-upload', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${apiKey}`
                },
                body: formData
            });

            const result = await response.json();
            if (!response.ok) {
                throw new Error(result.detail || '生成失败，未知错误。');
            }

            displayResult(result.prompt);

        } catch (error) {
            showError(error.message);
        } finally {
            setLoading(false);
        }
    }

    function displayResult(prompt) {
        resultPlaceholder.classList.add('hidden');
        resultContainer.classList.remove('hidden');
        promptOutput.textContent = prompt;
    }

    function copyToClipboard() {
        navigator.clipboard.writeText(promptOutput.textContent).then(() => {
            copyBtn.textContent = '已复制!';
            setTimeout(() => { copyBtn.textContent = '复制'; }, 2000);
        }).catch(err => {
            showError('复制失败: ' + err);
        });
    }

    // --- UI 状态辅助函数 ---
    function setLoading(isLoading) {
        generateBtn.disabled = isLoading;
        btnText.style.display = isLoading ? 'none' : 'inline';
        btnSpinner.classList.toggle('hidden', !isLoading);
        if (isLoading) {
            hideError();
            resultContainer.classList.add('hidden');
            resultPlaceholder.classList.remove('hidden');
        }
    }

    function showError(message) {
        errorMessage.textContent = message;
        errorMessage.classList.remove('hidden');
    }

    function hideError() {
        errorMessage.classList.add('hidden');
    }

    // --- 页面加载后执行 ---
    initialize();
});
