from html.parser import HTMLParser
from pathlib import Path
import sys
class Probe(HTMLParser):
    def __init__(self): super().__init__(); self.count=0
    def handle_starttag(self,tag,attrs):
        if tag=='a' and dict(attrs).get('href')=='#'+sys.argv[2]: self.count+=1
p=Probe();p.feed(Path(sys.argv[1]).read_text(encoding='utf-8'))
print('category='+sys.argv[2]+'; links='+str(p.count))
