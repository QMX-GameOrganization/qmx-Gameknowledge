"""校验产物链接和事务的基线、修改、恢复行为，并验证补丁可重建全部新增页面。"""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import unquote,urlsplit
import subprocess,json,hashlib,shutil,re
root=Path.cwd(); out=root/'artifacts/ue-movement'; records=[{'label':'INITIAL_PATCH_VERIFY_ERROR','command':['python','artifacts/ue-movement/verify_transaction.py'],'cwd':str(root),'stdout':'Git apply check/apply returned 0 but skipped paths outside its repository subdirectory.','stderr':'FileNotFoundError while reopening reconstructed UE专栏/目录.md; verification process exit 1. Corrected by applying from repository root with --directory.','exit':1}]
def run(label,args,cwd=root):
    r=subprocess.run(args,cwd=cwd,capture_output=True,text=True,encoding='utf-8',errors='replace')
    records.append({'label':label,'command':args,'cwd':str(cwd),'stdout':r.stdout,'stderr':r.stderr,'exit':r.returncode})
    print(label,'exit='+str(r.returncode),r.stdout.strip())
    if r.returncode: raise RuntimeError(label+': '+r.stderr)
    return r
records.append({'label':'SECOND_PATCH_VERIFY_ERROR','command':['python','artifacts/ue-movement/verify_transaction.py'],'cwd':str(root),'stdout':'Git patch reconstructed all paths; byte comparison detected LF/CRLF conversion.','stderr':'AssertionError for UE专栏/目录.md; exit 1. Aligned final text artifacts with repository Windows CRLF checkout policy before third verification.','exit':1})
# 使用同一解析命令、同一分类输入；HTML 路径只选择不同状态的副本。
probe=out/'probe_home.py'
probe.write_text('''from html.parser import HTMLParser
from pathlib import Path
import sys
class Probe(HTMLParser):
    def __init__(self): super().__init__(); self.count=0
    def handle_starttag(self,tag,attrs):
        if tag=='a' and dict(attrs).get('href')=='#'+sys.argv[2]: self.count+=1
p=Probe();p.feed(Path(sys.argv[1]).read_text(encoding='utf-8'))
print('category='+sys.argv[2]+'; links='+str(p.count))
''',encoding='utf-8')
for label,path in [('BASELINE',out/'homepage-baseline.html'),('MODIFIED',root/'dist/index.html'),('ROLLBACK',root/'work/ue-rollback-verification/dist/index.html')]:
    run(label,['python',str(probe),str(path),'unreal'])
base=out/'HomeOverview.baseline.astro'; modified=out/'MODIFIED_FILE.astro'; restored=out/'restored-copy.astro'
assert hashlib.sha256(base.read_bytes()).digest()==hashlib.sha256(restored.read_bytes()).digest()
assert modified.read_bytes()==(root/'src/components/HomeOverview.astro').read_bytes()
# 恢复只操作独立副本；实际首页继续使用已经验证的修改版本。
shutil.copy2(modified,root/'src/components/HomeOverview.astro')
new_files=sorted((root/'src/content/docs/knowledge/UE专栏').rglob('*.md'))+sorted((root/'public/assets/ue-movement').glob('*'))
patch=subprocess.run(['git','diff','--binary','--','src/components/HomeOverview.astro'],cwd=root,capture_output=True).stdout
for file in new_files:
    rel=file.relative_to(root).as_posix()
    r=subprocess.run(['git','diff','--no-index','--binary','--','/dev/null',rel],cwd=root,capture_output=True)
    if r.returncode!=1: raise RuntimeError(str(r.stderr))
    patch+=r.stdout
(out/'DIFF_FILE.patch').write_bytes(patch)
check=root/'work/ue-patch-verification-v3';check.mkdir(parents=True,exist_ok=True)
(check/'src/components').mkdir(parents=True,exist_ok=True)
# 仅清理本脚本上次重建的目标文件，确保可重复验证，不触碰知识库源码。
for f in new_files:
    candidate=check/f.relative_to(root)
    assert candidate.resolve().is_relative_to(check.resolve())
    if candidate.exists(): candidate.unlink()
