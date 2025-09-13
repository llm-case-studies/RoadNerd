document.addEventListener('DOMContentLoaded', async () => {
  try {
    const r = await fetch('/api/status');
    const data = await r.json();
    const statusEl = document.getElementById('status');
    statusEl.textContent = JSON.stringify(data, null, 2);
    const ips = (data.system && data.system.ips) ? data.system.ips : [];
    const conn = document.getElementById('conn');
    if (ips.length) {
      conn.innerHTML = '<pre>Local IPv4 addresses\n' + ips.map(ip => '  - ' + ip + ':8080').join('\n') + '</pre>';
    } else {
      conn.innerHTML = '<pre>No non-loopback IPv4 addresses detected.</pre>';
    }
  } catch (e) {
    document.getElementById('status').textContent = 'Failed to load status: ' + (e && e.toString ? e.toString() : 'error');
  }
});

