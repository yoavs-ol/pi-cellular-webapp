function showAlert(message, type) {
    const resultDiv = document.getElementById('result');
    if (resultDiv) {
        resultDiv.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
    }
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}
