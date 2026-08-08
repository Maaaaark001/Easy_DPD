"""核心算法模块 —— MATLAB 版逐函数移植，numpy/scipy 向量化。

与 MATLAB 版的对应关系（行为保持一致，数值上仅浮点级差异）：
    saleh.m          -> saleh
    distortion.m     -> distortion
    mat_delay.m      -> mat_delay
    MP_model.m       -> mp_model
    DPD_Func.m       -> dpd_func
    NMSE.m           -> nmse
    plt_fft.m        -> plt_fft（返回 (f, P1)，绘图交给调用方）
"""

from __future__ import annotations

import numpy as np
from scipy import signal


# ---------------------------------------------------------------------------
# PA 失真模型
# ---------------------------------------------------------------------------

def saleh(x):
    """Saleh 无记忆失真模型。

    参数（经验系数，与 saleh.m 一致）：
        a1=1.5  b1=0.5  a2=pi/3  b2=1
    AM/AM: a_out = a1*r / (1 + b1*r^2)
    AM/PM: phi    = a2*r^2 / (1 + b2*r^2)
    """
    a1, b1 = 1.5, 0.5
    a2, b2 = np.pi / 3, 1.0

    r = np.abs(x)
    phi_in = np.angle(x)

    a_out = a1 * r / (1 + b1 * r**2)
    phi_pm = a2 * r**2 / (1 + b2 * r**2)

    return a_out * np.exp(1j * (phi_in + phi_pm))


def distortion(x):
    """带记忆的 PA 失真模型：FIR 滤波（记忆效应）+ Saleh（无记忆非线性）。

    b = [0.7692 0.1538 0.0769] 取自《射频功放数字预失真线性化技术研究_詹鹏》。
    与 MATLAB 版一致，使用零初始状态的因果滤波（scipy.signal.lfilter）。
    """
    b = np.array([0.7692, 0.1538, 0.0769])
    a = np.array([1.0])
    return saleh(signal.lfilter(b, a, x))


# ---------------------------------------------------------------------------
# 记忆多项式（Memory Polynomial）基函数
# ---------------------------------------------------------------------------

def mat_delay(x, d):
    """对 x 产生 d 个采样的前向（因果）延迟，缺失部分补零。

    等价于 MATLAB 版：circshift(x, d) 后前 d 个元素置零，
    即 y[n] = x[n-d]（n>=d），y[n]=0（n<d）。
    """
    if d < 0:
        raise ValueError(f"mat_delay 要求非负延迟，实际 d={d}（前移请用 shift）")
    if d == 0:
        return x
    xd = np.roll(x, d)      # y[n] = x[(n-d) mod N]，返回新数组
    xd[:d] = 0
    return xd


def shift(x, s):
    """因果移位：s>0 前移（y[n] = x[n+s]，尾部补零）；s<0 后移（同 mat_delay）。"""
    x = np.asarray(x)
    s = int(s)
    if s == 0:
        return x
    if s > 0:
        out = np.zeros_like(x)
        out[:-s] = x[s:]
        return out
    return mat_delay(x, -s)


def estimate_delay(x, y):
    """估计 y 相对 x 的延迟（样本数）。

    返回 d>0 表示 y 滞后于 x 达 d 个样本（y[n] ≈ x[n-d]）。
    用互相关峰值定位（与工程常用的相关法时延估计一致）。
    """
    c = signal.correlate(y, x, mode="full")
    lag = int(np.argmax(np.abs(c))) - (len(x) - 1)
    return lag


def align_y_to_x(x, y):
    """把 y 对齐到 x（消除 y 相对 x 的延迟），返回对齐后的 y。

    用于 DPD 拟合前的时延对齐（见 docs/algorithm_review.md P2）：
    PA 的群延迟会使 y[n] 对应 x[n-d]，未对齐直接拟合会有偏。
    """
    d = estimate_delay(x, y)
    return y if d == 0 else shift(y, d)


def mp_model(x, K, M, odd_only=False):
    """构造记忆多项式基函数矩阵 Y，形状 (N, n_k * (M+1))。

    每列对应一项  x[n-m] * |x[n-m]|^k ，m=0..M，k 取自：
        - odd_only=False：k = 0..K（全阶次，与原 MATLAB 版一致）
        - odd_only=True ：k = 0, 2, 4, ...（仅奇次阶 x|x|^k 的 k 为偶数，
          窄带信号的偶次项只产生带外/直流分量，对带内线性化无贡献，
          可减少列数、降低条件数——见 docs/algorithm_review.md P1）
    列序（与原 MATLAB 版一致）：m 外层、k 内层。

    加速点：用递推 term *= |x| 构造各阶次，避免对每列重复做幂运算；
    一次性预分配矩阵，避免逐列 append。
    """
    x = np.asarray(x)
    if x.ndim != 1:
        raise ValueError(f"mp_model 要求一维输入，实际维度 {x.ndim}")
    N = x.shape[0]
    ks = list(range(0, K + 1, 2)) if odd_only else list(range(0, K + 1))
    P = len(ks) * (M + 1)
    Y = np.empty((N, P), dtype=x.dtype)

    col = 0
    for m in range(M + 1):
        xm = mat_delay(x, m)
        ax = np.abs(xm)
        term = xm                       # k = 0: x|x|^0
        for k in range(0, K + 1):
            if k in ks:
                Y[:, col] = term
                col += 1
            term = term * ax            # 递推得 x|x|^(k+1)
    return Y


