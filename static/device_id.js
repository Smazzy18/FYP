function generateDeviceId() {
    const navigator_info = window.navigator;
    const screen_info = window.screen;
    let fingerprint = '';

    // Browser and OS information
    fingerprint += navigator_info.userAgent.replace(/\D+/g, '');
    fingerprint += navigator_info.language.replace(/\D+/g, '');
    fingerprint += navigator_info.hardwareConcurrency || '';
    fingerprint += navigator_info.deviceMemory || '';
    fingerprint += navigator_info.platform || '';

    // Screen information
    fingerprint += screen_info.colorDepth;
    fingerprint += screen_info.pixelDepth;
    fingerprint += screen_info.width;
    fingerprint += screen_info.height;
    fingerprint += screen_info.availWidth;
    fingerprint += screen_info.availHeight;

    // Time and performance
    fingerprint += new Date().getTimezoneOffset();
    fingerprint += performance.now().toString().replace('.', '');

    // Canvas fingerprinting
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    ctx.textBaseline = "top";
    ctx.font = "14px 'Arial'";
    ctx.textBaseline = "alphabetic";
    ctx.fillStyle = "#f60";
    ctx.fillRect(125,1,62,20);
    ctx.fillStyle = "#069";
    ctx.fillText("Hello, world!", 2, 15);
    ctx.fillStyle = "rgba(102, 204, 0, 0.7)";
    ctx.fillText("Hello, world!", 4, 17);
    fingerprint += canvas.toDataURL().replace(/\D+/g, '');

    // Generate a 48-bit number (12 hexadecimal characters)
    const hexString = parseInt(fingerprint.substr(0, 15)).toString(16).padStart(12, '0');

    // Convert to MAC address format
    const macAddress = hexString.match(/.{1,2}/g).join(':');

    return macAddress.toUpperCase();
}

function setDeviceId() {
    if (!localStorage.getItem('device_id')) {
        localStorage.setItem('device_id', generateDeviceId());
    }
}

function getDeviceId() {
    return localStorage.getItem('device_id');
}
