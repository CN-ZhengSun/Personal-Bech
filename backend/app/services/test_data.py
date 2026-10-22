"""Local synthetic test-data jobs. Every run writes to a new directory."""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import random
import secrets
import shutil
import subprocess
import threading
import time
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

MIB = 1024 * 1024
GIB = 1024 * MIB
UPLOAD_DIR = Path(__file__).resolve().parents[1] / "uploads"
JOBS_DIR = UPLOAD_DIR / "test_data_jobs"
DEFAULT_OUTPUT = UPLOAD_DIR
_lock = threading.Lock()
_jobs: dict[str, dict] = {}
_stop_events: dict[str, threading.Event] = {}
_active_id: str | None = None
_TEXT_ALPHABET = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 .,-_\n"
_TEXT_TRANSLATION = bytes(_TEXT_ALPHABET[value % len(_TEXT_ALPHABET)] for value in range(256))


class GenerationRequest(BaseModel):
    kind: Literal["image", "video", "audio", "file"]
    count: int = Field(ge=1, le=50000)
    size_mib: float = Field(gt=0, le=2048)
    output_dir: str = Field(min_length=1, max_length=1024)
    format: Literal["jpg", "png", "mp4", "mp3", "bin", "txt"]
    duration_seconds: int = Field(default=10, ge=1, le=600)
    similarity_percent: int = Field(default=0, ge=0, le=100)

    @model_validator(mode="after")
    def check_kind_limits(self):
        limits = {
            "image": ({"jpg", "png"}, 10000, 0.02, 10),
            "video": ({"mp4"}, 5000, 0.2, 100),
            "audio": ({"mp3"}, 10000, 0.05, 20),
            "file": ({"bin", "txt"}, 50000, 0.001, 2048),
        }
        formats, max_count, min_size, max_size = limits[self.kind]
        if self.format not in formats or self.count > max_count or not min_size <= self.size_mib <= max_size:
            raise ValueError("格式、数量或单文件大小不适用于所选类型")
        if not math.isfinite(self.size_mib):
            raise ValueError("文件大小必须是有限数值")
        if self.kind in ("video", "audio") and self.similarity_percent:
            raise ValueError("相似度目前仅适用于图片和普通文件")
        if self.kind == "video":
            bitrate = self.size_mib * MIB * 8 / self.duration_seconds - 96000
            if not 150_000 <= bitrate <= 12_000_000:
                raise ValueError("视频目标大小与时长不匹配，请调整到约 0.15–12 Mbps")
        if self.kind == "audio":
            bitrate = self.size_mib * MIB * 8 / self.duration_seconds
            if not 32_000 <= bitrate <= 320_000:
                raise ValueError("音频目标大小与时长不匹配，请调整到约 32–320 kbps")
        return self


def _output_directory(raw: str) -> Path:
    path = Path(raw.strip())
    if not path.is_absolute() or str(path) == path.anchor or str(path.anchor).startswith("\\\\"):
        raise ValueError("请选择本机已有的具体目录，不能使用磁盘根目录或网络共享")
    if not path.is_dir():
        raise ValueError("保存目录不存在或不可访问")
    # Reject symlinks and Windows junctions before resolving the path.
    for part in (path, *path.parents):
        try:
            attrs = part.lstat()
        except OSError as exc:
            raise ValueError("无法检查保存目录") from exc
        if part.is_symlink() or getattr(attrs, "st_file_attributes", 0) & 0x400:
            raise ValueError("保存路径不能经过符号链接或目录联接")
    return path.resolve(strict=True)


def plan_generation(spec: GenerationRequest) -> dict:
    directory = _output_directory(spec.output_dir)
    target_bytes = round(spec.size_mib * MIB)
    estimated_bytes = target_bytes * spec.count
    if estimated_bytes > 20 * GIB:
        raise ValueError("单次任务预估超过 20 GiB，请拆分批次")
    free_bytes = shutil.disk_usage(directory).free
    required_bytes = math.ceil(estimated_bytes * 1.25) + 512 * MIB
    needs_confirmation = estimated_bytes > GIB or spec.count >= 1000
    return {
        "output_dir": str(directory),
        "target_bytes_each": target_bytes,
        "estimated_bytes": estimated_bytes,
        "required_bytes": required_bytes,
        "free_bytes": free_bytes,
        "can_run": free_bytes >= required_bytes,
        "needs_confirmation": needs_confirmation,
        "confirmation_text": f"CONFIRM {spec.kind} {spec.count} {estimated_bytes}" if needs_confirmation else "",
        "size_note": "普通文件按字节精确生成；图片、视频和音频为目标大小，实际大小可能不同。",
    }


def capabilities() -> dict:
    return {
        "default_output_dir": str(DEFAULT_OUTPUT),
        "ffmpeg": bool(shutil.which("ffmpeg")),
        "ffprobe": bool(shutil.which("ffprobe")),
        "pillow": _has_pillow(),
    }


def _has_pillow() -> bool:
    try:
        import PIL  # noqa: F401
        return True
    except ImportError:
        return False


