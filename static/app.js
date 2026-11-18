const form = document.querySelector("#plot-form");
const mode = document.querySelector("#mode");
const expression = document.querySelector("#expression");
const status = document.querySelector("#status");
const image = document.querySelector("#plot-image");
const placeholder = document.querySelector("#placeholder");
const button = document.querySelector("#submit-button");
const axisButtons = document.querySelectorAll(".axis-controls button");
const intervalGroups = document.querySelectorAll(".variable-interval");
const curveEditor = document.querySelector("#curve-function-editor");
const curveFunctionList = document.querySelector("#curve-function-list");
const addFunctionButton = document.querySelector("#add-function-button");
const axisIntervalControls = document.querySelector("#axis-interval-controls");
const curveColors = ["#2563eb", "#dc2626", "#16a34a", "#9333ea"];
const examples = {
  curve: String.raw`\sin(x)`,
  surface: String.raw`\sin(x)+\cos(y)`,
  implicit: String.raw`x^2+y^2+z^2=9`,
};
let ranges = defaultRanges(mode.value);
let autoYScale = mode.value === "curve";

function defaultRanges(plotMode) {
  const extent = plotMode === "curve" ? 10 : 5;
  return {
    x: [-extent, extent],
    y: plotMode === "curve" ? null : [-5, 5],
    z: [-5, 5],
  };
}

function updateIntervalInputs() {
  const visibleVariables = mode.value === "curve"
    ? ["x"]
    : mode.value === "surface"
      ? ["x", "y"]
      : ["x", "y", "z"];

  intervalGroups.forEach((group) => {
    const variable = group.dataset.variable;
    group.hidden = variable === "x"
      ? mode.value === "curve"
      : !visibleVariables.includes(variable);
    if (!group.hidden) {
      document.querySelector(`#${variable}-min`).value = ranges[variable][0];
      document.querySelector(`#${variable}-max`).value = ranges[variable][1];
    }
  });
  curveEditor.hidden = mode.value !== "curve";
  axisIntervalControls.hidden = mode.value === "curve";
  document.querySelectorAll(".expression-control").forEach((control) => {
    control.hidden = mode.value === "curve";
  });
}

function readInterval(variable) {
  const lowerInput = document.querySelector(`#${variable}-min`);
  const upperInput = document.querySelector(`#${variable}-max`);
  const bounds = [lowerInput.valueAsNumber, upperInput.valueAsNumber];
  if (
    bounds.some((bound) => !Number.isFinite(bound)) ||
    bounds[0] >= bounds[1]
  ) {
    throw new Error(`${variable} 区间必须是有效数字，且下限小于上限。`);
  }
  return bounds;
}

function addCurveFunction(value = "", functionRange = null) {
  const index = curveFunctionList.children.length;
  const row = document.createElement("div");
  row.className = "curve-function-row";
  row.style.setProperty("--function-color", curveColors[index]);

  const heading = document.createElement("div");
  heading.className = "curve-function-heading";
  const title = document.createElement("span");
  title.textContent = `函数 ${index + 1}`;
  const removeButton = document.createElement("button");
  removeButton.className = "remove-function-button";
  removeButton.type = "button";
  removeButton.textContent = "移除";
  removeButton.setAttribute("aria-label", `移除函数 ${index + 1}`);
  removeButton.disabled = index === 0;
  removeButton.addEventListener("click", () => {
    row.remove();
    refreshCurveFunctionRows();
  });
  heading.append(title, removeButton);

  const formulaLabel = document.createElement("label");
  formulaLabel.textContent = "LaTeX 公式";
  const formula = document.createElement("textarea");
  formula.rows = 2;
  formula.maxLength = 200;
  formula.spellcheck = false;
  formula.value = value;
  formula.setAttribute("aria-label", `函数 ${index + 1} 的 LaTeX 公式`);
  formulaLabel.append(formula);

  const interval = document.createElement("div");
  interval.className = "function-interval";
  const intervalLabel = document.createElement("span");
  intervalLabel.textContent = "x 区间（可选）";
  const lower = document.createElement("input");
  lower.type = "number";
  lower.step = "any";
  lower.placeholder = "默认下限";
  lower.setAttribute("aria-label", `函数 ${index + 1} 的 x 区间下限`);
  const separator = document.createElement("span");
  separator.textContent = "到";
  const upper = document.createElement("input");
  upper.type = "number";
  upper.step = "any";
  upper.placeholder = "默认上限";
  upper.setAttribute("aria-label", `函数 ${index + 1} 的 x 区间上限`);
  if (functionRange) {
    lower.value = functionRange[0];
    upper.value = functionRange[1];
  }
  interval.append(intervalLabel, lower, separator, upper);
  row.append(heading, formulaLabel, interval);
  curveFunctionList.append(row);
  refreshCurveFunctionRows();
}

