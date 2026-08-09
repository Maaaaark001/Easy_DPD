/**
 * 浏览器端到端验证：用系统 Edge（playwright-core，不下载浏览器）以 file://
 * 方式打开页面（模拟用户"双击 index.html"场景），等待仿真完成，检查状态、
 * 指标文本、点击运行按钮与滑块交互，并截图。
 *
 * 运行（无需本地服务器，file:// 直接打开）：
 *   cd web && npm run test:browser
 */

import path from "node:path";
import { pathToFileURL } from "node:url";
import { chromium } from "playwright-core";

const EDGE = "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const URL = process.env.URL
  || pathToFileURL(path.join(import.meta.dirname, "..", "index.html")).href;

const browser = await chromium.launch({ executablePath: EDGE, headless: true });
const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });

const errors = [];
page.on("console", (msg) => {
  if (msg.type() === "error") errors.push(msg.text());
});
page.on("pageerror", (err) => errors.push(String(err)));

console.log("打开页面 (file://):", URL);
await page.goto(URL, { waitUntil: "load", timeout: 30000 });

// 等待初始仿真完成（计算约 4s）
async function waitDone(timeoutMs = 30000) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeoutMs) {
    const st = await page.textContent("#status");
    if (st.includes("完成") || st.includes("错误")) return st.trim();
    await page.waitForTimeout(400);
  }
  return (await page.textContent("#status")).trim();
}

const status = await waitDone();
await page.waitForTimeout(1000); // 等 ECharts 渲染

const readMetrics = async () => ({
  nmse0: (await page.textContent("#m-nmse0")).trim(),
  nmseFit: (await page.textContent("#m-nmseFit")).trim(),
  nmse1: (await page.textContent("#m-nmse1")).trim(),
  nmse2: (await page.textContent("#m-nmse2")).trim(),
  acprT: (await page.textContent("#m-acprT")).trim(),
  acprG: (await page.textContent("#m-acprG")).trim(),
});

console.log("初始状态:", status);
console.log("指标:", JSON.stringify(await readMetrics(), null, 2));
console.log("JS 错误数:", errors.length);
if (errors.length) errors.forEach((e) => console.log("  -", e));

const canvases = await page.locator("canvas").count();
console.log("canvas 数量:", canvases, "(期望 4 个 ECharts)");

// ---- 图表数据结构校验（value 轴 + 点对数据 + 频谱峰位置） ----
const chartCheck = await page.evaluate(() => {
  const spec = echarts.getInstanceByDom(document.getElementById("c-spec"));
  const amam = echarts.getInstanceByDom(document.getElementById("c-amam"));
  const specOpt = spec.getOption();
  const specData = specOpt.series[0].data;
  const isPair = Array.isArray(specData) && specData.length > 0 && Array.isArray(specData[0]);
  const peaks = specData
    .map((p, i) => ({ x: p[0], y: p[1], i }))
    .sort((a, b) => b.y - a.y)
    .slice(0, 3)
    .map((p) => p.x.toFixed(1));
  return {
    specAxisType: specOpt.xAxis[0].type,
    specXName: specOpt.xAxis[0].name,
    specYName: specOpt.yAxis[0].name,
    specXNameLoc: specOpt.xAxis[0].nameLocation,
    specTitleLeft: specOpt.title[0].left,
    isPair,
    specDataLen: specData.length,
    peaks,
    amamAxisType: amam.getOption().xAxis[0].type,
    amamSeriesLen: amam.getOption().series[0].data.length,
    // AM/AM 的 x（u）应唯一：避免 tooltip 在同一 x 匹配多个点导致重复行
    amamXUnique: (() => {
      const xs = amam.getOption().series[0].data.map((p) => p[0]);
      return new Set(xs).size === xs.length;
    })(),
  };
});
console.log("ECharts 校验:", JSON.stringify(chartCheck));

