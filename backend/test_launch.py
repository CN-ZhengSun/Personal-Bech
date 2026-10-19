import subprocess, os, time

home = r'D:\Test-Bench\tools\apache-jmeter-5.6.3'
bat = os.path.join(home, 'bin', 'jmeter.bat')
print('bat exists:', os.path.isfile(bat))
env = {**os.environ, 'JMETER_HOME': home}
p = subprocess.Popen(f'cmd /c start "" "{bat}"', shell=True, env=env)
print('popen pid:', p.pid)
time.sleep(12)
# 检查 java 进程
import subprocess as sp
out = sp.run(['tasklist', '/FI', 'IMAGENAME eq java.exe'], capture_output=True, text=True).stdout
print('java procs:', [l for l in out.splitlines() if 'java' in l.lower()])
