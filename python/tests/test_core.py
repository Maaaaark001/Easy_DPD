"""核心算法单元测试。

验证每个函数与 MATLAB 版的数学等价性（手算基准 / 定义检查），
以及端到端 DPD 流程的数值回归基准。

运行：
    python -m pytest tests/ -q
    # 或无 pytest 时：python tests/test_core.py
"""

import numpy as np
import pytest
from scipy import signal

from easydpd import (
    acpr,
    align_y_to_x,
    distortion,
    dpd_func,
    estimate_delay,
    mat_delay,
    mp_model,
    nmse,
    plt_fft,
    run_simulation,
    saleh,
    shift,
)


# ---------------------------------------------------------------------------
# saleh
# ---------------------------------------------------------------------------

class TestSaleh:
    def test_am_am_formula(self):
        """AM/AM 曲线应满足 a_out = a1*r/(1+b1*r^2)。"""
        r = np.array([0.0, 0.5, 1.0, 2.0])
        y = saleh(r)
        expected = 1.5 * r / (1 + 0.5 * r**2)
        np.testing.assert_allclose(np.abs(y), expected, rtol=1e-14)

    def test_am_pm_formula(self):
        """零输入相位时输出相位 = a2*r^2/(1+b2*r^2)。"""
        r = np.array([0.3, 0.7, 1.2])
        y = saleh(r)
        expected = (np.pi / 3) * r**2 / (1 + r**2)
        np.testing.assert_allclose(np.angle(y), expected, rtol=1e-14)

    def test_phase_shift_preserved(self):
        """输入相位偏置应原样保留在输出中。"""
        x = 0.8 * np.exp(1j * 0.7)
        y = saleh(x)
        assert y.shape == x.shape
        np.testing.assert_allclose(np.angle(y) - np.angle(x),
                                   (np.pi / 3) * 0.8**2 / (1 + 0.8**2),
                                   rtol=1e-14)


# ---------------------------------------------------------------------------
# mat_delay
# ---------------------------------------------------------------------------

class TestMatDelay:
    def test_zero_delay_is_identity(self):
        x = np.arange(10.0)
        np.testing.assert_array_equal(mat_delay(x, 0), x)

    def test_forward_delay(self):
        """y[n] = x[n-d]（n>=d），前 d 个为零。"""
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        d = 2
        np.testing.assert_array_equal(mat_delay(x, d), [0.0, 0.0, 1.0, 2.0, 3.0])

    def test_does_not_mutate_input(self):
        x = np.arange(6.0)
        x_copy = x.copy()
        mat_delay(x, 2)
        np.testing.assert_array_equal(x, x_copy)

    def test_matches_circshift_semantics(self):
        """与 MATLAB circshift+置零 等价：np.roll 后前 d 个置零。"""
        rng = np.random.default_rng(0)
        x = rng.standard_normal(100)
        d = 7
        ref = np.roll(x, d)
        ref[:d] = 0
        np.testing.assert_array_equal(mat_delay(x, d), ref)


# ---------------------------------------------------------------------------
# mp_model
# ---------------------------------------------------------------------------

class TestMpModel:
    def test_shape(self):
        N = 100
        x = np.arange(N, dtype=float)
        K, M = 5, 3
        Y = mp_model(x, K, M)
        assert Y.shape == (N, (K + 1) * (M + 1))

    def test_column_values(self):
        """列序与 MATLAB 一致：m 外层、k 内层，列 = x[n-m]|x[n-m]|^k。"""
        x = np.array([1.0, 2.0, 3.0])
        K, M = 2, 1
        Y = mp_model(x, K, M)
        # m=0 块：k=0,1,2 -> x, x|x|, x|x|^2
        np.testing.assert_allclose(Y[:, 0], x)
        np.testing.assert_allclose(Y[:, 1], x * np.abs(x))
        np.testing.assert_allclose(Y[:, 2], x * np.abs(x) ** 2)
        # m=1 块：延迟 1 的同类基函数
        x1 = mat_delay(x, 1)
        np.testing.assert_allclose(Y[:, 3], x1)
        np.testing.assert_allclose(Y[:, 4], x1 * np.abs(x1))
        np.testing.assert_allclose(Y[:, 5], x1 * np.abs(x1) ** 2)

    def test_complex_input(self):
        rng = np.random.default_rng(1)
        x = rng.standard_normal(64) + 1j * rng.standard_normal(64)
        Y = mp_model(x, 3, 2)
        assert np.iscomplexobj(Y)
        assert Y.shape == (64, (3 + 1) * (2 + 1))


# ---------------------------------------------------------------------------
# distortion
# ---------------------------------------------------------------------------

