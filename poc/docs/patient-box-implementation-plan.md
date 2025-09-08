# Patient Box Implementation Plan: Context-Aware Client

**Target**: MSI Laptop (Patient Box) - `/home/alex/Projects/iHomeNerd/RoadNerd/poc/core/roadnerd_client.py`  
**Implementer**: Gemini  
**Scope**: Client-side modifications for multi-line input and context awareness  
**Complexity**: Low-to-Medium (focused changes to existing working code)

## Overview

Transform the current single-line input client into a context-aware conversational interface that can:
- Handle multi-line paste operations naturally
- Detect user intent (information vs problem vs question)
- Maintain conversation context
- Send enriched payloads to the server

## Current State Analysis

**Working Elements** ✅:
- Server connection and auto-discovery (`10.55.0.1:8080`)
- Basic API communication (`/api/diagnose`, `/api/execute`, `/api/status`)
- Interactive command loop
- Special command handling (`status`, `scan`, `execute`, `quit`)

**Problem Area** 🔴:
- **Line 136**: `user_input = input("🤖 RoadNerd> ").strip()`
- **Lines 174-177**: Direct single-line processing without context
- **No conversation memory** between interactions
- **No intent detection** - treats everything as a problem

## Implementation Tasks

### Task 1: Multi-Line Input Handler

**File**: `roadnerd_client.py`  
**Function**: Replace single-line `input()` with paste-friendly multi-line collector  
**Code Location**: Line 136 and new function

```python
def get_multiline_input(self, prompt: str = "🤖 RoadNerd> ") -> str:
    """
    Collect multi-line input until blank line or closing fence.
    Handles paste operations naturally.
    """
    print(prompt, end="", flush=True)
    lines = []
    seen_content = False
    
    while True:
        try:
            line = input()
        except EOFError:
            break
            
        stripped = line.strip()
        
        # Explicit end markers
        if stripped in ("```", "EOF", "END"):
            break
            
        # Empty line after content ends input
        if stripped == "" and seen_content:
            break
            
        if stripped:
            seen_content = True
            
        lines.append(line)
    
    return "\n".join(lines).strip()
```

**Integration Point**: 
- Replace `user_input = input("🤖 RoadNerd> ").strip()` 
- With `user_input = self.get_multiline_input()`

### Task 2: Intent Classification System

**Purpose**: Distinguish between information sharing vs problem reporting  
**Implementation**: Add lightweight pattern matching

```python
import re
from datetime import datetime

def analyze_user_intent(self, text: str) -> dict:
    """Classify user input intent with pattern matching"""
    
    # Information indicators
    info_patterns = [
        r"cat /etc/\w+",                    # Command output
        r"^[A-Za-z0-9._-]+@[A-Za-z0-9._-]+:.*\$",  # Shell prompt
        r"^[A-Z_]+=.*",                     # Environment variables
        r"PRETTY_NAME=|VERSION_ID=|ID=",    # OS release keys
        r"^#|^\$ ",                         # Commented/prompt lines
        r"Here is.*:|Like that:|Output:",   # User presenting info
        r"^====.*====",                     # Delimiter patterns
    ]
    
    # Problem indicators
    problem_patterns = [
        r"not working|broken|fail(ed)?|error|timeout",
        r"how (do|to)|why is|can't|cannot|won't",
        r"help me|fix|diagnose|troubleshoot",
        r"issue|problem|stuck|confused",
    ]
    
    info_score = sum(bool(re.search(p, text, re.IGNORECASE | re.MULTILINE)) 
                    for p in info_patterns)
    problem_score = sum(bool(re.search(p, text, re.IGNORECASE | re.MULTILINE)) 
                       for p in problem_patterns)
    
    # Default to question if no strong indicators
    intent = ("information" if info_score > problem_score 
             else ("problem" if problem_score > 0 else "question"))
    
    return {
        "intent": intent,
        "confidence": max(info_score, problem_score),
        "info_score": info_score,
        "problem_score": problem_score
    }
```

### Task 3: Conversation Context Manager

**Purpose**: Maintain session context for better LLM prompting  
**Storage**: Simple in-memory list (no persistence needed for POC)

```python
def __init__(self, server_url: str = None):
    # ... existing init code ...
    self.conversation_context = []  # New: conversation memory
    self.max_context_items = 10     # Limit memory usage

def add_to_context(self, user_input: str, intent_info: dict, response: dict = None):
    """Store interaction in conversation context"""
    context_item = {
        'type': intent_info['intent'],
        'content': user_input[:200],  # Truncate long content
        'timestamp': datetime.now().isoformat(),
        'intent_scores': {
            'info': intent_info['info_score'],
            'problem': intent_info['problem_score']
        }
    }
    
    # Add response summary if available
    if response:
        context_item['response_summary'] = response.get('llm_suggestion', '')[:100]
    
    self.conversation_context.append(context_item)
    
    # Keep only recent context
    if len(self.conversation_context) > self.max_context_items:
        self.conversation_context = self.conversation_context[-self.max_context_items:]

def get_context_for_api(self) -> list:
    """Format context for API transmission"""
    return [
        {
            'type': item['type'],
            'content': item['content'],
            'timestamp': item['timestamp']
        }
        for item in self.conversation_context[-5:]  # Send last 5 items
    ]
