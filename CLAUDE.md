# Claude Code Collaboration Guide for RoadNerd

## Project Overview
RoadNerd is a BACKLOG++ framework implementation for systematic LLM evaluation in diagnostic troubleshooting. The system provides brainstorming and judging capabilities for IT support scenarios.

## Development Workflow

### 1. **Claude Code + GPT Collaboration Pattern**
- **GPT**: Initial implementation and architectural decisions
- **Claude Code**: Testing, validation, debugging, and refinement
- **Handoff Protocol**: GPT documents changes, Claude continues with testing and fixes
- **Result**: Complementary strengths - GPT for architecture, Claude for systematic testing

### 2. **Testing & Validation Approach**
```bash
# Primary test commands
curl -X POST http://127.0.0.1:8080/api/ideas/brainstorm \
  -H "Content-Type: application/json" \
  -d '{"issue": "laptop overheating", "n": 5, "debug": true}'

# Model testing across sizes
RN_MODEL=llama3.2:1b python3 poc/core/roadnerd_server.py
RN_MODEL=llama3.2:3b python3 poc/core/roadnerd_server.py  
RN_MODEL=qwen2.5:7b python3 poc/core/roadnerd_server.py
RN_MODEL=codellama:13b python3 poc/core/roadnerd_server.py
```

### 3. **Debugging Methodology**
1. **Systematic Model Escalation**: Test 1B→3B→7B→13B to isolate capability vs parsing issues
2. **API Response Analysis**: Use `/api-docs` for interactive testing
3. **Debug Mode**: Add `"debug": true` to see complete pipeline: classification → retrieval → brainstorming
4. **Direct Ollama Testing**: Bypass server to test raw model capabilities
5. **Token Allocation Analysis**: Monitor `num_predict` vs actual response length

### 4. **Documentation Standards**
- **Session Progress**: `docs/SESSION-PROGRESS-YYYY-MM-DD.md` for major feature work
- **TODO Management**: `docs/todo-shortterm.md` with completed/pending status
- **Technical Details**: Include before/after comparisons, code snippets, impact metrics
- **Commit Messages**: Detailed with context and technical reasoning

### 5. **Common Issues & Solutions**

#### **N-Idea Generation Failures**
- **Symptom**: Requesting N ideas but getting 1 fallback response
- **Root Cause**: Insufficient token allocation (`num_predict` too small)
- **Solution**: Dynamic scaling `max(512, n * 120)` tokens per idea
- **Test**: Verify with different N values (1-10)

#### **JSON Parsing Issues**
- **Symptom**: Models generate valid JSON but parser fails
- **Root Cause**: Models output numbered lists `1. {...} 2. {...}` not clean arrays
- **Solution**: Multiple parsing strategies (direct JSON, fenced blocks, numbered lists, balanced braces)
- **Test**: Check different model outputs and parsing success rates

#### **Category Classification Narrow Scope**
- **Symptom**: "Laptop doesn't work" always classified as network issue
- **Root Cause**: Limited category set focused on networking
- **Solution**: Expand to comprehensive categories (power, boot, hardware, physical, software, user, network, performance, system)
- **Test**: Try diverse problem descriptions and verify category accuracy

### 6. **Key Technical Components**

#### **Core Files**
- `poc/core/roadnerd_server.py`: Main API server with brainstorm/judge endpoints
- `poc/core/classify.py`: Category classification with embedding fallback to heuristics
- `poc/core/prompts/brainstorm.base.txt`: Template for idea generation prompts

#### **Architecture Patterns**
- **Template-based Prompting**: External prompt files with variable substitution
- **Multi-strategy Parsing**: Robust JSON extraction from various LLM output formats
- **Debug Pipeline Visibility**: Complete step-by-step processing transparency
- **Dynamic Resource Allocation**: Token limits scale with request complexity

### 7. **PR & Commit Guidelines**
```bash
# Commit format
git add -A
git commit -m "$(cat <<'EOF'
Enhanced N-idea generation + multi-step debug diagnostics

- Fix token allocation: Dynamic scaling max(512, n * 120)
- Add 4 JSON parsing strategies including numbered lists  
- Expand categories: 5 networking → 9 comprehensive
- Implement debug mode: classification → retrieval → brainstorming visibility

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"

# PR preparation
git push origin feature/branch-name
# Use PR-TEMPLATE.md for comprehensive description
```

### 8. **Environment Setup**
```bash
# Activate virtual environment
source ~/.venvs/rn/bin/activate

# Start server with specific model
RN_MODEL=codellama:13b RN_NUM_PREDICT=1024 python3 poc/core/roadnerd_server.py

# Test API endpoints
curl http://127.0.0.1:8080/api-docs  # Interactive documentation
```

### 9. **Next Steps Protocol**
- Always update `docs/todo-shortterm.md` after major work
- Document technical decisions in session progress files
- Test across multiple model sizes before finalizing features
- Use debug mode for troubleshooting and validation
- Commit with detailed technical context

This workflow has proven effective for systematic LLM system development with high reliability and comprehensive testing coverage.