class TestDistortion:
    def test_equals_saleh_of_filtered(self):
        rng = np.random.default_rng(2)
        x = rng.standard_normal(256)
        b = np.array([0.7692, 0.1538, 0.0769])
        a = np.array([1.0])
        expected = saleh(signal.lfilter(b, a, x))
        np.testing.assert_allclose(distortion(x), expected, rtol=1e-14)


# ---------------------------------------------------------------------------
# dpd_func
# ---------------------------------------------------------------------------

class TestDpdFunc:
    def test_linear_case_exact(self):
        """纯线性系统 y = 2x 时，逆模型系数应精确恢复出 x。"""
        rng = np.random.default_rng(3)
        x = rng.standard_normal(256)
        y = 2.0 * x
        u = rng.standard_normal(256)  # 新输入
        x_pre = dpd_func(x, y, u, K=2, M=1)
        # 逆模型 y->x 是 0.5y，因此预失真输出应 ≈ 0.5*u
        np.testing.assert_allclose(x_pre, 0.5 * u, rtol=1e-10)

    def test_consistency_with_normal_equations(self):
        """dpd_func 与 MATLAB 正规方程解 pinv(Y'Y)Y'x 数值一致。"""
        rng = np.random.default_rng(4)
        x = rng.standard_normal(128) + 1j * rng.standard_normal(128)
        y = saleh(signal.lfilter([0.7692, 0.1538, 0.0769], [1.0], x))
        u = rng.standard_normal(128) + 1j * rng.standard_normal(128)
        K, M = 3, 2

        U = mp_model(u, K, M)
        Y = mp_model(y, K, M)
        w_ref = np.linalg.pinv(Y.conj().T @ Y) @ Y.conj().T @ x
        x_pre_ref = U @ w_ref

        x_pre = dpd_func(x, y, u, K, M)
        np.testing.assert_allclose(x_pre, x_pre_ref, rtol=1e-8, atol=1e-10)


# ---------------------------------------------------------------------------
# nmse / plt_fft
# ---------------------------------------------------------------------------

class TestNmse:
    def test_identical_signals(self):
        x = np.array([1.0 + 1j, 2.0 - 1j])
        assert nmse(x, x) == 0.0

    def test_known_value(self):
        x = np.array([1.0, 2.0, 3.0])
        y = np.array([1.0, 2.0, 4.0])  # 只有一处差 1
        expected = 1.0 / (1 + 4 + 9)
        np.testing.assert_allclose(nmse(x, y), expected, rtol=1e-14)

    def test_matches_direct_formula(self):
        rng = np.random.default_rng(5)
        x = rng.standard_normal(64) + 1j * rng.standard_normal(64)
        y = rng.standard_normal(64) + 1j * rng.standard_normal(64)
        expected = np.sum(np.abs(x - y) ** 2) / np.sum(np.abs(x) ** 2)
        np.testing.assert_allclose(nmse(x, y), expected, rtol=1e-14)


class TestPltFft:
    def test_normalized_peak_is_zero_db(self):
        rng = np.random.default_rng(6)
        x = rng.standard_normal(1024)
        f, P1 = plt_fft(x, fs=1e6, fl=1)
        assert len(f) == 1024 // 2 + 1
        assert len(P1) == 1024 // 2 + 1
        np.testing.assert_allclose(np.max(P1), 0.0, atol=1e-12)

    def test_absolute_mode_uses_absolute_levels(self):
        rng = np.random.default_rng(7)
        x = rng.standard_normal(1024)
        _, P1_norm = plt_fft(x, fs=1e6, fl=1)
        _, P1_abs = plt_fft(x, fs=1e6, fl=0)
        # 绝对模式峰值 = 20*log10(单边幅度峰值)，应明显低于 0 dB
        assert np.max(P1_abs) < 0.0
        assert np.max(P1_norm) == 0.0

    def test_tone_location(self):
        """100 kHz 单音应在频谱中正确落位。"""
        fs = 1e6
        N = 16384
        t = np.arange(N) / fs
        x = np.sin(2 * np.pi * 100e3 * t)
        f, P1 = plt_fft(x, fs, fl=1)
        peak_idx = np.argmax(P1)
        np.testing.assert_allclose(f[peak_idx], 100e3, atol=fs / N)


# ---------------------------------------------------------------------------
# 端到端回归：main_detail 流程的核心数值基准
# ---------------------------------------------------------------------------

