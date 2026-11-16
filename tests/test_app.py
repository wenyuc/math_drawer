import pytest

from app import app, parse_expression


def test_curve_plot_returns_png():
    response = app.test_client().post(
        "/plot", json={"mode": "curve", "expression": r"\sin(x)"}
    )
    assert response.status_code == 200
    assert response.mimetype == "image/png"
    assert response.data.startswith(b"\x89PNG")


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
