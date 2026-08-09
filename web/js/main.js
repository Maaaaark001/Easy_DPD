/**
 * Easy_DPD 浏览器版 —— UI 逻辑与 ECharts 渲染。
 * 普通 <script>（非 module）：依赖 vendor/math.min.js、vendor/echarts.min.js、
 * js/core.js、js/simulation.js 依次加载后产生的全局 window.EasyDPD。
 */
(function () {
  "use strict";

  const { runSimulation } = window.EasyDPD;

  // -------------------------------------------------------------------------
  // ECharts 图表
  // -------------------------------------------------------------------------

  const charts = {
    spec: null, amam: null, ampm: null, gen: null,
  };

  const SPEC_COLOR = { before: "#8fa0bd", after: "#3ddc84" };

  // 坐标轴统一样式（各图覆盖 xAxis/yAxis 时需显式带上 name）
  // nameLocation=middle：单位名显示在轴中间，避免“看不到单位”
  const AXIS_STYLE = {
    nameLocation: "middle",
    nameGap: 32,
    nameTextStyle: { color: "#8fa0bd", fontWeight: "bold" },
    axisLine: { lineStyle: { color: "#2a3550" } },
    axisLabel: { color: "#8fa0bd", fontSize: 10 },
  };

  function baseOption(title, xName, yName) {
    return {
      title: { text: title, left: "center", top: 6, textStyle: { fontSize: 13, color: "#dbe4f5" } },
      tooltip: { trigger: "axis", backgroundColor: "#161d2e", borderColor: "#2a3550", textStyle: { color: "#dbe4f5" } },
      legend: { bottom: 0, left: "center", textStyle: { color: "#8fa0bd" } },
      grid: { left: 62, right: 20, top: 40, bottom: 54 },
      xAxis: { type: "value", name: xName, ...AXIS_STYLE },
      yAxis: { type: "value", name: yName, ...AXIS_STYLE, splitLine: { lineStyle: { color: "#1b2436" } } },
      series: [],
    };
  }

  function initCharts() {
    charts.spec = echarts.init(document.getElementById("c-spec"), "dark");
    charts.amam = echarts.init(document.getElementById("c-amam"), "dark");
    charts.ampm = echarts.init(document.getElementById("c-ampm"), "dark");
    charts.gen = echarts.init(document.getElementById("c-gen"), "dark");
    window.addEventListener("resize", () => Object.values(charts).forEach((c) => c.resize()));
  }

  function updateCharts(r) {
    // 数据点对辅助：value 轴必须用 [x, y] 点对（一维数组会被当作"索引→值"）
    const specData = (P) => r.f.map((f, i) => [+(f / 1e3).toFixed(3), +P[i].toFixed(2)]);
    const curveData = (xArr, yArr) => xArr.map((x, i) => [+x.toFixed(6), +yArr[i].toFixed(6)]);

    // 1. 频谱对比（DPD 前/后）
    charts.spec.setOption({
      ...baseOption("频谱对比（训练信号）", "f / kHz", "功率谱 / dB"),
      legend: { data: ["DPD 前", "DPD 后"], top: 6, right: 10, textStyle: { color: "#8fa0bd" } },
      xAxis: { type: "value", name: "f / kHz", ...AXIS_STYLE, min: 0, max: 200 },
      yAxis: { type: "value", name: "功率谱 / dB", ...AXIS_STYLE, min: -90, max: 5 },
      series: [
        { name: "DPD 前", type: "line", showSymbol: false, data: specData(r.PBefore), lineStyle: { width: 1.2, color: SPEC_COLOR.before }, itemStyle: { color: SPEC_COLOR.before } },
        { name: "DPD 后", type: "line", showSymbol: false, data: specData(r.PAfter), lineStyle: { width: 1.2, color: SPEC_COLOR.after }, itemStyle: { color: SPEC_COLOR.after } },
      ],
    });

    // 2. AM/AM：x=u，y=幅度
    charts.amam.setOption({
      ...baseOption("AM/AM", "sig in", "PA out"),
      legend: { data: ["linear", "PA out", "GMP"], top: 6, right: 10, textStyle: { color: "#8fa0bd" } },
      xAxis: { type: "value", name: "sig in", ...AXIS_STYLE, min: 0, max: 1 },
      yAxis: { type: "value", name: "PA out", ...AXIS_STYLE },
      series: [
        { name: "linear", type: "line", showSymbol: false, data: curveData(r.u, r.u), lineStyle: { width: 1, color: "#8fa0bd" } },
        { name: "PA out", type: "line", showSymbol: false, data: curveData(r.u, r.PAOutU.map((v) => math.abs(v))), lineStyle: { width: 1.4, color: "#4da3ff" } },
        { name: "GMP", type: "line", showSymbol: false, data: curveData(r.u, r.yDis.map((v) => math.abs(v))), lineStyle: { width: 1.4, type: "dashed", color: "#ffb84d" } },
      ],
    });

    // 3. AM/PM：x=u，y=相位
    charts.ampm.setOption({
      ...baseOption("AM/PM", "sig in", "phase / rad"),
      legend: { data: ["PA out", "GMP"], top: 6, right: 10, textStyle: { color: "#8fa0bd" } },
      xAxis: { type: "value", name: "sig in", ...AXIS_STYLE, min: 0, max: 1 },
      yAxis: { type: "value", name: "phase / rad", ...AXIS_STYLE },
      series: [
        { name: "PA out", type: "line", showSymbol: false, data: curveData(r.u, r.PAOutU.map((v) => math.arg(v))), lineStyle: { width: 1.4, color: "#4da3ff" } },
        { name: "GMP", type: "line", showSymbol: false, data: curveData(r.u, r.yDis.map((v) => math.arg(v))), lineStyle: { width: 1.4, type: "dashed", color: "#ffb84d" } },
      ],
    });

    // 4. 泛化频谱
    if (r.P3) {
      charts.gen.setOption({
        ...baseOption("泛化测试频谱（新频点）", "f / kHz", "功率谱 / dB"),
        xAxis: { type: "value", name: "f / kHz", ...AXIS_STYLE, min: 0, max: 200 },
        yAxis: { type: "value", name: "功率谱 / dB", ...AXIS_STYLE, min: -90, max: 5 },
        series: [
          { name: "泛化", type: "line", showSymbol: false, data: specData(r.P3), lineStyle: { width: 1.2, color: "#c678dd" }, itemStyle: { color: "#c678dd" } },
        ],
      });
    } else {
      charts.gen.setOption({
        ...baseOption("泛化测试频谱", "f / kHz", "功率谱 / dB"),
        xAxis: { type: "value", name: "f / kHz", ...AXIS_STYLE, min: 0, max: 200 },
        series: [{ type: "line", data: [] }],
        graphic: [{ type: "text", left: "center", top: "middle", style: { text: "泛化测试未启用", fill: "#8fa0bd" } }],
      });
    }
  }

  function updateMetrics(r) {
    const db = (x) => `${(10 * Math.log10(x)).toFixed(2)} dB`;
    const set = (id, v) => { document.getElementById(id).textContent = v; };
    set("m-nmse0", `${r.nmse0.toExponential(3)} (${db(r.nmse0)})`);
    set("m-nmseFit", `${r.nmseFit.toExponential(3)} (${db(r.nmseFit)})`);
    set("m-nmse1", `${r.nmse1.toExponential(3)} (${db(r.nmse1)})`);
    set("m-nmse2", r.nmse2 === null ? "未启用" : `${r.nmse2.toExponential(3)} (${db(r.nmse2)})`);
    const fmt = (x) => (x === null || !isFinite(x) ? "--" : `${x.toFixed(1)} dBc`);
    set("m-acprT", `${fmt(r.acprBefore)} → ${fmt(r.acprAfter)}`);
    set("m-acprG", `${fmt(r.acprBeforeGen)} → ${fmt(r.acprAfterGen)}`);
  }

  // -------------------------------------------------------------------------
  // 参数与交互
  // -------------------------------------------------------------------------

  const DEFAULTS = { f1: 90, f2: 100, f3: 110, f4: 89, f5: 111, K: 5, M: 3, N: "16384", gen: true, oddOnly: false, delayAlign: false, realtime: true };

  const $ = (id) => document.getElementById(id);

  function bindRange(id, fmt) {
    const el = $(id), val = $(`${id}v`);
    const show = () => { val.textContent = fmt(+el.value); };
    el.addEventListener("input", () => { show(); scheduleRun(); });
    show();
  }

  function readParams() {
    const get = (id) => +$(id).value;
    return {
      fs: 1e6,
      N: +$("N").value,
      freqs: [get("f1"), get("f2"), get("f3")].map((f) => f * 1e3),
      genFreqs: $("gen").checked ? [get("f4"), get("f5")].map((f) => f * 1e3) : null,
      K: get("K"),
      M: get("M"),
      oddOnly: $("oddOnly").checked,
      delayAlign: $("delayAlign").checked,
    };
  }

  function setStatus(text, cls) {
    const el = $("status");
    el.textContent = text;
    el.className = "status" + (cls ? ` ${cls}` : "");
  }

  let timer = null;
  function scheduleRun() {
    clearTimeout(timer);
    if (!$("realtime").checked) return; // 实时更新关闭：调参数不自动重算，仅点 [运行]
    timer = setTimeout(run, 400);       // 防抖
  }

  function run() {
    setStatus("计算中…（约数秒）", "busy");
    // 让状态先渲染，再同步计算
    setTimeout(() => {
      try {
        const r = runSimulation(readParams());
        updateCharts(r);
        updateMetrics(r);
        setStatus(`完成 · N=${r.params.N} · ${r.params.K} 阶 / 记忆 ${r.params.M}`, "done");
      } catch (e) {
        console.error(e);
        setStatus(`错误：${e.message}`, "err");
      }
    }, 30);
  }

  function restoreDefaults() {
    for (const [key, val] of Object.entries(DEFAULTS)) {
      if (key === "gen" || key === "oddOnly" || key === "delayAlign") {
        $(key).checked = val;
      } else if (key === "K" || key === "M") {
        $(key).value = val;
        $(`${key}v`).textContent = val;
      } else if (key === "N") {
        $(key).value = val;
      } else {
        $(key).value = val;
        $(`${key}v`).textContent = `${val} kHz`;
      }
    }
    run();
  }

  function init() {
    initCharts();
    bindRange("f1", (v) => `${v} kHz`);
    bindRange("f2", (v) => `${v} kHz`);
    bindRange("f3", (v) => `${v} kHz`);
    bindRange("f4", (v) => `${v} kHz`);
    bindRange("f5", (v) => `${v} kHz`);
    bindRange("K", (v) => v);
    bindRange("M", (v) => v);

    for (const id of ["gen", "oddOnly", "delayAlign", "N"]) {
      $(id).addEventListener("change", scheduleRun);
    }
    // 实时更新开关本身不触发重算；重新开启时用当前参数立即算一次
    $("realtime").addEventListener("change", () => {
      if ($("realtime").checked) scheduleRun();
    });
    $("run").addEventListener("click", run);
    $("reset").addEventListener("click", restoreDefaults);

    run(); // 初始仿真
  }

  init();
})();
