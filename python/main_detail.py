"""Easy_DPD 主流程 —— 对应 MATLAB 版 main_detail.m。

流程：
    1. 生成三音测试信号（90/100/110 kHz）
    2. distortion 模型（Saleh + FIR）模拟带记忆 PA 失真，画 AM/AM、AM/PM
    3. 观察预失真补偿前的频谱
    4. 记忆多项式拟合测试（检验模型能否匹配 PA 特性）
    5. 逆模型构建预失真（ILA），观察补偿后的时域/频域
    6. 用新频点信号（89/111 kHz）验证系数泛化能力

计算部分复用 easydpd.run_simulation（与 GUI 共用同一套逻辑）。

运行：
    python main_detail.py
    - 默认交互模式：图表保存到 results/ 并弹窗显示（关闭全部窗口后结束）
    - 无头环境：EASY_DPD_HEADLESS=1 python main_detail.py（仅保存 PNG）
"""

import os

import matplotlib

# 默认使用交互后端（弹窗显示图表）；无头环境设 EASY_DPD_HEADLESS=1 则只保存 PNG
HEADLESS = os.environ.get("EASY_DPD_HEADLESS") == "1"
if HEADLESS:
    matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from easydpd import distortion, run_simulation

# matplotlib 中文字体（Windows 下使用微软雅黑；其它平台可按需调整）
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")


def save_fig(fig, name):
    """保存 PNG（窗口保留，供末尾 plt.show() 统一显示）。"""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    path = os.path.join(RESULTS_DIR, name)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    print(f"[fig] saved -> {path}")


# ---------------------------------------------------------------------------
# 仿真（参数与 MATLAB 版一致：K=5, M=3，训练 90/100/110，泛化 89/111 kHz）
# ---------------------------------------------------------------------------
r = run_simulation(fs=1e6, N=1024 * 16,
                   freqs=(90e3, 100e3, 110e3),
                   gen_freqs=(111e3, 89e3),
                   K=5, M=3)

sig_in, PA_out, PA_out2 = r["sig_in"], r["PA_out"], r["PA_out2"]
sig_in2, PA_out3 = r["sig_in2"], r["PA_out3"]
u, PA_out_u, y_dis = r["u"], r["PA_out_u"], r["y_dis"]

# ---------------------------------------------------------------------------
# 1. AM/AM 与 AM/PM（PA 失真特性）
# ---------------------------------------------------------------------------
fig = plt.figure(1, figsize=(8, 8))
plt.subplot(2, 1, 1)
plt.plot(u, np.abs(PA_out_u), label="PA out")
plt.plot(u, u, label="line")
plt.title("AM/AM")
plt.xlabel("sig in")
plt.ylabel("PA out")
plt.legend()
plt.subplot(2, 1, 2)
plt.plot(u, np.angle(PA_out_u))
plt.title("AM/PM")
plt.xlabel("sig in")
plt.ylabel("PA out")
plt.tight_layout()
save_fig(fig, "fig1_am_am_pm.png")

# ---------------------------------------------------------------------------
# 2. 时域：PA 输入/输出
# ---------------------------------------------------------------------------
fig = plt.figure(2, figsize=(10, 4))
plt.plot(np.real(PA_out), label="PA out")
plt.plot(np.real(sig_in), label="sig in")
plt.legend()
plt.title("时域：PA 输入/输出")
plt.tight_layout()
save_fig(fig, "fig2_time_domain.png")

# ---------------------------------------------------------------------------
# 3. 预失真补偿前频谱
# ---------------------------------------------------------------------------
fig = plt.figure(3, figsize=(10, 5))
plt.plot(r["f"], r["P_before"])
plt.ylim([-80, 0])
plt.xlim([0, 200e3])
plt.ylabel("功率谱/dB")
plt.xlabel("f/Hz")
plt.title("预失真补偿前")
plt.tight_layout()
save_fig(fig, "fig3_psd_before.png")

