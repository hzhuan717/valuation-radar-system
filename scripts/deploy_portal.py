# -*- coding: utf-8 -*-
"""把门户 HTML 发布到 GitHub Pages（永久公开网址）。

- 通过 Windows Credential Manager 的 GitHub 凭据认证（git credential fill），token 不打印、不落日志
- 仓库默认 hzhuan717/valuation-radar-valuation-portal，可在同级 deploy.json 覆盖
- 首次运行自动建公开仓库并开启 Pages；之后每次推送覆盖 index.html
- 被 update_daily.py 调用时以子进程方式执行（每日流水线末尾自动同步公开网址）

用法：python deploy_portal.py
"""
import base64
import json
import os
import subprocess
import sys
import time
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORTAL = os.path.join(BASE, "output", "估值雷达门户.html")
CFG = os.path.join(BASE, "deploy.json")
WORK = os.path.join(BASE, "deploy", "repo")

DEFAULT = {"owner": "hzhuan717", "repo": "valuation-radar-portal", "branch": "main"}


def log(msg):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    with open(os.path.join(BASE, "logs", "deploy.log"), "a", encoding="utf-8") as f:
        f.write(line + "\n")
    try:
        print(line)
    except Exception:
        pass


def load_cfg():
    cfg = dict(DEFAULT)
    if os.path.exists(CFG):
        try:
            with open(CFG, encoding="utf-8") as f:
                cfg.update(json.load(f))
        except Exception:
            pass
    return cfg


def get_token() -> str:
    """从 Windows 凭据管理器取 GitHub PAT；只在内存中使用，绝不打印。"""
    try:
        proc = subprocess.run(
            ["git", "credential", "fill"],
            input="protocol=https\nhost=github.com\n\n",
            capture_output=True, text=True, timeout=15, creationflags=0x08000000,
        )
    except TypeError:
        proc = subprocess.run(
            ["git", "credential", "fill"],
            input="protocol=https\nhost=github.com\n\n",
            capture_output=True, text=True, timeout=15,
        )
    for line in proc.stdout.splitlines():
        if line.startswith("password="):
            token = line.split("=", 1)[1].strip()
            if token:
                return token
    raise RuntimeError("未找到 GitHub 凭据（Windows 凭据管理器 git:https://github.com）")


def api(method: str, path: str, token: str, body: dict | None = None, accept: str = "application/vnd.github+json"):
    url = "https://api.github.com" + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": "token " + token,
        "Accept": accept,
        "User-Agent": "valuation-radar-portal-deploy",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return r.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {}


def ensure_repo(token: str, cfg: dict) -> bool:
    owner, repo = cfg["owner"], cfg["repo"]
    status, body = api("GET", f"/repos/{owner}/{repo}", token)
    if status == 200:
        return True
    if status == 404:
        status2, body2 = api("POST", "/user/repos", token, {
            "name": repo, "public": True,
            "description": "估值雷达估值区间六步决策台（研究/教学/回测用途，自动同步）",
        })
        if status2 in (200, 201):
            log(f"已创建公开仓库 {owner}/{repo}")
            return True
        log(f"创建仓库失败: HTTP {status2} {body2.get('message')}")
        return False
    log(f"检查仓库失败: HTTP {status} {body.get('message')}")
    return False


def ensure_pages(token: str, cfg: dict):
    owner, repo, branch = cfg["owner"], cfg["repo"], cfg["branch"]
    status, body = api("GET", f"/repos/{owner}/{repo}/pages", token)
    if status == 200:
        return
    for method in ("POST", "PUT"):
        status2, body2 = api(method, f"/repos/{owner}/{repo}/pages", token,
                             {"source": {"branch": branch, "path": "/"}})
        if status2 in (200, 201, 204):
            log(f"已启用 GitHub Pages（{branch} 分支根目录）")
            return
        log(f"Pages {method} 未成功: HTTP {status2} {body2.get('message')}")
    log("Pages 启用失败：请到仓库 Settings → Pages 手动选择 main 分支（一次性）")


def push_via_git(token: str, cfg: dict):
    owner, repo, branch = cfg["owner"], cfg["repo"], cfg["branch"]
    os.makedirs(WORK, exist_ok=True)
    askpass = os.path.join(WORK, ".askpass.py")
    with open(askpass, "w", encoding="utf-8") as f:
        f.write("import os,sys\nprint(os.environ['DEPLOY_GIT_TOKEN'])\n")
    with open(os.path.join(WORK, "index.html"), "w", encoding="utf-8") as f:
        f.write(open(PORTAL, encoding="utf-8").read())

    env = dict(os.environ)
    env["DEPLOY_GIT_TOKEN"] = token
    env["GIT_ASKPASS"] = askpass
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_HTTP_LOW_SPEED_LIMIT"] = "1"
    env["GIT_HTTP_LOW_SPEED_TIME"] = "60"

    def run(args, allow_fail=False):
        proc = subprocess.run(["git"] + args, cwd=WORK, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", env=env, timeout=300)
        if proc.returncode != 0 and not allow_fail:
            raise RuntimeError(f"git {' '.join(args)} 失败: {proc.stderr.strip()[-300:]}")
        return proc

    if not os.path.exists(os.path.join(WORK, ".git")):
        run(["init", "-q", "-b", branch])
        run(["config", "user.email", "portal@local"])
        run(["config", "user.name", "valuation-radar-portal-deploy"])
        run(["remote", "add", "origin", f"https://github.com/{owner}/{repo}.git"], allow_fail=True)
        run(["remote", "set-url", "origin", f"https://github.com/{owner}/{repo}.git"])
    run(["add", "-A"])
    proc = run(["commit", "-q", "-m", f"portal auto-update {time.strftime('%Y-%m-%d %H:%M:%S')}"],
               allow_fail=True)
    if proc.returncode != 0 and "nothing to commit" not in proc.stdout + proc.stderr:
        pass
    last_exc = None
    # 先走系统代理，代理节点不稳时回退直连（家庭宽带直连 github 通常可用）
    for attempt in range(2):
        try:
            run(["push", "-q", "-u", "origin", branch, "--force"])
            return
        except Exception as e:
            last_exc = e
            time.sleep(10 * (attempt + 1))
    for attempt in range(2):
        try:
            run(["-c", "http.proxy=", "-c", "https.proxy=",
                 "push", "-q", "-u", "origin", branch, "--force"])
            return
        except Exception as e:
            last_exc = e
            time.sleep(10 * (attempt + 1))
    raise RuntimeError(f"push 失败（代理+直连均重试）: {last_exc}")


def main():
    if not os.path.exists(PORTAL):
        log(f"门户文件不存在: {PORTAL}")
        return
    cfg = load_cfg()
    token = get_token()
    if not ensure_repo(token, cfg):
        log("仓库不可用，发布中止")
        return
    push_via_git(token, cfg)
    log(f"已推送 {cfg['owner']}/{cfg['repo']}（{os.path.getsize(PORTAL):,} 字节）")
    ensure_pages(token, cfg)
    url = f"https://{cfg['owner']}.github.io/{cfg['repo']}/"
    log(f"公开网址: {url}")
    print(url)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"发布失败: {type(e).__name__}: {e}")
        sys.exit(1)
