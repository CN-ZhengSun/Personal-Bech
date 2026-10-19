from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.bug import Bug
from app.models.execution import TestExecution
from app.models.prd import Requirement
from app.models.testcase import CaseRequirement, TestCase

router = APIRouter(prefix="/dashboard", tags=["dashboard"], dependencies=[Depends(get_current_user)])


@router.get("/summary")
def summary(project_id: int | None = None, module: str | None = None, db: Session = Depends(get_db)):
    """质量看板总览（所有统计均按 project_id 过滤，百分比不会超过 100%）。"""
    def cnt(model):
        q = db.query(func.count(model.id))
        if project_id and hasattr(model, "project_id"):
            q = q.filter(model.project_id == project_id)
        return q.scalar() or 0

    req_total = cnt(Requirement)
    case_total = cnt(TestCase)
    bug_total = cnt(Bug)

    # 当前项目下的用例 id 集合（用于过滤执行记录，执行表本身无 project_id）
    project_case_ids = None
    if project_id:
        project_case_ids = [cid for (cid,) in db.query(TestCase.id).filter(TestCase.project_id == project_id).all()]

    exec_q = db.query(TestExecution)
    if project_id is not None:
        exec_q = exec_q.filter(TestExecution.case_id.in_(project_case_ids)) if project_case_ids else exec_q.filter(TestExecution.id.is_(None))
    execs = exec_q.all()

    exec_counts = {"pass": 0, "fail": 0, "blocked": 0, "skipped": 0, "untested": 0}
    for e in execs:
        exec_counts[e.status] = exec_counts.get(e.status, 0) + 1
    exec_total = sum(exec_counts.values())
    executed_cnt = exec_counts["pass"] + exec_counts["fail"] + exec_counts["blocked"] + exec_counts["skipped"]

    # 未关闭缺陷：待修复/修复中/已修复/重新打开（终态：验证通过/无法修复/暂不修复/设计如此）
    bug_q = db.query(func.count(Bug.id)).filter(Bug.status.in_(["to_fix", "fixing", "fixed", "reopen"]))
    if project_id:
        bug_q = bug_q.filter(Bug.project_id == project_id)
    open_bugs = bug_q.scalar() or 0

    # 需求覆盖率：当前项目内有关联用例的需求数 / 需求总数
    linked_req_q = db.query(CaseRequirement.requirement_id).join(Requirement, Requirement.id == CaseRequirement.requirement_id)
    if project_id:
        linked_req_q = linked_req_q.filter(Requirement.project_id == project_id)
    linked_req = linked_req_q.distinct().count()
    req_coverage = round(linked_req / req_total * 100, 1) if req_total else 0

    # 缺陷严重程度分布（可按模块过滤）
    sev_dist = {}
    sev_q = db.query(Bug.severity, func.count(Bug.id))
    if project_id:
        sev_q = sev_q.filter(Bug.project_id == project_id)
    if module:
        sev_q = sev_q.filter(Bug.module == module)
    for row in sev_q.group_by(Bug.severity).all():
        sev_dist[row[0]] = row[1]

    # 缺陷所属模块列表（用于严重程度饼图按模块筛选）
    mod_q = db.query(Bug.module).filter(Bug.module.isnot(None), Bug.module != "")
    if project_id:
        mod_q = mod_q.filter(Bug.project_id == project_id)
    bug_modules = sorted({m for (m,) in mod_q.all()})

    # 缺陷状态分布（按项目过滤）
    status_dist = {}
    st_q = db.query(Bug.status, func.count(Bug.id))
    if project_id:
        st_q = st_q.filter(Bug.project_id == project_id)
    for row in st_q.group_by(Bug.status).all():
        status_dist[row[0]] = row[1]

    return {
        "requirement_total": req_total,
        "case_total": case_total,
        "bug_total": bug_total,
        "open_bugs": open_bugs,
        "exec_total": exec_total,
        "exec_counts": exec_counts,
        # 用例执行率 = 已执行的用例数 / 用例总数（≤100%）
        "exec_rate": round(executed_cnt / case_total * 100, 1) if case_total else 0,
        # 用例通过率 = 通过的执行记录 / 已执行的执行记录
        "pass_rate": round(exec_counts["pass"] / executed_cnt * 100, 1) if executed_cnt else 0,
        "req_coverage": req_coverage,
        "severity_dist": sev_dist,
        "bug_status_dist": status_dist,
        "bug_modules": bug_modules,
    }
