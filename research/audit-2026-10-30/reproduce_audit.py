"""Read-only post-hoc audit. Run with Python 3; no model download or benchmark writes."""
import csv
import hashlib
import json
import subprocess
import sys
from collections import Counter
from dataclasses import asdict
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parent / 'provenance-aware-graph-retrieval'
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
from retrieval_benchmark.data import load_benchmark
from retrieval_benchmark.graph import UnweightedGraphRetriever, ProvenanceGraphRetriever, _match_alias
from retrieval_benchmark.text import lexical_tokens, phrase_in_text

def hashes():
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for prefix in ('data', 'results/v1.0.0', 'retrieval_benchmark')
            for p in sorted((ROOT / prefix).rglob('*')) if p.is_file() and '__pycache__' not in str(p)}

before = hashes()
d = load_benchmark(ROOT)
ug = UnweightedGraphRetriever(d.graph)
pg = ProvenanceGraphRetriever(d.graph, d.retrieval_texts)
traces = [json.loads(s) for s in (ROOT / 'results/v1.0.0/provenance_traces.jsonl').read_text().splitlines()]
frozen = {(r['query_id'], r['implementation_id']): r for r in traces}
results = {}
for q in d.queries:
    for method in (ug, pg):
        r = method.retrieve(q)
        old = frozen[q.query_id, method.implementation_id]
        assert [asdict(s) for s in r.ranked_sources] == old['ranked_sources'], (q.query_id, method.implementation_id)
        assert r.trace == old['result_trace'], (q.query_id, method.implementation_id, 'trace')
        results[q.query_id, method.implementation_id] = r

def identity(sid):
    m = d.sources[sid]['attributes']['metadata']
    return {'source_id': sid, 'donor_id': m['donor_id'], 'name': m['name']}

def outcomes(qid):
    rows = {}
    for method in ('bm25_v1','minilm_vector_v1','unweighted_graph_v1','provenance_graph_v1'):
        ids = [x['source_id'] for x in frozen[qid,method]['ranked_sources']]
        gold = d.gold[qid]
        rows[method] = {'ranked_source_ids': ids, 'tp': len(set(ids)&gold), 'fp': len(set(ids)-gold), 'fn':len(gold-set(ids))}
    return rows

zero = []
excluded = []
all_gold_paths = []
for q in d.queries:
    seeds, candidates = ug.index.candidates(q.text)
    gold = d.gold[q.query_id]
    if d.answerable[q.query_id] and not seeds:
        overlaps = []
        for nid,n in ug.index.nodes.items():
            if n['type'] not in ('Concept','Discovered_entity'): continue
            for alias in ug.index.aliases(n):
                shared = sorted(set(lexical_tokens(alias))&set(lexical_tokens(q.text)))
                if shared: overlaps.append({'node_id':nid,'node_name':n['name'],'alias':alias,'shared_tokens':shared,'alias_tokens':lexical_tokens(alias)})
        gold_info = []
        for sid in sorted(gold):
            neighbors = [{'node_id':nid, 'node_type':ug.index.nodes[nid]['type'], 'name':ug.index.nodes[nid].get('name'), 'edge_id':eid} for nid,eid in ug.index.adjacency[sid]]
            gold_info.append({**identity(sid),'content':d.retrieval_texts[sid], 'metadata':d.sources[sid]['attributes']['metadata'],'neighbors':neighbors})
        zero.append({'query_id':q.query_id,'question':q.text,'query_tokens':lexical_tokens(q.text),'seed_count':0,'candidate_count':len(candidates),'alias_overlaps':overlaps,'gold':gold_info,'outcomes':outcomes(q.query_id)})
    res = results[q.query_id,pg.implementation_id]
    gold_ex = [e for e in res.trace['excluded_candidates'] if e['source_id'] in gold]
    if gold_ex:
        items = []
        for ex in gold_ex:
            sid = ex['source_id']; paths = []
            for path in candidates[sid]:
                alternatives = [{'alias':a,'matches_query':_match_alias(a,q.text),'in_source':phrase_in_text(a,d.retrieval_texts[sid])} for a in ug.index.aliases(ug.index.nodes[path['seed_id']])]
                detail = {**path,'evidence':pg._path_evidence(q.text,sid,path),'collision':pg._collision_supported(q.text,sid,path),'all_seed_alias_checks':alternatives}
                paths.append(detail)
                all_gold_paths.append({'query_id':q.query_id,'source_id':sid,'seed_label':path['seed_label'],'match_kind':path['seed_match_kind'],'edge_ids':path['edge_ids'],'evidence_count':len(detail['evidence'])})
            items.append({**identity(sid),'exclusion':ex,'content':d.retrieval_texts[sid],'paths':paths,
                          'unweighted_top3':sid in outcomes(q.query_id)['unweighted_graph_v1']['ranked_source_ids']})
        excluded.append({'query_id':q.query_id,'question':q.text,'seeds':[asdict(s) for s in seeds], 'candidate_count':len(candidates),'eligible_count':res.trace['eligible_count'],'excluded_gold':items,'gold':sorted(gold),'outcomes':outcomes(q.query_id)})

