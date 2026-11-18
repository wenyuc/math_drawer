# 函数画图工具

基于 Flask、SymPy 和 Matplotlib 的本地 LaTeX 函数绘图网页，默认仅监听本机 `127.0.0.1:5003`。

## 运行

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

浏览器打开 <http://127.0.0.1:5003>。

## 支持的绘图模式

- 二维曲线：输入 `f(x)`，例如 `\sin(x)`。
- 三维曲面：输入 `f(x,y)`，例如 `\sin(x)+\cos(y)`。
- 三维隐式曲面：输入 `F(x,y,z)=0`，例如 `x^2+y^2+z^2=9`。

二维曲线最多可同时输入 4 个函数，每个函数都可单独设置 x 区间；区间留空时默认使用 `[-10,10]`。各函数在图中以不同颜色显示。三维坐标默认范围为 `[-5,5]`，绘图前可在变量区间框中分别设置各自变量的下限和上限：三维曲面设置 x、y，隐式曲面设置 x、y、z。图片框中的方向键可分别放大或缩小 x、y 轴间距；二维曲线的 y 轴默认随 x 范围自动缩放，手动调整 y 轴后则保留该范围。表达式通过 LaTeX 解析，只允许所选模式中的变量和常见数学函数。

运行测试（先安装测试依赖）：

```bash
pip install -r requirements-dev.txt
python -m pytest
```
