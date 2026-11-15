const form = document.querySelector("#plot-form");
const mode = document.querySelector("#mode");
const expression = document.querySelector("#expression");
const status = document.querySelector("#status");
const image = document.querySelector("#plot-image");
const placeholder = document.querySelector("#placeholder");
const button = document.querySelector("#submit-button");
const axisButtons = document.querySelectorAll(".axis-controls button");
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
  };
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
  image.hidden = true;
  placeholder.hidden = false;
  axisButtons.forEach((axisButton) => {
    axisButton.disabled = true;
  });
  status.textContent = "";
});

expression.value = examples[mode.value];

async function drawPlot() {
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
        expression: expression.value,
        x_range: ranges.x,
        y_range: ranges.y,
      }),
    });
    if (!response.ok) {
      const result = await response.json();
      throw new Error(result.error || "绘图失败，请重试。");
    }
    ranges.x = rangeFromHeader(response, "x", ranges.x);
    ranges.y = rangeFromHeader(response, "y", ranges.y);
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
    if (axis === "y") {
      autoYScale = false;
    }
    drawPlot();
  });
});