class TestEndToEnd:
    @pytest.fixture(scope="class")
    @classmethod
    def scenario(cls):
        fs = 1e6
        N = 1024 * 16
        t = np.linspace(0, N / fs, N)
        sig_in = (np.sin(2 * np.pi * 90e3 * t)
                  + np.sin(2 * np.pi * 100e3 * t)
                  + np.sin(2 * np.pi * 110e3 * t))
        sig_in = sig_in / np.max(sig_in)
        u = np.linspace(0, 1, N)

        PA_out_u = distortion(u)
        PA_out = distortion(sig_in)
        x, y = sig_in, PA_out
        K, M = 5, 3

        y_dis = dpd_func(y, x, u, K, M)
        X_pre = dpd_func(x, y, x, K, M)
        PA_out2 = distortion(X_pre)

        f4, f5 = 111e3, 89e3
        sig_in2 = np.sin(2 * np.pi * f4 * t) + np.sin(2 * np.pi * f5 * t)
        sig_in2 = sig_in2 / np.max(sig_in2)
        PA_out3 = distortion(dpd_func(x, y, sig_in2, K, M))

        return {
            "nmse0": nmse(u, PA_out_u),
            "nmse_fit": nmse(PA_out_u, y_dis),
            "nmse1": nmse(x, PA_out2),
            "nmse2": nmse(sig_in2, PA_out3),
            "N": N, "K": K, "M": M,
        }

    def test_fit_is_good(self, scenario):
        """拟合测试：GMP 模型应能很好复现 PA 的 AM/AM、AM/PM。"""
        # K=5 阶截断的正常拟合水平（约 -25 dB），且远优于失真本底
        assert scenario["nmse_fit"] < 1e-2
        assert scenario["nmse_fit"] < 0.1 * scenario["nmse0"]

    def test_linearization_improves(self, scenario):
        """预失真后 NMSE 应显著低于失真本底。"""
        assert scenario["nmse1"] < scenario["nmse0"] * 0.1

    def test_generalization_improves(self, scenario):
        """新频点信号同样应被线性化。"""
        assert scenario["nmse2"] < scenario["nmse0"] * 0.1

    def test_regression_benchmark(self, scenario):
        """数值回归基准（由 TestSimulation.test_consistent_with_main_detail_benchmark
        锁定 main_detail 基准；此处保留端到端场景的一致性检查）。"""
        # 与 TestSimulation 基准交叉验证：默认 K=5, M=3 的 NMSE 序列
        r = run_simulation()
        np.testing.assert_allclose(scenario["nmse1"], r["nmse1"], rtol=1e-12)
        np.testing.assert_allclose(scenario["nmse2"], r["nmse2"], rtol=1e-12)


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))


# ---------------------------------------------------------------------------
# 新增功能：奇次项开关 / 时延对齐 / ACPR / run_simulation
# ---------------------------------------------------------------------------

class TestOddOnly:
    def test_mp_model_columns(self):
        """odd_only 只保留 k=0,2,4 列，列内容正确。"""
        x = np.array([1.0, 2.0, 3.0])
        K, M = 5, 1
        Y = mp_model(x, K, M, odd_only=True)
        assert Y.shape == (3, 3 * (M + 1))      # k=0,2,4
        np.testing.assert_allclose(Y[:, 0], x)
        np.testing.assert_allclose(Y[:, 1], x * np.abs(x) ** 2)
        np.testing.assert_allclose(Y[:, 2], x * np.abs(x) ** 4)
        x1 = mat_delay(x, 1)
        np.testing.assert_allclose(Y[:, 3], x1)
        np.testing.assert_allclose(Y[:, 4], x1 * np.abs(x1) ** 2)

    def test_end_to_end_improves(self):
        """窄带三音下 odd_only 仍能有效线性化。"""
        fs = 1e6; N = 4096
        t = np.linspace(0, N / fs, N)
        x = (np.sin(2 * np.pi * 90e3 * t) + np.sin(2 * np.pi * 100e3 * t)
             + np.sin(2 * np.pi * 110e3 * t))
        x = x / np.max(x)
        y = distortion(x)
        x_pre = dpd_func(x, y, x, K=5, M=3, odd_only=True)
        out = distortion(x_pre)
        assert nmse(x, out) < 0.01


