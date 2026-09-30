function updateStatus() {
    fetch('/api/status')
        .then(r => r.json())
        .then(data => {
            document.getElementById('state').textContent = data.state || 'N/A';
            document.getElementById('imei').textContent = data.imei || 'N/A';
            document.getElementById('imsi').textContent = data.imsi || 'N/A';
            document.getElementById('iccid').textContent = data.iccid || 'N/A';
            document.getElementById('operator').textContent = data.operator || 'N/A';
            document.getElementById('rat').textContent = data.rat || 'N/A';
            document.getElementById('signal').textContent = data.signal ? `${data.signal}%` : 'N/A';
            document.getElementById('ip').textContent = data.ip || 'N/A';
        })
        .catch(err => {
            console.error('Status poll error:', err);
        });
}

function updateTime() {
    fetch('/api/time')
        .then(r => r.json())
        .then(data => {
            const netTime = new Date(data.network_time);
            document.getElementById('network-time').textContent = netTime.toLocaleString();
            document.getElementById('tz-offset').textContent = data.tz_offset;
            document.getElementById('time-source').textContent = data.source;
        })
        .catch(err => {
            console.error('Time poll error:', err);
        });
}

function syncTime() {
    if (!confirm('Sync system clock from cellular network?')) return;
    
    fetch('/api/time/sync', {method: 'POST'})
        .then(r => r.json())
        .then(data => {
            alert(data.message);
            updateTime();
        })
        .catch(err => {
            alert('Sync failed: ' + err);
        });
}

setInterval(updateStatus, 3000);
setInterval(updateTime, 1000);
updateStatus();
updateTime();
