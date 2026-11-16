"""Shared explicit input columns for future ML models and grouped ablation."""
import json
from . import config


def featureColumns(excludedGroups=()):
    """Select configured groups; reject unknown groups and target leakage. O(p)."""
    schema = json.loads((config.PROJECT_ROOT / 'configs/forecast_features.json').read_text(encoding="utf-8"))
    unknown = set(excludedGroups) - set(schema['groups'])
    if unknown:
        raise ValueError(f'Unknown feature groups: {unknown}')
    columns = [c for g, cs in schema['groups'].items() if g not in excludedGroups for c in cs]
    if set(columns) & set(schema['forbidden']):
        raise ValueError('Forbidden target or evaluation columns in feature schema')
    return columns

