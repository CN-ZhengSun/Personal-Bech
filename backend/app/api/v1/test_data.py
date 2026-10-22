from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.core.security import get_current_user
from app.services.test_data import (
    GenerationRequest,
    capabilities,
    get_job,
    list_jobs,
    plan_generation,
    start_job,
    stop_job,
)


router = APIRouter(prefix="/test-data", tags=["test-data"], dependencies=[Depends(get_current_user)])


class StartRequest(BaseModel):
    spec: GenerationRequest
    confirmation_text: str = ""


@router.get("/capabilities")
def get_capabilities():
    return capabilities()


@router.post("/plan")
def plan(payload: GenerationRequest):
    try:
        return plan_generation(payload)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/jobs")
def jobs():
    return list_jobs()


@router.post("/jobs", status_code=202)
def create_job(payload: StartRequest):
    try:
        return start_job(payload.spec, payload.confirmation_text)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/jobs/{job_id}")
def job_status(job_id: str):
    try:
        job = get_job(job_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if job is None:
        raise HTTPException(404, "任务不存在")
    return job


@router.post("/jobs/{job_id}/stop")
def stop(job_id: str):
    try:
        job = stop_job(job_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if job is None:
        raise HTTPException(404, "任务不存在")
    return job


@router.get("/jobs/{job_id}/manifest")
def manifest(job_id: str):
    try:
        job = get_job(job_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if job is None:
        raise HTTPException(404, "任务不存在")
    path = Path(job["manifest_path"])
    if path != Path(job["output_dir"]) / "manifest.json":
        raise HTTPException(404, "任务清单路径无效")
    if not path.is_file():
        raise HTTPException(404, "任务清单尚未生成")
    return FileResponse(path, media_type="application/json", filename=f"test-data-{job_id}.json",
                        content_disposition_type="inline")
