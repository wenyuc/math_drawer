import io
import logging

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import sympy as sp
from flask import Flask, jsonify, render_template, request, send_file
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from skimage.measure import marching_cubes
from sympy.parsing.latex import parse_latex
from sympy.parsing.latex.errors import LaTeXParsingError


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024
logging.basicConfig(level=logging.INFO)

VARIABLES = {
    "curve": (sp.Symbol("x"),),
    "surface": (sp.Symbol("x"), sp.Symbol("y")),
    "implicit": (sp.Symbol("x"), sp.Symbol("y"), sp.Symbol("z")),
}
SAFE_FUNCTIONS = {
    sp.Abs,
    sp.acos,
    sp.asin,
    sp.atan,
    sp.cos,
    sp.cosh,
    sp.exp,
    sp.log,
    sp.sin,
    sp.sinh,
    sp.sqrt,
    sp.tan,
    sp.tanh,
}
CURVE_COLORS = ("#2563eb", "#dc2626", "#16a34a", "#9333ea")


class InvalidExpression(ValueError):
    pass


def parse_expression(latex, mode):
    if mode not in VARIABLES:
        raise InvalidExpression("请选择有效的绘图模式。")
    if not isinstance(latex, str) or not latex.strip() or len(latex) > 200:
        raise InvalidExpression("请输入不超过 200 个字符的 LaTeX 数学表达式。")

    latex = latex.strip()
    if latex.startswith(r"\(") and latex.endswith(r"\)"):
        latex = latex[2:-2].strip()
    elif latex.startswith("$$") and latex.endswith("$$"):
        latex = latex[2:-2].strip()
    elif latex.startswith("$") and latex.endswith("$"):
        latex = latex[1:-1].strip()

    try:
        expression = parse_latex(latex, strict=True)
    except (LaTeXParsingError, ValueError, TypeError) as error:
        raise InvalidExpression("无法解析该 LaTeX 表达式，请检查公式格式。") from error

    constants = {"e": sp.E, "pi": sp.pi}
    constant_symbols = {
        symbol: constants[symbol.name]
        for symbol in expression.free_symbols
        if symbol.name in constants
    }
    expression = expression.xreplace(constant_symbols)

    logarithms = {}
    for logarithm in expression.atoms(sp.log):
        if len(logarithm.args) == 2:
            argument, base = logarithm.args
            logarithms[logarithm] = (
                sp.log(argument)
                if base == sp.E
                else sp.log(argument) / sp.log(base)
            )
    expression = expression.xreplace(logarithms)

    if mode == "implicit" and isinstance(expression, sp.Equality):
        expression = expression.lhs - expression.rhs
    elif isinstance(expression, sp.Equality):
        raise InvalidExpression("只有三元隐式曲面模式支持等式，请输入函数表达式。")

    allowed_symbols = set(VARIABLES[mode])
    if not expression.free_symbols.issubset(allowed_symbols):
        raise InvalidExpression(
            f"此模式只支持变量 {', '.join(str(symbol) for symbol in VARIABLES[mode])}。"
        )
    if sp.count_ops(expression) > 100:
        raise InvalidExpression("表达式过于复杂，请简化后重试。")
    if any(function.func not in SAFE_FUNCTIONS for function in expression.atoms(sp.Function)):
        raise InvalidExpression("表达式包含不支持的函数。")
    return expression


def evaluate(expression, variables, *values):
    function = sp.lambdify(variables, expression, modules=[{"Abs": np.abs}, "numpy"])
    with np.errstate(all="ignore"):
        result = np.asarray(function(*values), dtype=float)
    result = np.broadcast_to(result, np.shape(values[0]))
    if not np.isfinite(result).any():
        raise InvalidExpression("该公式在当前范围内没有可绘制的实数值。")
    return result


def parse_axis_range(data, axis, default):
    value = data.get(f"{axis}_range")
    if value is None:
        return default
    if not isinstance(value, list) or len(value) != 2:
        raise InvalidExpression(f"{axis} 轴范围格式无效。")
    if any(isinstance(bound, bool) or not isinstance(bound, (int, float)) for bound in value):
        raise InvalidExpression(f"{axis} 轴范围必须是数字。")
    bounds = tuple(float(bound) for bound in value)
    if (
        not np.isfinite(bounds).all()
        or bounds[0] >= bounds[1]
        or bounds[1] - bounds[0] > 1e6
        or max(abs(bound) for bound in bounds) > 1e6
    ):
        raise InvalidExpression(f"{axis} 轴范围无效或过大。")
    return bounds


