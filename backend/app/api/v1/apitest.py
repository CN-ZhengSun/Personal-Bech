"""接口测试工具：用例库、环境变量、Apifox 风格调试执行。"""
import json
import re
import time
import warnings

import requests
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.apitest import ApiCase, ApiEnv

router = APIRouter(prefix="/apitest", tags=["apitest"], dependencies=[Depends(get_current_user)])

# ---------- 序列化 ----------
def _case_out(c: ApiCase) -> dict:
    return {
        "id": c.id, "project_id": c.project_id, "name": c.name, "method": c.method,
        "url": c.url, "headers": _load_json(c.headers, []), "query": _load_json(c.query, []),
        "body_type": c.body_type, "body": c.body, "assertions": _load_json(c.assertions, []),
        "description": c.description, "enabled": c.enabled,
        "created_at": str(c.created_at) if c.created_at else None,
        "updated_at": str(c.updated_at) if c.updated_at else None,
    }


def _env_out(e: ApiEnv) -> dict:
    return {
        "id": e.id, "project_id": e.project_id, "name": e.name, "base_url": e.base_url,
        "variables": _load_json(e.variables, {}),
        "created_at": str(e.created_at) if e.created_at else None,
        "updated_at": str(e.updated_at) if e.updated_at else None,
    }


def _load_json(s, default):
    if not s:
        return default
    try:
        return json.loads(s)
    except Exception:
        return default


# ---------- 用例 CRUD ----------
@router.get("/cases")
def list_cases(project_id: int | None = None, keyword: str | None = None, db: Session = Depends(get_db)):
    q = db.query(ApiCase)
    if project_id:
        q = q.filter(ApiCase.project_id == project_id)
    if keyword:
        kw = f"%{keyword}%"
        q = q.filter(ApiCase.name.like(kw) | ApiCase.url.like(kw))
    return [_case_out(c) for c in q.order_by(ApiCase.id.desc()).all()]


@router.post("/cases", status_code=201)
def create_case(payload: dict, db: Session = Depends(get_db)):
    data = {
        "project_id": int(payload["project_id"]),
        "name": str(payload.get("name") or "未命名用例"),
        "method": str(payload.get("method") or "GET").upper(),
        "url": str(payload.get("url") or ""),
        "headers": json.dumps(payload.get("headers") or [], ensure_ascii=False),
        "query": json.dumps(payload.get("query") or [], ensure_ascii=False),
        "body_type": str(payload.get("body_type") or "none"),
        "body": str(payload.get("body") or ""),
        "assertions": json.dumps(payload.get("assertions") or [], ensure_ascii=False),
        "description": str(payload.get("description") or ""),
        "enabled": bool(payload.get("enabled", True)),
    }
    case = ApiCase(**data)
    db.add(case)
    db.commit()
    db.refresh(case)
    return _case_out(case)


@router.put("/cases/{case_id}")
def update_case(case_id: int, payload: dict, db: Session = Depends(get_db)):
    case = db.get(ApiCase, case_id)
    if not case:
        raise HTTPException(404, "用例不存在")
    if "name" in payload:
        case.name = str(payload["name"] or "未命名用例")
    if "method" in payload:
        case.method = str(payload["method"] or "GET").upper()
    if "url" in payload:
        case.url = str(payload.get("url") or "")
    if "headers" in payload:
        case.headers = json.dumps(payload["headers"] or [], ensure_ascii=False)
    if "query" in payload:
        case.query = json.dumps(payload["query"] or [], ensure_ascii=False)
    if "body_type" in payload:
        case.body_type = str(payload.get("body_type") or "none")
    if "body" in payload:
        case.body = str(payload.get("body") or "")
    if "assertions" in payload:
        case.assertions = json.dumps(payload["assertions"] or [], ensure_ascii=False)
    if "description" in payload:
        case.description = str(payload.get("description") or "")
    if "enabled" in payload:
        case.enabled = bool(payload["enabled"])
    db.commit()
    db.refresh(case)
    return _case_out(case)


@router.delete("/cases/{case_id}")
def delete_case(case_id: int, db: Session = Depends(get_db)):
    case = db.get(ApiCase, case_id)
    if not case:
        raise HTTPException(404, "用例不存在")
    db.delete(case)
    db.commit()
    return {"ok": True}


