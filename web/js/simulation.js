/**
 * 端到端仿真封装 —— 对应 python/easydpd/simulation.py 的 run_simulation。
 * UMD 包装：浏览器挂到全局 EasyDPD.runSimulation，Node 为 module.exports。
 */

(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory(require("./core.js"));
  } else {
    root.EasyDPD = root.EasyDPD || {};
    root.EasyDPD.runSimulation = factory(root.EasyDPD);
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function (core) {
  "use strict";

  const { acpr, distortion, dpdFunc, nmse, pltFft } = core;

  /** 按信号频点动态定义主信道与上邻道（邻道起点外推 8 个频率分辨率 bin，避开窗泄漏）。 */
  function bands(freqs, fs, N) {
    const fLow = Math.min(...freqs);
    const fHigh = Math.max(...freqs);
    const df = fs / N;
    const margin = 8 * df;
    const bw = fHigh - fLow;
    return { main: [fLow - margin, fHigh + margin], adj: [fHigh + margin, fHigh + margin + bw] };
  }

  /**
   * 运行完整 DPD 仿真，返回与 Python 版相同结构的指标与信号。
   * 参数：{ fs, N, freqs, genFreqs(或 null), K, M, oddOnly, delayAlign }
   */
  function runSimulation(p) {
    p = p || {};
    const fs = p.fs ?? 1e6;
    const N = p.N ?? 1024 * 16;
    const freqs = p.freqs ?? [90e3, 100e3, 110e3];
    // 注意：genFreqs 传 null 表示跳过泛化，不能用 ??（null ?? 默认值会取默认值）
    const genFreqs = p.genFreqs === undefined ? [111e3, 89e3] : p.genFreqs;
    const K = p.K ?? 5;
    const M = p.M ?? 3;
    const oddOnly = p.oddOnly ?? false;
    const delayAlign = p.delayAlign ?? false;

    // 1. 训练信号（归一化）
    const t = Array.from({ length: N }, (_, i) => (i * (N / fs)) / (N - 1)); // linspace(0, N/fs, N)
    const sigIn = t.map((ti) => freqs.reduce((a, f) => a + Math.sin(2 * Math.PI * f * ti), 0));
    const maxIn = Math.max(...sigIn.map(Math.abs));
    sigIn.forEach((v, i) => { sigIn[i] = v / maxIn; });

    // 2. PA 失真模型与 AM/AM、AM/PM 观察
    const u = Array.from({ length: N }, (_, i) => i / (N - 1)); // linspace(0,1,N)
    const PAOutU = distortion(u);
    const PAOut = distortion(sigIn);

    // 3. 拟合测试（逆模型拟合，x 与 y 反过来）
    const yDis = dpdFunc(PAOut, sigIn, u, K, M, oddOnly, delayAlign);

    // 4. 逆模型构建预失真（训练信号）
    const XPre = dpdFunc(sigIn, PAOut, sigIn, K, M, oddOnly, delayAlign);
    const PAOut2 = distortion(XPre);

    // 5. 泛化测试
    let sigIn2 = null, PAOut3 = null, P3 = null;
    let acprBeforeGen = null, acprAfterGen = null;
    if (genFreqs) {
      sigIn2 = t.map((ti) => genFreqs.reduce((a, f) => a + Math.sin(2 * Math.PI * f * ti), 0));
      const max2 = Math.max(...sigIn2.map(Math.abs));
      sigIn2.forEach((v, i) => { sigIn2[i] = v / max2; });
      const XPre2 = dpdFunc(sigIn, PAOut, sigIn2, K, M, oddOnly, delayAlign);
      PAOut3 = distortion(XPre2);
      const b2 = bands(genFreqs, fs, N);
      const fg = pltFft(distortion(sigIn2), fs, 1);
      P3 = pltFft(PAOut3, fs, 1).P1;
      acprBeforeGen = acpr(fg.f, fg.P1, b2.main, b2.adj);
      acprAfterGen = acpr(fg.f, P3, b2.main, b2.adj);
    }

    // 6. 指标
    const { f, P1: PBefore } = pltFft(PAOut, fs, 1);
    const { P1: PAfter } = pltFft(PAOut2, fs, 1);
    const b = bands(freqs, fs, N);

    return {
      sigIn, PAOut, PAOut2, u, PAOutU, yDis, sigIn2, PAOut3,
      f, PBefore, PAfter, P3,
      nmse0: nmse(u, PAOutU),
      nmseFit: nmse(PAOutU, yDis),
      nmse1: nmse(sigIn, PAOut2),
      nmse2: genFreqs ? nmse(sigIn2, PAOut3) : null,
      acprBefore: acpr(f, PBefore, b.main, b.adj),
      acprAfter: acpr(f, PAfter, b.main, b.adj),
      acprBeforeGen, acprAfterGen,
      params: { fs, N, freqs, genFreqs, K, M, oddOnly, delayAlign },
    };
  }

  return runSimulation;
});
