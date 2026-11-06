import unittest,sys,csv
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from adapter import QUESTIONS,grade
from research.compare import audit
class ResearchTests(unittest.TestCase):
 def test_cases_have_no_real_pii(self):
  with (ROOT/'research/data/curated_demo_cases.csv').open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
  self.assertEqual(len(rows),29)
  self.assertTrue(all(r['provenance'].startswith('ARTIFICIAL_') for r in rows))
 def test_v2_crucial_changes(self):
  self.assertEqual(grade(QUESTIONS['SA02'],'freq','v1')['decision'],'incorrect')
  self.assertEqual(grade(QUESTIONS['SA02'],'freq','v2')['decision'],'needs_review')
  self.assertEqual(grade(QUESTIONS['MC01'],'Answer: B','v1')['decision'],'needs_review')
  self.assertEqual(grade(QUESTIONS['MC01'],'Answer: B','v2')['decision'],'correct')
  self.assertEqual(grade(QUESTIONS['MA03'],'2.000000001 Hz','v2')['decision'],'needs_review')
 def test_reproducibility_matrix(self):
  rows,meta=audit()
  self.assertEqual(len(rows),29)
  self.assertEqual(meta['total_cases'],29)
  self.assertTrue(all(x['v2_matches_illustrative_policy']=='True' for x in rows))
  self.assertTrue(any(x['changed_v1_to_v2']=='True' for x in rows))
 def test_essay_is_not_model_scored(self):
  self.assertEqual(grade(QUESTIONS['E01'],'anything','v2')['decision'],'needs_review')
 def test_human_template_empty(self):
  with (ROOT/'research/templates/human_holdout_template.csv').open(encoding='utf-8-sig',newline='') as f:
   self.assertEqual(len(list(csv.DictReader(f))),0)
if __name__=='__main__':unittest.main()