class TestDelayAlign:
    def test_estimate_delay_known(self):
        rng = np.random.default_rng(8)
        x = rng.standard_normal(512)
        y = mat_delay(x, 3)                     # y 滞后 x 3 个样本
        assert estimate_delay(x, y) == 3

    def test_align_recovers(self):
        rng = np.random.default_rng(9)
        x = rng.standard_normal(512)
        y = mat_delay(x, 3)
        ya = align_y_to_x(x, y)
        # 因果前移在尾部截断 d 个样本（工程中靠数据裁剪处理），其余应完全对齐
        np.testing.assert_allclose(ya[:-3], x[:-3], atol=1e-14)
        np.testing.assert_allclose(ya[-3:], 0.0)

    def test_shift_forward_backward(self):
        x = np.array([1.0, 2.0, 3.0, 4.0])
        np.testing.assert_allclose(shift(x, 1), [2.0, 3.0, 4.0, 0.0])
        np.testing.assert_allclose(shift(x, -1), [0.0, 1.0, 2.0, 3.0])


class TestAcpr:
    def test_clean_tone_high_acpr(self):
        """无失真单音：邻道几乎无功率，ACPR 应很大。"""
        fs = 1e6; N = 16384
        t = np.arange(N) / fs
        x = np.sin(2 * np.pi * 100e3 * t)
        f, P = plt_fft(x, fs, 1)
        a = acpr(f, P, (90e3, 110e3), (120e3, 140e3))
        assert a > 40

    def test_distortion_reduces_acpr(self):
        """失真信号的 ACPR 应低于线性信号。"""
        fs = 1e6; N = 16384
        t = np.linspace(0, N / fs, N)
        x = (np.sin(2 * np.pi * 90e3 * t) + np.sin(2 * np.pi * 100e3 * t)
             + np.sin(2 * np.pi * 110e3 * t))
        x = x / np.max(x)
        y = distortion(x)
        f, Pb = plt_fft(y, fs, 1)
        _, Pa = plt_fft(x, fs, 1)
        ab = acpr(f, Pb, (88e3, 112e3), (112e3, 132e3))
        aa = acpr(f, Pa, (88e3, 112e3), (112e3, 132e3))
        assert ab < aa

    def test_adjacent_band_not_double_counted(self):
        """回归：主带右边界与邻带左边界重合时不得双计（邻带左开）。"""
        fs = 1e6; N = 1024
        f = fs * np.arange(N // 2 + 1) / N     # 网格 df = fs/N
        P1 = np.full_like(f, -100.0)
        # 把边界 f_high+margin 恰好放在一个网格点上
        df = fs / N
        margin = 8 * df
        edge = 100e3 + margin
        k = int(round(edge / df))
        f[k] = edge                            # 确保网格上恰好存在该频率
        # 主带 (90k, edge)，邻带 (edge, 110k)：功率只由主带内的点贡献
        P1[np.abs(f - 95e3) < df / 2] = -10.0  # 主带内一个峰
        main = (90e3, edge)
        adj = (edge, edge + 10e3)
        a = acpr(f, P1, main, adj)
        # 若边界被双计，p_main 会把 -10dB 峰算两次 → ACPR 变小
        # 构造所有功率都在主带时，ACPR 应等于 10*log10(P_main/P_adj)
        p_main = np.sum(10.0 ** (P1[(f >= main[0]) & (f <= main[1])] / 10.0))
        p_adj = np.sum(10.0 ** (P1[(f > adj[0]) & (f <= adj[1])] / 10.0))
        np.testing.assert_allclose(a, 10 * np.log10(p_main / p_adj), rtol=1e-9)


class TestSimulation:
    def test_returned_keys(self):
        r = run_simulation(N=4096, gen_freqs=(111e3, 89e3))
        for k in ("sig_in", "PA_out", "PA_out2", "nmse0", "nmse_fit",
                  "nmse1", "nmse2", "acpr_before", "acpr_after", "P3"):
            assert k in r
        assert r["sig_in2"] is not None

    def test_consistent_with_main_detail_benchmark(self):
        """run_simulation 默认参数结果与 main_detail.py 基准一致。"""
        r = run_simulation()
        np.testing.assert_allclose(r["nmse0"], 0.21001508023211118, rtol=1e-12)
        np.testing.assert_allclose(r["nmse_fit"], 0.0029586606414997107, rtol=1e-9)
        np.testing.assert_allclose(r["nmse1"], 9.401892455186185e-06, rtol=1e-6)
        np.testing.assert_allclose(r["nmse2"], 9.130496458375846e-06, rtol=1e-6)

    def test_acpr_improves(self):
        r = run_simulation()
        assert r["acpr_after"] > r["acpr_before"] + 20
        assert r["acpr_after_gen"] > r["acpr_before_gen"] + 20

    def test_no_generalization(self):
        r = run_simulation(gen_freqs=None)
        assert r["sig_in2"] is None and "nmse2" not in r

    def test_odd_only_and_delay_align_runnable(self):
        r = run_simulation(odd_only=True, delay_align=True)
        assert r["nmse1"] < 1e-3
