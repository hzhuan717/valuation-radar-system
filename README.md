# 估值雷达（ValuationRadar · 终端仪表盘）

A 股自选池估值区间决策门户：单文件 HTML 终端仪表盘 + 每日自动更新流水线 + fail-closed 估值引擎。

> 仅用于研究、教学、回测和决策辅助。不得承诺收益、不连接券商、不执行交易。

## 开源协议

MIT License（见 [LICENSE](LICENSE)）：可自由使用、修改、商用，仅需保留版权声明。

## 在线访问

- 公开门户（每日 15:05 后自动刷新）：https://hzhuan717.github.io/valuation-radar-portal/

## 快速开始（本地运行）

```powershell
git clone https://github.com/hzhuan717/valuation-radar-system.git
cd valuation-radar-system
pip install -r requirements.txt      # 核心流水线仅需标准库；akshare/pandas 为回退通道
python scripts\update_daily.py --force   # 拉取行情与估值数据（交易日收盘后）
python scripts\build_dashboard.py        # 生成门户 HTML
start output\估值雷达门户.html            # 单文件离线可打开
```

想换自选池：编辑 `watchlist.json`（冻结参数：路由/模型/倍数/来源）后重跑上面三步即可。

## 目录结构

```
watchlist/
├── watchlist.json          # 自选池冻结参数（路由/模型/倍数/来源/板块，32 只）
├── state.json              # 每日计算结果（行情/K线/估值/质量门/信号）
├── VERSION                 # 项目版本号（每次发布递增并打标签）
├── snapshots/              # 每日快照留档（不入库）
├── output/                 # 生成的门户 HTML（单文件，离线可用）
└── scripts/
    ├── update_daily.py            # 每日流水线（交易日 15:05~15:35 自动运行）
    ├── valuation_engine_v2.py     # fail-closed 估值引擎（路由+质量门+计算账本）
    ├── data_fetch.py              # 行情/K线/一致预期/中证指数数据层
    ├── fetch_insurance_ev.py      # 保险 EV/NBV（东财F10）
    ├── fetch_normalized_eps.py    # 周期股正常化 EPS（同花顺摘要 10 年 ROE）
    ├── fetch_special_routes.py    # 银行 PB-ROE / 建筑现金流质量数据
    ├── calibrate_multiples.py     # 倍数历史分位校准（PE/PB，百度股市通 5 年）
    ├── fetch_pe_history.py        # PE/PB 历史分位补充器（含 ETF 底层指数）
    ├── build_dashboard.py         # 终端仪表盘生成器（K线为主、三栏环绕、单屏）
    ├── deploy_portal.py           # 门户推送到 GitHub Pages（永久公开网址）
    ├── publish_repo.py            # 本项目发布到 GitHub + 版本标签
    ├── verify_decision_data.py    # 离线/状态质量门回归测试
    └── scheduler_loop.py          # 每日更新看门狗
```

## 引擎路由（v2，fail-closed）

| 路由 | 状态 | 公式 |
|---|---|---|
| forward_pe / growth_pe | ✅ decision 级 | V = 前瞻EPS × 合理PE（同花顺一致预期 + 百度5年分位校准） |
| insurance_pev | ✅ 参考级 | V = 每股EV × 目标P/EV（东财F10 年报） |
| normalized_pe | ✅ 参考级 | 正常化EPS = 周期ROE分位 × 最新每股净资产（10 年报） |
| bank_pb_roe | ✅ 参考级 | V = 每股净资产 × 历史PB分位带；PB-ROE 理论值诊断 |
| infrastructure_cashflow | ✅ 参考级 | V = 每股净资产 × 历史PB分位带 + 现金流/应收/负债质量门 |
| etf_index | 🚫 分位信号 | ETF 用底层中证指数 PE 分位（官网限流时自动重试） |
| 亏损股 | 🚫 observe | 禁止 PE，仅 PB 分位信号 |

只有 `decision_usable=true` 才显示买卖阶梯与仓位动作；参考/拦截绝不补造数值。

## 研究板块分组（sector）

`watchlist.json` 每只标的可带 `sector` 字段，`meta.sectors` 定义板块顺序、重点标记与说明：

```json
{ "ticker": "603259", "name": "药明康德", "sector": "创新药", "valuation_model": { "code": "growth_pe", ... } }
```

- 当前 11 个分组，其中 **创新药**（荣昌生物 / 药明康德）与 **有色铜**
  （紫金矿业 / 洛阳钼业 / 江西铜业 / 铜陵有色）标记为 `focus` 重点跟踪。
- 左导航按板块分组 + 横向板块筛选条；大盘页「自选池板块」卡聚合等权涨跌幅、
  涨跌家数、平均 PE 历史分位、决策级成员估值带位置均值与状态分布。
- 板块是**人工维护的研究分组（D 级工程补充）**，只做横向对照：
  不改变任何单只的路由、质量门与 `decision_usable` 判定，也不生成板块级买卖动作。
- 加新标的：补 `sector` 字段即可；新板块直接写中文名，页面自动出现在筛选条与聚合卡。

## 常用命令

```powershell
# 每日刷新（交易日 15:05 后自动跑；手动补跑）
python scripts\update_daily.py --force

# 按指定交易日收盘计算（如"按昨天收盘算"）
python scripts\update_daily.py --force --as-of 2026-08-12

# 重建门户 HTML
python scripts\build_dashboard.py

# 发布门户到公开网址（update_daily 末尾自动执行）
python scripts\deploy_portal.py

# 质量门回归测试
python scripts\verify_decision_data.py --state state.json

# 发布本仓库新版本（补丁号 +1 / 次版本 / 主版本）
python scripts\publish_repo.py
python scripts\publish_repo.py --bump minor
```

## 版本与更新约定

- 每次用户要求更新门户/引擎/股票池 → 运行 `publish_repo.py` 提交一个新版本并打标签 `vX.Y.Z`。
- 公开网址（GitHub Pages）由每日流水线自动同步，无需手动操作。
- 数据来源：行情 腾讯/akshare（东财→新浪→腾讯回退）、一致预期 同花顺F10、EV/NBV 东方财富F10、PE/PB 分位 百度股市通、指数估值 中证指数官方。
