---
title: "Remediation Plan: C1 Security — In-Unit Secret Scrubbing is Defeatable"
status: live
part_of: repo-meta
doc_type: reference
---

# Remediation Plan: C1 Security — In-Unit Secret Scrubbing is Defeatable

## 1. Finding Summary
Secrets are currently scrubbed inside the execution isolation unit where Task Dev agents have write access to `src/`. An adversarial or compromised agent could tamper with the scrubbing logic, encode credentials into filenames or commit messages, or exfiltrate them directly via network calls during test execution.

## 2. Root Cause
The current architecture (defined in `core_adapter_boundary.md` §5) places the scrubbing mechanism inside the isolation unit because the scrubber needs access to the raw credential values. However, placing security controls within the same trust boundary as the untrusted agent execution violates Principle 12: "Enforce with permissions, not prompts". By giving the agent write access to the environment where the scrubber operates, the agent can bypass or modify the redaction process.

## 3. Remediation Design
To secure the scrubbing process, the scrubber must be moved to a distinct, higher-privilege trust boundary (the Core) that the isolation unit (Adapter/Agent) cannot manipulate. 

### 3.1 Trust Boundary Realignment
- **Scrubber Relocation**: The scrubber will execute in the Core environment. It will intercept all outgoing artifacts (logs, screenshots, DOM dumps, HAR files, filenames, commit messages, and network payloads) from the isolation unit before they are processed by the rest of the system or stored.
- **Credential Management**: Core will maintain a transient mapping of active credentials for the duration of a task. The isolation unit will receive injected credentials (e.g., via environment variables), but the Core will retain a copy of these values strictly for the purpose of exact-match and regex-based redaction on data egressing the isolation unit.

### 3.2 Mitigation of Exfiltration Vectors
- **Network Exfiltration**: Isolation units must enforce strict egress network restrictions. An egress proxy operated by Core will perform deep packet inspection and secret scrubbing on outgoing traffic. If deep packet inspection is unfeasible, egress must be restricted via strictly allow-listed domains. 
- **Artifact & Metadata Scrubbing**: The Core scrubber will explicitly parse and sanitize metadata, including filenames, Git commit messages, and binary artifact metadata. Any detected secrets will be replaced with `[REDACTED_SECRET]`.

### 3.3 Schema Changes (`agent_interface_contracts.py`)
We need to update the credential schemas to support the Core-side scrubber, utilizing Pydantic v2 strictness.

```python
from pydantic import BaseModel, Field

class SecretScrubberConfig(BaseModel, frozen=True, extra="forbid"):
    active_secrets: list[str] = Field(
        ..., 
        description="List of raw secret values to be redacted from isolation unit outputs."
    )
    redaction_placeholder: str = Field(
        default="[REDACTED_SECRET]", 
        description="String to replace detected secrets with."
    )

class EgressPayload(BaseModel, frozen=True, extra="forbid"):
    payload_type: str = Field(..., description="Type of egress data: 'log', 'commit', 'filename', 'network', etc.")
    content: str = Field(..., description="Raw content requiring scrubbing.")

class ScrubbedEgressPayload(BaseModel, frozen=True, extra="forbid"):
    original_type: str = Field(..., description="Type of egress data.")
    scrubbed_content: str = Field(..., description="Content with secrets redacted.")
    secrets_detected: bool = Field(..., description="True if secrets were found and redacted.")
```

## 4. Required Document Updates

- **`plan/core_adapter_boundary.md` §5 (Credential Injection)**: 
  - Update to specify that Core retains a copy of the injected secrets exclusively for the egress scrubber. 
  - Define the egress interception points for logs, artifacts, and metadata.
- **`plan/agent_interface_contracts.py`**:
  - Add the `SecretScrubberConfig`, `EgressPayload`, and `ScrubbedEgressPayload` schemas.
- **`plan/execution_isolation.md` §5 (Isolation Units)**:
  - Add a mandate: Tasks requiring credentials *must* use container-based isolation units to enforce network egress proxying. Worktree isolation is insufficient for credential-bearing tasks because it lacks robust network boundaries.

## 5. Open Questions
- **Egress Proxy Performance**: Will running an egress proxy with deep packet inspection and regex matching for all outbound container traffic introduce unacceptable latency, potentially causing timeouts in the 8-phase pipeline?
- **Binary Artifact Redaction**: How do we safely scrub binary files (e.g., images, PDFs) without corrupting them? Should we strictly forbid binary exfiltration if credentials are active, or rely entirely on filename/metadata scrubbing for binaries?
- **Core Memory Footprint**: Retaining raw credential values in Core memory for redaction increases the risk of Core memory dumps exposing secrets. How do we securely manage the lifecycle of the `SecretScrubberConfig` in memory (e.g., wiping memory explicitly)?
