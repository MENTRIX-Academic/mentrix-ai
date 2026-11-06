import csv,sys,tempfile,unittest,importlib.util
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from prepare_asap import prepare
from evaluate_ocr import edit_distance,evaluate
from evaluate_short_asap import evaluate as evaluate_short

class Sprint1Tests(unittest.TestCase):
    def test_edit_distance(self):
        self.assertEqual(edit_distance('abc','adc'),1)
        self.assertEqual(edit_distance('','xyz'),3)
        self.assertEqual(edit_distance(['red','cat'],['red','hat']),1)
    def test_writer_disjoint_ocr(self):
        with tempfile.TemporaryDirectory() as t:
            inp=Path(t)/'pred.csv';out=Path(t)/'metrics.json'
            with inp.open('w',newline='',encoding='utf-8') as f:
                w=csv.writer(f);w.writerow(['sample_id','writer_code','split','ground_truth','prediction'])
                w.writerow(['one','W1','test','The cat sat','The cat sit'])
                w.writerow(['two','W2','validation','Yes','Yes'])
            res=evaluate(inp,out)
            self.assertEqual(res['metrics']['samples'],1)
            self.assertGreater(res['metrics']['cer'],0)
            self.assertTrue(out.is_file())
    def test_asap_split_duplicates_not_leaked(self):
        with tempfile.TemporaryDirectory() as t:
            inp=Path(t)/'train.tsv';out=Path(t)/'clean.csv'
            with inp.open('w',newline='',encoding='utf-8') as f:
                w=csv.writer(f,delimiter='\t');w.writerow(['Id','EssaySet','Score1','Score2','EssayText'])
                for i in range(60):
                    w.writerow([str(i),1,i%5,i%5,f'Answer number {i//2} extra words'])
            rows,_=prepare(inp,out)
            for answer in {r['answer_text'] for r in rows}:
                self.assertEqual(len({r['split'] for r in rows if r['answer_text']==answer}),1)
            self.assertEqual({r['split'] for r in rows},{'train','validation','test'})
    @unittest.skipUnless(importlib.util.find_spec("sklearn") is not None, "Optional scikit-learn not installed; install research/sprint1/requirements.txt")
    def test_short_baseline_smoke_only_fake_data(self):
        with tempfile.TemporaryDirectory() as t:
            inp=Path(t)/'train.tsv';out=Path(t)/'prepared.csv';metrics=Path(t)/'metrics.json'
            with inp.open('w',newline='',encoding='utf-8') as f:
                w=csv.writer(f,delimiter='\t');w.writerow(['Id','EssaySet','Score1','Score2','EssayText'])
                for i in range(100):
                    w.writerow([i,1,i%3,i%3,'artificial answer '+str(i)])
            prepare(inp,out)
            result=evaluate_short(out,metrics)
            self.assertEqual(result['dataset'],'KAGGLE_ASAP_SAS')  # contract only; fixture is synthetic!
            self.assertEqual(len(result['results_by_prompt']),1)

if __name__=='__main__':unittest.main(verbosity=2)
