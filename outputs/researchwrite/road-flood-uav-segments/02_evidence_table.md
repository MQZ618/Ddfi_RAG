# 02 Evidence Table — Claim → Evidence 映射

| # | Claim | Evidence | Status |
|---|---|---|---|
| 1 | 政策要求风险感知/应急联动/基础设施信息获取 | [1-3] 政策文件 | supported |
| 2 | 地面逐路核查受积水扩展、区域难进入、力量有限限制 | 常识性推理（原文论证） | inferred（合理前提） |
| 3 | 低空 UAV 适合重点片区快速获取高分辨率影像 | 传感器能力常识 | inferred |
| 4 | 语义分割独立类别不能直接说明道路片段受淹 | [4][5] 类别设计推理 | plausible-inference |
| 5 | DL 广泛用于洪涝制图；实时/泛化/不确定性是持续问题 | [6] 综述 | supported |
| 6 | 低空影像公开任务大多停留在场景分类或像素分割 | [4][5] | supported |
| 7 | 现有输出为像素/影像块/网格/预设标签，未研究分布相对道路结构 | [4][5][7][8] 对比 | plausible-inference（研究缺口） |
| 8 | FloodNet 道路标签并集不能恢复遮挡下道路 | [4] 标注机制 | supported |
| 9 | Road-Blocked 与 Road-flooded 不同义 | [5] vs [4] | supported |
| 10 | 道路段级表达可实施（Sakamoto） | [8] | supported |
| 11 | 未见研究"受淹面积相近时分布局部差异" | [7][8] 对比 | gap（本研究假设） |
| 12 | OBIA 为像素→对象提供基础；道路片段≠普通连通区域 | [9] | supported + inferred |
| 13 | 阴影/树冠下洪水难以从光学影像直接获得 | [10] | supported |
| 14 | 仅掩膜重叠不能认定车辆滞留/树木倒伏/阻断 | 原文推理 | plausible-inference |
| 15 | 相同受淹比例可来自沿路延伸/横向覆盖/边缘零散等不同分布 | 研究设想 | hypothesis（待验证） |
| 16 | 分布差异在不同道路结构下是否稳定需专门验证 | 研究设想 | hypothesis |
| 17 | FloodNet 适合验证像素→片段转化，不能单独支持"独立水体→道路受淹"一般结论 | [4] 标签结构 | supported（局限性） |
| 18 | 复杂场景"强制给结果 vs 转复核"比较可减少明显错误 | [11] 选择性分类思想 | hypothesis（[11] 需补引） |
| 19 | DeepFlood/BlessemFlood21 为后续候选数据 | [12][13] | supported（候选，非已有） |
| 20 | 遥感地理空间 Agent 多步规划/工具调用仍不足 | [14-16] | supported |
| 21 | 固定规则计算和一次性报告生成不需要 Agent 包装 | 原文定位声明 | scope statement |
