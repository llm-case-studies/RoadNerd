# Session Progress: N-Idea Generation & Debug Diagnostics
**Date:** September 9, 2025  
**Focus:** Enhanced brainstorming system with multi-step diagnostics

## 🎯 **Major Achievements**

### 1. **Fixed N-Idea Generation** 
**Problem:** Users requested 5 ideas but only got 1 fallback response  
**Root Cause:** Token allocation was too small (`128` tokens for n=5)  
**Solution:** Dynamic scaling `max(512, n * 120)` tokens per request  
**Result:** ✅ Now generates exactly N structured ideas as requested

### 2. **Expanded Category Coverage**
**Problem:** "My laptop doesn't work" was narrowly classified as wifi issue  
**Solution:** Expanded from 5 networking categories to 9 comprehensive ones:

| **Before** | **After** |
|------------|-----------|
| wifi, dns, network, performance, system | power, boot, hardware, physical, software, user, network, performance, system |

**Impact:** Now handles full spectrum from "battery dead" to "run over by truck" to "user error"

### 3. **Enhanced JSON Parsing**
**Discovery:** Models CAN generate multiple JSON objects in numbered format  
**Implementation:** 4 parsing strategies:
- Direct JSON arrays `[{...}, {...}]`
- Fenced code blocks ````json ... ````
- **Numbered lists** `1. {...} 2. {...}` ← **Key fix**
- Balanced brace extraction

### 4. **Multi-Step Debug Diagnostics**
**Feature:** Added `"debug": true` parameter to brainstorm endpoint  
**Visibility:** Shows complete pipeline:

```json
{
  "debug": {
    "steps": {
      "1_classification": {
        "method": "automatic",
        "confidence_level": "high|medium|low", 
        "ambiguous": true/false,
        "result": { "label": "power", "confidence": 0.8, "candidates": [...] }
      },
      "2_retrieval": {
        "snippets_found": 12,
        "used_category": "power"
      },
      "3_brainstorming": {
        "template_used": "brainstorm.power.txt",
        "model": "codellama:13b",
        "num_predict": 600,
        "parsing_success": true
      }
    },
    "recommendations": [
      "Low classification confidence - consider manual category override"
    ]
  }
}
```

## 🔧 **Technical Details**

### Files Modified
- **`poc/core/classify.py`**: Expanded CATEGORIES and HEUR_PATTERNS
- **`poc/core/roadnerd_server.py`**: Enhanced token allocation, debug endpoints
- **`poc/core/prompts/brainstorm.base.txt`**: Updated category list in template

### Key Code Changes

#### Token Allocation Fix
```python
# Before: Too restrictive
num_predict = 256 if n > 5 else 128

# After: Scales with request
num_predict = max(512, n * 120)  # At least 120 tokens per idea
```

#### Enhanced Parsing Logic
```python
# Added numbered list parsing
numbered_pattern = re.compile(r'^\d+\.\s*(\{.*?\})', re.MULTILINE | re.DOTALL)
for match in numbered_pattern.findall(text):
    obj = json.loads(match)
    ideas.append(to_idea(obj))
```

#### Debug Information
```python
if debug:
    response['debug'] = {
        'steps': { /* classification → retrieval → brainstorming */ },
        'recommendations': [ /* automatic suggestions */ ]
    }
```

## 🧪 **Testing Results**

### Model Escalation Testing
- **1B → 3B → 7B → 13B**: All models generate multiple ideas in numbered format
- **Key insight**: Issue was parsing, not model capability
- **Recommended**: 13B for best structured output quality

### Classification Accuracy
- **"Laptop battery drains quickly"** → `confidence: 1.0, category: power` ✅
- **"Something is not working"** → `confidence: 0.0, ambiguous: true` → Triggers recommendations ✅

### API Response Examples

**Clear Classification:**
```json
"1_classification": {
  "confidence_level": "high",
  "ambiguous": false,
  "result": { "label": "power", "confidence": 1.0 }
}
```

**Ambiguous Classification:**
```json
"1_classification": {
  "confidence_level": "low", 
  "ambiguous": true,
  "result": { "label": "power", "confidence": 0.0 }
},
"recommendations": [
  "Low classification confidence - consider manual category override or disambiguation flow"
]
```

## 🚀 **Impact & Next Steps**

### Immediate Benefits
1. **Reliable N-idea generation**: Users get exactly what they request
2. **Broader problem coverage**: From simple wifi to catastrophic hardware failures  
3. **Transparent decision-making**: Full visibility into AI reasoning process
4. **Ambiguity detection**: System knows when it's uncertain and suggests alternatives

### Ready for Implementation
- **Disambiguation flow integration**: Automatically trigger when `confidence < 0.5`
- **Category-specific templates**: `brainstorm.physical.txt`, `brainstorm.user.txt`
- **Enhanced UI**: Show debug information in /api-docs console

## 📊 **Before vs After**

| **Metric** | **Before** | **After** |
|------------|------------|-----------|
| Ideas generated | 1 (fallback) | N (as requested) |
| Categories covered | 5 networking | 9 comprehensive |
| Classification visibility | Hidden | Full debug mode |
| Ambiguity handling | Silent failure | Explicit detection + recommendations |
| JSON parsing | Single strategy | 4 robust strategies |
| Token allocation | Fixed 128 | Dynamic scaling |

## ✅ **Ready for PR**
All changes tested, documented, and ready for production deployment.