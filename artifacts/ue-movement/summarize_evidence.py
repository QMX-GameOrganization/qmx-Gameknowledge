"""生成适合随文章阅读的蓝图证据摘要，不输出机器指针或完整资源数据。"""
from pathlib import Path
import json,re,hashlib
root=Path('artifacts/ue-movement')
d=json.loads((root/'blueprints.json').read_text(encoding='utf-8'))
summary={'engine':d['engine'],'method':'UE Python Commandlet; read-only queries; no asset save','assets':[]}
selected={'ProduceInput','CacheInputsFromMover','UpdateMovement_PreCMC','Get_PropertiesForAnimation','Update_Trajectory','Update_MotionMatching','SetWarpTargets','Evaluate'}
for a in d['assets']:
 entry={'path':a['path'],'parent':a['parent'],'sha256':a['sha256_after'],'original_bytes_unchanged':a['original_bytes_unchanged'],'graphs':[]}
 for g in a['graphs']:
  if g['name'] in selected:
   entry['graphs'].append({'name':g['name'],'nodes':[{'id':n['name'],'title':n.get('title',n['class']),**({'delegate_function':n['delegate_function']} if n.get('delegate_function') else {})} for n in g['nodes'] if 'title' in n]})
  if 'MovementTransition_' in a['path'] and g['name']=='Evaluate':
   entry['graphs'][-1]['nodes']=g['nodes']
  if a['path'].endswith('AC_TraversalLogic') and g['name']=='EventGraph':
   entry['montage_execution_edges']=[n for n in g['nodes'] if n['name'] in ['K2Node_CustomEvent_3','K2Node_CustomEvent_4']]
 entry['components']=[{'name':c['name'],'class':c['class'],'properties':{k:re.sub(r' \(0x[0-9A-Fa-f]+\)','',v) for k,v in c['properties'].items()},**({'mode_details':c['mode_details']} if 'mode_details' in c else {})} for c in a.get('components',[])]
 summary['assets'].append(entry)
Path('public/assets/ue-movement/blueprint-evidence.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
files=['Engine/Source/Runtime/Engine/Private/Components/CharacterMovementComponent.cpp','Engine/Source/Runtime/Engine/Classes/GameFramework/CharacterMovementComponent.h','Engine/Plugins/Experimental/Mover/Source/Mover/Private/MoverComponent.cpp','Engine/Plugins/Experimental/Mover/Source/Mover/Private/KinematicActorSimulation.cpp','Engine/Plugins/Experimental/Mover/Source/Mover/Private/MovementModeStateMachine.cpp','Engine/Plugins/Experimental/Mover/Source/Mover/Private/DefaultMovementSet/Modes/WalkingMode.cpp','Engine/Plugins/Experimental/Mover/Source/Mover/Private/DefaultMovementSet/Modes/SmoothWalkingMode.cpp','Engine/Plugins/Experimental/Mover/Source/Mover/Private/DefaultMovementSet/CharacterMoverComponent.cpp','Engine/Plugins/Experimental/Mover/Source/Mover/Private/Backends/MoverNetworkPredictionLiaison.cpp','Engine/Plugins/Experimental/Mover/Source/Mover/Public/MovementMode.h']
manifest=[]
for f in files:
 p=Path('D:/UE/UE_5.8')/f
 manifest.append({'path':str(p.resolve()),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(root/'source-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
lines=[]
for a in d['assets']:
 lines.append(a['path']+' | '+a['parent']+' | '+str(sum(len(g['nodes']) for g in a['graphs']))+' nodes')
 for g in a['graphs']:
  if g['name'] in selected: lines.append('  '+g['name']+': '+', '.join(n['title'].replace('\n',' / ') for n in g['nodes'] if 'title' in n))
(root/'blueprint-summary.txt').write_text('\n'.join(lines),encoding='utf-8')
assert all(a['original_bytes_unchanged'] and not a['errors'] and all(not g['errors'] for g in a['graphs']) for a in d['assets'])
print('Verified 12 read-only blueprint exports; generated evidence and source manifest')
