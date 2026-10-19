#!/bin/bash
# 启动 noVNC 远程桌面，并在桌面内拉起 JMeter GUI
set -e

# 启动桌面（xvfb + vnc + fluxbox + novnc），镜像自带 startup.sh
/startup.sh &

# 等待 X 服务就绪
for i in $(seq 1 30); do
  if xdpyinfo -display :1 >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

# 等待 fluxbox 就绪
sleep 3

# 在桌面内启动 JMeter（挂载目录 /opt/jmeter）
if [ -f /opt/jmeter/bin/jmeter ]; then
  export DISPLAY=:1
  export JVM_ARGS="-Dfile.encoding=UTF-8"
  nohup /opt/jmeter/bin/jmeter > /tmp/jmeter-gui.log 2>&1 &
  echo "JMeter GUI started" >> /tmp/jmeter-gui.log
else
  echo "JMeter not found at /opt/jmeter" >> /tmp/jmeter-gui.log
fi

# 保持前台运行（startup.sh 的 noVNC 服务在后台）
wait
