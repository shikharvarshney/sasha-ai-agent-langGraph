# Internal Policy: Use of Cursor AI in Engineering

## Purpose

This policy defines **how Cursor AI may be used safely and effectively** within the engineering organization, acknowledging its **real capabilities and limitations**.

Cursor is an **AI coding assistant**, not a deterministic system, policy engine, or security boundary.

---

## What Cursor Is (Reality)

- A **probabilistic coding assistant**
- Optimized for speed, iteration, and developer productivity
- Helpful for:
  - Code generation
  - Refactoring
  - Explanations
  - Documentation
- **Not guaranteed** to:
  - Follow rules deterministically
  - Apply instructions in a fixed order
  - Acknowledge which rules were loaded

---

## What Cursor Is NOT

Cursor must **not** be treated as:
- A security control
- A policy enforcement engine
- A compliance gate
- A replacement for code review
- A substitute for CI/CD checks

All outputs must be reviewed and validated.

---

## Rule Hierarchy & Enforcement (Practical)

### 1. Project Rules (`.cursor/rules/*.mdc`) — Primary Control
- Project rules are the **most reliable constraint mechanism** available.
- All critical guidance must live in project rules.
- Each rule file must be **self-contained** and enforceable without referencing other rules.

Examples:
- Security constraints
- Architectural boundaries
- Coding standards

### 2. User Rules — Advisory Only
- User rules may guide behavior but are **not guaranteed** to be injected or applied.
- User rules **must not** be relied upon for safety, compliance, or enforcement.

### 3. Chat Instructions — Lowest Priority
- Chat prompts are contextual and non-deterministic.
- They must not override project rules.

---

## Security & Safety Principles

Cursor **must never** be the final authority for:
- Secret handling
- Authentication logic
- Authorization logic
- Infrastructure changes
- Production configuration

Mandatory controls outside Cursor:
- Code reviews
- CI/CD pipelines
- Secret scanners (e.g., Gitleaks)
- Linters and static analysis
- Access controls and approvals

---

## Approved Usage

Cursor may be used for:
- Writing boilerplate code
- Refactoring existing code
- Generating tests (with review)
- Explaining unfamiliar code
- Drafting documentation
- Prototyping ideas

---

## Restricted Usage

Cursor must **not** be used to:
- Autonomously deploy to production
- Modify secrets or credentials
- Execute commands without review
- Bypass security or architectural constraints
- Make compliance-related decisions

---

## Privacy & Data Handling

- **Privacy Mode must be enabled** for confidential or proprietary projects.
- Sensitive files must be excluded via `.cursorignore`.
- Secrets must never be pasted into prompts.

---

## Review & Accountability

- All AI-generated code is treated as **human-authored code**.
- The engineer using Cursor is **fully accountable** for:
  - Correctness
  - Security
  - Compliance
  - Maintainability

---

## Guiding Principle

> Cursor accelerates development,  
> **but responsibility remains with engineers.**

We optimize for:
- Speed **with** guardrails
- Productivity **with** accountability
- Assistance **without** abdication of judgment

---

## Policy Status

- This policy reflects **current observed behavior**, not future promises.
- It will be reviewed as Cursor capabilities evolve.

---


# Cursor PRO Tips & Safety Best Practices

A curated set of **power-user tips, workflows, and security practices** for using **Cursor / Cursor Pro** effectively and safely in production-grade environments.

---

## 🧠 Cursor PRO Productivity Tips

### 1. *** Use Plan Mode Before Coding and ASK Mode for clarifying something ***
- Start a new chat (`Cmd + N`) and switch to **Plan Mode** (`Shift + Tab`).
- Let Cursor analyze the codebase and generate:
  - File changes
  - Step-by-step execution plan
  - Architectural suggestions
- Review and edit the plan before running Build.
- Ask mode to get knowledge. 
- Only use Agent mode when you want to perform a task after asking and planning.

---

### 2. *** Use Context Injection with `@` ***
- Type `@` to explicitly add context:
  - Files, folders
  - Git branches (`@branch`)
  - Previous chats
- Prevents hallucinations and out-of-context changes.

---

### 3. *** Create Custom Commands ***
- Add Markdown files under a `commands/` directory.
- Commands appear when typing `/` in Cursor.
- Example use cases:
  - `/do-code-review`
  - `/write-tests`
  - `/develop`