# ---------------------------------------------------------------------------
# 4. 拟合测试（判断阶数与记忆深度是否匹配）
# ---------------------------------------------------------------------------
fig = plt.figure(4, figsize=(8, 8))
plt.subplot(2, 1, 1)
plt.plot(u, u, label="line")
plt.plot(u, np.abs(PA_out_u), label="PA out")
plt.plot(u, np.abs(y_dis), label="GMP")
plt.title("AM/AM")
plt.xlabel("sig in")
plt.ylabel("PA out")
plt.legend()
plt.subplot(2, 1, 2)
plt.plot(u, np.angle(PA_out_u), label="PA out")
plt.plot(u, np.angle(y_dis), label="GMP")
plt.title("AM/PM")
plt.xlabel("sig in")
plt.ylabel("PA out")
plt.legend()
plt.tight_layout()
save_fig(fig, "fig4_fit_check.png")

# ---------------------------------------------------------------------------
# 5. 预失真补偿后：时域 + 频谱
# ---------------------------------------------------------------------------
fig = plt.figure(5, figsize=(10, 4))
plt.plot(np.real(PA_out2), label="Using Pre")
plt.plot(np.real(PA_out), label="Unusing Pre")
plt.legend()
plt.xlabel("Sample")
plt.ylabel("A")
plt.title("时域：预失真补偿前后")
plt.tight_layout()
save_fig(fig, "fig5_time_comp.png")

fig = plt.figure(6, figsize=(10, 5))
plt.plot(r["f"], r["P_after"])
plt.ylim([-80, 0])
plt.xlim([0, 200e3])
plt.ylabel("功率谱/dB")
plt.xlabel("f/Hz")
plt.title("预失真补偿后")
plt.tight_layout()
save_fig(fig, "fig6_psd_after.png")

# ---------------------------------------------------------------------------
# 6. 泛化测试（新频点信号）
# ---------------------------------------------------------------------------
fig = plt.figure(7, figsize=(10, 5))
plt.plot(r["f"], r["P3"])
plt.ylim([-80, 0])
plt.xlim([0, 200e3])
plt.ylabel("功率谱/dB")
plt.xlabel("f/Hz")
plt.title("预失真补偿后（泛化）")
plt.tight_layout()
save_fig(fig, "fig7_psd_generalization.png")

fig = plt.figure(8, figsize=(8, 6))
plt.plot(np.abs(sig_in2), np.abs(np.real(distortion(sig_in2))), "*",
         label="Unusing Pre")
plt.plot(np.abs(sig_in2), np.abs(np.real(PA_out3)), "*", label="Using Pre")
plt.plot(np.abs(u), np.abs(u), label="Linear")
plt.xlabel("Input")
plt.ylabel("Output")
plt.legend(loc="upper left")
plt.title("泛化：幅度转移特性")
plt.tight_layout()
save_fig(fig, "fig8_scatter_generalization.png")

# ---------------------------------------------------------------------------
# 汇总结果
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("NMSE summary (linear, smaller is better; dB for reference)")
print("=" * 60)
print(f"distortion floor  nmse0  = {r['nmse0']:.6e}  ({10*np.log10(r['nmse0']):8.2f} dB)")
print(f"model fit         nmse   = {r['nmse_fit']:.6e}  ({10*np.log10(r['nmse_fit']):8.2f} dB)")
print(f"after DPD (same)  nmse1  = {r['nmse1']:.6e}  ({10*np.log10(r['nmse1']):8.2f} dB)")
print(f"after DPD (gen.)  nmse2  = {r['nmse2']:.6e}  ({10*np.log10(r['nmse2']):8.2f} dB)")
print("\nACPR (dBc, 越大越好):")
print(f"train signal  before = {r['acpr_before']:7.2f} dBc   after = {r['acpr_after']:7.2f} dBc")
print(f"gen.  signal  before = {r['acpr_before_gen']:7.2f} dBc   after = {r['acpr_after_gen']:7.2f} dBc")
print("=" * 60)
print(f"figures saved to {RESULTS_DIR}")

# ---------------------------------------------------------------------------
# 弹窗显示（阻塞，直到所有窗口关闭）
# ---------------------------------------------------------------------------
if HEADLESS:
    print("\n[info] 非交互模式（EASY_DPD_HEADLESS=1）：图表仅保存为 PNG。")
else:
    print("\n[show] 打开显示窗口，关闭全部窗口后脚本结束...")
    try:
        plt.show()
    except Exception as e:  # 无桌面会话（如服务/远程）时回退为仅保存
        print(f"[warn] 窗口显示失败（{e}），图表已保存为 PNG。")