function refreshCurveFunctionRows() {
  Array.from(curveFunctionList.children).forEach((row, index) => {
    row.style.setProperty("--function-color", curveColors[index]);
    row.querySelector(".curve-function-heading span").textContent = `函数 ${index + 1}`;
    const removeButton = row.querySelector(".remove-function-button");
    removeButton.disabled = index === 0;
    removeButton.setAttribute("aria-label", `移除函数 ${index + 1}`);
    const formula = row.querySelector("textarea");
    formula.setAttribute("aria-label", `函数 ${index + 1} 的 LaTeX 公式`);
    row.querySelectorAll("input")[0].setAttribute("aria-label", `函数 ${index + 1} 的 x 区间下限`);
    row.querySelectorAll("input")[1].setAttribute("aria-label", `函数 ${index + 1} 的 x 区间上限`);
  });
  addFunctionButton.disabled = curveFunctionList.children.length >= 4;
  addFunctionButton.textContent = `添加函数 (${curveFunctionList.children.length}/4)`;
}

function readCurveFunctions() {
  return Array.from(curveFunctionList.children).map((row, index) => {
    const formula = row.querySelector("textarea").value.trim();
    if (!formula) {
      throw new Error(`请输入函数 ${index + 1} 的公式。`);
    }
    const inputs = row.querySelectorAll("input");
    const lower = inputs[0].value;
    const upper = inputs[1].value;
    if (Boolean(lower) !== Boolean(upper)) {
      throw new Error(`函数 ${index + 1} 的 x 区间请同时填写上下限，或都留空。`);
    }
    let functionRange = null;
    if (lower && upper) {
      functionRange = [Number(lower), Number(upper)];
      if (
        functionRange.some((bound) => !Number.isFinite(bound)) ||
        functionRange[0] >= functionRange[1]
      ) {
        throw new Error(`函数 ${index + 1} 的 x 区间必须是有效数字，且下限小于上限。`);
      }
    }
    return { expression: formula, x_range: functionRange };
  });
}

function rangeFromHeader(response, axis, fallback) {
  const value = response.headers.get(`X-Plot-${axis.toUpperCase()}-Range`);
  const bounds = value?.split(",").map(Number);
  return bounds?.length === 2 && bounds.every(Number.isFinite) ? bounds : fallback;
}

mode.addEventListener("change", () => {
  expression.value = examples[mode.value];
  ranges = defaultRanges(mode.value);
  autoYScale = mode.value === "curve";
  updateIntervalInputs();
  image.hidden = true;
  placeholder.hidden = false;
  axisButtons.forEach((axisButton) => {
    axisButton.disabled = true;
  });
  status.textContent = "";
});

expression.value = examples[mode.value];
addCurveFunction(examples.curve);
updateIntervalInputs();

async function drawPlot(preserveXView = false) {
  let curveFunctions = null;
  try {
    if (mode.value === "curve") {
      curveFunctions = readCurveFunctions();
      if (!preserveXView) {
        const functionRanges = curveFunctions.map(
          (item) => item.x_range || [-10, 10],
        );
        ranges.x = [
          Math.min(...functionRanges.map((item) => item[0])),
          Math.max(...functionRanges.map((item) => item[1])),
        ];
      }
    } else {
      ranges.x = readInterval("x");
      ranges.y = readInterval("y");
      if (mode.value === "implicit") {
        ranges.z = readInterval("z");
      }
    }
  } catch (error) {
    status.textContent = error.message;
    return;
  }
  if (mode.value === "curve" && autoYScale) {
    ranges.y = null;
  }
  button.disabled = true;
  axisButtons.forEach((axisButton) => {
    axisButton.disabled = true;
  });
  status.textContent = "正在计算并绘图…";
  image.hidden = true;

  try {
    const response = await fetch("/plot", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        mode: mode.value,
        ...(mode.value === "curve"
          ? { functions: curveFunctions }
          : { expression: expression.value }),
        x_range: ranges.x,
        y_range: ranges.y,
        z_range: ranges.z,
      }),
    });
    if (!response.ok) {
      const result = await response.json();
      throw new Error(result.error || "绘图失败，请重试。");
    }
    ranges.x = rangeFromHeader(response, "x", ranges.x);
    ranges.y = rangeFromHeader(response, "y", ranges.y);
    ranges.z = rangeFromHeader(response, "z", ranges.z);
    updateIntervalInputs();
    const plotUrl = URL.createObjectURL(await response.blob());
    const previousUrl = image.dataset.url;
    image.src = plotUrl;
    image.dataset.url = plotUrl;
    if (previousUrl) URL.revokeObjectURL(previousUrl);
    image.hidden = false;
    placeholder.hidden = true;
    axisButtons.forEach((axisButton) => {
      axisButton.disabled = false;
    });
    status.textContent = "绘图完成";
  } catch (error) {
    status.textContent = error.message;
    placeholder.hidden = false;
  } finally {
    button.disabled = false;
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  drawPlot();
});

axisButtons.forEach((axisButton) => {
  axisButton.addEventListener("click", () => {
    const axis = axisButton.dataset.axis;
    const scale = axisButton.dataset.zoom === "in" ? 0.8 : 1.25;
    const bounds = ranges[axis];
    const center = (bounds[0] + bounds[1]) / 2;
    const halfSpan = ((bounds[1] - bounds[0]) * scale) / 2;
    ranges[axis] = [center - halfSpan, center + halfSpan];
    if (mode.value !== "curve" || axis === "x") {
      updateIntervalInputs();
    }
    if (axis === "y") {
      autoYScale = false;
    }
    drawPlot(true);
  });
});

addFunctionButton.addEventListener("click", () => {
  if (curveFunctionList.children.length < 4) {
    addCurveFunction();
  }
});
