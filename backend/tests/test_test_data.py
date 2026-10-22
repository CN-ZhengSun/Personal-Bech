import hashlib
import json
from pathlib import Path
import shutil
import time

import pytest
from PIL import Image

from app.services import test_data as td


@pytest.fixture
def isolated_jobs(monkeypatch, tmp_path):
    monkeypatch.setattr(td, "JOBS_DIR", tmp_path / "jobs")
    with td._lock:
        td._jobs.clear()
        td._stop_events.clear()
        td._active_id = None
    yield tmp_path
    with td._lock:
        td._jobs.clear()
        td._stop_events.clear()
        td._active_id = None


def wait_for_job(job_id, timeout=40):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = td.get_job(job_id)
        if job["state"] in ("completed", "failed", "stopped"):
            return job
        time.sleep(0.05)
    raise AssertionError("job did not finish")


def test_plan_rejects_root_and_invalid_media_size(isolated_jobs):
    with pytest.raises(ValueError, match="具体目录"):
        td.plan_generation(td.GenerationRequest(kind="file", count=1, size_mib=1,
                                                 format="bin", output_dir=str(isolated_jobs.anchor)))
    with pytest.raises(ValueError, match="码率|不匹配"):
        td.GenerationRequest(kind="audio", count=1, size_mib=20, duration_seconds=1,
                             format="mp3", output_dir=str(isolated_jobs))
    with pytest.raises(ValueError):
        td.GenerationRequest(kind="file", count=2, size_mib=0.01, format="bin",
                             output_dir=str(isolated_jobs), similarity_percent=101)
    with pytest.raises(ValueError, match="仅适用于"):
        td.GenerationRequest(kind="audio", count=2, size_mib=0.1, format="mp3",
                             output_dir=str(isolated_jobs), similarity_percent=50)


def test_files_have_exact_size_and_manifest(isolated_jobs):
    spec = td.GenerationRequest(kind="file", count=2, size_mib=0.01, format="txt",
                                output_dir=str(isolated_jobs))
    plan = td.plan_generation(spec)
    assert plan["can_run"]
    job = wait_for_job(td.start_job(spec)["id"])
    assert job["state"] == "completed", job["error"]
    manifest = json.loads(Path(job["manifest_path"]).read_text(encoding="utf-8"))
    assert manifest["request"]["similarity_percent"] == 0
    assert len(manifest["files"]) == 2
    for row in manifest["files"]:
        content = (Path(job["output_dir"]) / row["name"]).read_bytes()
        assert len(content) == plan["target_bytes_each"]
        assert hashlib.sha256(content).hexdigest() == row["sha256"]


@pytest.mark.parametrize("fmt", ["bin", "txt"])
@pytest.mark.parametrize("similarity", [0, 50, 100])
def test_file_similarity_is_within_one_batch(isolated_jobs, fmt, similarity):
    spec = td.GenerationRequest(kind="file", count=3, size_mib=0.01, format=fmt,
                                output_dir=str(isolated_jobs), similarity_percent=similarity)
    job = wait_for_job(td.start_job(spec)["id"])
    assert job["state"] == "completed", job["error"]
    files = [(Path(job["output_dir"]) / f"file-{index:05d}.{fmt}").read_bytes()
             for index in range(1, 4)]
    assert all(len(content) == job["target_bytes_each"] for content in files)
    for content in files[1:]:
        ratio = sum(a == b for a, b in zip(files[0], content)) / len(content)
        if similarity == 0:
            assert ratio < 0.1
        elif similarity == 50:
            assert 0.48 <= ratio <= 0.58
        else:
            assert content == files[0]


