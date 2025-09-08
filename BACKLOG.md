# RoadNerd Project Backlog

**Generated:** 2025-09-08 from comprehensive document review

---

## 🎯 **Strategic Vision & Goals**

### Core Mission
- **Portable Offline Diagnostics**: Solve "need internet to fix internet" problem
- **Local-First AI**: Use minimal viable intelligence for efficient problem-solving  
- **Field-Ready Architecture**: Work in hostile network environments (hotels, conferences)
- **Sustainable Computing**: "Just enough intelligence" approach vs brute-force large models

### Key Insights from Testing
- ✅ **Ethernet > USB**: Direct networking superior to USB tethering complexity
- ✅ **Small models work**: llama3.2:3b surprisingly capable for structured troubleshooting
- ✅ **Resource headroom exists**: Minimal utilization during testing suggests enhancement opportunities
- ✅ **Role flexibility**: Hardware-agnostic architecture allows easy server/client swapping

---

## 🚀 **Feature Backlog** (Priority Ordered)

### **IMMEDIATE PRIORITIES** (Next 1-2 weeks)

#### **P0: Core Stability & Enhancement**
- [ ] **Prompt Engineering & Tuning**
  - Optimize diagnostic prompts for common IT issues (DNS, WiFi, network)
  - A/B test prompt variations with deterministic settings (`RN_TEMP=0`)
  - Improve success rate for real-world scenarios
  - Create prompt templates for different issue types

- [ ] **Field Validation Testing**
  - Test BeeLink ↔ Patient direct ethernet scenarios
  - Validate auto-discovery with 10.55.0.x subnet
  - Real-world scenario testing using test recipes
  - Performance benchmarking across different hardware

- [ ] **Enhanced Auto-Discovery**
  - Add 10.55.0.x subnet to default client scan list
  - Improve server detection reliability
  - Multi-interface connection testing
  - Connection fallback mechanisms

#### **P1: Usability & Robustness**
- [ ] **Client Bootstrap System** (GPT5 feedback)
  - `/bootstrap.sh` endpoint to download client from server
  - Zero-install client deployment over ethernet
  - "Kiosk mode" for easy patient system setup
  - USB sneakernet fallback option

- [ ] **Model Escalation System** (GPT5 feedback)
  - Stateless model ladder (3b → 7b → 13b)
  - `/harder` and `/hardest` client commands
  - Try-harder escalation without context loss
  - Smart tier selection based on problem complexity

- [ ] **Enhanced Safety Mechanisms**
  - Token-level command safety analysis
  - Expanded denylist regex patterns (`rm -rf`, `dd if=`, `mkfs`)
  - Command preview with risk assessment
  - User confirmation for potentially dangerous operations

### **PHASE 2: Intelligence Enhancement** (2-4 weeks)

#### **P2: Guided Reasoning for Small LLMs** (Testing Results insight)
- [ ] **Self-Reflection Architecture**
  - Confidence assessment for initial responses
  - Gap identification in reasoning chains
  - Iterative response refinement
  - Multi-pass reasoning with resource efficiency

- [ ] **Structured Decision Trees**
  - JSON-defined troubleshooting flows for common issues
  - Context-aware prompting templates
  - Progressive complexity handling
  - Pattern matching for known solutions

- [ ] **Dual-Model Architecture** (GPT5 feedback)
  - Parallel tiny+small model execution
  - Small model as evaluator/judge of tiny model outputs
  - Automatic medium model escalation on repeated failures
  - Resource-efficient collaborative reasoning

#### **P3: Case File System** (GPT5 feedback)
- [ ] **Offline Documentation & Handoff**
  - Structured case file generation (.zip format)
  - System snapshot collection (network, logs, configs)
  - Timeline tracking of all actions and responses
  - Air-gap friendly export for external consultation

- [ ] **External Consultation Workflow**
  - Standardized case file format for friends/cloud consultation
  - Import advice.json from external LLMs (GPT/Claude/Gemini)
  - Apply external recommendations with local safety validation
  - "Boot-loop-ish" offline collaboration pattern

### **PHASE 3: Advanced Features** (1-2 months)

#### **P4: Command History & Shell Integration** (Feature proposal)
- [ ] **Semantic Command History**
  - SQLite-based command storage with FTS5 search
  - Contextual metadata (host, dir, exit code, duration)
  - Fuzzy and semantic search capabilities
  - Cross-machine sync with E2E encryption

- [ ] **LLM-Guided Shell Assistant**
  - Ctrl+G keybinding for command suggestions
  - Commented command insertion (`# llm: command`)
  - Safety-first approach (never auto-execute)
  - Learning from user acceptance/rejection patterns

