"""准备单文件回滚工件与隔离站点，保留当前知识库结果。"""
from pathlib import Path
import base64,shutil,os
root=Path.cwd(); out=root/'artifacts/ue-movement'
base=(out/'HomeOverview.baseline.astro').read_bytes()
(out/'MODIFIED_FILE.astro').write_bytes((root/'src/components/HomeOverview.astro').read_bytes())
(out/'ROLLBACK.sh').write_text('#!/bin/sh\n# 将传入的目标副本恢复为修改前的首页组件；不处理其他文件。\nset -eu\n[ "$#" -eq 1 ] || { echo "Usage: ROLLBACK.sh TARGET_COPY" >&2; exit 2; }\nprintf %s '+"'"+base64.b64encode(base).decode()+"'"+' | base64 -d > "$1"\n',encoding='utf-8',newline='\n')
(out/'restored-copy.astro').write_bytes((out/'MODIFIED_FILE.astro').read_bytes())
rollback=root/'work/ue-rollback-verification'
rollback.mkdir(parents=True,exist_ok=True)
if not (rollback/'src').exists():shutil.copytree(root/'src',rollback/'src',ignore=shutil.ignore_patterns('UE专栏'))
for f in ['package.json','package-lock.json','astro.config.mjs','tsconfig.json']:
 shutil.copy2(root/f,rollback/f)
shutil.copy2(out/'MODIFIED_FILE.astro',rollback/'src/components/HomeOverview.astro')
print(rollback)
