# RoadNerd Refactoring Plan

**Date**: 2025-09-10  
**Updated**: 2025-09-12  
**Current State**: roadnerd_server.py = 1789 lines + 272 lines embedded static content  
**Goal**: Modular architecture with comprehensive test coverage + presentation layer separation  

## ✅ Phase 1: Pre-Refactoring Test Coverage (COMPLETED)

**Status**: All tests passing - comprehensive safety net established  
**Test Results**: 15 failures → 0 failures across unit/integration tests

### Required Dependencies
```bash
# Install in virtual environment
source ~/.venvs/rn/bin/activate
pip install pytest pytest-mock requests-mock pytest-cov
```

### 🎉 Test Coverage Achievements

**Files Fixed/Created**:
- `tests/unit/test_llm_interface.py` - ✅ Fixed modular API signatures (125 lines)
- `tests/unit/test_brainstorm_engine.py` - ✅ Fixed instance method calls (363 lines) 
- `tests/integration/test_ideas_endpoints.py` - ✅ Working with flask_client fixtures (91 lines)
- `tests/integration/test_api_endpoints.py` - ✅ All endpoints tested (64 lines)
- `tests/conftest.py` - ✅ Fixed mock infrastructure for modular architecture (55 lines)

**Key Fixes Applied**:
- Changed from static method calls to instance-based: `BrainstormEngine(llm).generate_ideas()`
- Updated import paths: `from modules.brainstorm_engine import BrainstormEngine, Idea`
- Fixed LLMInterface mocking for new API signatures
- All 15 test failures resolved → comprehensive safety net established

### Original Test Requirements (COMPLETED)

#### 1. LLMInterface Tests (100 lines)
**File**: `tests/unit/test_llm_interface.py`
```python
# High Priority - Core functionality
- test_query_ollama_generate_api()      # Standard Llama models
- test_query_ollama_chat_api()          # GPT-OSS models  
- test_auto_chat_api_detection()        # Auto-routing logic
- test_gpt_oss_parameters()             # temp=1.0, top_p=1.0
- test_json_parsing_multiple_strategies() # 4 parsing fallbacks
- test_timeout_handling()               # Large model timeouts
- test_connection_error_handling()      # Ollama offline scenarios
```

#### 2. BrainstormEngine Tests (80 lines)  
**File**: `tests/unit/test_brainstorm_engine.py`
```python
# Critical - N-idea generation logic
- test_single_idea_generation()
- test_n_idea_generation_success()      # 5-idea challenge
- test_n_idea_generation_fallback()     # Graceful degradation
- test_json_parsing_numbered_lists()    # "1. {...} 2. {...}"
- test_creativity_levels()              # 1-3 creativity impact
- test_debug_mode_output()              # Pipeline visibility
```

#### 3. JudgeEngine Tests (60 lines)
**File**: `tests/unit/test_judge_engine.py`  
```python
- test_idea_scoring()                   # Individual idea ranking
- test_bulk_ranking()                   # Multiple ideas sorting
- test_judge_json_parsing()             # Ranking output format
- test_empty_ideas_handling()           # Edge case safety
```

#### 4. API Endpoints Tests (80 lines)
**File**: `tests/integration/test_new_endpoints.py`
```python
# New functionality from recent session
- test_model_switch_endpoint()          # /api/model/switch
- test_model_list_endpoint()            # /api/model/list  
- test_standard_profile_endpoint()      # /api/profile/standard
- test_performance_metrics()            # psutil integration
- test_test_presets_endpoint()          # /api/test-presets
```

### Mock Strategy
```python
# Use requests-mock for Ollama API calls
@requests_mock.Mocker()
def test_llm_interface_mock(m):
    m.post('http://localhost:11434/api/generate', json={'response': 'test'})
    m.post('http://localhost:11434/api/chat', json={'message': {'content': 'test'}})
```

## 🎨 Phase 2: Presentation Layer Refactoring (NEW - URGENT)

**Issue Identified**: roadnerd_server.py contains 272 lines of embedded HTML/CSS/JavaScript  
**Risk**: Continued growth will make core business logic maintenance difficult  
**Priority**: High - should be done before further UI features

### Presentation Layer Analysis
- **Line 204-213**: Home page CSS styles (10 lines)
- **Line 236-250**: Home page JavaScript status loading (15 lines)  
- **Line 567-574**: Log viewer CSS styles (8 lines)
- **Line 595-610**: Log viewer JavaScript functions (16 lines)
- **Line 642-650**: API console CSS styles (9 lines)
- **Line 784-1056**: **Bundle management JavaScript (272 lines)** ⚠️ CRITICAL
- **Total static content**: ~330 lines mixed throughout business logic

