import csv
import sys
import tempfile
import unittest
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
sys.path.insert(0,str(HERE.parent/'sprint1'))
from prepare_asap import prepare
from benchmark import analyze,metrics
from run import main

class Sprint2Tests(unittest.TestCase):
    def test_no_dataset_is_not_a_benchmark(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(main(['--input',str(Path(d)/'train.tsv')]),2)
            self.assertFalse((Path(d)/'asap_s02_metrics.json').is_file())

    def test_human_score_metric_contract(self):
        result=metrics([1,2,3],[1.0,2.0,2.9],(0,3))
        self.assertEqual(result['exact_match'],1.0)
        self.assertEqual(result['mae'],0)

    def test_no_leakage_and_all_baselines(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);tsv=d/'train.tsv';prepared=d/'prepared.csv'
            with tsv.open('w',encoding='utf-8',newline='') as f:
                w=csv.writer(f,delimiter='\t');w.writerow(['Id','EssaySet','Score1','Score2','EssayText'])
                for i in range(1080):
                    score=i%4
                    w.writerow([i,1,score,score,'This score '+str(score)+' and response number '+str(i//2)+' is longer.'])
            _,info=prepare(tsv,prepared)
            result=analyze(prepared,d/'output',tsv)
            self.assertEqual(result['rows_total'],1080)
            self.assertEqual(result['prompts'],1)
            self.assertEqual(len(result['per_prompt'][0]['baselines']),6)
            self.assertEqual(len(result['method_summary']),6)
            self.assertTrue((d/'output'/'asap_s02_report.md').is_file())
            self.assertEqual((d/'output'/'asap_s02_test_predictions.csv').read_text(encoding='utf-8-sig').count('\n')-1,6*result['per_prompt'][0]['rows']['test'])

    def test_leakage_blocks_benchmark(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);inp=d/'fake.csv'
            with inp.open('w',encoding='utf-8',newline='') as f:
                w=csv.writer(f)
                w.writerow(['sample_id','prompt_id','answer_text','human_score','split'])
                for i in range(1050):w.writerow([i,'1','answer '+str(i),i%2,'train' if i<850 else 'test'])
                w.writerow([1200,'1','ANSWER 0',1,'test'])
            with self.assertRaisesRegex(ValueError,'leaked across splits'):
                analyze(inp,d/'out')

if __name__=='__main__':unittest.main(verbosity=2)
