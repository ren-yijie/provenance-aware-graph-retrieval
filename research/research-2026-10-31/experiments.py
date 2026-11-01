"""Local mechanism experiments. Retrieval code accepts no gold labels or query IDs as rules."""
import copy,hashlib,re,sys
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent.parent/'provenance-aware-graph-retrieval'
sys.path.insert(0,str(ROOT))
from retrieval_benchmark.graph import ProvenanceGraphRetriever,UnweightedGraphRetriever,_match_alias
from retrieval_benchmark.text import normalize_text,phrase_in_text

def name_overlay(graph):
    graph=copy.deepcopy(graph)
    names={normalize_text(n.get('name','')):n['id'] for n in graph['nodes'] if n['type']=='Discovered_entity'}
    existing={(e['source'],e['target'],e['type']) for e in graph['edges']}
    for node in list(graph['nodes']):
        if node['type']!='Source':continue
        name=node['attributes']['metadata']['name'];key=normalize_text(name)
        if key not in names:
            nid='EXP_NAME_'+hashlib.sha256(key.encode()).hexdigest()[:24]
            names[key]=nid
            graph['nodes'].append({'id':nid,'type':'Discovered_entity','name':name,'attributes':{'tags':[],'experimental_origin':'metadata.name'}})
        nid=names[key]
        if (node['id'],nid,'MENTIONS') in existing or (nid,node['id'],'MENTIONS') in existing:continue
        eid='EXP_EDGE_'+hashlib.sha256((node['id']+nid).encode()).hexdigest()[:24]
        graph['edges'].append({'id':eid,'source':node['id'],'target':nid,'type':'MENTIONS','attributes':{'experimental_origin':'metadata.name'}})
    return graph

def fold_possessive(text):
    return re.sub(r"['’]s\b",'',normalize_text(text))

def possessive_span(label,content):
    """Span in normalize_text(content), not in the shorter possessive-folded text."""
    original=normalize_text(content)
    removed=set()
    for m in re.finditer(r"['’]s\b",original):removed.update(range(*m.span()))
    positions=[i for i in range(len(original)) if i not in removed]
    folded=''.join(original[i] for i in positions)
    needle=fold_possessive(label)
    if not needle:return None
    match=re.search(r'(?<![^\W_])'+re.escape(needle)+r'(?![^\W_])',folded,re.UNICODE)
    if not match:return None
    return positions[match.start()],positions[match.end()-1]+1

class MultiAliasProvenance(ProvenanceGraphRetriever):
    def _path_evidence(self,query_text,source_id,path):
        evidence=super()._path_evidence(query_text,source_id,path)
        content=self.retrieval_texts[source_id]
        for alias in self.index.aliases(self.index.nodes[path['seed_id']]):
            if not _match_alias(alias,query_text):continue
            span=phrase_in_text(alias,content)
            if span is not None:evidence.append({'kind':'seed_alias','text':normalize_text(alias),'span':list(span),'node_id':path['seed_id']})
        unique={(e['kind'],e['text']):e for e in evidence}
        return [unique[k] for k in sorted(unique)]

class PossessiveProvenance(ProvenanceGraphRetriever):
    def _path_evidence(self,query_text,source_id,path):
        content=self.retrieval_texts[source_id];evidence=[]
        def add(kind,label,node_id=None):
            span=possessive_span(label,content)
            if span is not None:evidence.append({'kind':kind,'text':normalize_text(label),'span':list(span),'node_id':node_id})
        add('seed_alias',path['seed_label'],path['seed_id'])
        for nid in path['node_ids']:
            node=self.index.nodes[nid]
            if node['type']=='Discovered_entity' and _match_alias(node.get('name',''),query_text):add('named_entity',node['name'],nid)
        for edge in path['edges']:
            trigger=edge.get('attributes',{}).get('original_trigger')
            if isinstance(trigger,str) and _match_alias(trigger,query_text):add('original_trigger',trigger)
        unique={(e['kind'],e['text']):e for e in evidence}
        return [unique[k] for k in sorted(unique)]

def build_methods(graph,texts):
    augmented=name_overlay(graph)
    return {'U0':UnweightedGraphRetriever(graph),'P0':ProvenanceGraphRetriever(graph,texts),
            'U1_names':UnweightedGraphRetriever(augmented),'P1_names':ProvenanceGraphRetriever(augmented,texts),
            'P2_aliases':MultiAliasProvenance(graph,texts),'P3_possessive':PossessiveProvenance(graph,texts)}