def render_plot(
    expression,
    mode,
    x_range=None,
    y_range=None,
    z_range=None,
    curve_functions=None,
):
    figure = plt.figure(figsize=(8, 6), dpi=120)
    try:
        if mode == "curve":
            curves = curve_functions or [(expression, x_range or (-10, 10))]
            x_range = x_range or (
                min(function_range[0] for _, function_range in curves),
                max(function_range[1] for _, function_range in curves),
            )
            axis = figure.add_subplot(111)
            for index, (function, function_range) in enumerate(curves):
                x = np.linspace(*function_range, 800)
                y = evaluate(function, VARIABLES[mode], x)
                axis.plot(
                    x,
                    y,
                    color=CURVE_COLORS[index],
                    linewidth=2,
                    label=str(function),
                )
            if len(curves) > 1:
                axis.legend()
            axis.axhline(0, color="#64748b", linewidth=0.8)
            axis.axvline(0, color="#64748b", linewidth=0.8)
            axis.set_xlim(*x_range)
            if y_range:
                axis.set_ylim(*y_range)
            axis.set(xlabel="x", ylabel="f(x)", title="2D Function Plot")
            axis.grid(True, alpha=0.25)
        elif mode == "surface":
            x_range = x_range or (-5, 5)
            y_range = y_range or (-5, 5)
            x = np.linspace(*x_range, 100)
            y = np.linspace(*y_range, 100)
            xx, yy = np.meshgrid(x, y)
            zz = evaluate(expression, VARIABLES[mode], xx, yy)
            axis = figure.add_subplot(111, projection="3d")
            axis.plot_surface(xx, yy, zz, cmap="viridis", linewidth=0, antialiased=True)
            axis.set(xlim=x_range, ylim=y_range)
            axis.set(xlabel="x", ylabel="y", zlabel="f(x, y)", title="3D Function Surface")
        else:
            x_range = x_range or (-5, 5)
            y_range = y_range or (-5, 5)
            z_range = z_range or (-5, 5)
            axis = figure.add_subplot(111, projection="3d")
            x = np.linspace(*x_range, 48)
            y = np.linspace(*y_range, 48)
            z = np.linspace(*z_range, 48)
            xx, yy, zz = np.meshgrid(x, y, z, indexing="ij")
            values = evaluate(expression, VARIABLES[mode], xx, yy, zz)
            try:
                vertices, faces, _, _ = marching_cubes(
                    values,
                    level=0,
                    spacing=(x[1] - x[0], y[1] - y[0], z[1] - z[0]),
                )
            except ValueError as error:
                raise InvalidExpression(
                    "当前显示范围内没有找到 F(x,y,z)=0 的曲面，请调整公式。"
                ) from error
            vertices[:, 0] += x[0]
            vertices[:, 1] += y[0]
            vertices[:, 2] += z[0]
            surface = Poly3DCollection(vertices[faces], alpha=0.8, edgecolor="none")
            surface.set_facecolor("#3282b8")
            axis.add_collection3d(surface)
            axis.set(
                xlim=x_range,
                ylim=y_range,
                zlim=z_range,
                xlabel="x",
                ylabel="y",
                zlabel="z",
                title="3D Implicit Surface",
            )
        visible_ranges = {"x": axis.get_xlim(), "y": axis.get_ylim()}
        if mode == "implicit":
            visible_ranges["z"] = axis.get_zlim()
        figure.tight_layout()
        image = io.BytesIO()
        figure.savefig(image, format="png", bbox_inches="tight")
        image.seek(0)
        return image, visible_ranges
    finally:
        plt.close(figure)


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/plot")
def plot():
    data = request.get_json(silent=True) or {}
    try:
        mode = data.get("mode", "")
        curve_functions = None
        if mode == "curve" and "functions" in data:
            function_data = data["functions"]
            if (
                not isinstance(function_data, list)
                or not 1 <= len(function_data) <= 4
            ):
                raise InvalidExpression("请提供 1 到 4 个函数。")
            curve_functions = []
            for index, function in enumerate(function_data, start=1):
                if not isinstance(function, dict):
                    raise InvalidExpression(f"函数 {index} 格式无效。")
                try:
                    parsed = parse_expression(function.get("expression"), mode)
                except InvalidExpression as error:
                    raise InvalidExpression(
                        f"函数 {index} 无法解析：{error}"
                    ) from error
                function_range = parse_axis_range(
                    {"x_range": function.get("x_range")}, "x", (-10, 10)
                )
                curve_functions.append((parsed, function_range))
            expression = curve_functions[0][0]
            default_x_range = (
                min(function_range[0] for _, function_range in curve_functions),
                max(function_range[1] for _, function_range in curve_functions),
            )
        else:
            expression = parse_expression(data.get("expression"), mode)
            default_x_range = (-10, 10) if mode == "curve" else (-5, 5)
        default_y_range = None if mode == "curve" else (-5, 5)
        x_range = parse_axis_range(data, "x", default_x_range)
        y_range = parse_axis_range(data, "y", default_y_range)
        z_range = (
            parse_axis_range(data, "z", (-5, 5))
            if mode == "implicit"
            else (-5, 5)
        )
        image, visible_ranges = render_plot(
            expression,
            mode,
            x_range,
            y_range,
            z_range,
            curve_functions=curve_functions,
        )
    except InvalidExpression as error:
        return jsonify(error=str(error)), 400
    except (TypeError, ValueError, OverflowError) as error:
        app.logger.warning("Could not render plot: %s", error)
        return jsonify(error="公式计算失败，请检查表达式并重试。"), 400
    response = send_file(image, mimetype="image/png")
    for axis, bounds in visible_ranges.items():
        response.headers[f"X-Plot-{axis.upper()}-Range"] = ",".join(
            f"{bound:.12g}" for bound in bounds
        )
    return response


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5003, debug=False)
