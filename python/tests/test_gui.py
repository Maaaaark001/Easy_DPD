"""GUI 冒烟测试：窗口能创建、跑一次仿真、指标更新、正常关闭。

无 tkinter 或桌面会话时自动跳过（不影响其余测试）。
"""

import pytest

tk = pytest.importorskip("tkinter")


def test_gui_smoke():
    try:
        import gui
    except Exception as e:
        pytest.skip(f"GUI 依赖不可用: {e}")

    try:
        app = gui.DpdGui()
    except tk.TclError as e:
        pytest.skip(f"无桌面会话，无法创建 Tk 窗口: {e}")

    try:
        app.update()                       # 处理初始 _run 与布局
        app.update_idletasks()
        assert app._vars["nmse1"].get() != "--", "初始仿真后 NMSE1 应已更新"

        # 修改参数（K 阶数）后重跑，指标应随之更新
        app._vars["K"].set(7)
        app._run()
        app.update()
        assert app._vars["nmse1"].get() != "--"

        # 切换泛化开关重跑
        app._vars["gen"].set(False)
        app._run()
        app.update()
        assert app._vars["nmse2"].get() == "未启用"
    finally:
        app.destroy()
