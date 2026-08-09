/**
 * Easy_DPD 核心算法 —— 对应 python/easydpd/core.py 逐一移植。
 *
 * 采用 UMD 包装，支持两种加载方式（关键：浏览器双击 file:// 打开时
 * 普通 <script> 不受 CORS 限制，而 <script type="module"> 会被拦截）：
 *   - 浏览器：<script src="vendor/math.min.js"></script> 先加载 mathjs，
 *     再 <script src="js/core.js"></script>，得到全局 EasyDPD
 *   - Node  ：require("mathjs")，module.exports 导出命名空间
 *
 * FFT 为内置的迭代 radix-2 实现（N 需为 2 的幂，本工程 N 均为 2 的幂）。
 * 复数表示：信号数组元素为 mathjs Complex 对象（或 number）。
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory(require("mathjs"));
  } else {
    root.EasyDPD = factory(root.math);
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function (math) {
  "use strict";

  if (!math) {
    throw new Error("Easy_DPD 需要 mathjs：浏览器请先加载 vendor/math.min.js");
  }

  // -------------------------------------------------------------------------
  // FFT（迭代 radix-2，原地，未归一化；逆变换会除以 N）
  // -------------------------------------------------------------------------

  /** 原地 FFT（radix-2，sign=-1 正变换 / +1 逆变换），re/im 为同长数组。 */
  function fftRadix2(re, im, sign) {
    const n = re.length;
    for (let i = 1, j = 0; i < n; i++) {
      let bit = n >> 1;
      for (; j & bit; bit >>= 1) j ^= bit;
      j ^= bit;
      if (i < j) {
        [re[i], re[j]] = [re[j], re[i]];
        [im[i], im[j]] = [im[j], im[i]];
      }
    }
    for (let len = 2; len <= n; len <<= 1) {
      const ang = (sign * -2 * Math.PI) / len;
      const wRe = Math.cos(ang), wIm = Math.sin(ang);
      const half = len >> 1;
      for (let i = 0; i < n; i += len) {
        let curRe = 1, curIm = 0;
        for (let k = 0; k < half; k++) {
          const uRe = re[i + k], uIm = im[i + k];
          const oRe = re[i + k + half], oIm = im[i + k + half];
          const vRe = oRe * curRe - oIm * curIm;
          const vIm = oRe * curIm + oIm * curRe;
          re[i + k] = uRe + vRe; im[i + k] = uIm + vIm;
          re[i + k + half] = uRe - vRe; im[i + k + half] = uIm - vIm;
          const nRe = curRe * wRe - curIm * wIm;
          curIm = curRe * wIm + curIm * wRe;
          curRe = nRe;
        }
      }
    }
  }

  /** 正变换（未归一化），原地修改 re/im。 */
  function fftForward(re, im) {
    fftRadix2(re, im, -1);
  }

  /** 逆变换（除以 N），原地修改 re/im。 */
  function fftInverse(re, im) {
    const n = re.length;
    for (let i = 0; i < n; i++) im[i] = -im[i]; // 共轭
    fftRadix2(re, im, -1);
    for (let i = 0; i < n; i++) { im[i] = -im[i]; re[i] /= n; im[i] /= n; }
  }

  // -------------------------------------------------------------------------
  // 复数辅助（避免 mathjs 逐元素动态分派的性能开销）
  // -------------------------------------------------------------------------

  function toComplex(v) {
    return typeof v === "number" ? math.complex(v, 0) : v;
  }

  function cxRe(v) {
    return typeof v === "number" ? v : v.re;
  }

  function cxIm(v) {
    return typeof v === "number" ? 0 : v.im;
  }

  function cxAdd(a, b) {
    return math.complex(cxRe(a) + cxRe(b), cxIm(a) + cxIm(b));
  }

  /** 复数乘以实数标量 */
  function cxMulReal(c, r) {
    if (typeof c === "number") return c * r;
    return math.complex(c.re * r, c.im * r);
  }

  /** 复数模（number 或 Complex） */
  function cxAbs(v) {
    return typeof v === "number" ? Math.abs(v) : math.abs(v);
  }

  // -------------------------------------------------------------------------
  // PA 失真模型
  // -------------------------------------------------------------------------

  /** Saleh 无记忆失真模型（参数与原 MATLAB/Python 版一致）。 */
  function saleh(x) {
    const a1 = 1.5, b1 = 0.5, a2 = Math.PI / 3, b2 = 1;
    return x.map((v) => {
      const c = toComplex(v);
      const r = math.abs(c);
      const phiIn = math.arg(c);
      const aOut = (a1 * r) / (1 + b1 * r * r);
      const phiPm = (a2 * r * r) / (1 + b2 * r * r);
      const phi = phiIn + phiPm;
      return math.complex(aOut * Math.cos(phi), aOut * Math.sin(phi));
    });
  }

  /**
   * 带记忆 PA 失真：FIR 滤波（记忆效应，支持复数输入）+ Saleh（无记忆非线性）。
   * b = [0.7692 0.1538 0.0769]，取自《射频功放数字预失真线性化技术研究_詹鹏》。
   */
  function distortion(x) {
    const b = [0.7692, 0.1538, 0.0769];
    const n = x.length;
    const y = new Array(n);
    for (let i = 0; i < n; i++) {
      let acc = null;
      for (let j = 0; j < b.length; j++) {
        if (i >= j) {
          const t = cxMulReal(toComplex(x[i - j]), b[j]);
          acc = acc === null ? t : cxAdd(acc, t);
        }
      }
      y[i] = acc;
    }
    return saleh(y);
  }

  // -------------------------------------------------------------------------
  // 延迟与对齐
  // -------------------------------------------------------------------------

  /** 因果前向延迟：y[n] = x[n-d]（n>=d），前 d 个为 0。与 MATLAB circshift+置零 等价。 */
  function matDelay(x, d) {
    if (d < 0) throw new Error(`matDelay 要求非负延迟，实际 d=${d}（前移请用 shift）`);
    if (d === 0) return x.slice();
    const n = x.length;
    const out = new Array(n).fill(0);
    for (let i = d; i < n; i++) out[i] = x[i - d];
    return out;
  }

  /** 因果移位：s>0 前移（y[n]=x[n+s]，尾部补零）；s<0 后移（同 matDelay）。 */
  function shift(x, s) {
    if (s === 0) return x.slice();
    const n = x.length;
    if (s < 0) return matDelay(x, -s);
    const out = new Array(n).fill(0);
    for (let i = 0; i < n - s; i++) out[i] = x[i + s];
    return out;
  }

  /**
   * 估计 y 相对 x 的延迟（样本数）。返回 d>0 表示 y 滞后 x 达 d 个样本。
   * 用 FFT 实现线性互相关并取峰值（与工程相关法时延估计一致）。
   */
  function estimateDelay(x, y) {
    const n = x.length;
    let m = 1;
    while (m < 2 * n) m <<= 1; // 线性相关 full 长度 2n-1，zero-pad 到 2 的幂

    const reX = new Float64Array(m), imX = new Float64Array(m);
    const reY = new Float64Array(m), imY = new Float64Array(m);
    for (let i = 0; i < n; i++) {
      reX[i] = cxRe(x[i]); imX[i] = cxIm(x[i]);
      reY[i] = cxRe(y[i]); imY[i] = cxIm(y[i]);
    }
    fftForward(reX, imX);
    fftForward(reY, imY);

    // C = Yf * conj(Xf)
    const reC = new Float64Array(m), imC = new Float64Array(m);
    for (let k = 0; k < m; k++) {
      reC[k] = reY[k] * reX[k] + imY[k] * imX[k];
      imC[k] = imY[k] * reX[k] - reY[k] * imX[k];
    }
    fftInverse(reC, imC); // 逆变换自带 /m 归一化

    // zero-padding 循环相关的索引语义：corr[k]（0<=k<n）直接等于"y 滞后 k"的
    // 线性相关；k>=n 的尾部对应负滞后（y 提前 |k-m|），故 lag = k-m。
    let best = 0, bestVal = -1;
    for (let i = 0; i < m; i++) {
      const mag = Math.hypot(reC[i], imC[i]);
      if (mag > bestVal) { bestVal = mag; best = i; }
    }
    return best >= n ? best - m : best;
  }

  /** 把 y 对齐到 x（消除 y 相对 x 的延迟），返回对齐后的 y。 */
  function alignYToX(x, y) {
    const d = estimateDelay(x, y);
    return d === 0 ? y.slice() : shift(y, d);
  }

  // -------------------------------------------------------------------------
  // 记忆多项式基函数
  // -------------------------------------------------------------------------

  /**
   * 构造记忆多项式基函数矩阵 Y（N×P，嵌套数组），列 = x[n-m]·|x[n-m]|^k。
   * oddOnly=true 时只保留奇次阶（k=0,2,4,...），窄带 DPD 标准做法。
   */
  function mpModel(x, K, M, oddOnly) {
    const N = x.length;
    const ks = [];
    for (let k = 0; k <= K; k++) if (!oddOnly || k % 2 === 0) ks.push(k);

    const cols = [];
    for (let m = 0; m <= M; m++) {
      const xm = matDelay(x, m);
      const absxm = xm.map((v) => cxAbs(v));
      let term = xm.slice(); // k=0
      for (let k = 0; k <= K; k++) {
        if (ks.includes(k)) cols.push(term);
        term = term.map((v, i) => cxMulReal(v, absxm[i])); // 递推 x|x|^(k+1)
      }
    }

    const P = cols.length;
    const Y = Array.from({ length: N }, () => new Array(P));
    for (let j = 0; j < P; j++) {
      const col = cols[j];
      for (let i = 0; i < N; i++) Y[i][j] = col[i];
    }
    return Y;
  }

  // -------------------------------------------------------------------------
  // DPD 系数拟合（ILA 间接学习架构）
  // -------------------------------------------------------------------------

  /**
   * DPD 系数核心算法（对应 DPD_Func.m / dpd_func）。
   * w = pinv(Yh·Y)·(Yh·x)，Yh 为 Y 的共轭转置；x_pre = U·w。
   * 用正规方程 + pinv（SVD），与 Python 版 lstsq 数学等价。
   */
  function dpdFunc(x, y, u, K, M, oddOnly, delayAlign) {
    const yFit = delayAlign ? alignYToX(x, y) : y;
    const U = mpModel(u, K, M, oddOnly);
    const Y = mpModel(yFit, K, M, oddOnly);

    const Yh = math.conj(math.transpose(Y)); // 共轭转置
    const G = math.multiply(Yh, Y);          // P×P
    const w = math.multiply(math.pinv(G), math.multiply(Yh, x));
    return math.multiply(U, w);              // N 维数组
  }

  // -------------------------------------------------------------------------
  // 评估与频谱
  // -------------------------------------------------------------------------

  /** 归一化均方误差 NMSE = sum(|x-y|^2) / sum(|x|^2)（线性值，越小越好）。 */
  function nmse(x, y) {
    const n = x.length;
    let dE = 0, dM = 0;
    for (let i = 0; i < n; i++) {
      const xr = cxRe(x[i]), xi = cxIm(x[i]);
      const yr = cxRe(y[i]), yi = cxIm(y[i]);
      dE += (xr - yr) ** 2 + (xi - yi) ** 2;
      dM += xr * xr + xi * xi;
    }
    return dE / dM;
  }

  /**
   * 加窗 FFT 单边幅度谱（dB），对应 plt_fft.m / plt_fft。
   * 返回 { f, P1 }：频率轴与功率谱（fl=1 归一化到峰值，否则绝对 dB）。
   * 注意：单边谱要求 L 为偶数。
   */
  function pltFft(x, fs, fl) {
    if (fl === undefined) fl = 1;
    const L = x.length;
    const re = new Float64Array(L);
    for (let n = 0; n < L; n++) {
      const w = 0.5 * (1 - Math.cos((2 * Math.PI * n) / (L - 1))); // Hann（对称）
      re[n] = cxRe(x[n]) * w;
    }
    const im = new Float64Array(L);
    fftForward(re, im); // 实数输入（虚部 0）直接做复数 FFT

    const P2 = new Array(L);
    for (let k = 0; k < L; k++) P2[k] = Math.hypot(re[k], im[k]) / L;
    const P1 = P2.slice(0, L / 2 + 1);
    for (let k = 1; k < L / 2; k++) P1[k] *= 2;

    const f = Array.from({ length: L / 2 + 1 }, (_, k) => (fs * k) / L);
    let out;
    if (fl === 1) {
      const peak = Math.max(...P1);
      out = P1.map((v) => 20 * Math.log10(Math.max(v / peak, 1e-300)));
    } else {
      out = P1.map((v) => 20 * Math.log10(Math.max(v, 1e-300)));
    }
    return { f, P1: out };
  }

  /** 邻道功率比 ACPR = 主信道功率 / 邻信道功率（dBc）。邻带左开避免与主带重叠双计。 */
  function acpr(f, P1, mainBand, adjBand) {
    const ml = mainBand[0], mh = mainBand[1];
    const al = adjBand[0], ah = adjBand[1];
    let pMain = 0, pAdj = 0;
    for (let k = 0; k < f.length; k++) {
      if (f[k] >= ml && f[k] <= mh) pMain += 10 ** (P1[k] / 10);
      else if (f[k] > al && f[k] <= ah) pAdj += 10 ** (P1[k] / 10);
    }
    if (pMain <= 0 || pAdj <= 0) return Infinity;
    return 10 * Math.log10(pMain / pAdj);
  }

  // 导出（浏览器挂到全局 EasyDPD，Node 为 module.exports）
  return {
    saleh, distortion,
    matDelay, shift, estimateDelay, alignYToX,
    mpModel, dpdFunc,
    nmse, pltFft, acpr,
  };
});
