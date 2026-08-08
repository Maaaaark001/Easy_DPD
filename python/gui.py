"""Easy_DPD 交互式仿真面板（tkinter + matplotlib 嵌入）。

运行：
    python gui.py

左侧参数面板实时调节（滑块/复选框/下拉框），右侧图表自动刷新：
    - DPD 前 / DPD 后频谱对比（训练信号）
    - AM/AM、AM/PM 拟合观察
    - 泛化测试频谱（可开关）
    - NMSE 与 ACPR 指标实时显示

参数变化后自动重算（约 0.4 s 防抖），也可点 [运行] 立即重算。
"""

import tkinter as tk
from tkinter import ttk

import matplotlib

matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import numpy as np

from easydpd import run_simulation

# matplotlib 中文字体（Windows 下使用微软雅黑；其它平台可按需调整）
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

DEFAULTS = dict(f1=90, f2=100, f3=110, f4=89, f5=111,
                K=5, M=3, N=16384, odd_only=False, delay_align=False, gen=True)
N_OPTIONS = [16384, 32768, 65536]
FREQ_RANGE = (50, 150)          # kHz
DEBOUNCE_MS = 400


class DpdGui(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Easy_DPD 仿真面板")
        self.geometry("1200x720")
        self.minsize(1000, 600)

        self._after_id = None
        self._rounding = False
        self._vars = self._make_vars()

        self._build_ui()
        self._run()                     # 初始仿真

    # ------------------------------------------------------------------
    # 控件变量
    # ------------------------------------------------------------------
    def _make_vars(self):
        v = {
            "f1": tk.DoubleVar(value=DEFAULTS["f1"]),
            "f2": tk.DoubleVar(value=DEFAULTS["f2"]),
            "f3": tk.DoubleVar(value=DEFAULTS["f3"]),
            "f4": tk.DoubleVar(value=DEFAULTS["f4"]),
            "f5": tk.DoubleVar(value=DEFAULTS["f5"]),
            "K": tk.IntVar(value=DEFAULTS["K"]),
            "M": tk.IntVar(value=DEFAULTS["M"]),
            "N": tk.StringVar(value=str(DEFAULTS["N"])),
            "odd_only": tk.BooleanVar(value=DEFAULTS["odd_only"]),
            "delay_align": tk.BooleanVar(value=DEFAULTS["delay_align"]),
            "gen": tk.BooleanVar(value=DEFAULTS["gen"]),
        }
        # 指标显示
        for key in ("nmse0", "nmse_fit", "nmse1", "nmse2",
                    "acpr_b", "acpr_a", "acpr_gb", "acpr_ga"):
            v[key] = tk.StringVar(value="--")
        return v

    # ------------------------------------------------------------------
    # 界面构建
    # ------------------------------------------------------------------
    def _build_ui(self):
        main = ttk.Frame(self)
        main.pack(fill="both", expand=True, padx=6, pady=6)

        left = ttk.Frame(main, width=300)
        left.pack(side="left", fill="y", padx=(0, 6))
        left.pack_propagate(False)

        right = ttk.Frame(main)
        right.pack(side="left", fill="both", expand=True)

        self._build_controls(left)
        self._build_plot(right)
        self._build_metrics(left)

    def _build_controls(self, parent):
        box = ttk.LabelFrame(parent, text="仿真参数", padding=8)
        box.pack(fill="x")

        row = 0
        for key in ("f1", "f2", "f3"):
            self._add_freq_scale(box, row, key, DEFAULTS[key])
            row += 1

        ttk.Checkbutton(box, text="启用泛化测试", variable=self._vars["gen"],
                        command=self._on_change).grid(row=row, column=0, columnspan=3,
                                                      sticky="w", pady=(4, 0))
        row += 1
        for key in ("f4", "f5"):
            self._add_freq_scale(box, row, key, DEFAULTS[key], gen=True)
            row += 1

        ttk.Separator(box).grid(row=row, column=0, columnspan=3, sticky="ew",
                                pady=6)
        row += 1

        self._add_int_scale(box, row, "K（阶数）", "K", 1, 9); row += 1
        self._add_int_scale(box, row, "M（记忆深度）", "M", 0, 5); row += 1

        ttk.Label(box, text="N（样本数）").grid(row=row, column=0, sticky="w")
        ncombo = ttk.Combobox(box, values=N_OPTIONS, textvariable=self._vars["N"],
                              state="readonly", width=10)
        ncombo.grid(row=row, column=1, columnspan=2, sticky="ew", pady=2)
        ncombo.bind("<<ComboboxSelected>>", self._on_change)
        row += 1

        ttk.Checkbutton(box, text="只保留奇次项（窄带 DPD 标准做法）",
                        variable=self._vars["odd_only"],
                        command=self._on_change).grid(row=row, column=0, columnspan=3,
                                                      sticky="w")
        row += 1
        ttk.Checkbutton(box, text="拟合前时延对齐",
                        variable=self._vars["delay_align"],
                        command=self._on_change).grid(row=row, column=0, columnspan=3,
                                                      sticky="w")
        row += 1

        btns = ttk.Frame(box)
        btns.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(8, 0))
        ttk.Button(btns, text="运行", command=self._run).pack(side="left", expand=True, fill="x")
        ttk.Button(btns, text="恢复默认", command=self._restore_defaults).pack(
            side="left", expand=True, fill="x", padx=(4, 0))

    def _add_freq_scale(self, parent, row, key, default, gen=False):
        lo, hi = FREQ_RANGE
        ttk.Label(parent, text=f"{'泛化' if gen else '训练'}频点 {key[1:]}").grid(
            row=row, column=0, sticky="w")
        ttk.Scale(parent, from_=lo, to=hi, variable=self._vars[key],
                  command=self._on_change, length=140).grid(
            row=row, column=1, sticky="ew", padx=4)
        ttk.Label(parent, textvariable=self._vars[key], width=6).grid(
            row=row, column=2, sticky="e")
        self._vars[key].trace_add("write", lambda *_: self._fmt_freq(key))

    def _fmt_freq(self, key):
        if self._rounding:          # 防重入：set 会再次触发 trace
            return
        self._rounding = True
        try:
            self._vars[key].set(round(self._vars[key].get()))
        finally:
            self._rounding = False

    def _add_int_scale(self, parent, row, label, key, lo, hi):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w")
        ttk.Scale(parent, from_=lo, to=hi, variable=self._vars[key],
                  command=self._on_change, length=140).grid(
            row=row, column=1, sticky="ew", padx=4)
        ttk.Label(parent, textvariable=self._vars[key], width=6).grid(
            row=row, column=2, sticky="e")

        def _round_int(*_):
            if self._rounding:
                return
            self._rounding = True
            try:
                self._vars[key].set(int(round(self._vars[key].get())))
            finally:
                self._rounding = False

        self._vars[key].trace_add("write", _round_int)

    def _build_plot(self, parent):
        self.fig, self.axes = plt.subplots(2, 2, figsize=(11, 7))
        self.fig.tight_layout(h_pad=2.2)
        self.canvas = FigureCanvasTkAgg(self.fig, master=parent)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        toolbar = NavigationToolbar2Tk(self.canvas, parent)
        toolbar.update()

    def _build_metrics(self, parent):
        box = ttk.LabelFrame(parent, text="指标", padding=8)
        box.pack(fill="x", pady=(6, 0))
        rows = [
            ("失真本底 NMSE0", "nmse0"),
            ("拟合精度 NMSE", "nmse_fit"),
            ("补偿后(同频) NMSE1", "nmse1"),
            ("补偿后(泛化) NMSE2", "nmse2"),
            ("ACPR 训练 前/后 (dBc)", "acpr_b", "acpr_a"),
            ("ACPR 泛化 前/后 (dBc)", "acpr_gb", "acpr_ga"),
        ]
        for i, (label, *keys) in enumerate(rows):
            ttk.Label(box, text=label).grid(row=i, column=0, sticky="w", pady=1)
            if len(keys) == 1:
                ttk.Label(box, textvariable=self._vars[keys[0]]).grid(
                    row=i, column=1, sticky="e", pady=1)
            else:
                f = ttk.Frame(box)
                f.grid(row=i, column=1, sticky="e", pady=1)
                ttk.Label(f, textvariable=self._vars[keys[0]]).pack(side="left")
                ttk.Label(f, text=" → ").pack(side="left")
                ttk.Label(f, textvariable=self._vars[keys[1]]).pack(side="left")

    # ------------------------------------------------------------------
    # 交互逻辑
    # ------------------------------------------------------------------
    def _on_change(self, *_):
        if self._after_id is not None:
            self.after_cancel(self._after_id)
        self._after_id = self.after(DEBOUNCE_MS, self._run)

    def _read_params(self):
        v = self._vars
        return dict(
            fs=1e6,
            N=int(v["N"].get()),
            # 统一取整（与面板显示一致），再转 Hz
            freqs=(round(v["f1"].get()), round(v["f2"].get()), round(v["f3"].get())),
            gen_freqs=(round(v["f4"].get()), round(v["f5"].get())) if v["gen"].get() else None,
            K=int(v["K"].get()),
            M=int(v["M"].get()),
            odd_only=bool(v["odd_only"].get()),
            delay_align=bool(v["delay_align"].get()),
        )

    def _run(self):
        if self._after_id is not None:
            self.after_cancel(self._after_id)
            self._after_id = None
        self.config(cursor="watch")
        self.update_idletasks()
        try:
            p = self._read_params()
            r = run_simulation(
                fs=p["fs"], N=p["N"],
                freqs=tuple(f * 1e3 for f in p["freqs"]),
                gen_freqs=None if p["gen_freqs"] is None
                else tuple(f * 1e3 for f in p["gen_freqs"]),
                K=p["K"], M=p["M"],
                odd_only=p["odd_only"], delay_align=p["delay_align"],
            )
            self._draw(r, p)
            self._update_metrics(r, p)
        except Exception as e:      # 参数异常时给出提示而非崩溃
            self._show_error(e)
        finally:
            self.config(cursor="")

    def _draw(self, r, p):
        ax1, ax2, ax3, ax4 = self.axes.flat
        fk = r["f"] / 1e3

        ax1.clear()
        ax1.plot(fk, r["P_before"], label="DPD 前", lw=1.2)
        ax1.plot(fk, r["P_after"], label="DPD 后", lw=1.2)
        ax1.set_ylim(-90, 5)
        ax1.set_xlim(0, 200)
        ax1.set_title("频谱对比（训练信号）")
        ax1.set_xlabel("f / kHz")
        ax1.set_ylabel("功率谱 / dB")
        ax1.legend(fontsize=8)
        ax1.grid(alpha=0.3)

        u, pau, yd = r["u"], r["PA_out_u"], r["y_dis"]
        ax2.clear()
        ax2.plot(u, u, "k-", lw=1, label="linear")
        ax2.plot(u, np.abs(pau), label="PA out", lw=1.2)
        ax2.plot(u, np.abs(yd), "--", label="GMP", lw=1.2)
        ax2.set_title("AM/AM")
        ax2.set_xlabel("sig in")
        ax2.set_ylabel("PA out")
        ax2.legend(fontsize=8)
        ax2.grid(alpha=0.3)

        ax3.clear()
        ax3.plot(u, np.angle(pau), label="PA out", lw=1.2)
        ax3.plot(u, np.angle(yd), "--", label="GMP", lw=1.2)
        ax3.set_title("AM/PM")
        ax3.set_xlabel("sig in")
        ax3.set_ylabel("phase / rad")
        ax3.legend(fontsize=8)
        ax3.grid(alpha=0.3)

        ax4.clear()
        if p["gen_freqs"] is not None and "P3" in r:
            ax4.plot(fk, r["P3"], lw=1.2, color="C2")
            ax4.set_ylim(-90, 5)
            ax4.set_xlim(0, 200)
            ax4.set_title("泛化测试频谱（新频点）")
            ax4.set_xlabel("f / kHz")
            ax4.set_ylabel("功率谱 / dB")
        else:
            ax4.text(0.5, 0.5, "泛化测试未启用", ha="center", va="center",
                     transform=ax4.transAxes, color="gray")
            ax4.set_title("泛化测试频谱")
        ax4.grid(alpha=0.3)

        self.fig.tight_layout(h_pad=2.2)
        self.canvas.draw_idle()

    def _update_metrics(self, r, p):
        def fmt(x, suffix=""):
            return f"{x:.2e}{suffix}" if x is not None else "--"

        v = self._vars
        v["nmse0"].set(fmt(r["nmse0"]))
        v["nmse_fit"].set(fmt(r["nmse_fit"]))
        v["nmse1"].set(fmt(r["nmse1"]))
        if p["gen_freqs"] is not None and "nmse2" in r:
            v["nmse2"].set(fmt(r["nmse2"]))
        else:
            v["nmse2"].set("未启用")
        v["acpr_b"].set(self._fmt_acpr(r["acpr_before"]))
        v["acpr_a"].set(self._fmt_acpr(r["acpr_after"]))
        if p["gen_freqs"] is not None and "acpr_before_gen" in r:
            v["acpr_gb"].set(self._fmt_acpr(r["acpr_before_gen"]))
            v["acpr_ga"].set(self._fmt_acpr(r["acpr_after_gen"]))
        else:
            v["acpr_gb"].set("未启用")
            v["acpr_ga"].set("未启用")

    @staticmethod
    def _fmt_acpr(x):
        return "--" if x is None or not np.isfinite(x) else f"{x:.1f}"

    def _show_error(self, e):
        self.axes.flat[0].clear()
        self.axes.flat[0].text(0.5, 0.5, f"仿真失败：{e}", ha="center", va="center",
                               transform=self.axes.flat[0].transAxes, color="red")
        self.canvas.draw_idle()

    def _restore_defaults(self):
        for key, val in DEFAULTS.items():
            if key in self._vars:
                self._vars[key].set(val)
        self._run()


def main():
    try:
        app = DpdGui()
    except tk.TclError as e:
        print(f"[错误] 无法创建图形窗口（{e}）。"
              "当前环境可能没有桌面会话，请改用 python main_detail.py（无头模式）。")
        raise SystemExit(1)
    app.mainloop()


if __name__ == "__main__":
    main()
