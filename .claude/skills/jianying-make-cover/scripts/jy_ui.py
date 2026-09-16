# -*- coding: utf-8 -*-
"""剪映 (JianYing Pro) 5.9 UI 自动化分步驱动脚本（做封面用）。

设计成"一条命令一步、每步截图肉眼确认"的调试式驱动：Claude 用 shot / dump
先看清界面，再用 click-xy / click-name / paste-at 点下一步。**不要写死一整套
坐标一把梭**——剪映版本/分辨率/DPI 不同，坐标会漂，必须每步截图校准。

分工约定（见 SKILL.md）：进草稿→点「封面」→上传底图→切「模板」页签由**用户手动**
完成，自动化从「模板」页签接手（先 shot 校验）。launch / open-draft / file-dialog
保留备用，默认流程不用；卡壳步骤直接交回用户手动。

环境（绕开损坏的 e:\\Documents\\kuaishou\\venv，见记忆 kuaishou-venv-broken-py313）：
  $env:PYTHONPATH = '<deps 含 uiautomation/comtypes>'   # 从旧 venv site-packages 拷
  $env:PYTHONIOENCODING = 'utf-8'
  & 'C:\\Program Files\\Python313\\python.exe' jy_ui.py <命令> [参数]

可用 JY_EXE / JY_SHOT_DIR 两个环境变量覆盖默认程序路径与截图目录。

命令:
  launch                    启动剪映(若未运行)并等待窗口就绪
  shot <文件名>              截当前剪映窗口 -> 截图目录/<文件名>
  dump [深度] [关键词]       遍历控件树, 打 ClassName/Name/FullDescription/矩形(可按关键词过滤)
  open-draft <草稿名>        目录页点击该草稿进入编辑器
  home                      从编辑器返回目录页(点标题栏第3个按钮)
  click-desc <desc> [深度]   点 FullDescription 含 desc 的控件
  click-name <name> [深度]   点 Name 含 name 的控件
  click-xy <x> <y>          点窗口内相对坐标(配合 shot 定位)
  type-at <x> <y> <text>    点(x,y)后全选清空并逐字输入 text + 回车
  paste-at <x> <y> <text>   点(x,y)后全选并粘贴 text(中文优先用这个, 逐字输入会丢字)
  file-dialog <path>        处理标准 Windows 打开文件对话框(#32770): 填路径+回车
"""
import sys, os, time, subprocess
sys.stdout.reconfigure(encoding='utf-8')
import uiautomation as uia

JY_EXE = os.environ.get(
    'JY_EXE', r"e:\Documents\kuaishou\JianyingPro\5.9.0.11632\JianyingPro.exe")
SHOT_DIR = os.environ.get(
    'JY_SHOT_DIR', os.path.abspath('.'))


def is_jy_window(c, d):
    cn = (c.ClassName or "").lower()
    return "homepage" in cn or "mainwindow" in cn


def get_window(timeout=30):
    t0 = time.time()
    while time.time() - t0 < timeout:
        w = uia.WindowControl(searchDepth=1, Compare=is_jy_window)
        if w.Exists(1):
            w.SetActive()
            w.SetTopmost(True)
            time.sleep(0.3)
            w.SetTopmost(False)
            return w
        time.sleep(1)
    raise RuntimeError("未找到剪映窗口")


def full_desc(c):
    try:
        return c.GetPropertyValue(30159) or ""   # UIA FullDescription 属性 id
    except Exception:
        return ""


def cmd_launch():
    w = uia.WindowControl(searchDepth=1, Compare=is_jy_window)
    if not w.Exists(1):
        subprocess.Popen([JY_EXE])
        print("已启动剪映进程, 等待窗口...")
    w = get_window(60)
    print("窗口就绪: ClassName=%s Name=%s rect=%s" % (w.ClassName, w.Name, w.BoundingRectangle))


def cmd_shot(fname):
    w = get_window()
    path = os.path.join(SHOT_DIR, fname)
    w.CaptureToImage(path)
    print("截图: " + path)


def cmd_dump(max_depth=6, keyword=None):
    w = get_window()
    n = 0

    def walk(c, d):
        nonlocal n
        if d > max_depth or n > 4000:
            return
        fd = full_desc(c)
        name = c.Name or ""
        line = "d%d %s | Name=%r | FD=%r | %s" % (
            d, c.ClassName, name[:40], fd[:80], c.BoundingRectangle)
        if keyword is None or keyword.lower() in line.lower():
            print(line)
        n += 1
        for ch in c.GetChildren():
            walk(ch, d + 1)
    walk(w, 0)
    print("(共遍历 %d 个控件)" % n)


def find_ctrl(w, pred, max_depth):
    hit = []

    def walk(c, d):
        if hit or d > max_depth:
            return
        if pred(c):
            hit.append(c)
            return
        for ch in c.GetChildren():
            walk(ch, d + 1)
    walk(w, 0)
    return hit[0] if hit else None


