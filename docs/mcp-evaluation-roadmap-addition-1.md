# RoadNerd MCP Evaluation - Additional Requirements & Questions

**Purpose**: Supplement the main roadmap with operational requirements and clarification questions for the Reusable MCP team.

## 🔧 Operational Requirements (Missing from Main Roadmap)

### 1. Configuration Management
```yaml
# Per-MCP server configuration
mcp_config:
  network_diag:
    timeouts:
      default_ms: 2000
      dns_resolve_ms: 5000
      http_check_ms: 8000
    allowlists:
      http_targets: ["neverssl.com", "*.corp.internal", "httpbin.org"]
      ports: [80, 443, 8080, 53, 22, 25, 993, 995]
    security:
      max_redirects: 3
      user_agent: "RoadNerd-MCP/1.0"
  service_diag:
    timeouts:
      journal_tail_ms: 3000
    limits:
      max_journal_lines: 120
```

### 2. Error Recovery & Process Management
- **Server crash handling**: What happens when MCP server crashes mid-request?
- **Auto-restart policy**: Should orchestrator auto-restart failed MCPs?
- **Circuit breaker**: Pattern for repeatedly failing servers (5 failures → 30s cooldown)?
- **Graceful shutdown**: How to cleanly terminate MCP servers during RoadNerd shutdown?

### 3. Resource Limits & Security Constraints
```yaml
# Per-MCP resource constraints
resource_limits:
  memory_mb: 128        # Max memory per MCP server
  cpu_percent: 10       # Max CPU usage
  concurrent_requests: 3 # Max parallel tool calls
  disk_tmp_mb: 50      # Temp file space limit

security_profile:
  user: "mcp-runner"    # Non-root execution user
  chroot: "/opt/mcp-sandbox/"  # Optional sandboxing
  network_access: "restricted"  # localhost + allowlist only
  file_access: "read_only"      # No writes except temp
```

### 4. Development & Testing Infrastructure
- **Local dev setup**: Docker compose for MCP server development?
- **Integration testing**: Framework for testing MCP + RoadNerd integration
- **Mock/stub patterns**: Testing without real network/system calls
- **Regression tests**: Automated testing for MCP server updates

### 5. Deployment & Distribution
- **Packaging format**: pip install? Binary executables? Docker containers?
- **Version compatibility**: Matrix of RoadNerd ↔ MCP server versions
- **Dependency management**: How are MCP server deps handled in offline bundles?
- **Rollback strategy**: Reverting to previous MCP version on failure
- **Portable deployment**: Integration with RoadNerd bundle creation system

### 6. Enhanced Observability & Monitoring
```json
// Enhanced logging format for MCP operations
{
  "timestamp": "2025-09-12T10:30:45Z",
  "component": "mcp_orchestrator",
  "mcp_server": "network-diag",
  "tool": "dns_resolve",
  "request_id": "req_20250912_123",
  "run_id": "brainstorm_456", 
  "duration_ms": 234,
  "result": "success|timeout|error|partial",
  "resource_usage": {
    "memory_mb": 45,
    "cpu_ms": 120,
    "network_calls": 2
  },
  "error_code": "E_DNS_FAIL",
  "retry_count": 0
}
```

## 🚀 Immediate Opportunities & Questions

### 1. Existing MCP Assets
**Question**: What MCP servers do you already have that we could start experimenting with immediately?
- **Memory-MCP**: Could this help with small model experimentation?
- **Existing HTTP+SSE servers**: Any prototypes we could adapt?
- **Testing frameworks**: Do you have MCP integration test patterns?

**Goal**: Start small-model experiments while custom MCPs are being built.

### 2. Deployment Architecture Questions
**Critical**: Where should MCP servers run in RoadNerd's portable deployment model?

#### Option A: MCP Servers on Nerd Device (Helper)
```
[Patient Machine] ←USB/Ethernet→ [Nerd Device]
                                 ├── RoadNerd Server
                                 ├── Ollama + Models  
                                 └── MCP Servers ←── Run here?
```
**Pros**: Simple, no patient-side installation
**Cons**: Network diagnostics run remotely, may miss patient-specific issues

