"""OPTIONAL GPU-only training starter. Not run in this deliverable.
Manifest: image_path,text,writer_code,split; writer-disjoint required.
Use a licensed dataset (IAM noncommercial registration) with verified line ground truth.
"""
from __future__ import annotations
import argparse,csv
from pathlib import Path
from PIL import Image,ImageOps
from validate_training_manifest import validate


def main():
    cli=argparse.ArgumentParser()
    cli.add_argument('--manifest',required=True)
    cli.add_argument('--output',default='trained_model_experiment')
    cli.add_argument('--base-model',default='microsoft/trocr-base-handwritten')
    cli.add_argument('--epochs',type=int,default=3)
    cli.add_argument('--batch-size',type=int,default=2)
    args=cli.parse_args()
    validate(args.manifest)
    import torch
    if not torch.cuda.is_available():
        raise SystemExit('GPU with CUDA required for this sample configuration. Do not train large TrOCR on the old CPU laptop.')
    from transformers import TrOCRProcessor,VisionEncoderDecoderModel,Seq2SeqTrainer,Seq2SeqTrainingArguments
    from torch.utils.data import Dataset
    from jiwer import cer,wer
    root=Path(args.manifest).resolve().parent
    with open(args.manifest,encoding='utf-8-sig',newline='') as f:
        rows=list(csv.DictReader(f))
    processor=TrOCRProcessor.from_pretrained(args.base_model)
    model=VisionEncoderDecoderModel.from_pretrained(args.base_model)
    model.config.decoder_start_token_id=processor.tokenizer.cls_token_id
    model.config.pad_token_id=processor.tokenizer.pad_token_id
    model.config.eos_token_id=processor.tokenizer.sep_token_id
    model.config.vocab_size=model.config.decoder.vocab_size
    model.config.max_length=128
    class Lines(Dataset):
        def __init__(self,split):self.items=[r for r in rows if r['split']==split]
        def __len__(self):return len(self.items)
        def __getitem__(self,index):
            r=self.items[index]
            with Image.open(root/r['image_path']) as im:
                pixels=processor(ImageOps.exif_transpose(im).convert('RGB'),return_tensors='pt').pixel_values[0]
            labels=processor.tokenizer(r['text'],max_length=128,truncation=True).input_ids
            return {'pixel_values':pixels,'labels':labels}
    train=Lines('train');valid=Lines('validation');test=Lines('test')
    if not train or not valid or not test:raise SystemExit('train, validation and test splits must all be present')
    def collate(batch):
        pixel=torch.stack([x['pixel_values'] for x in batch])
        pad=processor.tokenizer.pad_token_id
        labels=torch.nn.utils.rnn.pad_sequence([torch.tensor(x['labels']) for x in batch],batch_first=True,padding_value=pad)
        labels[labels==pad]=-100
        return {'pixel_values':pixel,'labels':labels}
    def metrics(eval_predictions):
        p,lab=eval_predictions
        import numpy as np
        if isinstance(p,tuple):p=p[0]
        lab=np.where(lab==-100,processor.tokenizer.pad_token_id,lab)
        preds=processor.batch_decode(p,skip_special_tokens=True)
        refs=processor.batch_decode(lab,skip_special_tokens=True)
        return {'cer':cer(refs,preds),'wer':wer(refs,preds)}
    output=Path(args.output).resolve()
    train_args=Seq2SeqTrainingArguments(
        output_dir=str(output),num_train_epochs=args.epochs,learning_rate=2e-5,
        per_device_train_batch_size=args.batch_size,per_device_eval_batch_size=args.batch_size,
        predict_with_generate=True,eval_strategy='epoch',save_strategy='epoch',
        load_best_model_at_end=True,metric_for_best_model='cer',greater_is_better=False,
        logging_steps=20,save_total_limit=2,fp16=True,report_to='none'
    )
    trainer=Seq2SeqTrainer(model=model,args=train_args,train_dataset=train,eval_dataset=valid,
                          data_collator=collate,compute_metrics=metrics,processing_class=processor)
    trainer.train()
    trainer.save_model(str(output/'best'))
    processor.save_pretrained(str(output/'best'))
    # ONLY AFTER choosing the best model on validation, run once on untouched test.
    print('Held-out test metrics:',trainer.evaluate(test,metric_key_prefix='test'))

if __name__=='__main__':main()
