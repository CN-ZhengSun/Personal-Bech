# JMeter 远程桌面容器：noVNC + Xvfb + fluxbox + OpenJDK
FROM dorowu/ubuntu-desktop-lxde-vnc:focal

# 切换国内 apt 源（并移除无效的 google chrome 源）后安装 OpenJDK 17（JMeter 5.6.3 需 Java 8+）
RUN rm -f /etc/apt/sources.list.d/google-chrome.list /etc/apt/sources.list.d/*chrome* 2>/dev/null; \
    sed -i 's|http://archive.ubuntu.com/ubuntu|http://mirrors.aliyun.com/ubuntu|g; s|http://security.ubuntu.com/ubuntu|http://mirrors.aliyun.com/ubuntu|g' /etc/apt/sources.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends openjdk-17-jre xterm && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# 启动入口：启动远程桌面后自动拉起 JMeter GUI
COPY jmeter-entry.sh /opt/jmeter-entry.sh
RUN chmod +x /opt/jmeter-entry.sh

ENV VNC_RESOLUTION=1440x900
EXPOSE 6080 5900
ENTRYPOINT ["/opt/jmeter-entry.sh"]