# Partition all graph misses by the first failed stage, preserving the original Gold.
stages = Counter(); partition=[]
for q in d.queries:
    if not d.answerable[q.query_id]:continue
    seeds,candidates = ug.index.candidates(q.text)
    ex={e['source_id']:e['reason'] for e in results[q.query_id,pg.implementation_id].trace['excluded_candidates']}
    for method in (ug,pg):
        selected={r.source_id for r in results[q.query_id,method.implementation_id].ranked_sources}
        for sid in sorted(d.gold[q.query_id]-selected):
            stage = 'zero_seed' if not seeds else 'not_reachable_within_2_hops' if sid not in candidates else 'provenance_excluded' if method is pg and sid in ex else 'rank_below_top3'
            stages[method.implementation_id,stage]+=1
            partition.append({'query_id':q.query_id,'implementation_id':method.implementation_id,'source_id':sid,'first_failed_stage':stage})

assert len(zero)==8 and sum(len(x['gold']) for x in zero)==21
assert len(excluded)==6 and sum(len(x['excluded_gold']) for x in excluded)==7
assert hashes()==before
tag=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','v1.0.0^{}'],text=True).strip()
head=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
# Tag used an older results directory name; compare identical artifact basenames.
tag_paths=subprocess.check_output(['git','-C',str(ROOT),'ls-tree','-r','--name-only',tag],text=True).splitlines()
tag_verified=[]
for path in before:
    if path.startswith('data/') or path.startswith('retrieval_benchmark/') or path.startswith('results/'):
        candidates=[p for p in tag_paths if p==path or (path.startswith('results/') and p.startswith('results/') and Path(p).name==Path(path).name)]
        assert len(candidates)==1,(path,candidates)
        raw=subprocess.check_output(['git','-C',str(ROOT),'show',f'{tag}:{candidates[0]}'])
        assert hashlib.sha256(raw).hexdigest()==before[path],path
        tag_verified.append(path)
evidence={'audit_date':'2026-10-30','head':head,'release_tag_commit':tag,'replayed_graph_rows':60,'frozen_graph_traces_exact_match':True,'tag_verified_files':tag_verified,'input_sha256':before,'zero_seed':zero,'provenance_exclusions':excluded,'fn_partition':partition}
(OUT/'audit_evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
audit_rows=[]
for q in d.queries:
    for method, row in outcomes(q.query_id).items():
        ids=row['ranked_source_ids']; gold=d.gold[q.query_id]
        audit_rows.append({'query_id':q.query_id,'question':q.text,'answerable':d.answerable[q.query_id],
            'implementation_id':method,'gold_source_ids':'|'.join(sorted(gold)),
            'ranked_source_ids':'|'.join(ids),'tp':row['tp'],'fp':row['fp'],'fn':row['fn'],
            'false_positive_ids':'|'.join(sorted(set(ids)-gold)), 'missed_gold_ids':'|'.join(sorted(gold-set(ids)))})
with (OUT/'all_120_method_audit.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=list(audit_rows[0]));w.writeheader();w.writerows(audit_rows)
with (ROOT/'results/v1.0.0/per_query_results.csv').open(newline='',encoding='utf-8-sig') as f:
    original_rows={(r['query_id'],r['implementation_id']):r for r in csv.DictReader(f)}
assert len(original_rows)==len(audit_rows)==120
for row in audit_rows:
    original=original_rows[row['query_id'],row['implementation_id']]
    ids=row['ranked_source_ids'].split('|') if row['ranked_source_ids'] else []
    assert ids==json.loads(original['retrieved_source_ids'])
    assert set(row['gold_source_ids'].split('|') if row['gold_source_ids'] else [])==set(json.loads(original['gold_source_ids']))
    assert all(row[k]==int(original[k]) for k in ('tp','fp','fn'))
with (OUT/'fn_stage_partition.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(partition[0]));w.writeheader();w.writerows(partition)
print(json.dumps({'zero_seed':[{ 'id':x['query_id'],'gold_count':len(x['gold']),'overlaps':[(a['alias'],a['shared_tokens']) for a in x['alias_overlaps']]} for x in zero], 'excluded':[{'id':x['query_id'],'gold':[(e['donor_id'],e['exclusion']['reason'],e['unweighted_top3']) for e in x['excluded_gold']]} for x in excluded], 'stages':{str(k):v for k,v in stages.items()},'tag_verified_files':len(tag_verified)},ensure_ascii=False,indent=2))
