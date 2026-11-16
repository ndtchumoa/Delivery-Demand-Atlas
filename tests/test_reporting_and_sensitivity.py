"""Tests for live audit text, shared feature schema and A/B decision criteria."""
import json
import re
import unittest
import pandas as pd
from src import config
from src.audit_reporting import loadUnobservedSummary, summarizeUnobservedDays
from src.feature_schema import featureColumns
from src.sensitivity_keep_all_orders import compareArms

class ReportingTests(unittest.TestCase):
    def testDisplayedCountMatchesAudit(self):
        summary = loadUnobservedSummary(config.PANEL_AUDIT_FILE)
        audit = json.loads(config.PANEL_AUDIT_FILE.read_text(encoding="utf-8"))
        count = int(re.search(r'\*\*(\d+)\*\*', summary['markdown']).group(1))
        self.assertEqual(count, len(audit['unobserved_city_days']))
        notebook = json.loads((config.PROJECT_ROOT / 'notebooks/01_eda.ipynb').read_text(encoding="utf-8"))
        rendered = [o.get('data', {}).get('text/markdown', '') for c in notebook['cells'] for o in c.get('outputs', [])]
        rendered = [''.join(x) if isinstance(x, list) else x for x in rendered]
        self.assertIn(summary['markdown'], rendered)

        for day in audit['unobserved_city_days']:
            self.assertIn(day, summary['markdown'])
        # A changed audit must change the displayed value, without editing Markdown.
        self.assertIn('**2**', summarizeUnobservedDays({'unobserved_city_days':['2022-01-02','2022-01-01']})['markdown'])

    def testCalendarRetainedAndAblation(self):
        self.assertIn('day_of_week', featureColumns())
        self.assertNotIn('demand', featureColumns())
        self.assertNotIn('day_of_week', featureColumns(['calendar']))
        with self.assertRaises(ValueError): featureColumns(['unknown'])

    def testSensitivityThresholdAndRanking(self):
        rows = [dict(scenario='s',model=m,arm=a,mae=mae,wape=wape) for a,m,mae,wape in
                [('A','m1',1.,.2),('A','m2',2.,.3),('B','m1',1.005,.21),('B','m2',2.005,.31)]]
        data=pd.DataFrame(rows)
        self.assertTrue(compareArms(data,.01)[1][0]['passed'])
        data.loc[(data.arm=='B')&(data.model=='m1'),'mae']=1.02
        self.assertFalse(compareArms(data,.01)[1][0]['passed'])
        data.loc[(data.arm=='B')&(data.model=='m1'),['mae','wape']]=[1.,.4]
        self.assertFalse(compareArms(data,.01)[1][0]['ranking_unchanged'])

if __name__=='__main__': unittest.main()