### Phase 2A: Static File Extraction Plan
```
poc/core/
├── static/                         # Flask static files
│   ├── css/
│   │   ├── main.css               # Consolidated styles (~50 lines)
│   │   └── bundle-ui.css          # Bundle management styles (~30 lines)
│   └── js/
│       ├── status.js              # Home page status loading (~20 lines)  
│       ├── logs.js                # Log viewer functions (~25 lines)
│       ├── api-console.js         # API testing functions (~100 lines)
│       └── bundle-ui.js           # Bundle management UI (~150 lines)
├── templates/                      # Flask Jinja2 templates
│   ├── base.html                  # Common layout (~30 lines)
│   ├── home.html                  # Status dashboard (~40 lines)
│   ├── logs.html                  # Log viewer (~35 lines) 
│   ├── api-console.html           # API testing interface (~120 lines)
│   └── bundle-ui.html             # Bundle creation interface (~80 lines)
└── roadnerd_server.py             # Business logic only (~1450 lines)
```

### Phase 2A Implementation Steps
1. **Configure Flask for static files**: Add `static_folder='static', template_folder='templates'`
2. **Extract CSS**: Create consolidated stylesheets with consistent design system
3. **Extract JavaScript**: Separate UI logic from Python, maintain API compatibility  
4. **Create Jinja2 templates**: Replace return statements with `render_template()`
5. **Test all UI routes**: Ensure no functionality regression
6. **Expected result**: ~330 lines removed from roadnerd_server.py

### Phase 2A.1: Routes → Templates Mapping (Claude-ready)
- `/` → `templates/home.html`
  - Loads `static/js/status.js`, `static/css/main.css`
  - Renders system/IP card and links to `/api-docs` and bundle UI.
- `/api-docs` → `templates/api_console.html`
  - Loads `static/js/api-console.js`, `static/css/main.css`
  - Provides buttons that call global functions: `callStatus()`, `callDiagnose()`, `callExecute()`, `callBrainstorm()`, `callProbe()`, `callJudge()`, `getModel()`, `setModel()`.
- Bundle UI (currently embedded inside the console) → `templates/bundle-ui.html`
  - Loads `static/js/bundle-ui.js`, `static/css/bundle-ui.css`
  - Exposes: `scanStorage()`, `createBundle()`, `pollBundleStatus()` and a small `showProgress(elId, text)` helper.
- Logs viewer (optional promotion) → `templates/logs.html`
  - Loads `static/js/logs.js`

All pages extend `templates/base.html` with `{% block head %}` and `{% block content %}`.

### Phase 2A.2: Static Assets Contracts (Claude-ready)
- `api-console.js`
  - Must define exactly the global functions used by the UI buttons now.
  - Keep request shapes and headers stable.
- `bundle-ui.js`
  - Implements storage scan, bundle create, and status polling against existing endpoints.
- `status.js` and `logs.js`
  - `status.js` calls `/api/status` on load; `logs.js` targets the logs route you expose.
- CSS
  - Move style attributes to `main.css`/`bundle-ui.css`; preserve dark theme.

### Phase 2A.3: Security Headers and CSP
- Add headers for HTML responses:
  - `Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'`
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Referrer-Policy: no-referrer`
- Rationale: eliminate inline scripts/styles and pin network targets to same-origin.

### Phase 2A.4: Asset Versioning (cache busting)
- Use `url_for('static', filename='js/api-console.js', v=app.config.get('ASSET_VER'))`.
- Set `ASSET_VER` (short hash/timestamp) once at startup.

### Phase 2A.5: Accessibility
- Semantic headings, labels for inputs, focus-visible styles, button elements for actions.

### Phase 2A.6: Acceptance Criteria
- No inline `<script>` or `<style>` remain (except minimal critical CSS if absolutely necessary).
- Pages load with CSP enabled and no console errors.
- Functional parity with current flows.
- `roadnerd_server.py` shrinks by ~300 lines; only route wiring remains.

### Phase 2A.7: Tests (add under RoadNerd/tests/)

Create `tests/integration/test_presentation.py`:
```python
def test_home_serves(template_client):
    r = template_client.get('/')
    assert r.status_code == 200
    assert b'/static/js/status.js' in r.data

def test_api_docs_serves(template_client):
    r = template_client.get('/api-docs')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert '/static/js/api-console.js' in body
    assert '<script>' not in body or 'src=' in body  # no inline scripts

def test_bundle_ui_serves(template_client):
    r = template_client.get('/bundle-ui')
    assert r.status_code == 200
    assert b'/static/js/bundle-ui.js' in r.data

def test_static_assets_content_type(template_client):
    js = template_client.get('/static/js/api-console.js')
    assert js.status_code == 200
    assert js.headers['Content-Type'].startswith('application/javascript')