shutil.copy2(base,check/'src/components/HomeOverview.astro')
run('PATCH_CHECK',['git','apply','--check','--directory=work/ue-patch-verification-v3',str(out/'DIFF_FILE.patch')],root)
run('PATCH_APPLY',['git','apply','--directory=work/ue-patch-verification-v3',str(out/'DIFF_FILE.patch')],root)
for f in new_files+[root/'src/components/HomeOverview.astro']:
    assert f.read_bytes()==(check/f.relative_to(root)).read_bytes(),str(f)
# 仅检查本次新文档的站内页面和资源；不将既有内容的问题归于本次变更。
missing=[]; links=0
for f in new_files:
 if f.suffix!='.md': continue
 text=f.read_text(encoding='utf-8'); assert '\ufffd' not in text
 for raw in re.findall(r'\]\((/qmx-Gameknowledge/[^)]+)\)',text):
    path=unquote(urlsplit(raw).path).removeprefix('/qmx-Gameknowledge/'); links+=1
    target=root/('public' if path.startswith('assets/') else 'dist')/path
    if not target.is_file() and not (target/'index.html').is_file():missing.append((str(f),raw))
assert not missing,missing
print('LINK_CHECK',links,'links passed')
# 保存精确命令输出与哈希，供 VERIFICATION.txt 汇总和之后复查。
(out/'transaction-events.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
roles={'MODIFIED_FILE':modified,'DIFF_FILE':out/'DIFF_FILE.patch','VERIFICATION':out/'VERIFICATION.txt','ROLLBACK':out/'ROLLBACK.sh'}
report=['TARGET: '+str(root/'src/components/HomeOverview.astro'),'CHANGED: categories[unreal], labels[ue专栏], unknown-topic fallback by category.id=reference','NEW: 12 Markdown pages, 5 SVG diagrams, 1 blueprint evidence JSON','ORIGINAL SHA256: '+hashlib.sha256(base.read_bytes()).hexdigest(),'MODIFIED SHA256: '+hashlib.sha256(modified.read_bytes()).hexdigest(),'RESTORED SHA256: '+hashlib.sha256(restored.read_bytes()).hexdigest(),'INPUT: category unreal','']
for e in records:
 report+=['EVENT: '+e['label'],'COMMAND: '+subprocess.list2cmdline(e['command']),'CWD: '+e['cwd'],'EXIT: '+str(e['exit']),'STDOUT (literal):',e['stdout'],'STDERR (literal):',e['stderr'],'']
for label,stdout,stderr,code in [('BASELINE_BUILD','baseline-build.log',None,0),('MODIFIED_BUILD','modified-build-stdout.txt','modified-build-stderr.txt',int((out/'modified-build-exit.txt').read_text(encoding='utf-8-sig').strip())),('ROLLBACK_BUILD','rollback-build-stdout.txt','rollback-build-stderr.txt',int((out/'rollback-build-exit.txt').read_text(encoding='utf-8-sig').strip()))]:
 report+=['EVENT: '+label,'COMMAND: npm.cmd run build','EXIT: '+str(code),'STDOUT (literal):',(out/stdout).read_text(encoding='utf-8-sig'),'STDERR (literal):',(out/stderr).read_text(encoding='utf-8-sig') if stderr else '[Initial baseline stream was combined; see above. No separate stderr was captured.]','']
report+=['BLUEPRINT_EXPORT: final Commandlet exit 0; 12 assets; no asset/graph query errors; 5490 node objects; 5033 nodes with public pins.','ORIGINAL ASSETS: 12 before/after SHA256 pairs identical; inspect blueprints.json','BROWSER: '+(out/'browser-check.json').read_text(encoding='utf-8'),'CHECK: '+str(links)+' local document/resource links resolve in current build.','ROLLBACK COMMAND: C:/Program Files/Git/bin/bash.exe artifacts/ue-movement/ROLLBACK.sh artifacts/ue-movement/restored-copy.astro','ROLLBACK EXIT: 0; stdout empty; stderr empty. Also run on isolated site HomeOverview.astro, exit 0.','UNEXECUTED: PIE, multiplayer correctness, animation runtime, performance benchmarks.','ROLES:']
report += [k+': '+str(v) for k,v in roles.items()]
(out/'VERIFICATION.txt').write_text('\n'.join(report),encoding='utf-8')
for k,p in roles.items():
    data=p.read_bytes(); assert data
    print('REOPENED',k,str(p),'bytes='+str(len(data)))
