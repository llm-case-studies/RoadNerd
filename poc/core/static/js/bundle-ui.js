(function(){
  function headers(){ return {'Content-Type':'application/json'} }

  async function scanStorage(){
    const out = document.getElementById('storageList');
    out.textContent = 'Scanning...';
    try {
      const r = await fetch('/api/bundle/storage/scan');
      const data = await r.json();
      if (data.error){ out.textContent = data.error; return; }
      const drives = (data.drives||[]).map(d=>`- ${d.name} (${d.size}) ${d.mountpoint}`).join('\n');
      out.innerHTML = `<pre>${drives||'(no removable drives detected)'}</pre>`;
    } catch(e){ out.textContent = 'Scan failed: '+e; }
  }

  async function createBundle(){
    const target = document.getElementById('targetPath').value.trim();
    const include_models = document.getElementById('includeModels').checked;
    const include_deps = document.getElementById('includeDeps').checked;
    const out = document.getElementById('bundleOut');
    if (!target){ out.textContent = 'Please provide a target path.'; return; }
    out.textContent = 'Starting bundle...';
    try {
      const r = await fetch('/api/bundle/create', {method:'POST', headers: headers(), body: JSON.stringify({target_path: target, include_models, include_deps})});
      const data = await r.json();
      if (data.error){ out.textContent = data.error; return; }
      document.getElementById('bundleProgress').style.display = 'block';
      pollBundleStatus();
    } catch(e){ out.textContent = 'Create failed: '+e; }
  }

  async function pollBundleStatus(){
    try {
      const r = await fetch('/api/bundle/status');
      const data = await r.json();
      const pct = Math.max(0, Math.min(100, data.progress||0));
      document.getElementById('progressBar').style.width = pct + '%';
      document.getElementById('progressText').textContent = data.message || '';
      if ((data.status||'') === 'running') setTimeout(pollBundleStatus, 800);
    } catch(e){ console.error('status poll failed', e); }
  }

  // Wire up buttons
  document.addEventListener('DOMContentLoaded', () => {
    const s = document.getElementById('scanBtn'); if (s) s.addEventListener('click', scanStorage);
    const c = document.getElementById('createBtn'); if (c) c.addEventListener('click', createBundle);
  });
})();

