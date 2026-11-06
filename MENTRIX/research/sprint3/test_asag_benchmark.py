import csv
import pathlib
import tempfile
import unittest
from research.sprint3.asag_benchmark import read_asag, split_prompt, ref_jaccard, execute

class ASAGBenchmarkTests(unittest.TestCase):
    def test_dataset_profile_is_reproducible(self):
        data=pathlib.Path(__file__).parent/'data'/'asag_dataset.csv'
        allrows, usable, blanks=read_asag(data)
        self.assertEqual(len(allrows),646)
        self.assertEqual(len(usable),607)
        self.assertEqual(len(blanks),39)
        self.assertTrue(all(x['human_score']==0 for x in blanks))

    def test_grouped_split_prevents_identical_text_cross_split(self):
        rows=[{'prompt_id':'1','answer_text':'Response '+str(i//2)} for i in range(36)]
        splits=split_prompt(rows)
        norm=lambda s: ' '.join(s.lower().split())
        keys={s:{norm(r['answer_text']) for r in split} for s,split in splits.items()}
        for a in keys:
            for b in keys:
                if a != b:self.assertFalse(keys[a] & keys[b])

    def test_reference_similarity(self):
        self.assertAlmostEqual(ref_jaccard('cat dog','dog cat'),1.0)
        self.assertEqual(ref_jaccard('cat','dog'),0.0)

    def test_missing_dataset_is_not_success(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(FileNotFoundError):
                execute(pathlib.Path(d)/'not_found.csv',pathlib.Path(d)/'out')

    def test_no_student_answer_text_in_public_predictions(self):
        with tempfile.TemporaryDirectory() as d:
            data=pathlib.Path(__file__).parent/'data'/'asag_dataset.csv'
            out=pathlib.Path(d)/'report'
            results=execute(data,out)
            self.assertEqual(len(results['per_prompt']),17)
            self.assertEqual(set(results['method_summary']),{
                'mean','tfidf_word_ridge','tfidf_char_ridge',
                'token_overlap_knn','tfidf_word_knn','tfidf_char_knn','reference_jaccard_ridge'})
            with (out/'asag_s03_test_predictions.csv').open(encoding='utf-8-sig',newline='') as f:
                reader=csv.DictReader(f)
                self.assertNotIn('answer_text',reader.fieldnames)
                self.assertTrue(any(r['selected_on_validation']=='True' for r in reader))

if __name__=='__main__':unittest.main(verbosity=2)
