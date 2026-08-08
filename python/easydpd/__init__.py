"""Easy_DPD —— 数字预失真（DPD）仿真库（Python 版）。

对应原 MATLAB 仓库，核心算法逐一移植，并向量化加速：
- saleh / distortion : Saleh 模型 + FIR 记忆效应模拟 PA 失真
- mat_delay / shift / estimate_delay / align_y_to_x : 延迟与对齐工具
- mp_model : 记忆多项式基函数矩阵构造（支持奇次项开关）
- dpd_func : 逆模型最小二乘拟合（ILA 间接学习架构）
- nmse / plt_fft / acpr : 评估与频谱绘图工具
- simulation.run_simulation : 端到端仿真封装（脚本与 GUI 共用）
"""

from .core import (
    acpr,
    align_y_to_x,
    distortion,
    dpd_func,
    estimate_delay,
    mat_delay,
    mp_model,
    nmse,
    plt_fft,
    saleh,
    shift,
)
from .simulation import run_simulation

__all__ = [
    "acpr",
    "align_y_to_x",
    "distortion",
    "dpd_func",
    "estimate_delay",
    "mat_delay",
    "mp_model",
    "nmse",
    "plt_fft",
    "run_simulation",
    "saleh",
    "shift",
]

__version__ = "0.2.0"
