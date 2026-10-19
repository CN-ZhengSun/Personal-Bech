from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.bug import Bug, BugComment
from app.models.execution import TestExecution
from app.schemas.bug import BugCommentCreate, BugCommentOut, BugCreate, BugOut, BugUpdate

router = APIRouter(prefix="/bugs", tags=["bugs"], dependencies=[Depends(get_current_user)])

# 缺陷状态流转集合（图1）
BUG_STATUSES = ("to_fix", "fixing", "fixed", "verified", "cant_fix", "wont_fix", "by_design", "reopen")
# 仅以下状态允许编辑已提交的内容
EDITABLE_STATUSES = ("to_fix", "reopen")
# 内容字段（状态流转之外的编辑项）
CONTENT_FIELDS = ("title", "description", "steps", "severity", "priority", "probability",
                  "module", "version", "environment", "assignee", "attachments")
# 状态中文名（用于流转记录）
STATUS_TEXT = {
    "to_fix": "待修复", "fixing": "修复中", "fixed": "已修复", "verified": "验证通过",
    "cant_fix": "无法修复", "wont_fix": "暂不修复", "by_design": "设计如此", "reopen": "重新打开",
}


@router.get("", response_model=list[BugOut])
def list_bugs(
    project_id: int | None = None,
    status: str | None = None,
    severity: str | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(Bug)
    if project_id:
        q = q.filter(Bug.project_id == project_id)
    if status:
        q = q.filter(Bug.status == status)
    if severity:
        q = q.filter(Bug.severity == severity)
    return q.order_by(Bug.id.desc()).limit(500).all()


@router.post("", response_model=BugOut, status_code=201)
def create_bug(payload: BugCreate, user=Depends(get_current_user), db: Session = Depends(get_db)):
    if payload.status not in BUG_STATUSES:
        raise HTTPException(status_code=422, detail="非法缺陷状态")
    bug = Bug(**payload.model_dump())
    db.add(bug)
    db.flush()
    # 自动写入创建流转记录
    db.add(BugComment(bug_id=bug.id, user=user.display_name or user.username,
                      event_type="created", content="创建缺陷"))
    db.commit()
    db.refresh(bug)
    return bug


@router.get("/{bug_id}", response_model=BugOut)
def get_bug(bug_id: int, db: Session = Depends(get_db)):
    bug = db.get(Bug, bug_id)
    if not bug:
        raise HTTPException(status_code=404, detail="缺陷不存在")
    return bug


@router.patch("/{bug_id}", response_model=BugOut)
def update_bug(bug_id: int, payload: BugUpdate, user=Depends(get_current_user), db: Session = Depends(get_db)):
    bug = db.get(Bug, bug_id)
    if not bug:
        raise HTTPException(status_code=404, detail="缺陷不存在")
    data = payload.model_dump(exclude_none=True)
    if not data:
        return bug
    if "status" in data and data["status"] not in BUG_STATUSES:
        raise HTTPException(status_code=422, detail="非法缺陷状态")
    # 内容编辑仅限「待修复 / 重新打开」状态；状态流转本身始终允许
    content_changed = any(k in CONTENT_FIELDS for k in data)
    if content_changed and bug.status not in EDITABLE_STATUSES:
        raise HTTPException(status_code=403, detail="仅「待修复 / 重新打开」状态的缺陷允许编辑内容")
    old_status = bug.status
    for k, v in data.items():
        setattr(bug, k, v)
    # 状态变更时自动写入流转记录
    if "status" in data and data["status"] != old_status:
        db.add(BugComment(bug_id=bug.id, user=user.display_name or user.username,
                          event_type="status", content=f"状态变更：{STATUS_TEXT.get(old_status, old_status)} → {STATUS_TEXT.get(data['status'], data['status'])}"))
    db.commit()
    db.refresh(bug)
    return bug


@router.delete("/{bug_id}", status_code=204)
def delete_bug(bug_id: int, db: Session = Depends(get_db)):
    bug = db.get(Bug, bug_id)
    if not bug:
        raise HTTPException(status_code=404, detail="缺陷不存在")
    db.query(BugComment).filter(BugComment.bug_id == bug_id).delete()
    db.delete(bug)
    db.commit()


# ---------------- 评论/流转记录 ----------------

@router.get("/{bug_id}/comments", response_model=list[BugCommentOut])
def list_comments(bug_id: int, db: Session = Depends(get_db)):
    return db.query(BugComment).filter(BugComment.bug_id == bug_id).order_by(BugComment.id).all()


@router.post("/{bug_id}/comments", response_model=BugCommentOut, status_code=201)
def add_comment(bug_id: int, payload: BugCommentCreate, user=Depends(get_current_user), db: Session = Depends(get_db)):
    if not db.get(Bug, bug_id):
        raise HTTPException(status_code=404, detail="缺陷不存在")
    comment = BugComment(bug_id=bug_id, user=payload.user or user.display_name or user.username,
                         event_type=payload.event_type or "comment", content=payload.content)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


# ---------------- 从执行记录提交缺陷 ----------------

@router.post("/from-execution", response_model=BugOut, status_code=201)
def create_bug_from_execution(exec_id: int, title: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    """从一条失败的执行记录快速创建缺陷并回填关联。"""
    rec = db.get(TestExecution, exec_id)
    if not rec:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    bug = Bug(
        project_id=1,
        case_id=rec.case_id,
        title=title,
        description=rec.actual_result,
        steps=rec.fail_reason,
        severity="major",
        status="to_fix",
        probability="always",
        reporter=rec.assignee,
        attachments=rec.evidence,  # 执行附件一并带入缺陷
    )
    db.add(bug)
    db.flush()
    db.add(BugComment(bug_id=bug.id, user=user.display_name or user.username,
                      event_type="created", content="从执行记录创建缺陷"))
    rec.bug_id = bug.id
    db.commit()
    db.refresh(bug)
    return bug
