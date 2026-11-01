from pathlib import Path
import hashlib,json,sys
sys.stdout.reconfigure(encoding="utf-8")
root=Path(sys.argv[1]); h=hashlib.sha256(); pages=sorted(root.glob("*.md"))
for p in pages:
    h.update(p.name.encode("utf-8")); h.update(b"\0"); h.update(p.read_bytes()); h.update(b"\0")
print(json.dumps({"topic_present":bool(pages),"pages":len(pages),"sha256":h.hexdigest()},ensure_ascii=False))