```

### Task 4: Enhanced API Communication

**Purpose**: Send context and intent to server for better LLM prompting  
**Modification**: Update `diagnose()` method

```python
def diagnose(self, issue: str, intent_info: dict) -> dict:
    """Send issue with context and intent to server"""
    try:
        payload = {
            'issue': issue,
            'intent': intent_info['intent'],
            'context': self.get_context_for_api(),
            'intent_analysis': {
                'confidence': intent_info['confidence'],
                'info_score': intent_info['info_score'],
                'problem_score': intent_info['problem_score']
            }
        }
        
        response = self.session.post(
            f"{self.server_url}/api/diagnose",
            json=payload
        )
        return response.json()
        
    except Exception as e:
        return {'error': str(e)}
```

### Task 5: Enhanced Response Handling

**Purpose**: Better user feedback based on intent  
**Location**: Main interactive loop (lines 172-179)

```python
# Replace the current "else" block (lines 172-179) with:
else:
    # Multi-line input handling
    if not user_input:  # Empty first line, get multi-line
        user_input = self.get_multiline_input()
        if not user_input:
            continue
    
    # Intent analysis
    intent_info = self.analyze_user_intent(user_input)
    
    # Information handling
    if intent_info['intent'] == 'information':
        print(f"📝 Information noted ({intent_info['confidence']} confidence)")
        self.add_to_context(user_input, intent_info)
        
        # Ask if they need help with anything
        if len(user_input.split('\n')) > 3:  # Multi-line info
            print("What would you like me to help you with regarding this information?")
        continue
    
    # Problem/Question processing
    print("🔍 Analyzing issue...")
    
    # Get diagnosis with context
    diagnosis = self.diagnose(user_input, intent_info)
    
    # Store in context
    self.add_to_context(user_input, intent_info, diagnosis)
    
    # Display results (existing code can mostly stay the same)
    # ... existing response display logic ...
```

## Integration Points

### Minimal Changes Required

1. **Import additions** (top of file):
   ```python
   import re
   from datetime import datetime
   ```

2. **Class initialization** (`__init__` method):
   ```python
   self.conversation_context = []
   self.max_context_items = 10
   ```

3. **Main loop modification** (lines 134-210):
   - Replace `input()` call
   - Add intent analysis
   - Modify response handling
   - Add context storage

4. **Method additions** (new methods):
   - `get_multiline_input()`
   - `analyze_user_intent()`
   - `add_to_context()`
   - `get_context_for_api()`

5. **API method update** (`diagnose` method):
   - Accept intent parameter
   - Send enriched payload

## Testing Strategy

### Phase 1: Basic Multi-Line Handling
```bash
cd /home/alex/Projects/iHomeNerd/RoadNerd/poc/core
python3 roadnerd_client.py

# Test cases:
# 1. Single line input (should work as before)
# 2. Paste multi-line command output
# 3. Empty line to end input
# 4. ``` or EOF to end input
```

### Phase 2: Intent Classification
```bash
# Test patterns:
# 1. "cat /etc/os-release" output → should detect as "information"
# 2. "My wifi is broken" → should detect as "problem"
# 3. "What OS am I running?" → should detect as "question"
```

### Phase 3: Context Accumulation
```bash
# Test flow:
# 1. Paste system info → stored as context
# 2. Ask question → should reference stored info
# 3. Follow-up questions → should maintain conversation flow
```

## Risk Mitigation

### Low-Risk Changes ✅
- Multi-line input handler (isolated function)
- Intent classification (pure function, no side effects)
- Context storage (in-memory only)

### Medium-Risk Changes ⚠️
- Main loop modification (test thoroughly)
- API payload changes (ensure backward compatibility)

### Rollback Plan 🔄
- Keep backup of original `roadnerd_client.py`
- Changes are additive - can fall back to original logic
- Server should handle missing context gracefully

## Success Criteria

### Functional Requirements ✅
- [ ] Multi-line paste works without line-by-line processing
- [ ] Intent classification correctly identifies information vs problems
- [ ] Context accumulates across conversation
- [ ] API sends enriched payloads to server
- [ ] Backward compatibility maintained for single-line usage

### User Experience Goals 🎯
- [ ] Zero false problem detection for informational content
- [ ] Natural paste-and-ask workflow
- [ ] Conversation flows logically
- [ ] Reduced user frustration with context awareness

### Technical Validation 🔧
- [ ] No regression in existing functionality
- [ ] Memory usage remains reasonable (context limit enforced)
- [ ] Error handling for malformed input
- [ ] Graceful degradation if server doesn't support new format

## Estimated Implementation Time

- **Task 1** (Multi-line input): 30 minutes
- **Task 2** (Intent classification): 45 minutes  
- **Task 3** (Context management): 30 minutes
- **Task 4** (API enhancement): 20 minutes
- **Task 5** (Response handling): 45 minutes
- **Testing & Integration**: 60 minutes

**Total**: ~3.5 hours for complete implementation and testing

## Next Steps for Gemini

1. **Backup existing client**: `cp roadnerd_client.py roadnerd_client.py.backup`
2. **Implement tasks in order** (1→2→3→4→5)
3. **Test each phase incrementally** before moving to next
4. **Document any issues** or deviations from plan
5. **Test with actual server** to ensure compatibility

The client changes are indeed **relatively small and focused** - mostly enhancing input handling and API communication while preserving all existing functionality.

---

**Ready for Implementation** ✅  
**Server Dependency**: Minimal - server should handle extra payload fields gracefully  
**Risk Level**: Low - additive changes with clear rollback path