```

Create `tests/security/test_headers.py`:
```python
def test_csp_headers(template_client):
    for path in ['/', '/api-docs', '/bundle-ui']:
        r = template_client.get(path)
        csp = r.headers.get('Content-Security-Policy')
        assert csp and "default-src 'self'" in csp
        assert r.headers.get('X-Content-Type-Options') == 'nosniff'
        assert r.headers.get('X-Frame-Options') == 'DENY'
```

Pytest fixture (add to `tests/conftest.py`):
```python
import pytest
from RoadNerd.poc.core.roadnerd_server import app as flask_app

@pytest.fixture()
def template_client():
    flask_app.config['TESTING'] = True
    with flask_app.test_client() as c:
        yield c
```

## 🏗️ Phase 2B: Modular Refactoring  

### Target Directory Structure (Updated)
```
poc/core/
├── roadnerd_server.py              # Flask app only (~200 lines) 
├── static/ & templates/            # Presentation layer (Phase 2A)
├── modules/
│   ├── __init__.py
│   ├── llm_interface.py            # LLMInterface class (~300 lines)
│   ├── system_diagnostics.py       # SystemDiagnostics (~200 lines)  
│   ├── brainstorm_engine.py        # BrainstormEngine + Idea (~400 lines)
│   ├── judge_engine.py             # JudgeEngine (~200 lines)
│   ├── command_executor.py         # CommandExecutor (~150 lines)
│   ├── performance_metrics.py      # psutil monitoring (~100 lines)
│   └── logging_utils.py            # Centralized logging (~100 lines)
├── api/
│   ├── __init__.py
│   ├── routes.py                   # All Flask routes (~600 lines)
│   └── models.py                   # Data classes (~100 lines)
```

### Refactoring Order (Risk-Minimized)
1. **SystemDiagnostics** (lowest risk - existing tests)
2. **CommandExecutor** (medium risk - existing tests)  
3. **LLMInterface** (high risk - NEW tests required)
4. **BrainstormEngine** (highest risk - core business logic)
5. **JudgeEngine** (high risk - ranking logic)
6. **API Routes** (medium risk - integration tests exist)

### Migration Steps Per Module
1. Extract class to new file
2. Add imports to roadnerd_server.py  
3. Run full test suite
4. Test API endpoints manually
5. Update imports in other modules
6. Commit incremental change

---

## 📘 Post-Refactor Specs (Defer implementation until Phase 2A completes)

### Spec A: GPT‑OSS Reliability Profile (No code changes now)
Goals
- Deterministic, parseable idea generation for GPT‑OSS models.

Contract
- Chat API with JSON mode:
  - Use `/api/chat` with `options.format = "json"` when `model.startswith('gpt-oss')`.
  - Append to prompt: "Return ONLY a JSON array with exactly N items and no prose."
- Token budget:
  - `num_predict >= max(768, N*180)` for GPT‑OSS 20B; smaller budget + stricter schema for 1B.
- One-shot repair:
  - If `< N` ideas parsed, send a repair prompt with the same constraints asking to re-output exactly N items.
- Small-model profile (`:1b`):
  - `temperature=0.2`, `top_p=0.9`, `repeat_penalty=1.2`, reduced schema, seed 2–3 domain checks, optional two‑pass.

Acceptance Tests (to add later)
```python
def test_gpt_oss_uses_chat_json(mock_requests):
    # assert /api/chat called with options.format == 'json'

def test_num_predict_budget_applied():
    # assert num_predict >= max(768, N*180)

def test_repair_pass_triggers_on_short_output():
    # simulate 3/5 ideas parsed, expect a second call with repair prompt
```

### Spec B: Bundling Continuation (No code changes now)
Goals
- Move orchestration into a module; persist status; add CLI; validate targets.

Planned Structure
```
poc/core/modules/bundling.py      # scan, validate, create, status persist
poc/core/api/bundle.py            # blueprint wiring endpoints
tools/make_portable_bundle.sh     # heavy lifting remains here
```

Contracts
- Status persistence: write JSON to `$RN_LOG_DIR/e2e/YYYYMMDD/<run_id>/bundle/status.json` with {status, progress, message}.
- Path validation: target must be writable, on a mounted device, with sufficient free space; reject traversal.
- CLI (later): `roadnerd-bundle list|create|status` wrappers over the module.

Acceptance Tests (to add later)
```python
def test_bundle_validation_blocks_bad_paths(tmp_path):
    # invalid path or unwritable parent → 400

def test_bundle_status_persists(tmp_path):
    # simulate progress, assert status.json updated

def test_api_scan_create_status(flask_client, tmp_mount):
    # happy path scan→create→status