def cmd_open_draft(name):
    w = get_window()
    t = w.TextControl(searchDepth=2,
                      Compare=lambda c, d: full_desc(c) == "HomePageDraftTitle:" + name)
    if not t.Exists(3):
        raise RuntimeError("目录页未找到草稿: " + name)
    p = t.GetParentControl()
    p.Click(simulateMove=False)
    print("已点击草稿, 等待编辑器加载...")
    time.sleep(12)
    w = get_window()
    print("当前窗口: ClassName=%s Name=%s" % (w.ClassName, w.Name))


def cmd_home():
    """从编辑器回目录页(点标题栏第3个按钮, 同 pyJianYingDraft jianying_controller.switch_to_home)"""
    w = get_window()
    if "homepage" in w.ClassName.lower():
        print("已在目录页")
        return
    btn = w.GroupControl(searchDepth=1, ClassName="TitleBarButton", foundIndex=3)
    btn.Click(simulateMove=False)
    time.sleep(3)
    w = get_window()
    print("当前窗口: " + w.ClassName)


def cmd_click_desc(desc, max_depth=10):
    w = get_window()
    c = find_ctrl(w, lambda c: desc.lower() in full_desc(c).lower(), max_depth)
    if c is None:
        raise RuntimeError("未找到 FullDescription 含 %r 的控件" % desc)
    print("命中: %s | Name=%r | FD=%r | %s" % (
        c.ClassName, c.Name, full_desc(c)[:80], c.BoundingRectangle))
    c.Click(simulateMove=False)
    print("已点击")


def cmd_click_name(name, max_depth=10):
    w = get_window()
    c = find_ctrl(w, lambda c: name in (c.Name or ""), max_depth)
    if c is None:
        raise RuntimeError("未找到 Name 含 %r 的控件" % name)
    print("命中: %s | Name=%r | FD=%r | %s" % (
        c.ClassName, c.Name, full_desc(c)[:80], c.BoundingRectangle))
    c.Click(simulateMove=False)
    print("已点击")


def cmd_click_xy(x, y):
    w = get_window()
    r = w.BoundingRectangle
    uia.Click(r.left + int(x), r.top + int(y))
    print("已点击窗口内坐标 (%s,%s) -> 屏幕 (%d,%d)" % (x, y, r.left + int(x), r.top + int(y)))


def cmd_type_at(x, y, text):
    w = get_window()
    r = w.BoundingRectangle
    uia.Click(r.left + int(x), r.top + int(y))
    time.sleep(0.5)
    uia.SendKeys('{Ctrl}a', waitTime=0.2)
    uia.SendKeys(text, interval=0.02, waitTime=0.3)
    uia.SendKeys('{Enter}', waitTime=0.3)
    print("已在 (%s,%s) 输入文本并回车: %s" % (x, y, text))


def cmd_paste_at(x, y, text):
    """中文文本优先用粘贴: SendKeys 逐字输入中文会丢字/触发候选词。"""
    w = get_window()
    r = w.BoundingRectangle
    uia.Click(r.left + int(x), r.top + int(y))
    time.sleep(0.6)
    uia.SetClipboardText(text)
    uia.SendKeys('{Ctrl}a', waitTime=0.3)
    uia.SendKeys('{Ctrl}v', waitTime=0.5)
    print("已在 (%s,%s) 粘贴文本: %s" % (x, y, text))


def cmd_file_dialog(path, timeout=15):
    """处理标准 Windows 打开文件对话框(#32770): 填路径 + 回车"""
    t0 = time.time()
    dlg = None
    while time.time() - t0 < timeout:
        d = uia.WindowControl(searchDepth=2, ClassName="#32770")
        if d.Exists(1):
            dlg = d
            break
        time.sleep(0.5)
    if dlg is None:
        raise RuntimeError("未等到文件对话框 (#32770)")
    print("文件对话框: Name=%r" % dlg.Name)
    edit = dlg.EditControl(searchDepth=10, foundIndex=1)
    edit.Click(simulateMove=False)
    time.sleep(0.3)
    uia.SendKeys('{Ctrl}a', waitTime=0.2)
    edit.GetValuePattern().SetValue(path)
    time.sleep(0.3)
    uia.SendKeys('{Enter}', waitTime=0.5)
    print("已提交文件路径: " + path)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "launch":
        cmd_launch()
    elif cmd == "shot":
        cmd_shot(sys.argv[2])
    elif cmd == "dump":
        d = int(sys.argv[2]) if len(sys.argv) > 2 else 6
        kw = sys.argv[3] if len(sys.argv) > 3 else None
        cmd_dump(d, kw)
    elif cmd == "open-draft":
        cmd_open_draft(sys.argv[2])
    elif cmd == "home":
        cmd_home()
    elif cmd == "click-desc":
        cmd_click_desc(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 10)
    elif cmd == "click-name":
        cmd_click_name(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 10)
    elif cmd == "click-xy":
        cmd_click_xy(sys.argv[2], sys.argv[3])
    elif cmd == "type-at":
        cmd_type_at(sys.argv[2], sys.argv[3], sys.argv[4])
    elif cmd == "paste-at":
        cmd_paste_at(sys.argv[2], sys.argv[3], sys.argv[4])
    elif cmd == "file-dialog":
        cmd_file_dialog(sys.argv[2])
    else:
        print("未知命令: " + cmd)