- [ ] **Shell Integration**
  - Bash/Zsh hooks for command capture
  - Real-time command safety analysis
  - PII/secret redaction before LLM processing
  - Incremental learning from successful patterns

#### **P5: Model Management & Performance**
- [ ] **Intelligent Model Selection**
  - Task complexity classification heuristics
  - Hardware capability assessment
  - Dynamic model recommendation engine
  - Energy-aware model selection for battery scenarios

- [ ] **Model Vault System** (GPT5 feedback)
  - Store larger models on server for patient deployment
  - `/download/ollama-models.tgz` endpoint
  - Hot-swap server roles when patient has better hardware
  - Offline model transfer and deployment

- [ ] **Resource-Aware Operations**
  - Pre-flight model loading checks
  - Memory usage prediction and monitoring
  - Graceful fallback to smaller models
  - Performance benchmarking and optimization

### **PHASE 4: Advanced Intelligence** (2-3 months)

#### **P6: Collaborative Intelligence**
- [ ] **Multi-Model Reasoning**
  - "Diagnostic council" of specialized small models
  - Model consensus and disagreement resolution
  - Specialized models for different problem domains
  - Cross-validation of diagnostic recommendations

- [ ] **Learning & Adaptation**
  - Historical success/failure pattern recognition
  - Automatic improvement of guidance templates
  - Field experience integration into knowledge base
  - User satisfaction-driven model optimization

#### **P7: Next-Generation Features**
- [ ] **Diagnostic OS Integration**
  - Bootable diagnostic environment
  - Pre-boot network problem diagnosis
  - Hardware-level troubleshooting capabilities
  - Recovery mode operations

- [ ] **Advanced Networking**
  - Multi-device RoadNerd mesh networks
  - Load sharing across available compute resources
  - Distributed problem solving
  - Edge case handling through network collaboration

---

## 🔧 **Technical Debt & Infrastructure**

### **Code Quality & Testing**
- [ ] **Comprehensive Test Suite**
  - Expand MCP + Playwright integration
  - API-first e2e test automation
  - Prompt suite runner with YAML test cases
  - Automated regression testing pipeline

- [ ] **Code Refactoring**
  - Extract common functionality into reusable modules
  - Improve error handling and logging
  - Configuration management enhancement
  - Documentation consistency across codebase

### **Deployment & Operations**
- [ ] **Installation & Setup**
  - Automated setup scripts for different platforms
  - Dependency management and isolation
  - Service configuration and management
  - Update and maintenance procedures

- [ ] **Monitoring & Observability**
  - Performance metrics collection
  - Usage analytics and success rate tracking
  - Error reporting and diagnostics
  - Resource utilization monitoring

---

## 📋 **Architecture Improvements**

### **Modularity & Extensibility**
- [ ] **Plugin Architecture**
  - Extensible problem-solving modules
  - Custom diagnostic workflows
  - Third-party integration capabilities
  - Domain-specific reasoning modules

### **Security & Privacy**
- [ ] **Enhanced Security**
  - Command execution sandboxing
  - Network traffic analysis and filtering
  - Audit logging and compliance
  - Data encryption at rest and in transit

- [ ] **Privacy Protection**
  - Local-only processing guarantees
  - PII detection and redaction
  - User consent and data control
  - Minimal data collection principles

---

## 🎯 **Success Metrics**

### **Performance Targets**
- **Response Time**: < 5s for common diagnostic queries
- **Success Rate**: > 80% problem resolution in week 2 of use
- **Resource Efficiency**: < 2GB RAM usage for standard operations
- **Safety**: Zero incidents of unintended command execution

### **User Experience Goals**
- **Time to Problem Resolution**: < 10 minutes for common issues
- **Learning Curve**: < 30 minutes to productive use
- **Reliability**: 99%+ uptime in field conditions
- **User Satisfaction**: > 4.5/5 rating after 1 week use

---

## 🗂️ **Ideas Parking Lot**

### **Future Exploration**
- Integration with OpenAI's GPT-OSS models for specialized tasks
- Voice interface for hands-free operation
- Mobile app companion for field technicians  
- Integration with existing IT management tools
- Collaborative debugging with remote experts
- Machine learning for predictive issue detection
- IoT device integration and management
- Cloud-hybrid operations for large-scale deployments

### **Research Questions**
- How to quantify "computational carbon footprint" for model selection?
- Can small models + guidance outperform large models for specific domains?
- What's the optimal balance between automation and human oversight?
- How to measure and improve "intelligence per watt" efficiency?

---

*"The most sustainable AI is the one that uses just enough intelligence to solve the problem effectively."*

**Last Updated:** 2025-09-08  
**Next Review:** When priorities shift or major milestones achieved