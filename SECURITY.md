# Security Policy

## Supported Versions

Currently, only the latest `main` branch version of the Kannada RAG Agent is supported with security updates.

| Version | Supported          |
| ------- | ------------------ |
| Main    | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

Security is a priority for this repository, particularly regarding prompt injection mitigations and API key exposure in edge deployments.

If you discover a security vulnerability, please DO NOT open a public issue. Instead, please report it privately:

1. **Email the Maintainers:** Send a detailed report to the core maintainers.
2. **Details to Include:** Provide detailed steps to reproduce the vulnerability, including any relevant code snippets or screenshots. Please state the potential impact of the vulnerability.
3. **Response Time:** We will acknowledge receipt of your vulnerability report within 48 hours and strive to provide a timeline for a fix.

### Areas of Interest
We are particularly interested in vulnerabilities related to:
- Prompt Injection / Jailbreaking that bypasses the deterministic page router.
- Remote Code Execution (RCE) in the FastAPI backend or Streamlit frontend.
- API Key exfiltration vulnerabilities in the deployment configuration.
- Denial of Service (DoS) vectors targeting the memory-mapped ChromaDB instances.
