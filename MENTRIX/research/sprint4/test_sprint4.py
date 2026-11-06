import json, csv, tempfile, unittest
from pathlib import Path
import numpy as np
from research.sprint4.error_analysis import frozen_inputs, analyze, scores, S03, DATA
from research.sprint4.model_benchmark import choose_review_threshold, wilson_lower, reference_features, get_nli_label_mapping

class Sprint04Tests(unittest.TestCase):
    def test_frozen_test_ids_and_labels(self):
        _,ids,splits,preds,test_ids=frozen_inputs()
        self.assertEqual(len(test_ids),129)
        self.assertEqual(len({(x['sample_id'],x['method']) for x in preds}),len(preds))
        self.assertTrue(all(splits[x]=='test' for x in test_ids))

    def test_reproduce_s03_metrics_offline(self):
        with tempfile.TemporaryDirectory() as tmp:
            report=analyze(output=tmp,max_review=10)
            self.assertEqual(report['status'],'EXECUTED_FROZEN_SPRINT03_ERROR_ANALYSIS')
            self.assertEqual(report['test_n'],129)
            self.assertEqual(report['s03_validation_selected']['n'],129)
            self.assertEqual(report['human_review_examples'],17) # at least one from each question
            self.assertTrue(Path(tmp,'s04_human_review_template_LOCAL_ONLY.csv').exists())

    def test_reject_modified_dataset_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            data=Path(tmp,'changed.csv');data.write_bytes(Path(DATA).read_bytes()+b'\n')
            with self.assertRaisesRegex(ValueError,'hash differs'):
                frozen_inputs(dataset=data)

    def test_dangerous_full_credit_and_confusion(self):
        s=scores([0,1,2],[2,2,2])
        self.assertEqual(s['dangerous_full_credit'],2)
        self.assertEqual(s['two_point_errors'],1)
        self.assertEqual(s['confusion_gold_rows_pred_cols'],[[0,0,1],[0,0,1],[0,0,1]])

    def test_reference_features_shape_and_nli_order(self):
        rows=[{'sample_id':'1','prompt_id':'P','answer_text':'not working','reference_text':'working'}]
        vec={'1':np.array([0.,1.])}; ref={'P':np.array([1.,0.])}
        nli={'1':np.array([0.8,0.1,0.1])}
        feats=reference_features(rows,vec,ref,nli)
        self.assertEqual(feats['minilm_reference_cosine'].shape,(1,1))
        self.assertEqual(feats['minilm_nli_reference_features'].shape,(1,5))
        self.assertAlmostEqual(feats['nli_reference_probabilities'][0,0],0.8)

    def test_review_gate_does_not_promote_small_validation(self):
        r=choose_review_threshold([0,1,2,0,1],[0,1,2,0,1])
        self.assertIsNone(r['threshold'])
        self.assertEqual(r['status'],'NO_VALIDATED_AUTO_APPROVAL_THRESHOLD')

    def test_labels_mapping(self):
        class Config: id2label={0:'ENTAILMENT',1:'NEUTRAL',2:'CONTRADICTION'}
        class M: config=Config()
        class E: model=M()
        order,src=get_nli_label_mapping(E())
        self.assertEqual(order,[2,0,1])
        self.assertEqual(src,'checkpoint_id2label')

if __name__=='__main__':unittest.main()
