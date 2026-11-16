"""Controlled baseline sensitivity to the retrospective >24h exclusion rule."""
import json
import numpy as np
import pandas as pd
from . import config
from .data_loader import loadRawDelivery
from .preprocessing import addDerivedColumns, buildFlaggedAndAnalysis, buildDemandPanel
from .train_forecast import runScenario
from .evaluate_forecast import evaluatePredictions


def compareArms(metrics, threshold):
    """Compare full WAPE ranking and each baseline MAE on validation. O(M log M)."""
    a = metrics[metrics.arm.eq('A')].copy()
    b = metrics[metrics.arm.eq('B')].copy()
    keys = ['scenario', 'model']
    comparison = a.merge(b, on=keys, suffixes=('_A', '_B'), validate='one_to_one')
    base = comparison.mae_A.to_numpy()
    delta = np.abs(comparison.mae_B - base)
    comparison['relative_mae_change'] = np.divide(delta, base, out=np.where(delta == 0, 0., np.inf), where=base != 0)
    comparison['mae_within_threshold'] = comparison.relative_mae_change < threshold
    summary = []
    for scenario in a.scenario.unique():
        order = lambda frame: frame[frame.scenario.eq(scenario)].sort_values(['wape','mae','model']).model.tolist()
        same = order(a) == order(b)
        sub = comparison[comparison.scenario.eq(scenario)]
        summary.append(dict(scenario=scenario, ranking_A=order(a), ranking_B=order(b),
                            ranking_unchanged=same, all_mae_within_threshold=bool(sub.mae_within_threshold.all()),
                            passed=bool(same and sub.mae_within_threshold.all())))
    return comparison, summary


def main():
    """Keep the primary outputs intact; write sensitivity results separately. O(N log N)."""
    protocol = json.loads((config.PROJECT_ROOT/'configs/sensitivity_keep_all_orders.json').read_text(encoding="utf-8"))
    windows = json.loads(config.STABLE_PERIOD_FILE.read_text(encoding="utf-8"))['splits']
    flagged, analysis, excluded = buildFlaggedAndAnalysis(addDerivedColumns(loadRawDelivery()))
    arms = {'A':analysis, 'B':flagged}
    panels = {arm:buildDemandPanel(frame) for arm,frame in arms.items()}
    assert panels['A'][['series_id','ds_date']].equals(panels['B'][['series_id','ds_date']])
    predictions, metrics, totals = [], [], []
    for arm, frame in arms.items():
        counts = frame.groupby(['region_id','aoi_type']).size().rename('n_orders').reset_index()
        counts['arm'] = arm; totals.append(counts)
        for scenario in protocol['scenarios']:
            _, pred = runScenario(panels[arm], scenario, windows[scenario])
            pred = pred[pred.split.eq('validation')].copy()
            pred['arm'] = arm; predictions.append(pred)
            scored = evaluatePredictions(pred)
            scored = scored[scored.level.eq('series')].copy(); scored['arm']=arm; metrics.append(scored)
    allPred = pd.concat(predictions, ignore_index=True)
    for scenario in protocol['scenarios']:
        a=allPred[(allPred.scenario==scenario)&(allPred.arm=='A')]
        b=allPred[(allPred.scenario==scenario)&(allPred.arm=='B')]
        keys=['model','series_id','ds_date']
        assert a[keys].reset_index(drop=True).equals(b[keys].reset_index(drop=True))
    comparison, summary = compareArms(pd.concat(metrics), protocol['relative_mae_threshold'])
    out=config.FORECASTS_DIR/'sensitivity_keep_all_orders';out.mkdir(parents=True,exist_ok=True)
    comparison.to_csv(out/'validation_comparison.csv',index=False)
    allPred.to_csv(out/'validation_predictions.csv',index=False)
    totals=pd.concat(totals).pivot(index=['region_id','aoi_type'],columns='arm',values='n_orders').fillna(0).astype(int)
    totals['B_minus_A']=totals.B-totals.A;totals.to_csv(out/'orders_by_series.csv')
    removed=flagged[flagged.flag_exclude_over_24h].copy()
    removed[['order_id','region_id','aoi_type','ds_date','delivery_minutes','flag_invalid_gps']].to_csv(out/'retained_8_orders.csv',index=False)
    report=dict(protocol=protocol,orders_A=len(analysis),orders_B=len(flagged),exclusion_reason='delivery_minutes > 1440; no GPS exclusion',
                removed_orders_by_date=removed.ds_date.dt.strftime('%Y-%m-%d').value_counts().sort_index().to_dict(),
                results=summary,scope='baseline validation only; does not establish ML or routing robustness')
    (out/'summary.json').write_text(json.dumps(report,indent=2), encoding="utf-8")
    print(comparison[['scenario','model','mae_A','mae_B','wape_A','wape_B','relative_mae_change']].to_string(index=False))
    print(json.dumps(summary,indent=2))
    return report


if __name__=='__main__':
    main()

