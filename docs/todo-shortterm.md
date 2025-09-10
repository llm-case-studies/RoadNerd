# RoadNerd Short-term TODO

## ✅ COMPLETED (September 2025)

### N-Idea Generation & Enhanced Classification
- ✅ **Fixed token allocation**: N-idea generation now works (was limited to 128 tokens, now scales with `max(512, n * 120)`)  
- ✅ **Enhanced JSON parsing**: Handles numbered lists, fenced blocks, balanced braces
- ✅ **Expanded categories**: From 5 narrow networking categories to 9 comprehensive ones:
  - `power` (battery, charger, won't turn on)
  - `boot` (BIOS, bootloader, startup)
  - `hardware` (RAM, disk, motherboard)
  - `physical` (dropped, liquid damage, environmental)
  - `software` (drivers, OS corruption, apps)
  - `user` (wrong expectations, user error)
  - `network` (wifi, connectivity, DNS)
  - `performance` (slow, overheating)
  - `system` (configuration issues)
- ✅ **Updated prompt templates**: `brainstorm.base.txt` now includes all new categories
- ✅ **Model escalation testing**: Confirmed capability across 1B→3B→7B→13B models

### Multi-Step Debug Diagnostics
- ✅ **Step-by-step API visibility**: Debug mode shows classification → retrieval → brainstorming pipeline
- ✅ **Confidence-based recommendations**: Automatic suggestions for low-confidence classifications
- ✅ **Ambiguity detection**: `"ambiguous": true` flag when confidence < 0.6
- ✅ **Template tracking**: Shows which prompt template was used
- ✅ **Parsing success metrics**: Detects when JSON parsing fails vs succeeds

## 🔄 IN PROGRESS

### Disambiguation Flow Integration
- **Automatic triggers**: When classification confidence < 0.5, trigger disambiguation
- **Multi-category brainstorming**: Generate ideas across multiple likely categories for ambiguous issues
- **Evidence integration**: Connect probe results back to idea ranking

## 📋 NEXT PRIORITIES

### Category-Specific Enhancements
- [ ] **Category-specific templates**: Create `brainstorm.physical.txt`, `brainstorm.user.txt`, etc.
- [ ] **Enhanced retrieval context**: Show actual snippets used in debug mode
- [ ] **Category-aware prompting**: Better context for each problem domain

### Judge Endpoint Improvements  
- [ ] **Judge debug mode**: Add step-by-step diagnostics to ranking process
- [ ] **Scoring transparency**: Show how safety/cost/determinism scores are calculated
- [ ] **Evidence weighting**: Better integration of probe results in ranking

### UI/UX Enhancements
- [ ] **API console improvements**: Better visualization of debug information
- [ ] **Interactive disambiguation**: UI for handling ambiguous classifications
- [ ] **Progress indicators**: Show multi-step processing status

### Performance & Reliability
- [ ] **JSONL evaluation framework**: Systematic testing of classification accuracy
- [ ] **Template hot-reload**: Dynamic prompt updates without restart
- [ ] **Caching**: Template and model response caching
- [ ] **Rate limiting**: Prevent API abuse

### Documentation
- [ ] **API documentation**: Complete OpenAPI spec for all endpoints
- [ ] **Troubleshooting guide**: Common issues and solutions
- [ ] **Model comparison**: Performance characteristics across different model sizes

## 🎯 LONG-TERM GOALS

- **Enterprise features**: Authentication, multi-tenant support, audit logging
- **Advanced routing**: ML-based classification with fallback heuristics  
- **Plugin system**: Custom diagnostic modules for specific environments
- **Integration APIs**: Slack, Teams, ticketing systems