// ---- tooltip 验证：触发 showTip，提示框应每系列只出现一行 ----
const tooltipText = await page.evaluate(() => new Promise((resolve) => {
  const chart = echarts.getInstanceByDom(document.getElementById("c-amam"));
  chart.dispatchAction({ type: "showTip", seriesIndex: 0, dataIndex: 8000 });
  setTimeout(() => {
    const divs = document.querySelectorAll("#c-amam div");
    const tip = [...divs].find((d) => d.style.position === "absolute"
      && d.style.display !== "none" && d.textContent.trim().length > 0);
    resolve(tip ? tip.textContent.trim() : "");
  }, 300);
}));
const tipLines = tooltipText.split("\n").map((s) => s.trim()).filter(Boolean);
console.log("AM/AM tooltip 文本:", JSON.stringify(tooltipText));
// ECharts tooltip 用 div 渲染，textContent 无换行；按系列名计数（每个系列应只出现一次）
const cnt = (s) => tooltipText.split(s).length - 1;
const tooltipOk = cnt("linear") === 1 && cnt("PA out") === 1 && cnt("GMP") === 1;
console.log(`tooltip 系列计数: linear=${cnt("linear")} PA out=${cnt("PA out")} GMP=${cnt("GMP")}`);
const chartOk = chartCheck.specAxisType === "value"
  && chartCheck.specXName === "f / kHz"
  && chartCheck.specYName === "功率谱 / dB"
  && chartCheck.specXNameLoc === "middle"
  && chartCheck.specTitleLeft === "center"
  && chartCheck.isPair
  && chartCheck.specDataLen > 8000
  && chartCheck.amamAxisType === "value"
  && chartCheck.amamSeriesLen > 1000
  && chartCheck.amamXUnique
  && chartCheck.peaks.every((x) => [90, 100, 110].some((f) => Math.abs(+x - f) < 1));

// ---- 针对性验证 1：点击 [运行] 按钮 ----
await page.click("#run");
const stRun = await waitDone();
console.log("点击[运行]后状态:", stRun);

// ---- 针对性验证 2：改 K=7 触发防抖重算 ----
await page.locator("#K").evaluate((el) => {
  el.value = 7;
  el.dispatchEvent(new Event("input", { bubbles: true }));
});
await page.waitForTimeout(700); // 越过 400ms 防抖，让 run 真正开始
const stK = await waitDone();
const nmse1K = (await page.textContent("#m-nmse1")).trim();
console.log("K=7 重算后状态:", stK, "| nmse1:", nmse1K);

// ---- 实时更新开关验证 ----
// 1) 关闭实时更新后改参数：不应触发重算
await page.locator("#realtime").evaluate((el) => {
  el.checked = false;
  el.dispatchEvent(new Event("change", { bubbles: true }));
});
const nmse1Before = (await page.textContent("#m-nmse1")).trim();
await page.locator("#K").evaluate((el) => {
  el.value = 9;
  el.dispatchEvent(new Event("input", { bubbles: true }));
});
await page.waitForTimeout(1500); // 超过防抖 + 计算时间，若有自动重算此时早已完成
const stOff = (await page.textContent("#status")).trim();
const nmse1Off = (await page.textContent("#m-nmse1")).trim();
const realtimeOffOk = stOff.includes("完成")
  && nmse1Off === nmse1Before
  && !stOff.includes("9 阶"); // K=9 未生效说明没有重算
console.log("实时关闭后改 K=9:", stOff, "| nmse1 未变 =", nmse1Off === nmse1Before,
  "| 未重算 =", realtimeOffOk);

// 2) 重新开启实时更新：应立即用当前参数（K=9）重算一次
await page.locator("#realtime").evaluate((el) => {
  el.checked = true;
  el.dispatchEvent(new Event("change", { bubbles: true }));
});
await page.waitForTimeout(700); // 越过防抖
const stOn = await waitDone();
const nmse1On = (await page.textContent("#m-nmse1")).trim();
const realtimeOnOk = stOn.includes("9 阶") && nmse1On !== nmse1Before;
console.log("实时开启后:", stOn, "| nmse1:", nmse1On, "| 立即重算 =", realtimeOnOk);

await page.screenshot({ path: "test/web_dashboard.png", fullPage: false });
console.log("截图已保存: test/web_dashboard.png");

const ok = status.includes("完成")
  && stRun.includes("完成")
  && stK.includes("完成")
  && realtimeOffOk
  && realtimeOnOk
  && canvases >= 4
  && chartOk
  && tooltipOk
  && errors.length === 0;
console.log(ok ? "\n浏览器验证通过 ✅（含按钮点击与参数调节）" : "\n浏览器验证失败 ❌");
await browser.close();
process.exit(ok ? 0 : 1);
