# Enhanced RoadNerd Profiling System

**Date**: 2025-09-10  
**Enhancement**: Extended `profile-machine.py` with RoadNerd workflow testing and cross-machine comparison  

## ✅ What Was Enhanced

### 🔬 RoadNerd Workflow Testing
Enhanced the profiling script to test **actual RoadNerd workflows** in addition to basic LLM performance:

**New Test Cases:**
1. **Basic Diagnose** - `/api/diagnose` endpoint validation
2. **Single Idea Brainstorm** - Standard 1-idea generation test
3. **Multi-Idea Brainstorm Stress** - **5-idea generation challenge** (the toughest test)
4. **Creative Brainstorm** - High creativity (level 3) testing
5. **Probe Safety** - Read-only command execution testing
6. **Judge Ranking** - Idea scoring and ranking validation

### 📊 Centralized Logging System
**New Logging Locations:**
- **Individual tests**: `/logs/escalation_runs/escalation_HOSTNAME_MODEL_TIMESTAMP.json`
- **Daily summaries**: `/logs/escalation_runs/daily_summary_YYYYMMDD.jsonl`
- **Cross-machine comparison**: Standardized hostname + timestamp format

### 🎯 Key Metrics Tracked
- **Success rate** for all workflow endpoints
- **N-idea generation success** (specifically tests if 5-idea requests work)
- **JSON parsing failures** (tracks small model limitations)
- **Model size categorization** (tiny/small/medium/large/xlarge/xxlarge)
- **Production readiness** (combines success rate + N-idea capability)

## 🚀 Usage Examples

### Test Single Model Workflow
```bash
python3 tools/profile-machine.py --test-workflows --models gpt-oss:20b --roadnerd-url http://localhost:8081
```

### Full Escalation Ladder Test
```bash
python3 tools/profile-machine.py --escalation-test --roadnerd-url http://localhost:8080
```
*Tests: llama3.2:1b → llama3.2:3b → llama3:8b → codellama:13b → gpt-oss:20b*

### Cross-Machine Comparison
```bash
# On MSI Raider
python3 tools/profile-machine.py --escalation-test

# On BeeLink 
python3 tools/profile-machine.py --escalation-test

# On Dell Laptop
python3 tools/profile-machine.py --escalation-test

# Results automatically stored in consistent format for comparison
```

## 📋 Test Results Structure

### Workflow Test Output
```json
{
  "model": "gpt-oss:20b",
  "summary": {
    "success_rate": 0.83,
    "n_idea_generation_success": true,
    "avg_response_time": 12.5,
    "model_size_category": "xlarge",
    "recommended_for_production": true,
    "json_parse_failures": 0
  },
  "workflow_tests": [
    {
      "test_name": "multi_idea_brainstorm_stress",
      "success": true,
      "n_idea_success": true,
      "ideas_requested": 5,
      "ideas_received": 4,
      "response_time": 23.4,
      "stress_test": true
    }
  ]
}
```

### Daily Summary Log (JSONL)
```json
{"timestamp": "2025-09-10T20:54:35", "hostname": "msi-raider", "model": "gpt-oss:20b", "success_rate": 0.83, "n_idea_success": true, "production_ready": true}
{"timestamp": "2025-09-10T21:15:22", "hostname": "beelink-mini", "model": "llama3.2:3b", "success_rate": 0.67, "n_idea_success": false, "production_ready": false}
```

## 🎯 The 5-Idea Generation Challenge

**Why This Test Matters:**
- Small models (1B-3B) typically fail at generating multiple structured ideas
- JSON parsing becomes much harder with complex multi-item responses
- This is the **toughest test** for determining if a model can handle real RoadNerd workflows

**Test Details:**
- Requests 5 diagnostic ideas for "network is unreliable"
- Uses creativity level 2 (balanced)
- Includes debug mode for parsing visibility
- Success criteria: ≥3 ideas actually generated and parsed

## 📂 File Locations

**Enhanced Script:**
- `tools/profile-machine.py` - Enhanced with workflow testing

**Results Storage:**
- `logs/escalation_runs/` - Individual test results
- `logs/escalation_runs/daily_summary_YYYYMMDD.jsonl` - Cross-machine comparison data
- `poc/core/profiles/HOSTNAME.json` - Machine profiles with workflow results

**Configuration:**
- `--roadnerd-url` parameter for testing different server instances
- Automatic model size categorization for analysis
- Hostname-based result organization for multi-machine testing

## 🔧 Technical Implementation

**Added to LLMBenchmark class:**
- `test_roadnerd_workflow()` - Main workflow testing method
- `_run_roadnerd_test()` - Individual endpoint testing
- `_categorize_model_size()` - Model size classification
- `_save_escalation_results()` - Centralized logging

**New Command Line Options:**
- `--test-workflows` - Test RoadNerd endpoints only
- `--escalation-test` - Full escalation ladder with workflows
- `--roadnerd-url` - Specify RoadNerd server URL

## 📊 Expected Results By Model Size

**Tiny (1B)**: Low success rate, N-idea generation fails  
**Small (3B)**: Medium success rate, N-idea generation inconsistent  
**Medium (7B-8B)**: Good success rate, N-idea generation possible  
**Large (13B)**: High success rate, reliable N-idea generation  
**XLarge (20B+)**: Excellent success rate, consistent complex tasks  

## 🚀 Next Steps

1. **Run full escalation ladder** on MSI Raider with all available models
2. **Test on BeeLink, Dell, HP** - Cross-machine performance comparison
3. **Analyze daily summary logs** - Identify optimal model tiers per hardware
4. **Update ESCALATION-RESULTS.md** - Include workflow test results
5. **GPT collaborator integration** - Use this enhanced system for systematic testing

---

**Impact**: Enhanced profiling now tests **real RoadNerd workflows** instead of just basic LLM performance, with the challenging 5-idea generation test specifically targeting the limitations found in smaller models.

*Generated with [Claude Code](https://claude.ai/code)*