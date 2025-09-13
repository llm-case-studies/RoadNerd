// RoadNerd API Console JavaScript (extracted from inline scripts)
// Provides the same global behaviors via event wiring to keep HTML clean.

(function(){
  function j(o){ try { return JSON.stringify(o, null, 2); } catch(e){ return String(o); } }
  function headers(){
    const t = document.getElementById('token');
    const h = {'Content-Type':'application/json'};
    const v = t && t.value ? t.value.trim() : '';
    if (v) h['Authorization'] = 'Bearer ' + v;
    return h;
  }
  function showProgress(elementId, message){
    const el = document.getElementById(elementId);
    if (el) el.textContent = message || 'Working...';
  }

  async function callStatus(){
    const r = await fetch('/api/status');
    document.getElementById('statusOut').textContent = j(await r.json());
  }

  async function callDiagnose(){
    const body = {issue: document.getElementById('issue').value};
    if (document.getElementById('diagDebug').checked) body.debug = true;
    const r = await fetch('/api/diagnose', {method:'POST', headers: headers(), body: JSON.stringify(body)});
    document.getElementById('diagOut').textContent = j(await r.json());
  }

  async function callExecute(){
    const r = await fetch('/api/execute', {method:'POST', headers: headers(), body: JSON.stringify({command: document.getElementById('cmd').value, force: document.getElementById('force').checked})});
    document.getElementById('execOut').textContent = j(await r.json());
  }

  async function callBrainstorm(){
    showProgress('brainOut', '🧠 Generating ideas...');
    const body = {issue: document.getElementById('issueIdeas').value, n: parseInt(document.getElementById('nIdeas').value||'5'), creativity: parseInt(document.getElementById('creativity').value||'2')};
    if (document.getElementById('brainDebug').checked) body.debug = true;
    const r = await fetch('/api/ideas/brainstorm', {method:'POST', headers: headers(), body: JSON.stringify(body)});
    document.getElementById('brainOut').textContent = j(await r.json());
  }

  async function callProbe(){
    try {
      const ideasJson = document.getElementById('ideasJSON').value;
      const ideas = JSON.parse(ideasJson);
      const runChecks = document.getElementById('runChecks').checked;
      const r = await fetch('/api/ideas/probe', {method:'POST', headers: headers(), body: JSON.stringify({ideas, run_checks: runChecks})});
      document.getElementById('probeOut').textContent = j(await r.json());
    } catch (e){
      document.getElementById('probeOut').textContent = 'Invalid JSON: ' + e;
    }
  }

  async function callJudge(){
    try {
      const ideas = JSON.parse(document.getElementById('ideasJudge').value);
      const issue = document.getElementById('issueJudge').value || '';
      const r = await fetch('/api/ideas/judge', {method:'POST', headers: headers(), body: JSON.stringify({issue, ideas})});
      document.getElementById('judgeOut').textContent = j(await r.json());
    } catch (e){
      document.getElementById('judgeOut').textContent = 'Invalid JSON: ' + e;
    }
  }

  async function callLLM(){
    showProgress('llmOut', '🧠 LLM processing...');
    const r = await fetch('/api/llm', {method:'POST', headers: headers(), body: JSON.stringify({prompt: document.getElementById('prompt').value})});
    document.getElementById('llmOut').textContent = j(await r.json());
  }

  async function getModel(){
    document.getElementById('modelOut').textContent = '🔄 Loading available models...';
    const r = await fetch('/api/model/list', {headers: headers()});
    const data = await r.json();
    document.getElementById('modelOut').textContent = j(data);
    if (data.available_models) {
      const select = document.getElementById('modelSelect');
      if (select) {
        select.innerHTML = '<option value="">Choose model...</option>';
        data.available_models.forEach(m => {
          const option = document.createElement('option');
          option.value = m.name;
          option.textContent = `${m.name} (${m.size})${m.current ? ' [CURRENT]' : ''}`;
          option.selected = m.current;
          select.appendChild(option);
        });
      }
    }
  }

  async function setModel(){
    const m = document.getElementById('newModel').value || document.getElementById('modelSelect')?.value;
    if (!m) { document.getElementById('modelOut').textContent = 'Please enter or select a model name'; return; }
    document.getElementById('modelOut').textContent = `🔄 Switching to ${m}... (testing model)`;
    const r = await fetch('/api/model/switch', {method:'POST', headers: headers(), body: JSON.stringify({model: m})});
    const data = await r.json();
    document.getElementById('modelOut').textContent = j(data);
    if (data.success) setTimeout(getModel, 500);
  }

  // Standard profiling/test presets
  let testPresets = {};
  async function loadTestPresets(){
    try{
      const r = await fetch('/api/test-presets');
      testPresets = await r.json();
      const pc = document.getElementById('presetCategory');
      pc.innerHTML = '<option value="">Select category...</option>';
      Object.keys(testPresets).forEach(k => { const opt = document.createElement('option'); opt.value=k; opt.textContent=k; pc.appendChild(opt); });
      document.getElementById('presetOut').textContent = 'Test presets loaded! Select a category to see available issues.';
    } catch(e){ document.getElementById('presetOut').textContent = 'Error loading presets: ' + e; }
  }
  function loadCategoryIssues(){
    const category = document.getElementById('presetCategory').value;
    const select = document.getElementById('presetIssue');
    select.innerHTML = '<option value="">Choose an issue to auto-fill...</option>';
    const arr = testPresets[category] || [];
    arr.forEach(issue => { const option = document.createElement('option'); option.value=issue; option.textContent=issue; select.appendChild(option); });
  }
  function usePresetIssue(){
    const issue = document.getElementById('presetIssue').value;
    if (issue) {
      document.getElementById('issueIdeas').value = issue;
      document.getElementById('presetOut').textContent = `Selected: "${issue}" - Ready to test brainstorming!`;
    }
  }
  async function runStandardProfile(){
    document.getElementById('presetOut').textContent = '🧪 Running 5-idea stress test on current model...';
    try{
      const r = await fetch('/api/profile/standard', {method: 'POST', headers: headers()});
      const data = await r.json();
      if (data.error){ document.getElementById('presetOut').textContent = 'Error: ' + data.error; return; }
      const analysis = data.analysis; const metrics = data.performance_metrics;
      let output = `STANDARD PROFILE RESULTS\n\n`;
      output += `Model: ${data.model}\n`;
      output += `Test: "${data.test_issue}"\n\n`;
      output += `PERFORMANCE METRICS:\n`;
      output += `• Response Time: ${metrics.response_time_sec}s\n`;
      output += `• Tokens/Second: ${metrics.tokens_per_second} (${analysis.speed_rating})\n`;
      output += `• Estimated Tokens: ${metrics.estimated_tokens}\n`;
      output += `• CPU Usage: ${metrics.cpu_usage_percent}%\n`;
      output += `• RAM Usage: ${metrics.ram_usage_percent}% (${metrics.ram_used_gb}GB)\n`;
      output += `• Model Size: ${metrics.model_size_disk_gb}GB on disk\n\n`;
      output += `QUALITY ANALYSIS:\n`;
      output += `• Ideas Generated: ${analysis.ideas_generated}/5\n`;
      output += `• Success: ${analysis.success ? '✅ PASS' : '❌ FAIL'}\n`;
      output += `• Production Ready: ${analysis.production_ready ? '✅' : '❌'}\n`;
      document.getElementById('presetOut').textContent = output;
    } catch(e){ document.getElementById('presetOut').textContent = 'Error: ' + e; }
  }

  // Wire up events on load
  document.addEventListener('DOMContentLoaded', () => {
    const bind = (id, fn) => { const el = document.getElementById(id); if (el) el.addEventListener('click', fn); };
    bind('btnStatus', callStatus);
    bind('btnDiagnose', callDiagnose);
    bind('btnExecute', callExecute);
    bind('btnBrainstorm', callBrainstorm);
    bind('btnProbe', callProbe);
    bind('btnJudge', callJudge);
    bind('btnLLM', callLLM);
    bind('btnGetModel', getModel);
    bind('btnSetModel', setModel);
    bind('btnLoadPresets', loadTestPresets);
    bind('btnRunProfile', runStandardProfile);
  });
})();

