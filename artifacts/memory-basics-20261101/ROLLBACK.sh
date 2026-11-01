#!/bin/sh
# This topic consists only of added files. Restore the pristine empty topic copy.
set -eu
[ "$#" -eq 1 ] || { echo "usage: ROLLBACK.sh TARGET_COPY" >&2; exit 2; }
python - "$1" <<'PY'
from pathlib import Path
import hashlib,json,sys
root=Path(sys.argv[1]).resolve(strict=True)
if not root.is_dir(): raise SystemExit('target must be a directory')
hashes=json.loads(r'''{"01-memory-map.md": "d3fac1231db5edbcc7aae1820a0738a6b34b8dd8811b31791b1dc1f09fdde42c", "02-types-and-copy.md": "24e5260bd47c273bf378f358186c7898caac24a1055148ea22462c30d3442efb", "03-managed-and-unmanaged.md": "4c2414ce103596570fdd5a1eda158f2ee9f4c8e4219fe851b0a296025cbd5c2d", "04-gc-and-allocation.md": "dfc0bafbe01b1873dc27c4ad911729d8bd1cb198422d3c0730b084e13c93c191", "05-containers-and-layout.md": "c9335393c202a8b9f706f60b8c80c28de599d5022f17b15d4e35129c7403aeda", "06-ownership-and-disposal.md": "e1cea9e1f0600a90e952347d222a282fafce8cb68afe4c08dfea29b88ac16d08", "07-native-and-allocator.md": "9d2e3ba2553b537a9e4ad447114c60bb2351cd3dbf8ea527f1df1014d62beeaf", "08-jobs-and-safety.md": "90fdce23f7f46afb2ff81ff29c3c6349c5dc2df9ee38e274fa54bb2bf548544d", "09-density-lab.md": "efbf6851ce97654089aae60aba3cad58569f2d654c6e8e80cecb177f861afa9d", "目录.md": "1c76ef934d741d52a0b1bf72c21f4010901f3327409ba7c2bc4d7322e391fb3f"}''')
# Validate every expected file before changing anything; preserve unrelated content.
for name,digest in hashes.items():
    p=root/name
    if p.is_symlink() or not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=digest:
        raise SystemExit('target differs from the delivered copy: '+name)
for name in hashes: (root/name).unlink()
print('restored pristine baseline: added topic pages removed')
PY
