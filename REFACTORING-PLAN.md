# RoadNerd Refactoring Plan

**Date**: 2025-09-10  
**Current State**: roadnerd_server.py = 78KB, ~2000 lines  
**Goal**: Modular architecture with comprehensive test coverage  

## 🎯 Phase 1: Pre-Refactoring Test Coverage (GPT-J Task)

### Required Dependencies
```bash
# Install in virtual environment
source ~/.venvs/rn/bin/activate
pip install pytest pytest-mock requests-mock pytest-cov
```

### Critical Tests Needed (300+ lines)

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

## 🏗️ Phase 2: Modular Refactoring  

### Target Directory Structure
```
poc/core/
├── roadnerd_server.py              # Flask app only (~200 lines)
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

---

**Next Steps**: Hand off Phase 1 testing to GPT-J, then proceed with modular refactoring once safety net is established.

*Generated with [Claude Code](https://claude.ai/code)*