def test_separate_batches_use_new_content(isolated_jobs, monkeypatch):
    seeds = iter([12345, 67890])
    monkeypatch.setattr(td.secrets, "randbits", lambda bits: next(seeds))
    spec = td.GenerationRequest(kind="file", count=1, size_mib=0.01, format="bin",
                                output_dir=str(isolated_jobs))
    jobs = [wait_for_job(td.start_job(spec)["id"]) for _ in range(2)]
    assert jobs[0]["state"] == jobs[1]["state"] == "completed"
    assert jobs[0]["output_dir"] != jobs[1]["output_dir"]
    first = Path(jobs[0]["output_dir"]) / "file-00001.bin"
    second = Path(jobs[1]["output_dir"]) / "file-00001.bin"
    assert first.read_bytes() != second.read_bytes()


@pytest.mark.parametrize("fmt", ["jpg", "png"])
def test_images_decode_and_have_recorded_size(isolated_jobs, fmt):
    spec = td.GenerationRequest(kind="image", count=1, size_mib=0.2, format=fmt,
                                output_dir=str(isolated_jobs))
    job = wait_for_job(td.start_job(spec)["id"])
    assert job["state"] == "completed", job["error"]
    image_path = Path(job["output_dir"]) / f"image-00001.{fmt}"
    with Image.open(image_path) as image:
        image.verify()
    assert image_path.stat().st_size == job["actual_bytes"]
    assert 0.65 <= job["actual_bytes"] / job["target_bytes_each"] <= 1.35


@pytest.mark.parametrize("similarity", [0, 50, 100])
def test_png_similarity_uses_shared_pixels(isolated_jobs, similarity):
    spec = td.GenerationRequest(kind="image", count=2, size_mib=0.2, format="png",
                                output_dir=str(isolated_jobs), similarity_percent=similarity)
    job = wait_for_job(td.start_job(spec)["id"])
    assert job["state"] == "completed", job["error"]
    paths = [Path(job["output_dir"]) / f"image-{index:05d}.png" for index in (1, 2)]
    with Image.open(paths[0]) as first, Image.open(paths[1]) as second:
        pixels = (first.tobytes(), second.tobytes())
    ratio = sum(a == b for a, b in zip(*pixels)) / len(pixels[0])
    if similarity == 0:
        assert ratio < 0.1
    elif similarity == 50:
        assert 0.48 <= ratio <= 0.58
    else:
        assert paths[0].read_bytes() == paths[1].read_bytes()


def test_jpg_hundred_percent_is_identical(isolated_jobs):
    spec = td.GenerationRequest(kind="image", count=2, size_mib=0.2, format="jpg",
                                output_dir=str(isolated_jobs), similarity_percent=100)
    job = wait_for_job(td.start_job(spec)["id"])
    assert job["state"] == "completed", job["error"]
    folder = Path(job["output_dir"])
    assert (folder / "image-00001.jpg").read_bytes() == (folder / "image-00002.jpg").read_bytes()


def test_stop_does_not_report_completion_while_worker_is_active(isolated_jobs, monkeypatch):
    def slow_write(path, size, base_seed, variant_seed, similarity_percent, text_mode, stop):
        time.sleep(0.15)
        path.write_bytes(b"x")

    monkeypatch.setattr(td, "_write_file", slow_write)
    spec = td.GenerationRequest(kind="file", count=10, size_mib=0.001, format="bin",
                                output_dir=str(isolated_jobs))
    job_id = td.start_job(spec)["id"]
    stopping = td.stop_job(job_id)
    assert stopping["state"] == "stopping"
    done = wait_for_job(job_id)
    assert done["state"] == "stopped"
    assert done["completed"] < 10


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="FFmpeg unavailable")
def test_audio_and_video_are_valid_media(isolated_jobs):
    for kind, fmt, size in (("audio", "mp3", 0.1), ("video", "mp4", 0.3),
                            ("video", "mp4", 3)):
        spec = td.GenerationRequest(kind=kind, count=1, size_mib=size, format=fmt,
                                    duration_seconds=5, output_dir=str(isolated_jobs))
        job = wait_for_job(td.start_job(spec)["id"], timeout=60)
        assert job["state"] == "completed", job["error"]
        assert job["actual_bytes"] > 0
        assert 0.5 <= job["actual_bytes"] / job["target_bytes_each"] <= 1.5
