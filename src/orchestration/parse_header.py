"""Parsing of provider rate-limit reset headers."""


def parse_reset_header(raw: object) -> float:
    """Parse ratelimit reset strings (e.g. '1m26.4s', '42.9s') into seconds."""
    if not isinstance(raw, (str, int, float)):
        return 65.0
    s = str(raw).strip()
    try:
        if s.endswith("ms"):
            return float(s[:-2]) / 1000.0
        if "m" in s and s.endswith("s"):
            parts = s.rstrip("s").split("m")
            mins = float(parts[0])
            secs = float(parts[1]) if parts[1] else 0.0
            return mins * 60.0 + secs
        elif s.endswith("s"):
            return float(s[:-1])
        elif s.endswith("m"):
            return float(s[:-1]) * 60.0
        return float(s)
    except Exception:
        return 65.0
