# RoadNerd Short-Term TODO

**Sprint Goals:** Next 1-2 weeks  
**Focus:** Stabilize core functionality, improve prompt quality, validate field scenarios

---

## 🎯 **This Week (Priority 1)**

### **Monday-Tuesday: Prompt Engineering Sprint**
- [ ] **Analyze Current Prompt Performance**
  - Run test suite with current prompts, document failure patterns
  - Identify common misdiagnoses in WiFi, DNS, network issues
  - Collect baseline metrics for improvement comparison

- [ ] **Create Specialized Prompt Templates**
  - DNS troubleshooting prompt with structured steps
  - WiFi connectivity prompt with systematic approach  
  - General network diagnostic prompt with safety checks
  - System info interpretation prompt for context awareness

- [ ] **A/B Test Prompt Variations**
  - Use deterministic settings (`RN_TEMP=0`) for consistent comparison
  - Test structured vs unstructured prompt approaches
  - Measure success rate improvements
  - Document winning prompt patterns

### **Wednesday-Thursday: Field Validation**
- [ ] **BeeLink ↔ Patient Testing**
  - Set up BeeLink as server (10.55.0.1) with MSI as client (10.55.0.2)
  - Test all documented scenarios from testing recipes
  - Validate auto-discovery works with 10.55.0.x subnet
  - Document any connection reliability issues

- [ ] **Real-World Scenario Testing**
  - DNS resolution problems
  - WiFi adapter issues  
  - Network interface configuration problems
  - Multi-step troubleshooting workflows
  - Performance under different system loads

### **Friday: Quick Wins & Polish**
- [ ] **Enhanced Auto-Discovery**
  - Add 10.55.0.x to client default subnet scan
  - Improve server detection speed and reliability
  - Add connection status feedback to user
  - Test multi-interface scenarios

- [ ] **Safety Improvements**
  - Expand dangerous command patterns (`rm -rf`, `dd if=`, `mkfs`)
  - Add token-level safety analysis
  - Improve command preview with risk assessment
  - Test safe mode edge cases

---

## 🚀 **Next Week (Priority 2)**

### **Monday-Wednesday: Client Bootstrap System**
- [ ] **Server-Side Bootstrap Endpoints**
  - Implement `/bootstrap.sh` endpoint (from GPT5 feedback)
  - Create `/download/client.py` file serving
  - Add auto-detection of server IP in bootstrap script
  - Test zero-install client deployment

- [ ] **Client Enhancement**
  - Fix help command recursion bug
  - Improve multi-line input handling edge cases
  - Add connection retry mechanisms
  - Enhanced error messages and user guidance

### **Thursday-Friday: Model Escalation Foundation**
- [ ] **Basic Model Ladder**
  - Define model escalation tiers (3b → 7b → 13b)
  - Create stateless escalation API endpoints
  - Implement `/harder` and `/hardest` client commands
  - Test model switching without context loss

- [ ] **Environment Variable Enhancements**
  - Improve `RN_MODEL` switching robustness
  - Add `RN_ESCALATION_LADDER` configuration
  - Test rapid model switching scenarios
  - Document environment configuration options

---

## 🧪 **Testing & Validation Tasks**

### **Automated Testing**
- [ ] **Expand Test Suite**
  - Add test cases for new prompt templates
  - Test model escalation scenarios
  - Add bootstrap system tests
  - Create performance regression tests

- [ ] **Integration Testing**
  - Test server-client communication reliability
  - Validate API endpoints under load
  - Test different network configurations
  - Verify safety mechanisms work correctly

### **Manual Testing**
- [ ] **User Experience Testing**
  - Test complete troubleshooting workflows
  - Validate help system and documentation
  - Test error handling and recovery
  - Collect user feedback on interaction quality

- [ ] **Field Condition Testing**
  - Test in different network environments
  - Validate offline operation capabilities
  - Test with limited resources scenarios
  - Document performance characteristics

---

## 📋 **Documentation & Cleanup Tasks**

### **Documentation Updates**
- [ ] **Update CLAUDE.md**
  - Document new testing procedures
  - Add prompt engineering guidelines
  - Update development workflow instructions
  - Add troubleshooting guide for common issues

- [ ] **Testing Documentation**
  - Update testing recipes with new scenarios
  - Document expected outcomes for test cases
  - Create quick-start guide for new contributors
  - Add performance benchmarking procedures

### **Code Cleanup**
- [ ] **Archive Management**
  - Move outdated documents to `/archive` folder
  - Clean up duplicate files in RoadNerd-POC
  - Remove temporary testing files
  - Organize documentation structure

- [ ] **RoadNerd-POC Evaluation**
  - Compare POC files with main implementation
  - Extract any missing useful features
  - Archive or delete obsolete POC files
  - Ensure no important code is lost

---

## 🎯 **Success Criteria for Sprint**

### **Week 1 Goals**
- ✅ **Prompt Quality**: 20% improvement in diagnostic accuracy
- ✅ **Field Testing**: All documented scenarios pass reliably  
- ✅ **Auto-Discovery**: 100% success rate on 10.55.0.x networks
- ✅ **Safety**: Zero dangerous command execution incidents

### **Week 2 Goals**
- ✅ **Bootstrap System**: Zero-install client deployment working
- ✅ **Model Escalation**: Basic escalation system functional
- ✅ **Testing Coverage**: >90% scenario coverage in automated tests
- ✅ **Documentation**: All changes documented and up-to-date

---

## 🚧 **Blockers & Dependencies**

### **Potential Issues**
- **Hardware Access**: Need reliable access to BeeLink for testing
- **Network Environment**: Consistent ethernet connection for validation
- **Model Resources**: Ensure sufficient disk space for model escalation testing
- **Time Constraints**: Balance feature development with thorough testing

### **Risk Mitigation**
- Prepare fallback testing scenarios using MSI as both server and client
- Document all test procedures for reproducibility
- Prioritize safety and stability over new features
- Maintain detailed progress logs for troubleshooting

---

## 📅 **Daily Standup Format**

**Daily Check-in Questions:**
1. What did I complete yesterday?
2. What will I focus on today?
3. What blockers or concerns do I have?
4. What did I learn that might help others?

**Weekly Review Questions:**
1. Did we meet our sprint goals?
2. What worked well in our process?
3. What should we improve for next sprint?
4. What new insights emerged from testing?

---

*Focus: Stabilize, validate, improve. Build on the solid foundation we've established.*

**Created:** 2025-09-08  
**Sprint End:** 2025-09-20  
**Next Review:** Friday EOD each week