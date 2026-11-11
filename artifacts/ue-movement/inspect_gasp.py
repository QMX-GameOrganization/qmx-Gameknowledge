"""只读取 GASP 蓝图的父类、图、节点和引脚，输出研究记录，不保存资源。"""
import unreal, json, traceback, hashlib
from pathlib import Path
out = Path('D:/QMX-Studio/qmx-Gameknowledge/artifacts/ue-movement')
lib = unreal.BlueprintEditorLibrary
paths = ['SandboxCharacter_CMC','SandboxCharacter_Mover','SandboxCharacter_CMC_ABP','SandboxCharacter_Mover_ABP','AC_TraversalLogic','BPI_SandboxCharacter_ABP','BPI_SandboxCharacter_Pawn','MovementModes/BP_MovementMode_Walking','MovementModes/BP_MovementMode_Falling','MovementModes/BP_MovementMode_Slide','MovementModes/BP_MovementTransition_ToSlide','MovementModes/BP_MovementTransition_FromSlide']
result = {'engine':str(unreal.SystemLibrary.get_engine_version()), 'assets':[], 'errors':[]}
for name in paths:
    record = {'path':'/Game/Blueprints/'+name, 'graphs':[], 'errors':[]}
    original_file = Path('D:/UE/Project/游戏动画示例/Content/Blueprints') / (name+'.uasset')
    record['sha256_before'] = hashlib.sha256(original_file.read_bytes()).hexdigest()
    try:
        bp = unreal.load_asset(record['path'])
        record['class'] = bp.get_class().get_path_name()
        record['parent'] = lib.get_blueprint_parent_class(bp).get_path_name()
        for graph in lib.list_graphs(bp):
            g = {'name':graph.get_name(), 'nodes':[], 'errors':[]}
            try:
                nodes = [obj for obj in unreal.ObjectIterator(unreal.EdGraphNode) if obj.get_outer() == graph]
                for node in nodes:
                    n = {'name':node.get_name(), 'class':node.get_class().get_name()}
                    try:
                        n['title'] = lib.get_node_title(node)
                        if n['class'] == 'K2Node_CreateDelegate': n['delegate_function'] = str(lib.get_create_delegate_function(node))
                        n['pins'] = []
                        pl = unreal.BlueprintGraphPinLibrary
                        for pin in lib.list_all_pins(node):
                            n['pins'].append({'name':str(pl.get_pin_name(pin)), 'direction':str(pl.get_pin_direction(pin)), 'value':pl.get_pin_value(pin), 'links':[{'node':pl.get_owning_node(q).get_name(),'pin':str(pl.get_pin_name(q))} for q in pl.list_connected_pins(pin)]})
                    except Exception as e:
                        n['detail_error'] = str(e)
                        try: n['comment'] = str(node.get_editor_property('node_comment'))
                        except Exception: pass
                    g['nodes'].append(n)
            except Exception as e: g['errors'].append(str(e))
            record['graphs'].append(g)
        try:
            handles = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem).k2_gather_subobject_data_for_blueprint(bp)
            components=[]
            for h in handles:
                data = unreal.SubobjectDataBlueprintFunctionLibrary.get_data(h)
                obj = unreal.SubobjectDataBlueprintFunctionLibrary.get_associated_object(data)
                entry={'name':obj.get_name(),'class':obj.get_class().get_path_name(),'properties':{}}
                for key in ['backend_class','starting_movement_mode','movement_modes','anim_class','max_walk_speed','replicate_movement']:
                    try: entry['properties'][key]=str(obj.get_editor_property(key))
                    except Exception: pass
                if isinstance(obj, unreal.MoverComponent):
                    entry['mode_details'] = []
                    for mode_name, mode in obj.get_editor_property('movement_modes').items():
                        detail = {'name':str(mode_name),'class':mode.get_class().get_path_name(),'properties':{}}
                        for key in ['transitions','supports_async']:
                            try: detail['properties'][key] = str(mode.get_editor_property(key))
                            except Exception: pass
                        entry['mode_details'].append(detail)
                components.append(entry)
            record['components']=components
        except Exception as e: record['errors'].append('components: '+str(e))
    except Exception: record['errors'].append(traceback.format_exc())
    record['sha256_after'] = hashlib.sha256(original_file.read_bytes()).hexdigest()
    record['original_bytes_unchanged'] = record['sha256_before'] == record['sha256_after']
    result['assets'].append(record)
    (out/'blueprints.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
unreal.log('QMX_GASP_EXPORT_COMPLETE '+str(len(result['assets'])))