# ---------------------------------------------------------------------------
# DPD 系数拟合（ILA 间接学习架构）
# ---------------------------------------------------------------------------

def dpd_func(x, y, u, K, M, odd_only=False, delay_align=False):
    """DPD 系数核心算法。

    参数：
        x : 学习样本中系统的输入（目标信号）
        y : 学习样本中系统的失真输出
        u : 待预失真的目标输出信号
        K : 阶数
        M : 记忆深度
        odd_only    : True 时只保留奇次阶基函数（窄带 DPD 标准做法）
        delay_align : True 时先做时延对齐再拟合（消除 PA 群延迟影响）

    流程（与 DPD_Func.m 一致）：
        U = MP_model(u), Y = MP_model(y)
        w = lstsq(Y, x)   # 拟合逆模型 y -> x
        x_pre = U @ w

    注意：MATLAB 版写为 pinv(Y'Y)*Y'*x，即正规方程形式；
    这里改用 np.linalg.lstsq（SVD 求解），二者数学等价
    （都是最小二乘解），但 SVD 对病态矩阵数值更稳、速度更快。
    """
    y_fit = align_y_to_x(x, y) if delay_align else y

    U = mp_model(u, K, M, odd_only=odd_only)
    Y = mp_model(y_fit, K, M, odd_only=odd_only)

    w, *_ = np.linalg.lstsq(Y, x, rcond=None)
    return U @ w


# ---------------------------------------------------------------------------
# 评估与绘图工具
# ---------------------------------------------------------------------------

def nmse(x, y):
    """归一化均方误差 NMSE = sum(|x-y|^2) / sum(|x|^2)（线性值，越小越好）。

    与 NMSE.m 一致：实部/虚部分开求和（数值上等于 |x-y|^2）。
    """
    x = np.asarray(x)
    y = np.asarray(y)
    d_e = np.sum((np.real(x) - np.real(y)) ** 2
                 + (np.imag(x) - np.imag(y)) ** 2)
    d_m = np.sum(np.real(x) ** 2 + np.imag(x) ** 2)
    return d_e / d_m


def plt_fft(x, fs, fl=1):
    """计算加窗 FFT 的单边幅度谱（dB），与 plt_fft.m 一致。

    参数：
        x  : 信号
        fs : 采样率
        fl : 1 归一化到峰值（峰值 = 0 dB），否则绝对 dB 值

    返回：
        f   : 频率轴
        P1  : 功率谱（dB）

    注意：单边谱要求 L 为偶数（与原 MATLAB 版一致）。
    """
    x = np.asarray(x)
    L = len(x)
    w = np.hanning(L)                       # 对称 Hann 窗，与 MATLAB hann(L) 一致
    Y = np.fft.fft(np.real(x * w))
    P2 = np.abs(Y / L)
    P1 = P2[: L // 2 + 1].copy()
    P1[1:-1] *= 2                           # 单边谱，除 DC 与 Nyquist 外加倍

    f = fs * np.arange(L // 2 + 1) / L
    with np.errstate(divide="ignore"):
        if fl == 1:
            P1 = 20 * np.log10(np.abs(P1 / np.max(P1)))
        else:
            P1 = 20 * np.log10(np.abs(P1))
    return f, P1


def acpr(f, P1, main_band, adj_band):
    """邻道功率比 ACPR = 主信道功率 / 邻信道功率（dBc）。

    参数：
        f         : plt_fft 返回的频率轴
        P1        : plt_fft 返回的 dB 谱（fl=1 的归一化谱不影响比值）
        main_band : 主信道频率区间 (lo, hi)
        adj_band  : 邻信道频率区间 (lo, hi)

    返回：ACPR（dBc），越大表示带外失真抑制越好。
    """
    m = (f >= main_band[0]) & (f <= main_band[1])
    a = (f > adj_band[0]) & (f <= adj_band[1])   # 左开：避免与主带边界重叠双计
    p_main = np.sum(10.0 ** (P1[m] / 10.0))
    p_adj = np.sum(10.0 ** (P1[a] / 10.0))
    if p_adj <= 0 or p_main <= 0:
        return np.inf
    return float(10.0 * np.log10(p_main / p_adj))
