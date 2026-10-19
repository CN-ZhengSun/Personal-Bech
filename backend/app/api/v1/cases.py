import csv
import io
import os
import re

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.testcase import CaseRequirement, TestCase, TestCaseStep
from app.models.execution import TestExecution
from app.models.bug import Bug
from app.models.automation import AutomationScript
from app.schemas.testcase import (
    CaseDetailOut,
    TestCaseCreate,
    TestCaseOut,
    TestCaseUpdate,
)

router = APIRouter(prefix="/cases", tags=["cases"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[TestCaseOut])
def list_cases(project_id: int | None = None, module: str | None = None, db: Session = Depends(get_db)):
    q = db.query(TestCase)
    if project_id:
        q = q.filter(TestCase.project_id == project_id)
    if module:
        q = q.filter(TestCase.module == module)
    return q.order_by(TestCase.id.desc()).all()


@router.post("", response_model=CaseDetailOut, status_code=201)
def create_case(payload: TestCaseCreate, db: Session = Depends(get_db)):
    steps = payload.steps
    req_ids = payload.requirement_ids
    data = payload.model_dump(exclude={"steps", "requirement_ids"})
    case = TestCase(**data)
    db.add(case)
    db.flush()
    for s in steps:
        db.add(TestCaseStep(case_id=case.id, step_no=s.step_no, action=s.action, expected=s.expected))
    for rid in req_ids:
        db.add(CaseRequirement(case_id=case.id, requirement_id=rid))
    db.commit()
    db.refresh(case)
    return _detail(db, case.id)


# ---------- 用例导入 / 模板 ----------
_TYPE_MAP = {"功能": "functional", "functional": "functional", "ui": "ui", "接口": "api", "api": "api", "性能": "performance", "performance": "performance", "其他": "other", "other": "other"}
_STATUS_MAP = {"启用": "active", "active": "active", "废弃": "deprecated", "deprecated": "deprecated"}
_ENV_MAP = {"开发环境": "dev", "dev": "dev", "测试环境": "test", "test": "test", "预发布": "staging", "staging": "staging", "生产环境": "prod", "prod": "prod"}
_COL_ALIASES = {
    "title": ["标题", "用例标题", "用例名称", "标题用例", "标题（用例）", "标题(用例)"],
    "module": ["所属模块", "模块", "模块名称"],
    "priority": ["优先级", "用例优先级"],
    "case_type": ["类型", "用例类型"],
    "status": ["状态", "用例状态"],
    "environment": ["环境", "执行环境"],
    "version": ["版本", "用例版本", "适用版本"],
    "preconditions": ["前置条件", "前置", "预置条件"],
    "action": ["操作步骤", "操作", "步骤", "操作步骤动作", "操作步骤(动作)"],
    "expected": ["预期结果", "预期", "期望结果", "预期结果期望", "预期结果(期望)"],
}


def _norm(s):
    return re.sub(r"[\s*()（）]", "", str(s or "")).lower()


def _map_header(header):
    colmap = {}
    for field, aliases in _COL_ALIASES.items():
        for al in aliases:
            a = _norm(al)
            if a in header:
                colmap[field] = header.index(a)
                break
    return colmap


def _split_steps(text: str) -> list[str]:
    """把单元格内多步骤文本拆成步骤列表。

    支持两种分隔方式：
    - 换行分隔：每行一个步骤（可带序号，如 "1. xxx" / "2、xxx"）
    - 未换行的连续序号（如 "1.xxx 2.xxx" 也在同一行时按序号切分）
    """
    if not text:
        return []
    lines = [ln.strip() for ln in re.split(r"[\r\n]+", text) if ln.strip()]
    out = []
    for ln in lines:
        m = re.match(r"^\d+\s*[.、)．]\s*", ln)
        if m:
            ln = ln[m.end():].strip()
        out.append(ln)
    return out


def _parse_file(raw: bytes, ext: str) -> list[list]:
    if ext == ".csv":
        for enc in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
            try:
                text = raw.decode(enc)
                return list(csv.reader(io.StringIO(text)))
            except (UnicodeDecodeError, csv.Error):
                continue
        raise HTTPException(status_code=400, detail="CSV 编码无法识别（支持 UTF-8 / GBK）")
    if ext in (".xlsx", ".xlsm"):
        import openpyxl

        wb = openpyxl.load_workbook(io.BytesIO(raw), data_only=True)
        ws = wb.active
        return [[c.value if c.value is not None else "" for c in row] for row in ws.iter_rows()]
    if ext == ".xls":
        import xlrd

        book = xlrd.open_workbook(file_contents=raw)
        sh = book.sheet_by_index(0)
        return [[sh.cell_value(r, c) for c in range(sh.ncols)] for r in range(sh.nrows)]
    raise HTTPException(status_code=400, detail="仅支持 xls / xlsx / csv 格式")


@router.post("/import")
def import_cases(project_id: int = Query(...), file: UploadFile = File(...), db: Session = Depends(get_db)):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in (".xls", ".xlsx", ".xlsm", ".csv"):
        raise HTTPException(status_code=400, detail="仅支持 xls / xlsx / csv 格式")
    rows = _parse_file(file.file.read(), ext)
    if len(rows) < 2:
        raise HTTPException(status_code=400, detail="文件缺少表头或数据行为空")
    colmap = _map_header([_norm(c) for c in rows[0]])
    if "title" not in colmap:
        raise HTTPException(status_code=400, detail="未识别到「标题」列，请使用模板格式")

    def gv(row, field):
        idx = colmap.get(field)
        if idx is None or idx >= len(row):
            return ""
        v = str(row[idx] or "").strip()
        return v

    cases_data = []  # [{title,module,priority,case_type,status,environment,version,preconditions, steps:[[action,expected],...]}]
    cur = None
    for row in rows[1:]:
        if not any((str(x or "").strip() for x in row)):
            continue
        title = gv(row, "title")
        action = gv(row, "action")
        expected = gv(row, "expected")
        if title:
            cur = {
                "title": title,
                "module": gv(row, "module") or None,
                "priority": (gv(row, "priority") or "P1").upper(),
                "case_type": _TYPE_MAP.get(gv(row, "case_type"), "functional"),
                "status": _STATUS_MAP.get(gv(row, "status"), "active"),
                "environment": _ENV_MAP.get(gv(row, "environment")) or (gv(row, "environment") or None),
                "version": gv(row, "version") or None,
                "preconditions": gv(row, "preconditions"),
                "expected": "",
                "steps": [],
            }
            cases_data.append(cur)
        elif cur is None:
            continue  # 无标题且无当前用例，跳过
        # 操作步骤按序号+换行拆分为多个步骤；预期结果为最终结果，整体保存（不按步骤拆分）
        cur["expected"] = expected
        for a in _split_steps(action):
            cur["steps"].append([a, ""])

    imported = 0
    errors = []
    for c in cases_data:
        if not c["title"]:
            errors.append("存在空标题用例")
            continue
        try:
            if c["priority"] not in ("P0", "P1", "P2", "P3"):
                c["priority"] = "P1"
            case = TestCase(
                project_id=project_id, module=c["module"], title=c["title"],
                preconditions=c["preconditions"], expected=c["expected"], priority=c["priority"],
                case_type=c["case_type"], status=c["status"],
                environment=c["environment"], version=c["version"],
            )
            db.add(case)
            db.flush()
            for i, (a, e) in enumerate(c["steps"], start=1):
                db.add(TestCaseStep(case_id=case.id, step_no=i, action=a, expected=e))
            imported += 1
        except Exception as ex:  # noqa: BLE001
            db.rollback()
            errors.append(f"{c['title']}: {ex}")
    db.commit()
    return {"imported": imported, "skipped": len(cases_data) - imported, "errors": errors[:50]}


@router.get("/template")
def case_template():
    import openpyxl
    from openpyxl.styles import Font, PatternFill

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "用例导入模板"
    headers = ["标题", "所属模块", "优先级", "类型", "状态", "环境", "版本", "前置条件", "操作步骤", "预期结果"]
    ws.append(headers)
    ws.append(["示例：登录成功校验", "登录模块", "P1", "功能", "启用", "测试环境", "v1.0", "已部署测试环境",
               "1.打开登录页\n2.输入正确账号密码\n3.点击登录", "1.登录页正常显示\n2.密码正常回显\n3.登录成功进入首页"])
    ws.append(["说明：", "操作步骤/预期结果写在同一单元格内，", "用序号（1. 2. 3.）加换行区分多个步骤，", "", "两个单元格按行数一一对应", "", "", "", "", ""])
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="2563EB")
    for col, w in zip("ABCDEFGHIJ", (24, 14, 10, 10, 10, 12, 10, 22, 40, 40)):
        ws.column_dimensions[col].width = w
    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    return StreamingResponse(
        bio,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename*=UTF-8''%E7%94%A8%E4%BE%8B%E5%AF%BC%E5%85%A5%E6%A8%A1%E6%9D%BF.xlsx"},
    )


