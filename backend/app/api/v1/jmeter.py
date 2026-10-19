import os
import subprocess

from fastapi import APIRouter, Depends, HTTPException

from app.core.security import get_current_user

router = APIRouter(prefix="/jmeter", tags=["jmeter"], dependencies=[Depends(get_current_user)])

# 迁移后的内置路径（JMETER_HOME 环境变量优先，便于整机迁移后自动适配）
DEFAULT_JMETER_HOME = r"D:\Test-Bench\tools\apache-jmeter-5.6.3"


def _jmeter_home() -> str:
    env = os.environ.get("JMETER_HOME", "")
    if env and os.path.isfile(os.path.join(env, "bin", "jmeter.bat")):
        return env
    return DEFAULT_JMETER_HOME


@router.post("/launch")
def launch_jmeter():
    """在本地启动 JMeter GUI（汉化版）。"""
    home = _jmeter_home()
    bat = os.path.join(home, "bin", "jmeter.bat")
    if not os.path.isfile(bat):
        raise HTTPException(status_code=404, detail=f"未找到 JMeter 启动脚本：{bat}")
    # detached 启动本地 GUI，不阻塞后端；显式传入正确环境（后端进程可能持有旧 JMETER_HOME）
    env = {**os.environ, "JMETER_HOME": home}
    subprocess.Popen(f'cmd /c start "" "{bat}"', shell=True, env=env)
    return {"status": "ok", "jmeter_home": home, "message": "JMeter 已在本机启动"}
