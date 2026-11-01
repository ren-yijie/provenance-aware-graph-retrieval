import hashlib,json,re
from pathlib import Path
P=Path(__file__).resolve().parent
G=json.loads((P.parent/'provenance-aware-graph-retrieval/data/test_graph_slice.json').read_text())
sources={n['attributes']['metadata']['donor_id']:n for n in G['nodes'] if n['type']=='Source'}
facts=[]
def add(donor,predicate,obj,field,start=None,end=None,quote=None,status='explicit'):
 n=sources[donor]
 facts.append({'fact_id':'FACT_'+hashlib.sha256((donor+predicate+obj).encode()).hexdigest()[:20],
 'subject':donor,'predicate':predicate,'object':obj,'source_id':n['id'],'field':field,
 'start':start,'end':end,'quote':quote,'status':status})
for donor,n in sources.items():
 m=n['attributes']['metadata'];text=n['attributes']['content']
 for field,pred in [('name','has_name'),('giving_tier','has_giving_tier'),('relationship_manager','managed_by')]:
  add(donor,pred,m[field],'attributes.metadata.'+field,status='metadata_explicit')
 name=m['name'];start=text.find(name)
 if start>=0:add(donor,'has_name',name,'attributes.content',start,start+len(name),name)
# Curated relation examples for representation design, not an automatic extraction claim.
relations=[('D0124','board_member_of','Studio Museum in Harlem','He is also a board member of the Studio Museum in Harlem.'),
('D0425','trustee_of','Studio Museum in Harlem','He serves as a trustee of the Studio Museum in Harlem, a role he has held for four years.'),
('D0975','board_member_of','Studio Museum in Harlem','He is a board member of the Studio Museum in Harlem.'),
('D0091','advisory_board_member_of','Dia Art Foundation',"Rosemary sits on the museum's finance committee and serves on the advisory board of the Dia Art Foundation."),
('D0350','board_member_of','Dia Art Foundation','She is on the board of the Dia Art Foundation and chairs their development committee.'),
('D0488','board_member_of','Dia Art Foundation','James is a board member of the Dia Art Foundation and gives through the Osei-Bonsu Family Foundation, which he and his husband established five years ago.'),
('D0154','profile_mentions_foundation','Kessler Family Foundation','The Kessler Family Foundation supports the museum, the Whitney Museum Council, and Jazz at Lincoln Center.'),
('D0475','profile_mentions_foundation','The Drummond Foundation','The Drummond Foundation distributes approximately $600,000 annually, with arts and education as primary areas.'),
('D0488','gives_through','Osei-Bonsu Family Foundation','James is a board member of the Dia Art Foundation and gives through the Osei-Bonsu Family Foundation, which he and his husband established five years ago.'),
('D0476','cofounder_of','Nair Family Foundation','Vikram and his wife Ananya are co-founders of the Nair Family Foundation, which focuses on arts education and access, distributing around $250,000 per year.')]
for donor,pred,obj,quote in relations:
 text=sources[donor]['attributes']['content'];start=text.index(quote)
 add(donor,pred,obj,'attributes.content',start,start+len(quote),quote,status='human_curated_explicit')
for fact in facts:
 if fact['field']=='attributes.content':
  text=sources[fact['subject']]['attributes']['content']
  assert text[fact['start']:fact['end']]==fact['quote']
(P/'representation_facts.jsonl').write_text(''.join(json.dumps(f,ensure_ascii=False)+'\n' for f in facts))
print('Verified',len(facts),'facts; metadata and original character spans distinguished.')