```

Non-Goals Now
- Changing business logic, LLM calls, or shell script internals. Focus Phase 2A first.

## 🧪 Phase 3: Enhanced Testing

### Test Coverage Goals
- **Unit Tests**: 80%+ coverage on business logic
- **Integration Tests**: Full API workflow coverage  
- **Mocking**: All external dependencies (Ollama, system commands)
- **CI Pipeline**: Automated testing on commits

### Performance Test Integration
```python
# Extend existing profile-machine.py workflow tests
def test_modular_performance():
    """Ensure refactored modules maintain performance"""
    # Compare pre/post refactoring metrics
    assert response_time_change < 5%  # Max 5% slowdown acceptable
```

## 📋 GPT-J Task Checklist

### Immediate Tasks (High Priority)
- [ ] Install pytest ecosystem in virtual environment
- [ ] Create `tests/unit/test_llm_interface.py` with 7 critical test functions
- [ ] Create `tests/unit/test_brainstorm_engine.py` with N-idea generation tests  
- [ ] Create `tests/unit/test_judge_engine.py` with ranking tests
- [ ] Create `tests/integration/test_new_endpoints.py` for recent API additions
- [ ] Set up proper mocking for Ollama API calls
- [ ] Create pytest configuration file

### Validation Criteria
```bash
# Must pass before refactoring begins
pytest tests/ -v --cov=roadnerd_server --cov-report=term-missing
# Target: >70% coverage on core classes
```

### Risk Mitigation
- **Backup Strategy**: Tag current working state before refactoring
- **Rollback Plan**: Keep monolithic version as roadnerd_server_legacy.py
- **Incremental Testing**: Test after each module extraction
- **Production Validation**: Run full escalation ladder test after refactoring

## 🚀 Success Metrics

### Code Quality
- File size: largest file <500 lines  
- Maintainability: Each module single responsibility
- Testability: >80% unit test coverage

### Performance
- Response time: <5% degradation  
- Memory usage: No significant increase
- Startup time: <10% increase acceptable

### Development Velocity  
- Parallel development capability
- Easier debugging with isolated modules
- Faster test execution with targeted testing

## 📦 Phase 3: Bundle Management System (NEW - IMPLEMENTED)

**Status**: Complete web UI-driven bundle creation system implemented  
**Files Modified**: roadnerd_server.py (+280 lines), tools/make_portable_bundle.sh (enhanced)

### Bundle Management Features
- **USB Storage Detection**: Automatic scanning for connected storage devices
- **Real-time Progress**: Threading-based bundle creation with status polling  
- **Offline Dependencies**: True offline Python package bundling using `pip download`
- **Web UI**: Complete management interface accessible via `/bundle-ui`
- **API Endpoints**: RESTful bundle creation and status monitoring

### Key Implementation Details

#### API Endpoints Added
```python
@app.route('/api/bundle/storage/scan', methods=['GET'])     # USB detection
@app.route('/api/bundle/create', methods=['POST'])          # Bundle creation  
@app.route('/api/bundle/status', methods=['GET'])           # Progress monitoring
```

#### Enhanced Bundle Script Features
- **Modular Architecture Support**: Copies entire `modules/` directory
- **True Offline Dependencies**: Downloads .whl files, uses `--no-index --find-links`
- **Flexible Model Selection**: Supports multiple Ollama model variants
- **Installation Automation**: Complete setup script for patient machines

#### Bundle Creation Workflow
1. **Connect USB storage** (500GB+ recommended for models)
2. **Access `/bundle-ui`** via web interface  
3. **Select storage device** from auto-detected list
4. **Configure bundle options**: Models, dependencies, components
5. **Monitor real-time progress** via JavaScript status updates
6. **Deploy on patient machine**: Run `install_roadnerd.sh` from USB

### Critical Offline Dependency Fix
**Problem**: Original bundling used `pip install` requiring internet on patient machines  
**Solution**: Implemented true offline bundling:
```bash
# Bundle creation (on connected machine)
pip download -r requirements.txt -d bundle/dependencies/

# Installation (on offline patient machine)  
pip install --no-index --find-links dependencies/ -r requirements.txt
```

### Bundle Structure
```
roadnerd_bundle_YYYYMMDD_HHMMSS/
├── poc/core/                    # Complete RoadNerd application
├── dependencies/                # Offline Python wheels (.whl files)
├── models/                      # Ollama model cache (optional)
├── tools/                       # Utility scripts
├── install_roadnerd.sh          # Automated installation script  
├── requirements.txt             # Python dependencies
└── README.md                    # Deployment instructions
```

---

**Next Steps**: 
1. **URGENT**: Phase 2A - Extract presentation layer (~330 lines) before further UI growth
2. Phase 2B - Continue modular refactoring with established test safety net
3. Phase 3 - Enhanced testing and CI pipeline integration

*Generated with [Claude Code](https://claude.ai/code)*
