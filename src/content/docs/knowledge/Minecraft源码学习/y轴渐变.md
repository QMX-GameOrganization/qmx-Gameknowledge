---
title: 2.2密度函数扩展-y轴渐变
description: 之前的密度函数过于简化，进一步扩展
---
## 源码方案
DensityFunctions.yClampedGradient(
    -64, 320,
    1.5, -1.5
)
规定最高与最低做渐变

1.得到渐变函数
YBase = YGradient(Y)

2.Offset =Spline(Continents, Erosion, Ridges)样条函数做偏移
HalfNegative=d > 0 ? d : d * 0.5
TerrainBase =
    YBase
  + Offset
  + Jaggedness × HalfNegative(JaggedNoise)
3.
ScaledTerrain =
    Factor × TerrainBase
4. QuarterNegative=d > 0 ? d : d * 0.25
   >0放大<0缩小
SlopedCheese =
    4 × QuarterNegative(ScaledTerrain)

FinalDensity =
    SlopedCheese + Base3DNoise