#### Option B: MCP Servers on Patient Machine
```
[Patient Machine] ←USB/Ethernet→ [Nerd Device]
├── MCP Servers ←── Run here?   ├── RoadNerd Server
└── Patient System Issues       └── Ollama + Models
```
**Pros**: Direct access to patient system state
**Cons**: Requires installation on potentially broken patient system

#### Option C: Hybrid Deployment
- **NetworkDiag MCP**: On patient (needs direct network access)
- **Service MCP**: On patient (needs systemctl access)
- **Storage MCP**: On patient (needs file system access)
- **Orchestrator**: On Nerd device

**Questions for MCP Team**:
1. Can you support **both** deployment patterns?
2. How would **remote MCP calls** work (Nerd → Patient MCPs)?
3. What's the **startup sequence** for portable scenarios vs daemon deployment?

### 3. Startup & Lifecycle Management
**Standard MCP Pattern**: Long-running daemon/service
**RoadNerd Pattern**: On-demand, portable, USB-deployed

#### Custom Startup Sequences Needed:
```bash
# Scenario 1: Quick diagnostic (no installation)
./roadnerd_portable.sh --mcp-local-only

# Scenario 2: Patient installation
./install_roadnerd.sh --with-mcps --patient-side

# Scenario 3: Development/testing
./dev_setup.sh --mcp-mock-mode
```

**Questions**:
1. Can MCP servers start **on-demand** rather than as persistent daemons?
2. **Embedded mode**: Can MCPs run as threads/subprocesses within RoadNerd?
3. **Discovery protocol**: How does RoadNerd find available MCP servers?
4. **Health monitoring**: Built-in health checks and auto-restart capabilities?

### 4. Small Model Integration Patterns
Given the **attach-on-request** orchestration pattern:

```python
# Example integration flow
def mcp_assisted_triage(issue: str, model_size: str):
    """
    1. Start with no MCPs attached
    2. Show model available tools catalog
    3. Model requests specific tool via JSON
    4. Orchestrator attaches MCP server if needed  
    5. Execute tool call and return results
    6. Repeat until confident diagnosis (≤3 tools)
    """
```

**Questions**:
1. **Tool catalog format**: How should available tools be presented to small models?
2. **JSON validation**: Built-in validation for model-generated tool calls?
3. **Repair prompting**: Standard patterns for invalid JSON recovery?
4. **Context management**: How to maintain state across tool calls for small models?

## 📋 Immediate Action Items for MCP Team

### Phase 0 (Immediate - This Week)
1. **Share existing assets**: What MCP servers/frameworks exist now?
2. **Architecture decision**: Patient vs Nerd vs Hybrid deployment preference?
3. **Startup patterns**: On-demand vs daemon - which can you support?
4. **Development environment**: Docker setup for local MCP development?

### Phase 1 (Week 1-2)
1. **Prototype deployment**: Simple NetworkDiag MCP with HTTP+SSE
2. **Integration POC**: RoadNerd + existing MCP (Memory-MCP?) 
3. **Resource limits**: Basic memory/CPU constraints implementation
4. **Error handling**: Standard error codes and recovery patterns

### Phase 2 (Week 3-4)
1. **Production MCPs**: NetworkDiag + Service + Ports MCPs per main roadmap
2. **Security profile**: Non-root execution and sandboxing
3. **Observability**: Enhanced logging and monitoring
4. **Bundle integration**: MCP servers in RoadNerd portable bundles

## 🎯 Success Metrics & Acceptance Criteria
- **Small model compatibility**: ≥95% valid JSON tool calls on first try
- **Performance**: Tool calls complete within timeout (2-5s typical)
- **Reliability**: MCP servers handle crashes gracefully with auto-restart
- **Portability**: MCPs deploy cleanly in RoadNerd bundle system
- **Security**: All tool calls run with minimal privileges and proper sandboxing

## 📞 Next Steps
Please respond with:
1. **Available assets**: What MCP infrastructure exists today?
2. **Architecture preferences**: Patient vs Nerd deployment recommendation
3. **Timeline**: Realistic delivery estimates for Phase 0 and Phase 1
4. **Technical constraints**: Any limitations or requirements we should know about

---

*Generated for Reusable MCP Team collaboration*  
*Contact: RoadNerd team via existing channels*