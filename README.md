# Easy_DPD

## 声明：本仓库未发表于Gitcode，并拒绝CSDN平台使用

一个简易的 DPD（数字预失真）仿真仓库，按语言分为两个独立版本：

```
Easy_DPD/
├── matlab/                  # MATLAB 版（原版）
│   ├── main_detail.m        #   主流程（main.m 为旧版，已被取代）
│   ├── DPD_Func.m / MP_model.m / NMSE.m / distortion.m
│   ├── saleh.m / mat_delay.m / plt_fft.m
│   └── powamp_dpd.slx       #   Simulink 模型
└── python/                  # Python 版（重写，numpy/scipy 加速）
    ├── main_detail.py       #   主流程（对应 main_detail.m）
    ├── gui.py               #   交互式仿真面板（tkinter）
    ├── easydpd/             #   核心算法包
    ├── tests/               #   单元测试（37 项）
    ├── docs/                #   算法审查报告
    └── requirements.txt
```

- MATLAB 版请直接看 `matlab/main_detail.m`。
- Python 版请直接看 `python/main_detail.py`，算法审查结论见 `python/docs/algorithm_review.md`。

## Python 版

### 环境依赖

```bash
cd python
pip install -r requirements.txt     # numpy / scipy / matplotlib
pip install pytest                  # 运行测试（可选）
```

### 运行

```bash
cd python
python main_detail.py               # 端到端仿真：8 张图保存到 results/ 并弹窗显示，NMSE 打印到终端
python gui.py                       # 交互式仿真面板：实时调节参数，观察频谱/AM-AM/AM-PM 与指标变化
python -m pytest tests/ -q          # 单元测试（含与 MATLAB 数学等价性验证）
```

- `main_detail.py` 默认交互模式：图表保存为 PNG **并** 弹出窗口显示（关闭全部窗口后脚本结束）。
- 无头环境（服务器/CI，无桌面）只保存不弹窗：
  `EASY_DPD_HEADLESS=1 python main_detail.py`
- 若所在会话无桌面且未设该变量，脚本会自动回退为仅保存 PNG 并给出提示。

### 交互式 GUI（gui.py）

`python gui.py` 打开仿真面板，左侧参数实时调节、右侧图表自动刷新：

- **仿真参数**：训练/泛化频点（滑块）、阶数 K、记忆深度 M、样本数 N、
  以及两个算法开关——"只保留奇次项"（窄带 DPD 标准做法）与"拟合前时延对齐"
- **图表**：DPD 前后频谱对比、AM/AM、AM/PM、泛化频谱
- **指标**：NMSE（本底/拟合/补偿/泛化）与 ACPR（邻道功率比，dBc）实时显示
- 参数变化后约 0.4 s 自动重算，也可点 [运行] 立即重算；[恢复默认] 复位参数

### 目录结构（python/）

```
easydpd/
  core.py          # 核心算法：saleh / distortion / mat_delay / shift / estimate_delay /
                   #           align_y_to_x / mp_model / dpd_func / nmse / plt_fft / acpr
  simulation.py    # run_simulation：端到端仿真封装（脚本与 GUI 共用）
main_detail.py     # 主流程（对应 main_detail.m）
gui.py             # 交互式仿真面板（tkinter + matplotlib 嵌入）
tests/test_core.py # 数值正确性测试
tests/test_gui.py  # GUI 冒烟测试（无桌面时自动跳过）
docs/algorithm_review.md  # 算法审查报告
```

### 与 MATLAB 版的关系

| MATLAB（matlab/） | Python（python/） | 说明 |
|---|---|---|
| `saleh.m` | `easydpd.saleh` | Saleh 无记忆失真 |
| `distortion.m` | `easydpd.distortion` | FIR 记忆效应 + Saleh |
| `mat_delay.m` | `easydpd.mat_delay` | 因果前向延迟 |
| `MP_model.m` | `easydpd.mp_model` | 记忆多项式基函数（递推构造加速，支持奇次项开关） |
| `DPD_Func.m` | `easydpd.dpd_func` | 逆模型拟合（`lstsq` 替代正规方程，数学等价） |
| `NMSE.m` | `easydpd.nmse` | 归一化均方误差 |
| `plt_fft.m` | `easydpd.plt_fft` | 加窗 FFT 单边谱（返回数据，绘图由调用方完成） |
| `main_detail.m` | `main_detail.py` | 主流程脚本 |
| — | `easydpd.acpr` | ACPR 邻道功率比（Python 版新增） |
| — | `easydpd.run_simulation` | 端到端仿真封装（Python 版新增） |
| — | `gui.py` | 交互式仿真面板（Python 版新增） |