def _job_file(job_id: str) -> Path:
    if len(job_id) != 32 or any(c not in "0123456789abcdef" for c in job_id):
        raise ValueError("任务 ID 不合法")
    return JOBS_DIR / f"{job_id}.json"


def _save_job(job: dict) -> None:
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    path = _job_file(job["id"])
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps({k: v for k, v in job.items() if k != "files"}, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def _public_job(job: dict) -> dict:
    return {k: v for k, v in job.items() if k != "files"}


def _read_job(job_id: str) -> dict | None:
    path = _job_file(job_id)
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("state") in ("running", "stopping"):
        data["state"] = "interrupted"
        data["error"] = "工作台进程重启，任务是否完成未知；请检查输出目录。"
    return data


def get_job(job_id: str) -> dict | None:
    with _lock:
        if job_id in _jobs:
            return _public_job(_jobs[job_id]).copy()
    return _read_job(job_id)


def list_jobs() -> list[dict]:
    if not JOBS_DIR.is_dir():
        return []
    result = []
    for path in sorted(JOBS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:50]:
        try:
            job = get_job(path.stem)
            if job:
                result.append(job)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
    return result


def start_job(spec: GenerationRequest, confirmation_text: str = "") -> dict:
    global _active_id
    plan = plan_generation(spec)
    if not plan["can_run"]:
        raise ValueError("保存盘空间不足，需保留 512 MiB 空闲并预留生成缓冲")
    if plan["needs_confirmation"] and confirmation_text != plan["confirmation_text"]:
        raise ValueError("大任务确认文字不匹配")
    if spec.kind == "image" and not _has_pillow():
        raise ValueError("图片生成需要安装 Pillow")
    if spec.kind in ("video", "audio") and (not shutil.which("ffmpeg") or not shutil.which("ffprobe")):
        raise ValueError("视频和音频生成需要 FFmpeg 与 ffprobe")
    with _lock:
        if _active_id is not None:
            raise ValueError("已有生成任务正在运行，请先等待或停止它")
        job_id = uuid4().hex
        folder = Path(plan["output_dir"]) / f"test-data-{time.strftime('%Y%m%d-%H%M%S')}-{job_id[:8]}"
        folder.mkdir(exist_ok=False)
        job = {
            "id": job_id, "state": "running", "kind": spec.kind, "format": spec.format,
            "count": spec.count, "completed": 0, "target_bytes_each": plan["target_bytes_each"],
            "similarity_percent": spec.similarity_percent,
            "actual_bytes": 0, "output_dir": str(folder), "last_file": "", "error": "",
            "started_at": time.time(), "finished_at": None, "manifest_path": str(folder / "manifest.json"),
            "files": [],
        }
        _jobs[job_id] = job
        _stop_events[job_id] = threading.Event()
        _active_id = job_id
        try:
            _save_job(job)
        except OSError:
            _jobs.pop(job_id, None)
            _stop_events.pop(job_id, None)
            _active_id = None
            folder.rmdir()
            raise
    worker = threading.Thread(target=_run_job, args=(job_id, spec), daemon=True, name=f"test-data-{job_id[:8]}")
    worker.start()
    return _public_job(job).copy()


def stop_job(job_id: str) -> dict | None:
    with _lock:
        job = _jobs.get(job_id)
        if job is None:
            return _read_job(job_id)
        if job["state"] == "running":
            job["state"] = "stopping"
            _stop_events[job_id].set()
            _save_job(job)
        return _public_job(job).copy()


class _Stopped(Exception):
    pass


def _write_file(path: Path, size: int, base_seed: int, variant_seed: int | None,
                similarity_percent: int, text_mode: bool, stop: threading.Event) -> None:
    base_rng = random.Random(base_seed)
    variant_rng = random.Random(variant_seed) if variant_seed is not None else None
    with path.open("xb") as stream:
        remaining = size
        while remaining:
            if stop.is_set():
                raise _Stopped()
            chunk_size = min(MIB, remaining)
            common_size = chunk_size if variant_rng is None else round(chunk_size * similarity_percent / 100)
            base_chunk = base_rng.randbytes(chunk_size) if common_size else b""
            chunk = base_chunk[:common_size]
            if variant_rng is not None and common_size < chunk_size:
                chunk += variant_rng.randbytes(chunk_size - common_size)
            if text_mode:
                chunk = chunk.translate(_TEXT_TRANSLATION)
            stream.write(chunk)
            remaining -= len(chunk)


def _write_image(path: Path, target_bytes: int, base_seed: int, variant_seed: int | None,
                 similarity_percent: int, fmt: str) -> None:
    from PIL import Image, ImageDraw

    bytes_per_pixel = 0.7 if fmt == "jpg" else 1.0
    pixels = target_bytes / bytes_per_pixel
    width = max(256, min(6000, round(math.sqrt(pixels * 4 / 3))))
    height = max(192, min(4500, round(width * 3 / 4)))
    pixels_data = random.Random(base_seed).randbytes(width * height)
    if variant_seed is not None and similarity_percent < 100:
        pixels = bytearray(pixels_data)
        variant_rng = random.Random(variant_seed)
        for start in range(0, len(pixels), 4096):
            end = min(start + 4096, len(pixels))
            common_size = round((end - start) * similarity_percent / 100)
            pixels[start + common_size:end] = variant_rng.randbytes(end - start - common_size)
        pixels_data = bytes(pixels)
    image = Image.frombytes("L", (width, height), pixels_data)
    if fmt == "jpg":
        image = image.convert("RGB")
    draw = ImageDraw.Draw(image)
    color = random.Random(base_seed).randrange(0x1000000)
    draw.rectangle((0, 0, min(width, 360), 32), fill=f"#{color:06x}" if fmt == "jpg" else 0)
    draw.text((8, 8), f"SYNTHETIC TEST IMAGE {base_seed % 100000000:08d}",
              fill="white" if fmt == "jpg" else 255)
    image.save(path, format="JPEG" if fmt == "jpg" else "PNG", **({"quality": 90} if fmt == "jpg" else {}))


def _write_media(path: Path, spec: GenerationRequest, seed: int, stop: threading.Event) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise ValueError("FFmpeg 不可用")
    duration = spec.duration_seconds
    desired_bitrate = round(spec.size_mib * MIB * 8 / duration)
    command = [ffmpeg, "-nostdin", "-v", "error", "-n"]
    if spec.kind == "video":
        color = f"0x{random.Random(seed).randrange(0x1000000):06x}"
        source = f"testsrc2=size=640x360:rate=24,drawbox=x={seed % 400}:y={seed % 260}:w=50:h=40:color={color}:t=fill"
        video_bitrate = max(150_000, desired_bitrate - 96_000)
        command += ["-f", "lavfi", "-i", source, "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100",
                    "-t", str(duration), "-c:v", "libx264", "-preset", "ultrafast", "-b:v", str(video_bitrate),
                    "-maxrate", str(video_bitrate), "-bufsize", str(video_bitrate * 2), "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", "-f", "mp4", str(path)]
    else:
        kbps = max(32, min(320, round(desired_bitrate / 1000)))
        command += ["-f", "lavfi", "-i", f"sine=frequency={440 + seed % 440}:sample_rate=44100",
                    "-t", str(duration), "-c:a", "libmp3lame", "-b:a", f"{kbps}k", "-f", "mp3", str(path)]
    process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                               stderr=subprocess.PIPE, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    while process.poll() is None:
        if stop.wait(0.2):
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            raise _Stopped()
    error = process.stderr.read().decode("utf-8", errors="replace") if process.stderr else ""
    if process.returncode != 0:
        raise RuntimeError(f"FFmpeg 生成失败：{error[-300:]}")
    probe = shutil.which("ffprobe")
    if not probe:
        raise RuntimeError("ffprobe 不可用，无法验证媒体文件")
    verified = subprocess.run([probe, "-v", "error", "-show_entries", "format=duration",
                               "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
                              capture_output=True, text=True, timeout=30,
                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if verified.returncode or not verified.stdout.strip():
        raise RuntimeError("媒体文件解码信息验证失败")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(MIB), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run_job(job_id: str, spec: GenerationRequest) -> None:
    global _active_id
    job = _jobs[job_id]
    stop = _stop_events[job_id]
    folder = Path(job["output_dir"])
    state = "completed"
    error = ""
    batch_seed = secrets.randbits(64)
    try:
        for index in range(spec.count):
            if stop.is_set():
                raise _Stopped()
            name = f"{spec.kind}-{index + 1:05d}.{spec.format}"
            final = folder / name
            temporary = folder / f"{name}.part"
            try:
                if spec.kind == "file":
                    _write_file(temporary, job["target_bytes_each"], batch_seed,
                                None if index == 0 else batch_seed + index,
                                spec.similarity_percent, spec.format == "txt", stop)
                elif spec.kind == "image":
                    _write_image(temporary, job["target_bytes_each"], batch_seed,
                                 None if index == 0 else batch_seed + index,
                                 spec.similarity_percent, spec.format)
                else:
                    _write_media(temporary, spec, batch_seed + index, stop)
                if stop.is_set():
                    raise _Stopped()
                file_hash = _sha256(temporary)
                temporary.replace(final)
            finally:
                temporary.unlink(missing_ok=True)
            size = final.stat().st_size
            job["files"].append({"name": name, "size": size, "sha256": file_hash})
            with _lock:
                job["completed"] += 1
                job["actual_bytes"] += size
                job["last_file"] = name
                _save_job(job)
    except _Stopped:
        state = "stopped"
    except Exception as exc:
        state = "failed"
        error = str(exc)[:500]
    finally:
        try:
            manifest = {"job_id": job_id, "state": state, "request": spec.model_dump(), "files": job["files"]}
            (folder / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as exc:
            state = "failed"
            error = f"清单写入失败：{exc}"[:500]
        with _lock:
            job["state"] = state
            job["error"] = error
            job["finished_at"] = time.time()
            try:
                _save_job(job)
            finally:
                # A full disk may also prevent persisting the final state. Never
                # leave the single-run guard stuck after the worker has exited.
                if _active_id == job_id:
                    _active_id = None
                _stop_events.pop(job_id, None)

