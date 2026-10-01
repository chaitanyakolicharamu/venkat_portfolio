"""Defense in depth for a bounded demo; regex is not a general injection solution."""
import re

PATTERNS = [
    r"ignore\s+(all\s+|previous\s+|the\s+)*(instructions|rules|polic\w*)",
    r"(reveal|dump|print|exfiltrate|send|export).{0,35}(secret|password|token|credential|patient|ssn)",
    r"(disable|bypass|skip).{0,20}(guard|approval|review|policy|audit|safety)",
    r"(rm\s+-rf|drop\s+table|curl\s+https?://|system\s*prompt)",
]


def blocked_reason(text: str) -> str | None:
    if any(re.search(pattern, text, re.I | re.S) for pattern in PATTERNS):
        return "Request conflicts with the sandbox safety policy"
    return None
