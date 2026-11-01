import copy,json,unittest
from dataclasses import asdict
from experiments import ROOT,name_overlay,possessive_span,fold_possessive,MultiAliasProvenance,PossessiveProvenance
from retrieval_benchmark.data import load_benchmark
from retrieval_benchmark.graph import ProvenanceGraphRetriever
from retrieval_benchmark.text import normalize_text

class MechanismTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=load_benchmark(ROOT)
    def test_possessive_span_original_coordinates(self):
        text="Role at Goldman Sachs's financial sponsors group yesterday."
        label='Goldman Sachs Financial Sponsors Group'
        span=possessive_span(label,text)
        self.assertEqual(normalize_text(text)[slice(*span)],"goldman sachs's financial sponsors group")
        self.assertEqual(fold_possessive(normalize_text(text)[slice(*span)]),fold_possessive(label))
    def test_curly_possessive(self):
        self.assertIsNotNone(possessive_span('Lazard restructuring advisory group',"Lazard’s restructuring advisory group"))
    def test_no_semantic_or_substring_broadening(self):
        self.assertIsNone(possessive_span('Law Firm Associate','associate at Sullivan & Cromwell'))
        self.assertIsNone(possessive_span('Lazard','Lazardous enterprise'))
        self.assertIsNone(possessive_span('Goldman Sachs Financial Sponsors Group',"Goldman Sachs's private wealth management division"))
    def test_overlay_deterministic_preserves_inputs(self):
        before=copy.deepcopy(self.data.graph)
        a=name_overlay(before);b=name_overlay(before)
        self.assertEqual(before,self.data.graph);self.assertEqual(a,b)
        self.assertEqual(name_overlay(a),a)
        self.assertEqual({n['id'] for n in a['nodes'] if n['type']=='Source'},set(self.data.sources))
    def test_alias_recovers_actual_q007_path_only(self):
        base=ProvenanceGraphRetriever(self.data.graph,self.data.retrieval_texts)
        alt=MultiAliasProvenance(self.data.graph,self.data.retrieval_texts)
        q=next(q for q in self.data.queries if q.query_id=='Q007')
        _,c=base.index.candidates(q.text)
        sid=next(sid for sid,s in self.data.sources.items() if s['attributes']['metadata']['donor_id']=='D0171')
        path=next(p for p in c[sid] if p['path_length']==1)
        self.assertEqual(base._path_evidence(q.text,sid,path),[])
        self.assertIn('public art programming budget',[e['text'] for e in alt._path_evidence(q.text,sid,path)])
        self.assertEqual(base.index.candidates(q.text),alt.index.candidates(q.text))
    def test_alias_does_not_invent_law_firm_phrase(self):
        alt=MultiAliasProvenance(self.data.graph,self.data.retrieval_texts)
        q=next(q for q in self.data.queries if q.query_id=='Q009')
        _,c=alt.index.candidates(q.text)
        sid=next(sid for sid,s in self.data.sources.items() if s['attributes']['metadata']['donor_id']=='D0067')
        self.assertTrue(all(not alt._path_evidence(q.text,sid,p) for p in c[sid]))
    def test_possessive_does_not_change_candidates(self):
        base=ProvenanceGraphRetriever(self.data.graph,self.data.retrieval_texts)
        alt=PossessiveProvenance(self.data.graph,self.data.retrieval_texts)
        for q in self.data.queries:self.assertEqual(base.index.candidates(q.text),alt.index.candidates(q.text))
    def test_validation_contract(self):
        from pathlib import Path
        cases=json.loads((Path(__file__).parent/'validation_questions.json').read_text())['cases']
        self.assertEqual(len({c['query_id'] for c in cases}),16)
        self.assertEqual(sum(not c['gold_source_ids'] for c in cases),4)
        for c in cases:
            self.assertLessEqual(len(c['gold_source_ids']),3)
            self.assertTrue(set(c['gold_source_ids'])<=set(self.data.sources))
            for s in c['source_evidence']:self.assertEqual(s['content'],self.data.retrieval_texts[s['source_id']])

if __name__=='__main__':unittest.main(verbosity=2)
