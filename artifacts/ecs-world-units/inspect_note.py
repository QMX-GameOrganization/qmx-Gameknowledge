import hashlib
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = path.read_bytes()
text = data.decode('utf-8')
markers = ['tileSize: 32', 'toWorldSpaceCenterOfTile', 'getTileSpaceBounds',
           'getEffectiveLengthTiles', '阶段 0', '8a79de5255fb6756f3a1d26579b1e9bc36e0c811']
print(json.dumps({'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
                  'world_units_note_present': all(s in text for s in markers)}, ensure_ascii=True))
