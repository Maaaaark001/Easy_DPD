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
├── python/                  # Python 版（numpy/scipy 加速）
│   ├── main_detail.py       #   主流程（对应 main_detail.m）
│   ├── gui.py               #   交互式仿真面板（tkinter）
│   ├── easydpd/             #   核心算法包
│   ├── tests/               #   单元测试（37 项）
│   ├── docs/                #   算法审查报告
│   └── requirements.txt
└── web/                     # 浏览器版（HTML5 + JS + CSS）
    ├── index.html           #   直接双击打开
    ├── js/core.js           #   核心算法（mathjs + fft.js）
    ├── js/simulation.js     #   端到端仿真封装
    ├── js/main.js           #   UI 逻辑（ECharts 绘图）
    ├── css/style.css
    └── test/test_web_core.mjs  # Node 数值验证（npm test）
```

- MATLAB 版请直接看 `matlab/main_detail.m`。
- Python 版请直接看 `python/main_detail.py`，算法审查结论见 `python/docs/algorithm_review.md`。
- 浏览器版请直接看 `web/index.html`（算法与 Python 版一致，数值经 Node 交叉验证）。

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

## 浏览器版（web/）

纯静态页面，无需构建、**离线可用、双击即用**：直接双击 `web/index.html` 即可在
浏览器中运行（mathjs 与 ECharts 已本地化到 `web/vendor/`，不依赖 CDN；算法为
普通 `<script>` 加载，`file://` 下不受 CORS 限制）。

- **功能与 Python GUI 一致**：频点/K/M/N 滑块、奇次项与时延对齐开关、
  DPD 前后频谱对比、AM/AM、AM/PM、泛化频谱、NMSE 与 ACPR 指标
- **实时更新开关**：默认开启（调参约 0.4 s 自动重算）；关闭后调参不自动计算、
  仅点 [运行] 才更新，节省算力；重新开启时立即用当前参数重算一次
- 算法（`web/js/core.js` / `simulation.js`）与 Python 版逐一对应，
  FFT 为内置实现，数值已通过 Node 与浏览器双重验证：

```bash
cd web
npm install             # 安装 mathjs / playwright-core（仅验证需要）
npm test                # Node 数值验证：与 Python 基准对比
npm run test:browser    # 浏览器端到端验证（file:// 打开 + 点击按钮 + 参数调节 + 截图）
```

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

### 目录结构（web/）

```
web/
  index.html              # 入口，直接双击打开（离线可用）
  vendor/                 # 本地化第三方库：math.min.js / echarts.min.js
  js/core.js              # 核心算法（复数用 mathjs，FFT 内置 radix-2）
  js/simulation.js        # run_simulation 端到端仿真封装
  js/main.js              # UI 逻辑与 ECharts 绘图
  css/style.css           # 深色主题样式
  test/test_web_core.mjs  # Node 数值验证（与 Python 基准对比）
  test/browser_check.mjs  # 浏览器端到端验证（playwright + 系统 Edge）
  package.json            # npm 依赖声明（mathjs / playwright-core）
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
