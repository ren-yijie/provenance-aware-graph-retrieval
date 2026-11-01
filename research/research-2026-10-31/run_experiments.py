import csv,hashlib,json,subprocess,sys
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path
sys.dont_write_bytecode=True
from experiments import ROOT,build_methods
from retrieval_benchmark.data import load_benchmark
from retrieval_benchmark.schema import Query
P=Path(__file__).resolve().parent

def tracked_hashes():
    paths=subprocess.check_output(['git','-C',str(ROOT),'ls-files'],text=True).splitlines()
    return {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}

before=tracked_hashes();data=load_benchmark(ROOT)
checks=json.loads((P/'validation_questions.json').read_text())
methods=build_methods(data.graph,data.retrieval_texts)
frozen={(r['query_id'],r['implementation_id']):r for r in map(json.loads,(ROOT/'results/v1.0.0/provenance_traces.jsonl').read_text().splitlines())}
# Manifest written before evaluation; no automatic experiment selection or tuning.
manifest={'classification':'post-hoc development experiment','frozen_repo_files':before,
          'inputs':{name:hashlib.sha256((P/name).read_bytes()).hexdigest() for name in ['experiments.py','run_experiments.py','experiment_protocol.md','validation_questions.json']},
          'repo_commit':subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),
          'variants':list(methods),'top_k':3,'original_dataset':'diagnostic, previously inspected','supplementary_dataset':'same-corpus development checks; NOT blind holdout'}
(P/'run_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
rows=[];traces=[];summary=[]
datasets={'original30':[(q,data.gold[q.query_id],data.answerable[q.query_id]) for q in data.queries],
          'checks16':[(Query(c['query_id'],c['text']),set(c['gold_source_ids']),bool(c['gold_source_ids'])) for c in checks['cases']]}
for split,questions in datasets.items():
    for variant,method in methods.items():
        totals=defaultdict(int)
        for q,gold,answerable in questions:
            r=method.retrieve(q);selected=[s.source_id for s in r.ranked_sources];pred=set(selected)
            seeds,candidates=method.index.candidates(q.text)
            if split=='original30' and variant in ('U0','P0'):
                old=frozen[q.query_id,method.implementation_id]
                assert [asdict(s) for s in r.ranked_sources]==old['ranked_sources']
                assert r.trace==old['result_trace']
            tp=len(pred&gold);fp=len(pred-gold);fn=len(gold-pred)
            row={'split':split,'variant':variant,'query_id':q.query_id,'answerable':answerable,'gold_ids':'|'.join(sorted(gold)),
                 'retrieved_ids':'|'.join(selected),'tp':tp,'fp':fp,'fn':fn,'abstained':r.abstained,
                 'seeds':len(seeds),'candidates':len(candidates),'candidate_gold':len(set(candidates)&gold),
                 'excluded_gold':len({e['source_id'] for e in r.trace.get('excluded_candidates',[])}&gold)}
            rows.append(row);traces.append({'split':split,'variant':variant,'question':q.text,**r.as_dict()})
            if answerable:
                for key in ('tp','fp','fn','candidate_gold','excluded_gold'):totals[key]+=row[key]
                totals['gold']+=len(gold);totals['answerable']+=1;totals['seeded_answerable']+=bool(seeds)
                totals['exact_answerable']+=pred==gold
            else:
                totals['negative']+=1;totals['correct_abstention']+=not pred;totals['negative_fp']+=len(pred)
        tp,fp,fn=(totals[k] for k in ('tp','fp','fn'))
        totals.update({'precision':tp/(tp+fp) if tp+fp else 0,'recall':tp/(tp+fn) if tp+fn else 0,'f1':2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0,
                       'candidate_recall':totals['candidate_gold']/totals['gold'] if totals['gold'] else 0})
        summary.append({'split':split,'variant':variant,**totals})
for filename,records in [('per_query_results.csv',rows),('summary.csv',summary)]:
    keys=list(dict.fromkeys(k for row in records for k in row))
    with (P/filename).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(records)
(P/'traces.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in traces))
# Every change recorded, including equal TP counts with changed identities.
base={(r['split'],r['variant'],r['query_id']):r for r in rows}
changes=[]
for row in rows:
    variant=row['variant']
    if variant in ('U0','P0'):continue
    parent=base[row['split'],'U0' if variant.startswith('U') else 'P0',row['query_id']]
    if row['retrieved_ids']!=parent['retrieved_ids']:
        changes.append({'split':row['split'],'variant':variant,'query_id':row['query_id'],'baseline_ids':parent['retrieved_ids'],'new_ids':row['retrieved_ids'],
                        'delta_tp':row['tp']-parent['tp'],'delta_fp':row['fp']-parent['fp'],'delta_fn':row['fn']-parent['fn']})
with (P/'changes.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(changes[0]));w.writeheader();w.writerows(changes)
assert tracked_hashes()==before,'Frozen repository was modified'
(P/'verification.json').write_text(json.dumps({'frozen_tracked_files_unchanged':len(before),'baseline_graph_rows_exactly_replayed':60,'experiment_rows':len(rows),
 'supplementary_positive_questions':sum(bool(c['gold_source_ids']) for c in checks['cases']),
 'supplementary_negative_questions':sum(not c['gold_source_ids'] for c in checks['cases'])},indent=2)+'\n')
print(json.dumps(summary,indent=2))
