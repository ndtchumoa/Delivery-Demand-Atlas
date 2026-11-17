"""As-of spatial statistics: training rows use earlier train dates; evaluation freezes at train end."""
import numpy as np
import pandas as pd
from . import config

DATE = config.DEMAND_DATE_COLUMN
KEYS = ['region_id', 'aoi_type']
SPATIAL = ['centroid_lng', 'centroid_lat', 'historical_density', 'spatial_fallback']


def fitSpatial(orders, observedDays):
    """Fit AOI medians in each original region/type, equal-AOI centroid and orders/AOI/day.

    Density is not geographic orders/km². Invalid coordinates do not remove orders from density.
    Fallback levels: 0=series, 1=region, 2=global. Never reassign multi-region AOIs to modal region.
    """
    orders = orders.copy()
    for col, limit in [('lng', 180), ('lat', 90)]:
        orders.loc[~np.isfinite(orders[col]) | orders[col].abs().gt(limit), col] = np.nan
    invalid = orders[['lng', 'lat']].isna().any(axis=1) | (
        orders.lng.abs().lt(1) & orders.lat.abs().lt(1))
    orders.loc[invalid, ['lng', 'lat']] = np.nan
    nDays = len(pd.Index(observedDays).unique())
    if orders.empty or not nDays:
        raise ValueError('Spatial fitting requires earlier observed training days and orders')

    def aggregate(keys):
        if not keys:
            src = orders.assign(_global=0)
            keys = ['_global']
        else:
            src = orders
        aois = src.groupby(keys + ['aoi_id'], dropna=False)[['lng', 'lat']].median()
        centres = aois.groupby(level=list(range(len(keys))))[['lng', 'lat']].mean()
        totals = src.groupby(keys, dropna=False).agg(n_orders=('order_id', 'size'), n_aois=('aoi_id', 'nunique'))
        out = totals.join(centres).reset_index().rename(columns={'lng': 'centroid_lng', 'lat': 'centroid_lat'})
        out['historical_density'] = out.n_orders / out.n_aois / nDays
        out['observed_train_days'] = nDays
        return out

    return {'series': aggregate(KEYS), 'region': aggregate(['region_id']), 'global': aggregate([])}


def applySpatial(frame, fitted):
    """Apply fitted values with deterministic region/global fallback; preserve row index and order."""
    out = frame.copy()
    # Map rather than merge so the original index remains aligned with forecasts.
    lookup = fitted['series'].set_index(KEYS)
    idx = pd.MultiIndex.from_frame(out[KEYS])
    for col in SPATIAL[:-1]:
        out[col] = lookup[col].reindex(idx).to_numpy()
    out['spatial_fallback'] = 0
    region = fitted['region'].set_index('region_id')
    for level in [1, 2]:
        missing = out[SPATIAL[:-1]].isna().any(axis=1)
        out.loc[missing, 'spatial_fallback'] = level
        for col in SPATIAL[:-1]:
            values = out.region_id.map(region[col]) if level == 1 else fitted['global'][col].iloc[0]
            if isinstance(values, pd.Series):
                out.loc[missing, col] = values.loc[missing]
            else:
                out.loc[missing, col] = values
    if out[SPATIAL].isna().any().any():
        raise ValueError('Training geography has no valid global centroid')
    return out


def buildSpatialFeatures(data, orders, bounds):
    """Return as-of features and final train-only lookup; test targets/coordinates are never fitted."""
    trainOrders = orders[orders[DATE].between(*bounds['train'])].copy()
    observed = data.loc[(data.split == 'train') & data.city_observed, DATE].drop_duplicates()
    fitted = fitSpatial(trainOrders, observed)
    # Only ready rows are needed for ML. Warmup rows remain history, not training examples.
    eligible = data[data.city_observed & data.history_ready].copy()
    frames = []
    for day, rows in eligible[eligible.split == 'train'].groupby(DATE, sort=True):
        prior = trainOrders[trainOrders[DATE] < day]
        frames.append(applySpatial(rows, fitSpatial(prior, observed[observed < day])))
    frames.append(applySpatial(eligible[eligible.split != 'train'], fitted))
    return pd.concat(frames).sort_index(), fitted