# ---------- 环境 CRUD ----------
@router.get("/envs")
def list_envs(project_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(ApiEnv)
    if project_id:
        q = q.filter(ApiEnv.project_id == project_id)
    return [_env_out(e) for e in q.order_by(ApiEnv.id.asc()).all()]


@router.post("/envs", status_code=201)
def create_env(payload: dict, db: Session = Depends(get_db)):
    env = ApiEnv(
        project_id=int(payload["project_id"]),
        name=str(payload.get("name") or "新环境"),
        base_url=str(payload.get("base_url") or ""),
        variables=json.dumps(payload.get("variables") or {}, ensure_ascii=False),
    )
    db.add(env)
    db.commit()
    db.refresh(env)
    return _env_out(env)


@router.put("/envs/{env_id}")
def update_env(env_id: int, payload: dict, db: Session = Depends(get_db)):
    env = db.get(ApiEnv, env_id)
    if not env:
        raise HTTPException(404, "环境不存在")
    if "name" in payload:
        env.name = str(payload.get("name") or "新环境")
    if "base_url" in payload:
        env.base_url = str(payload.get("base_url") or "")
    if "variables" in payload:
        env.variables = json.dumps(payload["variables"] or {}, ensure_ascii=False)
    db.commit()
    db.refresh(env)
    return _env_out(env)


@router.delete("/envs/{env_id}")
def delete_env(env_id: int, db: Session = Depends(get_db)):
    env = db.get(ApiEnv, env_id)
    if not env:
        raise HTTPException(404, "环境不存在")
    db.delete(env)
    db.commit()
    return {"ok": True}


# ---------- 执行引擎 ----------
_VAR_RE = re.compile(r"\{\{\s*([\w.]+)\s*\}\}")


def _resolve_vars(text: str, variables: dict) -> str:
    """替换 {{var}} 占位符；内置变量：{{$timestamp}} 秒、{{$timestamp_ms}} 毫秒、{{$random}} 随机串。"""
    def _rep(m):
        key = m.group(1)
        if key == "$timestamp":
            return str(int(time.time()))
        if key == "$timestamp_ms":
            return str(int(time.time() * 1000))
        if key == "$random":
            import uuid
            return uuid.uuid4().hex[:12]
        return str(variables.get(key, m.group(0)))
    return _VAR_RE.sub(_rep, text)


def _resolve_obj(obj, variables: dict):
    """对数组/字典递归替换变量。"""
    if isinstance(obj, dict):
        return {k: _resolve_obj(v, variables) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_resolve_obj(v, variables) for v in obj]
    if isinstance(obj, str):
        return _resolve_vars(obj, variables)
    return obj


def _path_get(data, path: str):
    """简易 JSON 路径：a.b.c、a[0].b，取不到返回 None。"""
    cur = data
    for seg in re.split(r"\.|\[|\]", path):
        if not seg:
            continue
        if isinstance(cur, dict):
            cur = cur.get(seg)
        elif isinstance(cur, list) and seg.isdigit():
            cur = cur[int(seg)] if int(seg) < len(cur) else None
        else:
            return None
        if cur is None:
            return None
    return cur


def _run_assertion(a: dict, status_code: int, body_text: str, json_data) -> dict:
    """执行单条断言。支持 type: status / json / text。"""
    a_type = a.get("type", "status")
    field = str(a.get("field") or "")
    op = a.get("operator", "==")
    want = str(a.get("value") or "")
    desc = f"{field or '状态码'} {op} {want}"
    if a_type == "status":
        actual = str(status_code)
        desc = f"状态码 {op} {want}"
    elif a_type == "json":
        actual = json.dumps(_path_get(json_data, field), ensure_ascii=False) if json_data is not None else ""
    else:  # text
        actual = body_text or ""
        desc = f"文本包含 {want}"
        op = "contains"
    ok = False
    try:
        if op == "==":
            ok = actual == want
        elif op == "!=":
            ok = actual != want
        elif op == "contains":
            ok = want in actual
        elif op == "not contains":
            ok = want not in actual
        elif op == "regex":
            ok = bool(re.search(want, actual))
    except Exception:
        ok = False
    return {"desc": desc, "ok": ok, "actual": str(actual)[:500]}


@router.post("/run")
def run_case(payload: dict):
    """执行接口调试/用例。body: {case: {...}, env: {base_url, variables}}。"""
    case = payload.get("case") or {}
    env = payload.get("env") or {}
    variables = env.get("variables") or {}
    if isinstance(variables, str):
        try:
            variables = json.loads(variables)
        except Exception:
            variables = {}
    method = str(case.get("method") or "GET").upper()
    url = _resolve_vars(str(case.get("url") or ""), variables)
    base_url = str(env.get("base_url") or "").rstrip("/")
    if url and not re.match(r"^https?://", url, re.I) and base_url:
        url = base_url + "/" + url.lstrip("/")
    if not url:
        raise HTTPException(400, "URL 不能为空")
    # 组装 Headers 与 Query（只取 enabled）
    headers = {}
    for h in _resolve_obj(case.get("headers") or [], variables):
        if isinstance(h, dict) and h.get("enabled", True) and h.get("key"):
            headers[str(h["key"])] = str(h.get("value") or "")
    params = []
    for q in _resolve_obj(case.get("query") or [], variables):
        if isinstance(q, dict) and q.get("enabled", True) and q.get("key"):
            params.append((str(q["key"]), str(q.get("value") or "")))
    body_type = str(case.get("body_type") or "none")
    body = _resolve_vars(str(case.get("body") or ""), variables)
    data = None
    json_data = None
    files = None
    if body_type == "json" and body.strip():
        try:
            json_data = json.loads(body)
        except Exception:
            json_data = None
            data = body
    elif body_type == "form":
        data = {}
        for pair in body.split("&"):
            if "=" in pair:
                k, v = pair.split("=", 1)
                data[k] = v
    elif body_type == "raw" and body:
        data = body

    warnings.filterwarnings("ignore")
    t0 = time.perf_counter()
    error = None
    try:
        resp = requests.request(
            method, url, headers=headers or None, params=params or None,
            data=data, json=json_data, timeout=30, verify=False,
        )
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        resp_headers = {k: v for k, v in resp.headers.items()}
        body_text = resp.text
        try:
            resp_json = resp.json()
        except Exception:
            resp_json = None
        result = {
            "ok": True, "status_code": resp.status_code, "elapsed_ms": elapsed_ms,
            "size_bytes": len(resp.content), "response_headers": resp_headers,
            "response_body": body_text, "response_json": resp_json,
            "error": None,
        }
    except requests.RequestException as e:
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        error = f"{type(e).__name__}: {e}"
        result = {
            "ok": False, "status_code": None, "elapsed_ms": elapsed_ms,
            "size_bytes": 0, "response_headers": {}, "response_body": "", "response_json": None,
            "error": error,
        }
    # 断言
    assertion_results = []
    if result["ok"]:
        for a in case.get("assertions") or []:
            if isinstance(a, dict):
                assertion_results.append(_run_assertion(a, result["status_code"], result["response_body"], result["response_json"]))
    result["assertions"] = assertion_results
    result["all_passed"] = all(x.get("ok") for x in assertion_results) if assertion_results else None
    return result