@router.get("/{case_id}", response_model=CaseDetailOut)
def get_case(case_id: int, db: Session = Depends(get_db)):
    case = db.get(TestCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="用例不存在")
    return _detail(db, case_id)


@router.patch("/{case_id}", response_model=CaseDetailOut)
def update_case(case_id: int, payload: TestCaseUpdate, db: Session = Depends(get_db)):
    case = db.get(TestCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="用例不存在")
    data = payload.model_dump(exclude_none=True)
    steps = data.pop("steps", None)
    for k, v in data.items():
        setattr(case, k, v)
    if steps is not None:
        db.query(TestCaseStep).filter(TestCaseStep.case_id == case_id).delete()
        for i, s in enumerate(steps, start=1):
            db.add(TestCaseStep(case_id=case_id, step_no=s.get("step_no") or i, action=s.get("action", "") or "", expected=s.get("expected", "") or ""))
    db.commit()
    db.refresh(case)
    return _detail(db, case_id)


@router.delete("/{case_id}", status_code=204)
def delete_case(case_id: int, db: Session = Depends(get_db)):
    case = db.get(TestCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="用例不存在")
    # 级联清理关联数据：执行记录随用例删除；缺陷/自动化脚本保留但解除关联
    db.query(TestCaseStep).filter(TestCaseStep.case_id == case_id).delete()
    db.query(CaseRequirement).filter(CaseRequirement.case_id == case_id).delete()
    db.query(TestExecution).filter(TestExecution.case_id == case_id).delete()
    db.query(Bug).filter(Bug.case_id == case_id).update({Bug.case_id: None})
    db.query(AutomationScript).filter(AutomationScript.case_id == case_id).update({AutomationScript.case_id: None})
    db.delete(case)
    db.commit()


def _detail(db: Session, case_id: int) -> CaseDetailOut:
    case = db.get(TestCase, case_id)
    steps = db.query(TestCaseStep).filter(TestCaseStep.case_id == case_id).order_by(TestCaseStep.step_no).all()
    req_ids = [r.requirement_id for r in db.query(CaseRequirement).filter(CaseRequirement.case_id == case_id).all()]
    out = CaseDetailOut.model_validate(case)
    out.steps = steps
    out.requirement_ids = req_ids
    return out
