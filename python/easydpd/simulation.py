"""端到端仿真封装 —— main_detail.py 脚本与 gui.py 共用同一套计算逻辑。

run_simulation 完成 main_detail.m 的全部仿真流程，返回各阶段信号、
NMSE 与 ACPR 指标，避免脚本与 GUI 各自实现导致结果漂移。
"""

from __future__ import annotations

import numpy as np

from .core import acpr, distortion, dpd_func, nmse, plt_fft


def _bands(freqs, fs, N):
    """按信号频点动态定义主信道与上邻道（ACPR 标准做法）。

    主信道覆盖全部信号频点，邻道起点外推 margin 个频率分辨率 bin：
    加窗（Hann）后主峰旁瓣在 8 bin 外已低于约 -50 dB，
    避免窗泄漏污染邻道功率而掩盖真实失真（实测验证该取值）。

    上邻道宽度等于信号带宽。
    """
    f_low, f_high = min(freqs), max(freqs)
    df = fs / N                     # 频率分辨率（一个 bin 宽）
    margin = 8 * df                 # 越过窗主瓣/旁瓣的余量
    bw = f_high - f_low
    main = (f_low - margin, f_high + margin)
    adj = (f_high + margin, f_high + margin + bw)
    return main, adj


def run_simulation(*, fs=1e6, N=1024 * 16,
                   freqs=(90e3, 100e3, 110e3),
                   gen_freqs=(111e3, 89e3),
                   K=5, M=3, odd_only=False, delay_align=False):
    """运行完整 DPD 仿真。

    参数（均为关键字参数）：
        fs          : 采样率
        N           : 样本数
        freqs       : 训练信号频点（可迭代）
        gen_freqs   : 泛化测试信号频点（可迭代，或 None 跳过泛化测试）
        K           : 记忆多项式阶数
        M           : 记忆深度
        odd_only    : 只保留奇次阶基函数（窄带 DPD 标准做法）
        delay_align : 拟合前做时延对齐

    返回：dict，包含：
        sig_in / PA_out / PA_out2 / sig_in2 / PA_out3 : 各阶段信号
        u / PA_out_u / y_dis                          : AM/AM、AM/PM 观察用
        f, P_before, P_after                          : 补偿前后频谱（训练信号）
        nmse0 / nmse_fit / nmse1 / nmse2              : NMSE 指标
        acpr_before / acpr_after                      : ACPR 指标（dBc）
        params                                        : 本次仿真的参数副本
    """
    freqs = tuple(freqs)                     # 统一转 tuple，避免生成器二次耗尽
    gen_freqs = None if gen_freqs is None else tuple(gen_freqs)
    params = dict(fs=fs, N=N, freqs=freqs, gen_freqs=gen_freqs,
                  K=K, M=M, odd_only=odd_only, delay_align=delay_align)

    t = np.linspace(0, N / fs, N)

    # 1. 训练信号（归一化）
    sig_in = sum(np.sin(2 * np.pi * f * t) for f in freqs)
    sig_in = sig_in / np.max(sig_in)

    # 2. PA 失真模型与 AM/AM、AM/PM 观察
    u = np.linspace(0, 1, N)
    PA_out_u = distortion(u)
    PA_out = distortion(sig_in)

    # 3. 拟合测试（检验 GMP 能否匹配 PA 特性；逆模型拟合，x 与 y 反过来）
    y_dis = dpd_func(PA_out, sig_in, u, K, M, odd_only=odd_only,
                     delay_align=delay_align)

    # 4. 逆模型构建预失真（训练信号）
    X_pre = dpd_func(sig_in, PA_out, sig_in, K, M, odd_only=odd_only,
                     delay_align=delay_align)
    PA_out2 = distortion(X_pre)

    # 5. 泛化测试（训练时未见过的频点）
    sig_in2 = None
    PA_out3 = None
    if gen_freqs is not None:
        sig_in2 = sum(np.sin(2 * np.pi * f * t) for f in gen_freqs)
        sig_in2 = sig_in2 / np.max(sig_in2)
        X_pre2 = dpd_func(sig_in, PA_out, sig_in2, K, M, odd_only=odd_only,
                          delay_align=delay_align)
        PA_out3 = distortion(X_pre2)

    # 6. 指标
    f, P_before = plt_fft(PA_out, fs, 1)
    _, P_after = plt_fft(PA_out2, fs, 1)
    main_b, adj_b = _bands(freqs, fs, N)

    result = {
        "sig_in": sig_in, "PA_out": PA_out, "PA_out2": PA_out2,
        "u": u, "PA_out_u": PA_out_u, "y_dis": y_dis,
        "sig_in2": sig_in2, "PA_out3": PA_out3,
        "f": f, "P_before": P_before, "P_after": P_after,
        "nmse0": nmse(u, PA_out_u),
        "nmse_fit": nmse(PA_out_u, y_dis),
        "nmse1": nmse(sig_in, PA_out2),
        "acpr_before": acpr(f, P_before, main_b, adj_b),
        "acpr_after": acpr(f, P_after, main_b, adj_b),
        "params": params,
    }
    if sig_in2 is not None and PA_out3 is not None:
        result["nmse2"] = nmse(sig_in2, PA_out3)
        _, P3 = plt_fft(PA_out3, fs, 1)
        result["P3"] = P3
        main_b2, adj_b2 = _bands(gen_freqs, fs, N)
        result["acpr_before_gen"] = acpr(f, plt_fft(distortion(sig_in2), fs, 1)[1],
                                          main_b2, adj_b2)
        result["acpr_after_gen"] = acpr(f, P3, main_b2, adj_b2)
    return result
