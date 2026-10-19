import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, File

from app.core.security import get_current_user

router = APIRouter(prefix="/upload", tags=["upload"], dependencies=[Depends(get_current_user)])

# 上传目录：backend/app/uploads（与当前运行环境保持一致）
UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_SIZE = 100 * 1024 * 1024  # 100MB

ALLOWED_EXT = {
    "png", "jpg", "jpeg", "gif", "webp", "bmp",
    "pdf", "txt", "log", "md",
    "doc", "docx", "xls", "xlsx", "ppt", "pptx",
    "zip", "rar", "7z", "mp4", "mp3", "xmind",
}

# 允许的子目录白名单（防路径穿越）
ALLOWED_SUBDIRS = {"knowledge"}


def _safe_ext(filename: str) -> str:
    ext = Path(filename).suffix.lower().lstrip(".")
    return ext if ext in ALLOWED_EXT else ""


@router.post("")
async def upload_file(file: UploadFile = File(...), subdir: str = Form("")):
    """通用附件上传，保存到 uploads/[subdir]/ 并返回可访问 URL。"""
    ext = _safe_ext(file.filename or "")
    if not ext:
        raise HTTPException(status_code=400, detail="不支持的文件类型，仅支持图片/文档/压缩包等常见格式")

    sub = subdir.strip().strip("/")
    if sub and sub not in ALLOWED_SUBDIRS:
        raise HTTPException(status_code=400, detail="不允许的上传目录")
    target_dir = (UPLOAD_DIR / sub) if sub else UPLOAD_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    name = f"{uuid.uuid4().hex}.{ext}"
    target = target_dir / name
    size = 0
    try:
        with open(target, "wb") as f:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_SIZE:
                    raise HTTPException(status_code=413, detail="文件超过 100MB 限制")
                f.write(chunk)
        if size == 0:
            raise HTTPException(status_code=400, detail="文件内容为空")
    except Exception:
        target.unlink(missing_ok=True)
        raise

    url = f"/uploads/{sub + '/' if sub else ''}{name}"
    return {"url": url, "filename": file.filename, "size": size}
