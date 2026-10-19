# -*- coding: utf-8 -*-
"""端到端 API 验证脚本（临时，验证后删除）。"""
import json
import http.cookiejar
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000/api/v1"
COOKIE_JAR = http.cookiejar.CookieJar()
OPENER = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(COOKIE_JAR))


def req(method, path, data=None, token=None):
    url = BASE + path
    body = json.dumps(data).encode() if data is not None else None
    r = urllib.request.Request(url, data=body, method=method)
    r.add_header("Content-Type", "application/json")
    try:
        with OPENER.open(r) as resp:
            raw = resp.read().decode()
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw


results = []


def check(name, ok, info=""):
    results.append((name, bool(ok), info))
    print(("PASS" if ok else "FAIL"), "|", name, "|", info)


# ---------- 认证（单管理员账号需预先存在） ----------
s, d = req("POST", "/auth/login", {"username": "admin", "password": "123456"})
token = s == 200
check("登录建立会话", token, str(s))
s, d = req("GET", "/auth/me", token=token)
check("当前用户", s == 200 and d.get("username") == "admin", str(s))

# ---------- 项目管理 ----------
import time
project_name = "电商平台-%d" % int(time.time())
s, d = req("POST", "/projects", {"name": project_name, "description": "电商后端项目", "owner": "admin"}, token)
check("创建项目", s == 201 and d.get("id"), str(s))
proj_id = d.get("id")
s, d = req("GET", "/projects", token=token)
check("项目列表", s == 200 and any(p["id"] == proj_id for p in d), str(s))

# ---------- 需求 PRD ----------
s, d = req("POST", "/prd", {"project_id": proj_id, "title": "登录功能 PRD", "content": "支持账号密码登录、第三方登录。", "version": "v1.0"}, token)
check("创建 PRD", s == 201 and d.get("id"), str(s))
prd_id = d.get("id")
s, d = req("POST", "/requirements",
           {"project_id": proj_id, "prd_id": prd_id, "title": "支持账号密码登录",
            "description": "用户可使用注册的账号密码登录系统", "priority": "P0", "module": "登录"}, token)
check("创建需求", s == 201 and d.get("id"), str(s))
req_id = d.get("id")
s, d = req("PATCH", f"/requirements/{req_id}", {"status": "approved"}, token)
check("需求状态更新", s == 200 and d.get("status") == "approved", str(s))
s, d = req("GET", f"/requirements/{req_id}/coverage", token=token)
check("需求覆盖统计", s == 200 and "case_count" in d, str(s))

# ---------- 版本/环境 ----------
s, d = req("POST", "/releases/versions", {"project_id": proj_id, "name": "v1.0.0", "description": "首个版本"}, token)
check("创建版本", s == 201 and d.get("id"), str(s))
ver_id = d.get("id")
s, d = req("POST", "/releases/environments", {"name": "测试环境-%d" % int(time.time()), "base_url": "http://test.example.com"}, token)
check("创建环境", s == 201 and d.get("id"), str(s))

# ---------- 测试计划 ----------
s, d = req("POST", "/plans",
           {"project_id": proj_id, "version_id": ver_id, "name": "登录功能测试计划", "description": "P0 功能回归"}, token)
check("创建测试计划", s == 201 and d.get("id"), str(s))
plan_id = d.get("id")

# ---------- 测试用例 ----------
case_body = {
    "project_id": proj_id, "module": "登录", "title": "正确账号密码登录成功",
    "preconditions": "已注册账号 admin/123456", "priority": "P0", "case_type": "functional",
    "steps": [
        {"step_no": 1, "action": "打开登录页", "expected": "显示登录表单"},
        {"step_no": 2, "action": "输入正确账号密码", "expected": "登录成功进入首页"},
    ],
    "requirement_ids": [req_id],
}
s, d = req("POST", "/cases", case_body, token)
check("创建用例", s == 201 and d.get("id"), str(s))
case_id = d.get("id")
s, d = req("GET", f"/cases/{case_id}", token=token)
check("用例详情含步骤", s == 200 and len(d.get("steps", [])) == 2, str(s))
s, d = req("POST", "/cases",
           {"project_id": proj_id, "module": "登录", "title": "错误密码提示", "steps": []}, token)
check("创建用例2", s == 201 and d.get("id"), str(s))
case_id2 = d.get("id")

