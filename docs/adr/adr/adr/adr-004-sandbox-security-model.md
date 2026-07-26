# ADR-004: Sandbox Security Model for Code Execution

**Status:** Draft
**Date:** 2026-07-26
**Project:** Synapsis

---

## Context

The Coder agent generates and executes Python code based on user queries.
This code comes from an LLM — it could contain bugs, infinite loops, or
malicious operations (file deletion, network calls, system modifications).

Since Synapsis is a local-first tool that also has a future deployment goal,
the sandbox must protect both the developer's machine now and a server later.

## Decision

We implement a layered sandbox with defense in depth:

### Layer 1: Process Isolation (subprocess)
Code executes in a separate Python subprocess, not in the main agent process.
If generated code crashes or hangs, the main system is unaffected.

### Layer 2: Filesystem Isolation (temp directory)
Each execution gets a unique temp directory (`/tmp/synapsis-sandbox/{sandbox_id}/`).
The subprocess runs with its working directory set to this path. All file I/O
is confined to this directory.

### Layer 3: Resource Limits
- **Timeout:** 120 seconds max execution time (configurable per task)
- **Memory:** 512 MB max (via `resource` module on Linux/macOS)
- **Output:** 10 MB max stdout/stderr capture

### Layer 4: Package Whitelist
Only pre-approved packages can be installed. Initial whitelist:
`numpy`, `pandas`, `matplotlib`, `scikit-learn`, `scipy`, `requests`, `sqlite3` (stdlib).
Installation of any other package requires the `--allow-dangerous-packages` CLI flag.

### Layer 5: Network Control (future)
In the current local version, network access is allowed (for `pip install`).
Before any cloud deployment, network will be disabled by default with an
explicit opt-in per session.

### What the Sandbox Does NOT Do
- Docker containerization (overkill for local use, adds complexity)
- Static analysis of generated code before execution (Critic handles this)
- Sandboxing of the host Python interpreter (subprocess is sufficient for a portfolio project)

## Alternatives Considered

### Option A: Docker-based sandbox
Execute code in an isolated Docker container.
Rejected: Requires Docker installation, adds complexity, slower startup.
Good for production, overkill for a local dev tool and portfolio project.

### Option B: RestrictedPython / AST-based filtering
Parse and restrict code before execution.
Rejected: Easy to bypass, high false positive rate, doesn't protect against
resource exhaustion (infinite loops, memory bombs).

### Option C: Subprocess with resource limits (chosen)
Simple, effective, no external dependencies beyond Python stdlib.
Protects against the most common failure modes: crashes, hangs, filesystem pollution.

## Consequences

Easier:
- Implementation: `subprocess.run()` with `timeout` and `cwd` is ~20 lines of code
- Debugging: sandbox directories persist after execution for inspection
- Portability: works on any Python 3.10+ installation, no Docker required

Harder:
- Cross-platform: `resource` module for memory limits is Unix-only (skipped on Windows)
- Package installation latency: `pip install` inside sandbox can be slow (mitigated by caching)

Risks:
- Subprocess isolation is not a security boundary against a determined attacker.
  Acceptable for a portfolio project. Would need containerization for production.
- Whitelist may be too restrictive for some use cases (mitigated by CLI flag)

## References
- Python subprocess documentation: https://docs.python.org/3/library/subprocess.html
- ADR-001: System Architecture (Coder agent)