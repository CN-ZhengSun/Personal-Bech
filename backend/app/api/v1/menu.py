from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.menu import MenuConfig

router = APIRouter(prefix="/menu-config", tags=["menu"], dependencies=[Depends(get_current_user)])

# 内置默认菜单：分组行与菜单行按显示顺序排列（sort_order 从 10 起每行 +10）
DEFAULT_MENU = [
    # 测试管理
    {"menu_key": None, "name": "测试管理", "group_key": "test_manage", "is_group": True, "sort_order": 10},
    {"menu_key": "/requirements", "name": "需求 PRD", "group_key": "test_manage", "is_group": False, "sort_order": 20},
    {"menu_key": "/cases", "name": "测试用例", "group_key": "test_manage", "is_group": False, "sort_order": 30},
    {"menu_key": "/executions", "name": "测试执行", "group_key": "test_manage", "is_group": False, "sort_order": 40},
    {"menu_key": "/bugs", "name": "缺陷跟踪", "group_key": "test_manage", "is_group": False, "sort_order": 50},
    {"menu_key": "/projects", "name": "项目管理", "group_key": "test_manage", "is_group": False, "sort_order": 60},
    {"menu_key": "/report", "name": "质量报表", "group_key": "test_manage", "is_group": False, "sort_order": 70},
    {"menu_key": "/automation", "name": "自动化脚本", "group_key": "test_manage", "is_group": False, "sort_order": 80},
    {"menu_key": "/releases", "name": "版本与环境", "group_key": "test_manage", "is_group": False, "sort_order": 90},
    # 测试工具
    {"menu_key": None, "name": "测试工具", "group_key": "test_tools", "is_group": True, "sort_order": 100},
    {"menu_key": "/apitest", "name": "接口测试工具", "group_key": "test_tools", "is_group": False, "sort_order": 110},
    {"menu_key": "/tracking", "name": "埋点监控", "group_key": "test_tools", "is_group": False, "sort_order": 120},
    {"menu_key": "/adbtools", "name": "ADB 工具", "group_key": "test_tools", "is_group": False, "sort_order": 130},
    {"menu_key": "/jmeter", "name": "JMeter 工具", "group_key": "test_tools", "is_group": False, "sort_order": 135},
    # 资产与 AI
    {"menu_key": None, "name": "资产与 AI", "group_key": "assets_ai", "is_group": True, "sort_order": 140},
    {"menu_key": "/knowledge", "name": "知识库", "group_key": "assets_ai", "is_group": False, "sort_order": 150},
    {"menu_key": "/skills", "name": "SKILL 管理", "group_key": "assets_ai", "is_group": False, "sort_order": 160},
    {"menu_key": "/ai", "name": "AI 模型配置", "group_key": "assets_ai", "is_group": False, "sort_order": 170},
    {"menu_key": "/menu-manage", "name": "菜单管理", "group_key": "assets_ai", "is_group": False, "sort_order": 180},
]


class MenuRowIn(BaseModel):
    menu_key: str | None = None
    name: str
    group_key: str | None = None
    is_group: bool = False
    sort_order: int = 0


def _seed_defaults(db: Session) -> None:
    """表为空时写入内置默认配置。"""
    if db.query(MenuConfig).count() == 0:
        for row in DEFAULT_MENU:
            db.add(MenuConfig(**row))
        db.commit()


@router.get("")
def list_menu_config(db: Session = Depends(get_db)):
    _seed_defaults(db)
    rows = db.query(MenuConfig).order_by(MenuConfig.sort_order, MenuConfig.id).all()
    return [
        {
            "id": r.id,
            "menu_key": r.menu_key,
            "name": r.name,
            "group_key": r.group_key,
            "is_group": r.is_group,
            "sort_order": r.sort_order,
        }
        for r in rows
    ]


@router.put("")
def save_menu_config(payload: list[MenuRowIn], db: Session = Depends(get_db)):
    """全量保存：按提交顺序整体替换菜单配置。"""
    # 校验：分组行必须带 group_key 且不重名（同一分组只出现一次）
    seen_groups = set()
    for row in payload:
        if row.is_group:
            if not row.group_key or row.group_key in seen_groups:
                raise HTTPException(status_code=400, detail="分组配置不合法：分组标识缺失或重复")
            seen_groups.add(row.group_key)
    # 校验通过后事务替换
    db.query(MenuConfig).delete()
    for i, row in enumerate(payload):
        db.add(
            MenuConfig(
                menu_key=row.menu_key,
                name=row.name.strip() or "未命名",
                group_key=row.group_key,
                is_group=row.is_group,
                sort_order=row.sort_order if row.sort_order else (i + 1) * 10,
            )
        )
    db.commit()
    return {"status": "ok", "count": len(payload)}
