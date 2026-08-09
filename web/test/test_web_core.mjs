/**
 * Node 数值验证：对比 Python 版基准（NMSE / ACPR / 频谱峰位置）。
 *
 * 运行：
 *   cd web
 *   npm install          # 安装 mathjs（算法验证用）
 *   npm test             # 或 node test/test_web_core.mjs
 *
 * 算法文件为 UMD（CJS 导出），这里用 createRequire 加载。
 *
 * Python 版基准（python/main_detail.py 无头模式输出）：
 *   nmse0=-6.78 dB  nmseFit=-25.29 dB  nmse1=-50.27 dB  nmse2=-50.40 dB
 *   ACPR train 22.31→67.39 dBc，gen 23.71→67.64 dBc
 */

import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const math = require("mathjs");
const core = require("../js/core.js");
const runSimulation = require("../js/simulation.js"); // UMD：module.exports 即函数

let failures = 0;

function check(name, got, expected, rel = 1e-2) {
  const ok = Math.abs(got - expected) <= rel * Math.abs(expected);
  if (!ok) failures++;
  console.log(
    `${ok ? "PASS" : "FAIL"}  ${name.padEnd(30)} got=${got.toExponential(4)}  expected≈${expected.toExponential(4)}`
  );
}

// ---- 默认仿真（与 Python 基准一致） ----
const t0 = performance.now();
const r = runSimulation({});
const t1 = performance.now();
console.log(`仿真耗时: ${(t1 - t0).toFixed(0)} ms (N=${r.params.N})`);

check("nmse0 (失真本底)", r.nmse0, 0.21001508023211118, 1e-2);
check("nmseFit (拟合)", r.nmseFit, 0.0029586606414997107, 5e-2);
check("nmse1 (补偿后)", r.nmse1, 9.401892455186185e-06, 5e-2);
check("nmse2 (泛化)", r.nmse2, 9.130496458375846e-06, 5e-2);

check("ACPR 训练前", r.acprBefore, 22.31, 0.2);
check("ACPR 训练后", r.acprAfter, 67.39, 0.2);
check("ACPR 泛化前", r.acprBeforeGen, 23.71, 0.2);
check("ACPR 泛化后", r.acprAfterGen, 67.64, 0.2);

// ---- 频谱峰位置 ----
function peaks(P1, f, thresh = -40, n = 6) {
  const idx = P1.map((v, i) => [i, v]).sort((a, b) => b[1] - a[1]).slice(0, n);
  return idx.filter(([, v]) => v > thresh).map(([i]) => f[i] / 1e3);
}
console.log("训练频谱峰 (kHz):", peaks(r.PBefore, r.f).join(", "));
console.log("泛化频谱峰 (kHz):", peaks(r.P3, r.f).join(", "));

// ---- 奇次项 / 时延对齐开关可运行 ----
const r2 = runSimulation({ oddOnly: true, delayAlign: true });
console.log(`oddOnly+delayAlign 仿真: nmse1=${r2.nmse1.toExponential(3)} (应 < 1e-3)`);
if (r2.nmse1 >= 1e-3) { failures++; console.log("FAIL  oddOnly+delayAlign 结果异常"); }

// ---- 无泛化 ----
const r3 = runSimulation({ genFreqs: null });
if (r3.nmse2 !== null || r3.sigIn2 !== null) {
  failures++;
  console.log("FAIL  genFreqs=null 时应跳过泛化");
} else {
  console.log("PASS  genFreqs=null 跳过泛化");
}

// ---- 单元级：saleh / matDelay / shift ----
{
  const x = core.saleh([0.5, 0.8, 1.0]);
  const amp = x.map((v) => math.abs(v));
  const expect = [1.5 * 0.5 / (1 + 0.5 * 0.25), 1.5 * 0.8 / (1 + 0.5 * 0.64), 1.5 / 1.5];
  const ok = amp.every((v, i) => Math.abs(v - expect[i]) < 1e-12);
  if (!ok) failures++; else console.log("PASS  saleh AM/AM 公式");
}
{
  const y = core.matDelay([1, 2, 3, 4, 5], 2);
  const ok = y.join(",") === "0,0,1,2,3";
  if (!ok) failures++; else console.log("PASS  matDelay 前向延迟");
}
{
  const y = core.shift([1, 2, 3, 4], 1);
  const ok = y.join(",") === "2,3,4,0";
  if (!ok) failures++; else console.log("PASS  shift 前移");
}

console.log(failures === 0 ? "\n全部通过 ✅" : `\n${failures} 项失败 ❌`);
process.exit(failures === 0 ? 0 : 1);