- Enables repeatable, opinionated workflows.
- A great example of a simple command wheneever you trying to develop/refactor something in the code base could be as below. This will simply ensure that 
coding standards are read through by cursor before coding and devs/designers have to only develop a habbit of typing `/develop` before building anything.
However, this does not deny the need of Code Reviews. They are still primary. 
- In some other optimisation strategy you can always make a command to instruct AI to do the PR Review of their own code. It has been proven that re-iterating 
an AI to force into feedback loop often improves the result.

An example for `/develop` command :- 

---
`You are helping develop a new feature

IMPORTANT:
- Before responding, ensure that `@coding-standards.mdc` is included in context.
- If it is not present, ask the user to attach it before continuing.

CODING STANDARDS (MANDATORY):
- Follow existing project structure and naming conventions
- Do not introduce new architectural patterns without explanation
- Prefer explicit, readable code over clever abstractions
- Write code that is testable and maintainable

SECURITY (MANDATORY):
- Never hardcode secrets or credentials
- Assume secrets are managed externally
- Do not modify auth, permissions, or infra unless explicitly requested

BEHAVIOR:
- Ask clarifying questions if requirements are ambiguous
- Stop and ask if a request conflicts with these constraints

Now implement the following feature:`

---

### 4. *** Code Review by AI builds a feedback loop to improve on its own code as a first line of defence ***
- use `/do-code-review` @diff or `/do-code-review` @branch commands every time you code something.
- refer the command instructions from the commands in the repo.

---

### 5. *** Manage the Context Window ***
- Monitor context usage (e.g., 200k token window).
- Use `/summarize` to compress long conversations.
- Prefer starting fresh chats for new features.
- This will help you to get better accurate results.

---

### 6. *** Keep Usage Summary Always Visible ***
- Enable usage visibility in settings.
- Helps manage resets, token limits, and cost awareness.

---

### 7. *** Master Keyboard Shortcuts ***
- `Cmd + I` → Open Agent
- `Cmd + /` → Switch Model
- `Cmd + N` → New Chat
- Customize shortcuts for faster workflows.

---

### 8. *** Use Checkpoints & Rollbacks ***
- Revert to previous AI states within a chat by using the U turn symbol at the bottom right corner of the chat window.
- Useful for undoing bad suggestions quickly.
- Still rely on Git for real version control.

---

### 9. *** Use Visualizations ***
- Ask Cursor to generate: 
  - Mermaid diagrams
  - System flow charts
  - Dependency graphs
- Useful for documentation and onboarding.

---

## 🔐 Cursor Security, Privacy & Safety Best Practices

### 10. Turn Off Auto-Run Mode (YOLO Mode)
- Disable **Auto-Run Mode** to prevent:
  - Automatic command execution
  - Silent file modifications
- Always review before allowing execution.
- **Critical protection against malicious code execution.**

---

### 11. Enable Built-In Protections
Enable the following in Cursor settings:
- **File Deletion Protection**
- **Dotfile Protection**

These add friction against:
- Accidental deletes
- Malicious filesystem changes

---

