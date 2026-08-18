# -*- coding: utf-8 -*-
"""估值雷达 · 每日更新看门狗（替代不可用的任务计划程序）

以 pythonw 常驻运行（开机自启），每 60 秒检查一次：
  1. 交易日 15:30~15:32 窗口内（用户约定：每个交易日 15:30 准时更新）→ 执行 update_daily.py
  2. 补跑：交易日 15:32 后~20:00，若当日尚未执行过（如 15:30 未开机）→ 立即补跑一次
  3. 心跳写入 logs/scheduler.log，便于诊断

启动方式：Windows 启动文件夹快捷方式 → pythonw scheduler_loop.py
"""
import datetime
import os
import subprocess
import sys
import time

BASE = r"E:\财报解读\watchlist"
SCRIPTS = os.path.join(BASE, "scripts")
UPDATE = os.path.join(SCRIPTS, "update_daily.py")
LOG = os.path.join(BASE, "logs", "scheduler.log")
MARK = os.path.join(BASE, "logs", ".last_run_date")

POLL_SECONDS = 60
WINDOW_START = (15, 30)   # 用户约定：15:30 准时更新
WINDOW_END = (15, 32)
CATCHUP_END = (20, 0)


def s_log(msg: str):
    line = f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def last_run_date() -> str:
    try:
        with open(MARK, encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return ""


def mark_run(date: str):
    try:
        with open(MARK, "w", encoding="utf-8") as f:
            f.write(date)
    except Exception:
        pass


def is_trading_day_lite() -> bool:
    """轻量判断：周末直接跳过；工作日由 update_daily 内的交易日历精确判断。"""
    return datetime.date.today().weekday() < 5


def run_update():
    s_log("触发 update_daily.py")
    try:
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        r = subprocess.run([sys.executable, UPDATE], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", env=env, timeout=1500)
        s_log(f"update_daily 退出码 {r.returncode}" + (f"：{(r.stdout or '').strip()[-200:]}" if r.stdout else ""))
        if r.returncode != 0 and r.stderr:
            s_log("stderr: " + r.stderr[-500:])
        return r.returncode == 0
    except Exception as e:
        s_log(f"update_daily 异常: {e}")
        return False


def main():
    s_log("看门狗启动（POLL=60s，15:30 准时触发，补跑至 20:00）")
    while True:
        try:
            today = datetime.date.today().isoformat()
            now = datetime.datetime.now()
            hhmm = (now.hour, now.minute)

            if is_trading_day_lite() and last_run_date() != today:
                in_window = WINDOW_START <= hhmm < WINDOW_END
                catchup = hhmm >= WINDOW_END and hhmm < CATCHUP_END
                if in_window:
                    ok = run_update()
                    if ok:
                        mark_run(today)
                        s_log(f"今日 {today} 已标记完成（15:30 窗口）")
                    else:
                        s_log(f"今日 {today} 首次运行失败，等待补跑重试")
                elif catchup:
                    s_log("检测到当日未运行（疑似 15:30 未开机），执行补跑")
                    ok = run_update()
                    if ok:
                        mark_run(today)
                    else:
                        s_log(f"今日 {today} 补跑失败，等待下一轮重试")
            elif last_run_date() != today:
                pass  # 非交易日
        except Exception as e:
            s_log(f"循环异常: {e}")
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
