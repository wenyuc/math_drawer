import pytest

from matplotlib.axes import Axes

from app import app, parse_expression


def test_curve_plot_returns_png():
    response = app.test_client().post(
        "/plot", json={"mode": "curve", "expression": r"\sin(x)"}
    )
    assert response.status_code == 200
    assert response.mimetype == "image/png"
    assert response.data.startswith(b"\x89PNG")


def test_curve_plot_supports_four_independent_functions(monkeypatch):
    plotted_curves = []
    original_plot = Axes.plot

    def record_plot(axis, x_values, y_values, *args, **kwargs):
        plotted_curves.append(
            (x_values[0], x_values[-1], kwargs.get("color"))
        )
        return original_plot(axis, x_values, y_values, *args, **kwargs)

    monkeypatch.setattr(Axes, "plot", record_plot)
    response = app.test_client().post(
        "/plot",
        json={
            "mode": "curve",
            "functions": [
                {"expression": "x", "x_range": [-2, 1]},
                {"expression": "x^2", "x_range": [3, 5]},
                {"expression": r"\sin(x)"},
                {"expression": "2*x", "x_range": [-1, 2]},
            ],
        },
    )

    assert response.status_code == 200
    assert response.headers["X-Plot-X-Range"] == "-10,10"
    assert [(curve[0], curve[1]) for curve in plotted_curves] == [
        (-2.0, 1.0),
        (3.0, 5.0),
        (-10.0, 10.0),
        (-1.0, 2.0),
    ]
    assert len({curve[2] for curve in plotted_curves}) == 4


def test_curve_plot_rejects_more_than_four_functions():
    response = app.test_client().post(
        "/plot",
        json={
            "mode": "curve",
            "functions": [{"expression": "x"} for _ in range(5)],
        },
    )
    assert response.status_code == 400


def test_curve_plot_error_identifies_unparseable_function():
    response = app.test_client().post(
        "/plot",
        json={
            "mode": "curve",
            "functions": [
                {"expression": "x"},
                {"expression": "x+*y"},
            ],
        },
    )

    assert response.status_code == 400
    assert "函数 2 无法解析" in response.json["error"]


def test_plot_accepts_and_returns_axis_ranges():
    response = app.test_client().post(
        "/plot",
        json={
            "mode": "curve",
            "expression": "x",
            "x_range": [-2, 4],
            "y_range": [-3, 5],
        },
    )
    assert response.status_code == 200
    assert response.headers["X-Plot-X-Range"] == "-2,4"
    assert response.headers["X-Plot-Y-Range"] == "-3,5"


def test_plot_rejects_invalid_axis_range():
    response = app.test_client().post(
        "/plot",
        json={"mode": "curve", "expression": "x", "x_range": [4, -2]},
    )
    assert response.status_code == 400


def test_curve_y_range_autoscales_with_x_range():
    client = app.test_client()
    y_ranges = []
    for x_range in ([-10, 10], [-8, 8]):
        response = client.post(
            "/plot",
            json={
                "mode": "curve",
                "expression": r"\e^{x}",
                "x_range": x_range,
            },
        )
        assert response.status_code == 200
        y_ranges.append(
            tuple(float(bound) for bound in response.headers["X-Plot-Y-Range"].split(","))
        )

    assert y_ranges[1][1] < y_ranges[0][1]


def test_natural_logarithm_curve_returns_png():
    response = app.test_client().post(
        "/plot", json={"mode": "curve", "expression": r"\ln(x+1)"}
    )
    assert response.status_code == 200
    assert response.mimetype == "image/png"
    assert response.data.startswith(b"\x89PNG")


def test_euler_constant_curve_returns_png():
    response = app.test_client().post(
        "/plot", json={"mode": "curve", "expression": r"\e^{x}"}
    )
    assert response.status_code == 200
    assert response.mimetype == "image/png"
    assert response.data.startswith(b"\x89PNG")


def test_surface_and_implicit_plots_return_png():
    client = app.test_client()
    for mode, expression in (
        ("surface", r"\sin(x)+\cos(y)"),
        ("implicit", r"x^2+y^2+z^2=9"),
    ):
        response = client.post(
            "/plot",
            json={
                "mode": mode,
                "expression": expression,
                "x_range": [-4, 3],
                "y_range": [-2, 4],
            },
        )
        assert response.status_code == 200
        assert response.mimetype == "image/png"
        assert response.headers["X-Plot-X-Range"] == "-4,3"
        assert response.headers["X-Plot-Y-Range"] == "-2,4"


def test_implicit_plot_uses_selected_z_interval():
    response = app.test_client().post(
        "/plot",
        json={
            "mode": "implicit",
            "expression": "x^2+y^2+z^2=9",
            "z_range": [-2, 4],
        },
    )
    assert response.status_code == 200
    assert response.headers["X-Plot-Z-Range"] == "-2,4"


def test_expression_rejects_variables_outside_selected_mode():
    with pytest.raises(ValueError, match="只支持变量 x"):
        parse_expression("x+y", "curve")


def test_expression_rejects_unsupported_function():
    with pytest.raises(ValueError):
        parse_expression(r"\operatorname{unknown}(x)", "curve")


def test_expression_rejects_malformed_latex():
    with pytest.raises(ValueError, match="无法解析"):
        parse_expression("x+*y", "curve")


def test_home_page_loads():
    response = app.test_client().get("/")
    assert response.status_code == 200
    assert "函数画图工具".encode() in response.data