### 12. Use `.cursorignore`
- Create a `.cursorignore` file in the project root.
- Prevent sensitive files from being indexed by Cursor.
- Recommended exclusions:
  ```txt
  .env
  *.pem
  *.key
  *.p12
  secrets/
  credentials/
  **/config/secrets.*

# Cursor Security & Governance Guidelines

This document outlines **critical security, privacy, and governance practices** for using Cursor in **enterprise, fintech, or regulated environments**.

---

## 13. Enable Privacy Mode

Enable **Privacy Mode** for confidential or proprietary projects.

### Why this matters
Privacy Mode ensures that:
- Code is **not stored** by model providers
- Interactions are **not used for training**

### Recommendation
- **Strongly recommended** for:
  - Enterprise codebases
  - Fintech systems
  - Regulated environments (SOC2, PCI, HIPAA, etc.)

---

## 14. Use Sandboxed Environments

Run Cursor inside a **restricted execution environment**, such as:
- Docker / Podman container
- Virtual Machine (VM)
- Separate OS user account

### Security Benefits
Prevents Cursor from accessing:
- SSH keys
- Cloud credentials
- Sensitive host files
- Personal or unrelated system data

This limits blast radius in case of misconfiguration or malicious output.

---

## 15. Implement Proper Secret Management

### Never Hardcode Secrets
- Do **not** embed secrets in:
  - Source code
  - Prompts
  - Configuration files

### Use Dedicated Secret Managers
Recommended tools:
- HashiCorp Vault
- AWS Secrets Manager
- GCP Secret Manager

### Integrate Secret Scanning
Add automated scanners to your workflow:
- Gitleaks
- Secretlint

Run scans:
- Pre-commit
- In CI pipelines  

This blocks credential leaks before they reach production or version control.

---

## 16. Implement Cursor Rules (`.cursor/rules/*.mdc`) - Increases code accuracy by 27%. 

Define **project-specific AI rules** using:

### Example Rules
- “Never hardcode secrets”
- “Validate all user input”
- “Follow layered / hexagonal architecture”

### Purpose
- Guides Cursor toward **secure, consistent behavior**
- Encodes architectural and security constraints directly into AI usage

### Rules are:-
- Rules are best-effort
- Determinism is not guaranteed
- Repetition + proximity to the prompt increases compliance
- Developer ergonomics matter more than theoretical purity

Refer these rules as an example:- https://github.com/PatrickJS/awesome-cursorrules/tree/main/rules-new

---

## 17. Treat Cursor Rule Files as Code
- Explicitly reference key rules at the start of conversations. Sometimes cursor ignores these rules even after declaring them.
- Attach critical rules as markdown files directly to the chat
- We can follow this tutorial for best practices:- https://pageai.pro/blog/cursor-rules-tutorial

- Store rule files in **version control**
- Apply:
  - Code reviews
  - Integrity checks
- Prevent:
  - Silent modifications
  - Malicious rule tampering

### Key Insight
Cursor rules act as an **AI policy enforcement layer**, similar to:
- Lint rules
- Security policies
- Architecture decision records (ADRs)

Cursor (like most AI coding tools) resolves instructions roughly in this order:
- System instructions (Cursor internal)
- Rules (user --> project) -- But this is not 100% picked up everytime by cursor.
- Chat prompt / instructions
- Implicit inference

## 18. Run Multi agents for the same task
- You can run multi agents by selecting different models using the 1x symbol besides the model name in chat window.
- once done, cursor automatically selects the best answer giving you double conformity.

## 19. Switch branches without commmiting or stashing the code
- you can now swithc the branches by using the Laptop icon beneath the chat window and select `worktree` and then choosing branch.
- this will help you to immediately change context to provide any hotfixes in the main branch even if you are working on some feature branch.

## 20. Use Cursor BugBot
- in your system to identify any breaking changes 
- any security vulnerabilities and allow and automatic PR review by the Agent
- you should be able to fix the bug right there from Github

---

# Cursor Do & Don’t — Quick Reference for Engineers

This document provides a **practical, reality-based guide** for using Cursor safely and effectively in day-to-day engineering work.

---

## ✅ DO

- ✅ Treat Cursor as a **pair programmer**, not an authority
- ✅ Review **every line** of AI-generated code
- ✅ Follow `.cursor/rules/*.mdc` **strictly**
- ✅ Use Cursor for:
  - Refactoring
  - Writing tests
  - Explanations
  - Documentation
- ✅ Start a **new chat** for new tasks or features
- ✅ Ask Cursor to **explain its output** if anything is unclear
- ✅ Stop and ask for help when something feels unsafe or wrong

---

## ❌ DON’T

- ❌ Do **NOT** paste secrets into prompts
- ❌ Do **NOT** assume Cursor followed all rules
- ❌ Do **NOT** trust statements like:
  - “I complied with the rules”
  - “This follows best practices”
- ❌ Do **NOT** let Cursor deploy or execute commands unattended
- ❌ Do **NOT** bypass code review because “AI wrote it”
- ❌ Do **NOT** use Cursor as a security decision-maker
- ❌ Do **NOT** rely on User Rules for enforcement

---

## 🚨 Red Flags — Stop Immediately

If you see any of the following, **STOP and escalate**:

- 🚩 Cursor suggests hardcoding credentials
- 🚩 Cursor modifies infrastructure or authentication logic casually
- 🚩 Cursor ignores architectural boundaries or layering
- 🚩 Cursor claims certainty without evidence
- 🚩 Cursor asks to disable safeguards or protections

---

## 🧠 Remember

> Cursor accelerates typing, not thinking.  
> Judgment, responsibility, and accountability remain **human**.

---



