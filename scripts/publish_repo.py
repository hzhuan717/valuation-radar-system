# -*- coding: utf-8 -*-
"""把项目发布到 GitHub 并打版本标签（每版一个版本）。

- 项目仓库：hzhuan717/valuation-radar-system（可在 repo.json 覆盖）
- 版本号来自仓库根目录 VERSION 文件（主.次.修订）
- 每次发布：提交全部改动（遵守 .gitignore）→ 打标签 v<版本> → push origin main --tags
- 通过 Windows 凭据管理器 GitHub token 认证（不打印、不落日志）
- 用法：
    python publish_repo.py              # 修订号 +1
    python publish_repo.py --bump minor # 次版本 +1
    python publish_repo.py --bump major # 主版本 +1
"""
import argparse
import json
import os
import subprocess
import sys
import time

BASE = r"E:\财报解读\watchlist"
CFG = os.path.join(BASE, "repo.json")

DEFAULT = {"owner": "hzhuan717", "repo": "valuation-radar-system", "branch": "main"}


def log(msg):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    with open(os.path.join(BASE, "logs", "publish.log"), "a", encoding="utf-8") as f:
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
    try:
        proc = subprocess.run(
            ["git", "credential", "fill"],
            input="protocol=https\nhost=github.com\n\n",
            capture_output=True, text=True, timeout=15,
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
    raise RuntimeError("未找到 GitHub 凭据")


def api(method, path, token, body=None):
    import urllib.request
    url = "https://api.github.com" + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": "token " + token,
        "Accept": "application/vnd.github+json",
        "User-Agent": "valuation-radar-project-publish",
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {}


def ensure_repo(token, cfg):
    owner, repo = cfg["owner"], cfg["repo"]
    status, _ = api("GET", f"/repos/{owner}/{repo}", token)
    if status == 200:
        return True
    if status == 404:
        status2, body2 = api("POST", "/user/repos", token, {
            "name": repo, "public": True,
            "description": "估值雷达 · 估值区间决策系统（六步决策台 · 终端仪表盘，研究/教学/回测用途）",
        })
        if status2 in (200, 201):
            log(f"已创建公开仓库 {owner}/{repo}")
            return True
        log(f"创建仓库失败: HTTP {status2} {body2.get('message')}")
        return False
    log(f"检查仓库失败: HTTP {status} ")
    return False


def bump_version(bump: str) -> str:
    path = os.path.join(BASE, "VERSION")
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write("1.0.0")
    with open(path, encoding="utf-8") as f:
        ver = f.read().strip()
    try:
        major, minor, patch = (int(x) for x in ver.split("."))
    except ValueError:
        major, minor, patch = 1, 0, 0
    if bump == "major":
        major, minor, patch = major + 1, 0, 0
    elif bump == "minor":
        minor, patch = minor + 1, 0
    else:
        patch += 1
    new_ver = f"{major}.{minor}.{patch}"
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_ver)
    return new_ver


def git(cfg, token, args, allow_fail=False):
    env = dict(os.environ)
    env["DEPLOY_GIT_TOKEN"] = token
    env["GIT_TERMINAL_PROMPT"] = "0"
    askpass = os.path.join(BASE, "deploy", ".askpass.py")
    if os.path.exists(askpass):
        env["GIT_ASKPASS"] = askpass
    proc = subprocess.run(["git"] + args, cwd=BASE, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=env, timeout=300)
    if proc.returncode != 0 and not allow_fail:
        raise RuntimeError(f"git {' '.join(args)} 失败: {proc.stderr.strip()[-300:]}")
    return proc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bump", default="patch", choices=["patch", "minor", "major"],
                    help="版本递增级别（默认修订号）")
    ap.add_argument("--note", default="", help="本次版本变更说明（写入提交信息；建议同步更新 CHANGELOG.md）")
    args = ap.parse_args()

    cfg = load_cfg()
    token = get_token()
    if not ensure_repo(token, cfg):
        log("仓库不可用，发布中止")
        return

    if not os.path.exists(os.path.join(BASE, ".git")):
        git(cfg, token, ["init", "-q", "-b", cfg["branch"]])
        git(cfg, token, ["config", "user.email", "portal@local"])
        git(cfg, token, ["config", "user.name", "valuation-radar"])
        git(cfg, token, ["remote", "add", "origin",
                         f"https://github.com/{cfg['owner']}/{cfg['repo']}.git"], allow_fail=True)
        git(cfg, token, ["remote", "set-url", "origin",
                         f"https://github.com/{cfg['owner']}/{cfg['repo']}.git"])

    # 无实质改动（除 VERSION 外）时跳过，避免产生纯版本号噪音提交
    status = git(cfg, token, ["status", "--porcelain"]).stdout
    real_changes = [l for l in status.splitlines() if l.strip() and not l.strip().endswith("VERSION")]
    if not real_changes:
        log("无实质改动，跳过发布（版本号不变）")
        return

    new_ver = bump_version(args.bump)
    msg = f"v{new_ver} · {args.note or '门户/引擎/数据更新'} · {time.strftime('%Y-%m-%d %H:%M')}"
    git(cfg, token, ["add", "-A"])
    proc = git(cfg, token, ["commit", "-q", "-m", msg],
               allow_fail=True)
    if proc.returncode != 0 and "nothing to commit" not in (proc.stdout + proc.stderr):
        log(f"提交无变化或失败，跳过打标: {proc.stderr.strip()[-200:]}")
        return
    git(cfg, token, ["tag", "-f", f"v{new_ver}"])
    last_exc = None
    for attempt in range(2):
        try:
            git(cfg, token, ["push", "-q", "-u", "origin", cfg["branch"], "--force"])
            break
        except Exception as e:
            last_exc = e
            time.sleep(8 * (attempt + 1))
    else:
        for attempt in range(2):
            try:
                git(cfg, token, ["-c", "http.proxy=", "-c", "https.proxy=",
                                 "push", "-q", "-u", "origin", cfg["branch"], "--force"])
                break
            except Exception as e:
                last_exc = e
                time.sleep(8 * (attempt + 1))
        else:
            raise RuntimeError(f"push 失败: {last_exc}")
    git(cfg, token, ["push", "-q", "-f", "origin", f"refs/tags/v{new_ver}"],
        allow_fail=True) or git(cfg, token, ["push", "-q", "-f", "origin", f"v{new_ver}"],
                                allow_fail=True)
    url = f"https://github.com/{cfg['owner']}/{cfg['repo']}"
    log(f"已发布 {cfg['owner']}/{cfg['repo']} v{new_ver} → {url}")
    print(url)
    print(f"v{new_ver}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"发布失败: {type(e).__name__}: {e}")
        sys.exit(1)
