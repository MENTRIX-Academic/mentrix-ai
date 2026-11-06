"""CLI for Kaggle ASAP-SAS baseline, supports local TSV or opt-in Kaggle CLI download."""
from __future__ import annotations
import argparse
import sys
import subprocess
import zipfile
from pathlib import Path
from datetime import datetime,timezone
import json

ROOT=Path(__file__).resolve().parents[2]
S1=ROOT/'research'/'sprint1'
S2=ROOT/'research'/'sprint2'
DEFAULT_TSV=S1/'data'/'asap'/'train.tsv'
DEFAULT_PREP=S1/'data'/'asap_prepared.csv'
OUT=S2/'results'


def download_tsv(destination:Path):
    print('\nKaggle competition license: https://www.kaggle.com/competitions/asap-sas/data')
    print('You must sign in, accept the competition rules, and configure Kaggle credentials on your PC.')
    destination.parent.mkdir(parents=True,exist_ok=True)
    result=subprocess.run([sys.executable,'-m','kaggle','competitions','download',
                           '-c','asap-sas','-f','train.tsv','-p',str(destination.parent)],
                           check=False)
    if result.returncode:raise RuntimeError('Kaggle download failed. Accept the rules and configure Kaggle authentication; no benchmark performed.')
    if destination.is_file():return
    for path in (destination.parent/'train.tsv.zip',destination.parent/'asap-sas.zip'):
        if path.is_file():
            with zipfile.ZipFile(path) as archive:
                names=[name for name in archive.namelist() if Path(name).name.casefold()=='train.tsv']
                if len(names)!=1:raise ValueError('Expected one train.tsv in downloaded archive')
                with archive.open(names[0]) as src, destination.open('wb') as out:
                    import shutil
                    shutil.copyfileobj(src,out)
            return
    raise FileNotFoundError('Kaggle command completed, but train.tsv was not found')


def main(argv=None):
    parser=argparse.ArgumentParser(description='MENTRIX Sprint 02 honest ASAP-SAS benchmark')
    parser.add_argument('--input',type=Path,default=DEFAULT_TSV,help='Official ASAP-SAS train.tsv file')
    parser.add_argument('--download',action='store_true',help='OPT-IN: download via your Kaggle CLI credentials (requires accepted rules)')
    parser.add_argument('--output-dir',type=Path,default=OUT)
    args=parser.parse_args(argv)
    if args.download and not args.input.is_file():download_tsv(args.input)
    if not args.input.is_file():
        print('DATA_NOT_AVAILABLE: No authorized Kaggle ASAP-SAS train.tsv found.\n'
              '1) Open https://www.kaggle.com/competitions/asap-sas/data and accept the rules.\n'
              '2) Download train.tsv and copy it to: '+str(args.input)+'\n'
              '3) Or install the official Kaggle CLI and run: python research/sprint2/run.py --download\n'
              'Existing project files and results were not modified.')
        return 2
    sys.path.insert(0,str(S1))
    from prepare_asap import prepare
    from benchmark import analyze
    print('Preparing leakage-aware prompt splits from locally supplied file ...')
    prepare(args.input,DEFAULT_PREP,42,0)
    print('Training/evaluating six predetermined baselines per prompt ...')
    result=analyze(DEFAULT_PREP,args.output_dir,args.input)
    print('SUCCESS: evaluation completed on locally supplied text dataset.')
    print('Samples:',result['rows_total'],'prompts:',result['prompts'])
    print('Read:', args.output_dir/'asap_s02_report.md')
    print('IMPORTANT: source is locally provided; verify official Kaggle provenance. Not valid for 1-3 words or OCR yet.')
    return 0

if __name__=='__main__':
    try:sys.exit(main())
    except (ValueError,OSError,RuntimeError,ImportError,subprocess.SubprocessError) as e:
        print('BENCHMARK_NOT_COMPLETED:',str(e))
        print('No actual human-scored benchmark result can be claimed.')
        sys.exit(1)