# ---------- 测试执行 ----------
s, d = req("POST", "/executions/batch",
           {"plan_id": plan_id, "case_ids": [case_id, case_id2], "assignee": "admin", "environment": "测试环境"}, token)
check("批量创建执行", s == 201 and len(d) == 2, str(s))
exec1, exec2 = d[0]["id"], d[1]["id"]
s, d = req("PATCH", f"/executions/{exec1}",
           {"status": "pass", "actual_result": "登录成功，页面跳转正常"}, token)
check("执行1通过", s == 200 and d.get("status") == "pass", str(s))
s, d = req("PATCH", f"/executions/{exec2}",
           {"status": "fail", "fail_reason": "错误密码未提示", "actual_result": "页面报 500"}, token)
check("执行2失败", s == 200 and d.get("status") == "fail", str(s))

# ---------- 缺陷管理 ----------
s, d = req("POST", "/bugs",
           {"project_id": proj_id, "requirement_id": req_id, "case_id": case_id2,
            "title": "错误密码未提示", "description": "输入错误密码页面报 500", "severity": "major",
            "priority": "P1", "assignee": "dev1", "reporter": "admin"}, token)
check("创建缺陷", s == 201 and d.get("id"), str(s))
bug_id = d.get("id")
s, d = req("POST", f"/bugs/{bug_id}/comments", {"bug_id": bug_id, "user": "admin", "content": "已复现，开始修复"}, token)
check("缺陷评论", s == 201, str(s))
s, d = req("PATCH", f"/bugs/{bug_id}", {"status": "fixing"}, token)
check("缺陷状态流转", s == 200 and d.get("status") == "fixing", str(s))
s, d = req("GET", "/bugs", token=token)
check("缺陷列表", s == 200 and any(b["id"] == bug_id for b in d), str(s))

# ---------- 自动化脚本托管 ----------
s, d = req("POST", "/automation/scripts",
           {"project_id": proj_id, "case_id": case_id, "name": "登录用例自动脚本",
            "script_type": "ui", "framework": "pytest+selenium",
            "content": "def test_login(): ...", "version": "v1.0"}, token)
check("创建脚本", s == 201 and d.get("id"), str(s))
script_id = d.get("id")
s, d = req("POST", "/automation/tasks",
           {"script_id": script_id, "name": "每日回归", "schedule": "0 2 * * *", "environment": "测试环境"}, token)
check("创建调度任务", s == 201 and d.get("id"), str(s))
task_id = d.get("id")
s, d = req("POST", f"/automation/tasks/{task_id}/run", token=token)
check("任务触发执行", s == 200 and d.get("last_run_at"), str(s))

# ---------- 知识库 ----------
s, d = req("POST", "/knowledge",
           {"project_id": proj_id, "category": "测试规范", "title": "登录模块测试要点",
            "content": "重点关注密码错误提示、token 过期等场景。", "tags": "登录,规范"}, token)
check("创建知识库文档", s == 201 and d.get("id"), str(s))

# ---------- AI 配置（后置模块的配置管理） ----------
s, d = req("POST", "/ai/models",
           {"name": "豆包主模型", "provider": "doubao", "model_name": "doubao-pro", "api_key": "sk-test"}, token)
check("创建模型配置", s == 201 and d.get("id"), str(s))
model_id = d.get("id")
s, d = req("POST", "/ai/skills",
           {"name": "测试用例生成", "description": "根据需求自动生成测试用例草稿",
            "input_template": "需求标题：{title}", "prompt_template": "请为以下需求生成测试用例：{input}",
            "model_id": model_id, "status": "enabled"}, token)
check("创建 Skill", s == 201 and d.get("id"), str(s))
s, d = req("POST", "/ai/prompts", {"name": "缺陷分析模板", "content": "分析以下缺陷并给出分类建议：{input}", "variables": "input"}, token)
check("创建 Prompt 模板", s == 201 and d.get("id"), str(s))

# ---------- 统计报表 ----------
s, d = req("GET", "/dashboard/summary", token=token)
check("质量看板统计", s == 200, str(s))
if s == 200:
    check("看板包含关键指标", "pass_rate" in d and "req_coverage" in d, str(d.get("pass_rate")) + "/" + str(d.get("req_coverage")))

print()
print("=" * 40)
passed = sum(1 for _, ok, _ in results if ok)
print(f"TOTAL: {passed}/{len(results)} passed")
