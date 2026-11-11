"""Dynamic reporting from the canonical panel audit."""
import json
from pathlib import Path


def summarizeUnobservedDays(audit):
    """Return count, dates and Markdown from the same audit list. O(k log k)."""
    days = sorted(audit['unobserved_city_days'])
    return {'count': len(days), 'days': days,
            'markdown': f"Có **{len(days)}** ngày không quan sát: " + ', '.join(days) + '.'}


def loadUnobservedSummary(auditPath):
    """Read the audit exactly once and render its date list. O(k log k)."""
    return summarizeUnobservedDays(json.loads(Path(auditPath).read_text(encoding='utf-8')))
