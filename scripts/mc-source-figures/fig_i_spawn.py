import sys
sys.path.insert(0, '.')
from fig_d_tree import render
nodes = [
    ('t', '每个 tick：ServerChunkCache.tickChunks', 'math'),
    ('s', '① createState：遍历一次所有实体，统计各类别数量\\n（之后所有区块共用，spawn 后增量更新）', 'cache'),
    ('c', '② 取所有“可 tick 的区块”并随机打乱', 'math'),
    ('f', '③ 区块过滤：允许自然刷新 且 128 格内有玩家', 'switch'),
    ('k', '④ 对每个 MobCategory：开关 + 频率\\n敌对/友好开关；被动生物仅 gameTime % 400 == 0', 'switch'),
    ('cap', '⑤ 上限：已有数量 < max × 可刷新区块数 / 289\\n且该玩家附近的本地上限未满', 'switch'),
    ('p', '⑥ 在区块内随机取一个点（x,z 随机；y 在最低层~地表之间随机）', 'math'),
    ('g', '⑦ 最多 3 组随机游走：每组先随机 1~4 步，\\n抽到种类后改为该种类的群体数量；每步偏移 ±5 格', 'math'),
    ('v', '⑧ 位置检查：距玩家 > 24 格；距世界出生点 > 24 格；\\n起点不是红石导体', 'switch'),
    ('w', '⑨ 按群系的 spawners 权重抽一种生物', 'noise'),
    ('r', '⑩ 放置类型（地面/水/岩浆）+ 刷新谓词\\n（光照、脚下方块、难度）+ 碰撞箱无阻挡', 'switch'),
    ('o', '⑪ 实例化实体并加入世界；afterSpawn 更新计数', 'ref'),
]
edges = [('t', 's'), ('s', 'c'), ('c', 'f'), ('f', 'k'), ('k', 'cap'), ('cap', 'p'), ('p', 'g'), ('g', 'v'), ('v', 'w'), ('w', 'r'), ('r', 'o')]
render('23-natural-spawn-funnel', nodes, edges)
