"""Prepare declared development checks before running any experimental variants."""
import json,hashlib
from pathlib import Path
P=Path(__file__).resolve().parent
G=json.loads((P.parent/'provenance-aware-graph-retrieval/data/test_graph_slice.json').read_text())
sources={n['attributes']['metadata']['donor_id']:n for n in G['nodes'] if n['type']=='Source'}
cases=[
('N01','name','Find every profile whose name begins with Kwame Asante.',['D0124','D0559'],'name prefix in metadata; verify profile first sentence'),
('N02','name','Find the profile named Elena Sorokina.',['D0481'],'exact metadata name; first sentence'),
('N03','name_collision','Find both profiles named Sophia Andreou.',['D0442','D0583'],'exact metadata name, separate donor IDs'),
('N04','name_collision','Find all profiles named Tariq Al-Rashid.',['D0215','D0566','D0905'],'exact metadata name, separate donor IDs'),
('N05','name_collision','Find both profiles named Vikram Nair.',['D0476','D0801'],'exact metadata name, separate donor IDs'),
('N06','name_collision','Find both profiles named Andre Beaumont.',['D0553','D0892'],'exact metadata name, separate donor IDs'),
('N07','negative_name','Find the profile named Zorina Vale.',[],'no matching name among all 50 metadata records'),
('N08','negative_conjunction','Which profile named Kwame Asante-Brown is a cardiologist?',[],'Asante-Brown is venture capitalist; cardiologist is Asante'),
('N09','affiliation','List the trustees and board members of the Studio Museum in Harlem.',['D0124','D0425','D0975'],'explicit board/trustee clauses; original Q006 labels'),
('N10','affiliation','List profiles serving on the Dia Art Foundation board or advisory board.',['D0091','D0350','D0488'],'explicit board clauses; original Q008 labels'),
('N11','metadata_conjunction','Find major-tier donors with named family foundations managed by James Reuter or Sarah Okafor.',['D0154','D0475','D0488'],'metadata tier+manager and foundation clauses; original Q017 labels'),
('N12','negative_conjunction','Which Studio Museum in Harlem board members or trustees are managed by James Reuter?',[],'all explicit Studio board/trustee profiles have other managers'),
('N13','alias_evidence','List the board members or trustees of the Public Art Fund.',['D0171','D0664','D0762'],'explicit board/trustee clauses; original Q007 labels'),
('N14','possessive_evidence','Which profile works in Lazard restructuring advisory and is linked to a Chinese American artistic identity exhibition?',['D0292'],'Lazard possessive and exhibition clauses'),
('N15','possessive_evidence','Which Greek-American donor works in Goldman Sachs private wealth management?',['D0455'],'Greek-American and Goldman private wealth clauses'),
('N16','negative_conjunction','Which donor leads JPMorgan technology-sector M&A and owns seven Cindy Sherman works?',[],'Sunita has four; Alexandra has seven and different employer'),
]
rows=[]
for qid,group,text,donors,rule in cases:
 rows.append(dict(query_id=qid,group=group,text=text,gold_source_ids=sorted(sources[d]['id'] for d in donors),gold_donor_ids=donors,label_basis=rule,source_evidence=[dict(source_id=sources[d]['id'],donor_id=d,content=sources[d]['attributes']['content'],metadata=sources[d]['attributes']['metadata']) for d in donors]))
(P/'validation_questions.json').write_text(json.dumps({'classification':'post-hoc mechanism development checks; NOT independent held-out test','same_corpus':True,'author_exposed_to_original_30_questions':True,'cases':rows},ensure_ascii=False,indent=2)+'\n')
print('Prepared',len(rows),'questions; SHA256',hashlib.sha256((P/'validation_questions.json').read_bytes()).hexdigest())
