<template>
  <div>
    <h1>ADB 工具</h1>

    <!-- 设备选择（全局） -->
    <div class="card">
      <div class="form-row" style="margin-bottom:0">
        <span class="ctl-label">无线连接</span>
        <input v-model="connHost" placeholder="设备 IP" style="width:150px" @keyup.enter="connect" />
        <input v-model.number="connPort" type="number" placeholder="5555" style="width:80px" @keyup.enter="connect" />
        <button class="btn" @click="connect">连接</button>
        <button class="btn btn-ghost" @click="loadDevices">刷新设备</button>
        <button class="btn btn-ghost" @click="disconnectAll">断开全部</button>
        <span class="muted" style="margin-left:auto">{{ lastRefresh }}</span>
      </div>
      <p v-if="adbError" class="error-text">{{ adbError }}</p>
      <p v-if="loaded && !devices.length" class="muted" style="margin-top:10px">无已连接设备：请用 USB 连接真机并开启调试授权，或通过上方无线连接。</p>
      <table class="tbl" v-if="devices.length">
        <thead>
          <tr><th>状态</th><th>设备</th><th>型号</th><th>系统</th><th>分辨率</th><th style="width:120px">操作</th></tr>
        </thead>
        <tbody>
          <tr v-for="d in devices" :key="d.serial" :class="{ 'row-selected': selected === d.serial }" style="cursor:pointer" @click="selectDevice(d.serial)">
            <td><span class="dot" :class="d.state === 'device' ? 'dot-ok' : 'dot-bad'"></span>{{ d.state }}</td>
            <td>{{ d.serial }}</td>
            <td>{{ d.model || '—' }}</td>
            <td>{{ d.version ? 'Android ' + d.version : '—' }}</td>
            <td>{{ d.resolution || '—' }}</td>
            <td>
              <button class="btn btn-small btn-gray" @click.stop="selectDevice(d.serial)">{{ selected === d.serial ? '已选择' : '选择' }}</button>
              <button v-if="d.state !== 'device'" class="btn btn-small btn-danger" @click.stop="disconnectOne(d.serial)">断开</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 分类导航（对应本地 ADB Fast Tools 目录，去除悬浮窗/模型管理） -->
    <div class="cat-nav" v-if="device">
      <button v-for="c in categories" :key="c.id" class="cat-btn" :class="{ active: cat === c.id }" @click="cat = c.id">{{ c.name }}</button>
    </div>

    <div v-if="device">
      <!-- ============ 屏幕镜像 ============ -->
      <div v-show="cat === 'mirror'">
        <div class="card">
          <div class="form-row" style="margin-bottom:0">
            <span class="ctl-label">屏幕镜像</span>
            <button v-if="!castOn" class="btn" @click="startCast" :disabled="casting">开始投屏</button>
            <button v-else class="btn btn-danger" @click="stopCast">停止投屏</button>
            <span class="muted" v-if="resolution">{{ resolution }} · 点击/滑动/长按可操控，聚焦画面可直接键盘输入，Ctrl+V 粘贴</span>
            <span class="muted" v-if="casting">连接中…</span>
          </div>
          <p class="muted" style="margin-top:8px">投屏画面将以悬浮面板展示在页面右侧，可拖动头部移动位置、拖拽右下角调整大小；页面滚动时始终保持可见。</p>
        </div>
      </div>

      <!-- 投屏悬浮面板：右侧固定，可拖动/缩放，滚动保持可见，保留触控操作 -->
      <div v-show="castOn" class="cast-panel" :style="panelStyle">
        <div class="cast-panel-head" @mousedown="startDrag">
          <span class="cast-title">屏幕镜像{{ resolution ? ' · ' + resolution : '' }}</span>
          <span class="cast-spacer"></span>
          <button class="btn btn-small btn-gray cast-btn" @click="wakeScreen">唤醒</button>
          <button class="btn btn-small btn-danger cast-btn" @click="stopCast">停止</button>
        </div>
        <div class="cast-panel-body">
          <div class="cast-box" tabindex="0" :class="{ focused: castFocus }"
               @mousedown="onMouseDown" @mousemove="onMouseMove" @mouseup="onMouseUp" @mouseleave="onMouseLeave"
               @keydown="onCastKey" @focus="castFocus = true" @blur="castFocus = false"
               @dblclick.prevent>
            <video ref="videoEl" class="cast-video" autoplay muted playsinline></video>
            <span v-if="castError" class="cast-err">{{ castError }}</span>
          </div>
          <div class="cast-panel-ctrl">
            <input v-model="inputText" style="flex:1;min-width:0" placeholder="文本输入，回车发送" @keyup.enter="sendText" />
            <button class="btn btn-small" @click="sendText">发送</button>
            <button v-for="k in keyBtns" :key="k.code" class="btn btn-small btn-gray" @click="sendKey(k.code)">{{ k.name }}</button>
          </div>
        </div>
        <div class="cast-resize" @mousedown="startResize"></div>
      </div>

      <!-- ============ 设备管理 ============ -->
      <div v-show="cat === 'device'">
        <div class="card">
          <div class="sec-title">设备参数</div>
          <div class="grid-btns">
            <button class="btn" @click="getFullInfo">获取完整设备信息</button>
            <button class="btn btn-gray" @click="runDevExec('shell getprop')">获取全部属性</button>
            <button class="btn btn-gray" @click="runDevExec('shell dumpsys battery')">电池状态</button>
            <button class="btn btn-gray" @click="runDevExec('shell cat /proc/cpuinfo')">CPU 信息</button>
            <button class="btn btn-gray" @click="runDevExec('shell cat /proc/meminfo')">内存信息</button>
            <button class="btn btn-gray" @click="runDevExec('shell df -h')">存储信息</button>
            <button class="btn btn-gray" @click="runDevExec('get-serialno')">序列号</button>
          </div>
          <pre class="mono-out" v-if="devOut">{{ devOut }}</pre>
        </div>
        <div class="card">
          <div class="sec-title">电源与模式控制</div>
          <div class="grid-btns">
            <button class="btn btn-danger" @click="doReboot('normal')">设备重启</button>
            <button class="btn btn-danger" @click="doReboot('bootloader')">重启 Bootloader</button>
            <button class="btn btn-danger" @click="doReboot('recovery')">重启 Recovery</button>
            <button class="btn btn-danger" @click="doShutdown">设备关机</button>
          </div>
          <p v-if="powerOut" class="mono-out">{{ powerOut }}</p>
        </div>
      </div>

      <!-- ============ 应用控制 ============ -->
      <div v-show="cat === 'app'">
        <div class="sub-nav">
          <button class="sub-btn" :class="{ active: appSub === 'control' }" @click="appSub = 'control'">应用控制</button>
          <button class="sub-btn" :class="{ active: appSub === 'activity' }" @click="appSub = 'activity'">Activity 诊断</button>
        </div>
        <div v-show="appSub === 'control'" class="card">
          <div class="form-row">
            <span class="ctl-label">APK 路径</span>
            <input v-model="apkPath" style="flex:1" placeholder="选择 APK 文件后自动填入" />
            <label class="btn btn-ghost" style="cursor:pointer">选择 APK<input type="file" accept=".apk" style="display:none" @change="onApkPick" /></label>
            <button class="btn" @click="installApk('')">安装</button>
            <button class="btn btn-gray" @click="installApk('-r')">替换安装 (-r)</button>
            <button class="btn btn-gray" @click="installApk('-g')">授权安装 (-g)</button>
            <button class="btn btn-gray" @click="analyzeApk">分析包名</button>
          </div>
          <div class="form-row">
            <span class="ctl-label">目标应用包名</span>
            <input v-model="pkgName" style="flex:1" placeholder="com.example.app" />
            <select v-model="pkgName" style="width:220px" @change="loadInfo">
              <option v-for="p in apps" :key="p" :value="p">{{ p }}</option>
            </select>
            <button class="btn btn-danger" @click="uninstallApp('')">直接卸载</button>
            <button class="btn btn-danger" @click="uninstallApp('-k')">保留数据卸载</button>
            <button class="btn btn-danger" @click="clearPkg">清除应用数据</button>
            <button class="btn btn-gray" @click="forceStop">强行停止</button>
            <button class="btn" @click="launchPkg">一键启动应用</button>
          </div>
          <p v-if="appOut" class="mono-out">{{ appOut }}</p>
          <div class="app-list">
            <div v-for="p in filteredApps" :key="p" class="app-item">
              <span class="app-name">{{ p }}</span>
              <span class="app-ops">
                <button class="btn btn-small" @click="pickPkg(p)">选用</button>
                <button class="btn btn-small" @click="launchPkgBy(p)">启动</button>
                <button class="btn btn-small btn-gray" @click="clearPkgBy(p)">清数据</button>
                <button class="btn btn-small btn-danger" @click="uninstallBy(p)">卸载</button>
              </span>
            </div>
            <p v-if="!filteredApps.length" class="muted" style="margin-top:8px">暂无第三方应用</p>
          </div>
        </div>
        <div v-show="appSub === 'activity'" class="card">
          <div class="form-row">
            <span class="ctl-label">目标包名</span>
            <input v-model="pkgName" style="flex:1" placeholder="com.example.app" />
            <span class="ctl-label">Activity 名称（可选）</span>
            <input v-model="activityName" style="flex:1" placeholder="MainActivity" />
            <button class="btn" @click="startActivity">启动指定 Activity</button>
          </div>
          <div class="grid-btns" style="margin-top:10px">
            <button class="btn btn-gray" @click="getCurrentActivity">查看当前前台 Activity</button>
            <button class="btn btn-gray" @click="getLaunchActivity">解析包主启动 Activity</button>
          </div>
          <p v-if="activityOut" class="mono-out">{{ activityOut }}</p>
        </div>
      </div>

      <!-- ============ 文件传输 ============ -->
      <div v-show="cat === 'file'">
        <div class="card">
          <div class="form-row">
            <span class="ctl-label">设备路径浏览</span>
            <input v-model="fsPath" style="flex:1" @keyup.enter="loadFs" />
            <button class="btn btn-gray" @click="fsUp">上一级</button>
            <button class="btn" @click="loadFs">打开</button>
            <span class="ctl-label">创建目录</span>
            <input v-model="mkdirPath" style="flex:1" placeholder="/sdcard/test/" @keyup.enter="doMkdir" />
            <button class="btn btn-gray" @click="doMkdir">创建</button>
          </div>
          <div class="fs-list" v-if="fsItems.length">
            <div v-for="it in fsItems" :key="it.name" class="fs-item">
              <span class="fs-name" :class="'fs-' + it.type" @click="fsOpen(it)">{{ it.type === 'dir' ? '📁' : it.type === 'link' ? '🔗' : '📄' }} {{ it.name }}</span>
              <span class="fs-size">{{ it.type === 'file' ? fmtSize(it.size) : '' }}</span>
              <span class="fs-ops">
                <button v-if="it.type === 'file'" class="btn btn-small btn-gray" @click="fsPull(it)">拉取到平台</button>
              </span>
            </div>
          </div>
          <p v-else-if="fsLoaded" class="muted" style="margin-top:8px">空目录</p>
        </div>
        <div class="card">
          <div class="form-row">
            <span class="ctl-label">推送到设备</span>
            <input type="file" style="flex:1" :disabled="pushing" @change="onPushPick" />
            <button class="btn" :disabled="!pushFile || pushing" @click="doPush">{{ pushing ? '推送中…' : '推送到当前目录' }}</button>
          </div>
          <p class="muted">目标目录：{{ fsPath }}<template v-if="pushFile"> · 已选：{{ pushFile.name }}（{{ fmtSize(pushFile.size) }}）</template></p>
          <p v-if="fileOut" class="mono-out">{{ fileOut }}</p>
        </div>
      </div>

      <!-- ============ 系统调试 ============ -->
      <div v-show="cat === 'debug'">
        <div class="card">
          <div class="sec-title">性能与服务</div>
          <div class="grid-btns">
            <button class="btn btn-gray" @click="runExec('shell top -n 10')">获取 CPU Top 10 进程</button>
          </div>
          <div class="form-row" style="margin-top:10px;margin-bottom:0">
            <span class="ctl-label">包名（内存分析）</span>
            <input v-model="memPkg" style="flex:1" placeholder="com.example.app" />
            <button class="btn btn-gray" @click="runExec('shell dumpsys meminfo ' + memPkg)">内存信息</button>
            <span class="ctl-label">服务名</span>
            <input v-model="serviceName" style="flex:1" placeholder="服务名" />
            <button class="btn btn-gray" @click="runExec('shell dumpsys activity services ' + serviceName)">服务状态</button>
          </div>
          <pre class="mono-out" v-if="execOut">{{ execOut }}</pre>
        </div>
      </div>

      <!-- ============ 实用工具 ============ -->
      <div v-show="cat === 'utils'">
        <div class="card">
          <div class="sec-title">保存目录设置</div>
          <div class="form-row">
            <span class="ctl-label">统一保存目录</span>
            <input v-model="saveDir" style="flex:1" placeholder="相对 uploads 的子目录，或本机绝对路径（可点击浏览选择）" />
            <button class="btn" @click="openBrowse">浏览…</button>
            <button class="btn" @click="saveDirSetting">保存设置</button>
            <button class="btn btn-gray" @click="loadSaveDir">刷新</button>
          </div>
          <p class="muted" style="margin-top:6px">截图、录屏、设备文件拉取等保存类功能统一存放在该目录下</p>
        </div>
        <!-- 本机目录选择弹窗 -->
        <div v-if="browseVisible" class="browse-mask" @click.self="browseVisible = false">
          <div class="browse-box">
            <div class="browse-head">
              <span>选择本机目录</span>
              <button class="btn btn-small btn-gray" @click="browseVisible = false">关闭</button>
            </div>
            <div class="browse-path">当前：{{ browsePath || '（请选择盘符或目录）' }}</div>
            <div class="browse-list">
              <button v-if="browseParent" class="browse-item" @click="browseGo(browseParent)">⬆ 上级目录</button>
              <button v-for="d in browseItems" :key="d.path" class="browse-item" @click="browseGo(d.path)">📁 {{ d.name }}</button>
              <p v-if="!browseItems.length" class="muted" style="padding:10px">无子目录</p>
            </div>
            <div class="browse-foot">
              <span class="muted" style="font-size:12px">点击目录进入，选中后填入保存目录</span>
              <button class="btn btn-gray" @click="browseVisible = false">取消</button>
              <button class="btn" @click="browsePick">选中此目录</button>
            </div>
          </div>
        </div>
        <div class="sub-nav">
          <button class="sub-btn" :class="{ active: utilsSub === 'media' }" @click="utilsSub = 'media'">截图与录屏</button>
          <button class="sub-btn" :class="{ active: utilsSub === 'ts' }" @click="utilsSub = 'ts'">时间戳转换</button>
        </div>
        <div v-show="utilsSub === 'media'" class="card">
          <div class="form-row">
            <span class="ctl-label">快捷截图</span>
            <input v-model="shotName" style="width:160px" placeholder="文件名（留空自动）" />
            <button class="btn" @click="takeScreenshot">执行截图</button>
            <span class="ctl-label">高清录屏</span>
            <select v-model="recResolution" style="width:150px" title="录屏分辨率">
              <option value="">自动</option>
              <option value="720x1280">720x1280</option>
              <option value="720x1600">720x1600</option>
              <option value="1080x1920">1080x1920</option>
              <option value="1080x2280">1080x2280</option>
              <option value="1080x2340">1080x2340</option>
              <option value="1440x3120">1440x3120</option>
            </select>
            <input v-model="recName" style="width:160px" placeholder="文件名(可选)" />
            <button v-if="!recording" class="btn" @click="startRecord" :disabled="stopping">{{ stopping ? '停止中…' : '开始录屏' }}</button>
            <button v-else class="btn btn-danger" @click="stopRecord">结束录屏</button>
            <span v-if="recording" class="rec-timer">{{ recTimer }}</span>
            <span v-else-if="stopping" class="rec-timer rec-stopping">停止中…</span>
          </div>
          <div class="form-row" style="margin-bottom:0">
            <span class="ctl-label">自定义 ADB 命令（不带 adb 前缀）</span>
            <input v-model="customCmd" style="flex:1" placeholder="shell pm list packages" @keyup.enter="runExec(customCmd)" />
            <button class="btn btn-gray" @click="runExec(customCmd)">执行自定义命令</button>
          </div>
          <p v-if="execOut" class="mono-out">{{ execOut }}</p>
          <div v-if="screenUrl" class="screen-box"><img :src="screenUrl" alt="设备截图" class="screen-img" /></div>
        </div>
        <div v-show="utilsSub === 'ts'" class="card">
          <div class="form-row" style="margin-bottom:0">
            <span class="ctl-label">北京时间</span>
            <input v-model="tsInput" style="flex:1" placeholder="YYYY-MM-DD HH:mm:ss.SSS（留空用当前时间）" />
            <button class="btn" @click="convertTs">转换为 13 位时间戳</button>
          </div>
          <p v-if="tsOutput" class="ts-out">timestamp: <b>{{ tsOutput }}</b></p>
          <p v-if="tsError" class="error-text">{{ tsError }}</p>
        </div>
      </div>

      <!-- ============ 日志分析（多视图） ============ -->
      <div v-show="cat === 'logcat2'">
        <div class="card">
          <div class="form-row" style="margin-bottom:0">
            <span class="ctl-label">AI 日志分析</span>
            <input v-model="analysisPkg" style="flex:1" placeholder="按包名过滤分析（留空分析当前视图全部）" />
            <span class="ctl-label">AI 模型</span>
            <select v-model="analyzeModelId" style="width:220px">
              <option v-for="m in analyzeModels" :key="m.id" :value="m.id">{{ m.name }}（{{ m.model_name }}）</option>
            </select>
            <button class="btn" @click="analyzeLog" :disabled="analyzing">{{ analyzing ? '分析中…' : '立即分析' }}</button>
          </div>
        </div>
        <div class="card">
          <div class="form-row" style="margin-bottom:0">
            <span class="ctl-label">日志视图</span>
            <button v-for="v in logViews" :key="v.id" class="sub-btn" :class="{ active: logActiveId === v.id }" @click="logActiveId = v.id">{{ v.name }}</button>
            <button class="btn btn-small btn-gray" @click="addLogView">+ 新建视图</button>
            <button v-if="logViews.length > 1" class="btn btn-small btn-danger" @click="closeLogView">关闭当前</button>
            <span class="muted">进程</span>
            <div class="sel-search" :class="{ open: procOpen }">
              <input
                v-if="procSearchMode"
                ref="procSearchInput"
                v-model="procSearchText"
                class="sel-search-input"
                placeholder="输入关键字搜索进程"
                @blur="procSearchMode = false"
                @keyup.enter="applyProcSearch"
              />
              <div v-else class="sel-search-input sel-search-read" :title="activeLog.procName ? activeLog.procName.split('|')[0] : '单击下拉选择，双击搜索'" @click="procOpen = !procOpen" @dblclick="enterProcSearch">
                <span>{{ activeLog.procName ? activeLog.procName.split('|')[0] : '全部进程' }}</span>
              </div>
              <div v-if="procOpen" class="sel-search-menu">
                <div class="sel-search-item" :class="{ on: !activeLog.procName }" @mousedown.prevent="setLogProc('')">全部进程</div>
                <div v-for="p in filteredProcOptions" :key="p.val" class="sel-search-item" :class="{ on: activeLog.procName === p.val }" @mousedown.prevent="setLogProc(p.val)">{{ p.label }}</div>
                <div v-if="!filteredProcOptions.length" class="sel-search-empty">无匹配进程</div>
              </div>
            </div>
            <span class="muted">展示</span>
            <select v-model="activeLog.mergeMode" style="width:80px" @change="scrollLogToBottom">
              <option :value="false">逐行</option>
              <option :value="true">合并</option>
            </select>
            <button class="btn btn-small" :class="activeLog.running ? 'btn-danger' : 'btn-primary'" @click="toggleLogCollect">{{ activeLog.running ? '停止采集' : '开始采集' }}</button>
            <button class="btn btn-small btn-gray" @click="clearLogView">清屏</button>
            <button class="btn btn-small btn-gray" @click="clearLogcat">清空设备日志</button>
            <button class="btn btn-small" :class="wrapMode ? 'btn-primary' : 'btn-gray'" @click="toggleLogWrap" title="长消息自动换行（换行模式仅展示最近 500 行）">{{ wrapMode ? '自动换行' : '单行显示' }}</button>
          </div>
          <div class="log-view-box" :class="{ 'log-max': logViewMax }">
            <div class="form-row q-row" style="margin-bottom:0">
              <span class="ctl-label">查询过滤</span>
              <div class="q-filter">
                <input v-model="activeLog.query" style="flex:1" placeholder="支持字段、&、|、括号、否定、正则和精确匹配" @keyup.enter="rememberLogQuery" />
                <button class="q-toggle" @click="queryOpen = !queryOpen" title="插入查询语法字段">▾</button>
                <div v-if="queryOpen" class="q-menu">
                  <div v-for="f in queryFields" :key="f.v" class="q-item" @mousedown.prevent="appendQueryField(f.v)"><code>{{ f.v }}</code><span class="q-desc">{{ f.d }}</span></div>
                </div>
              </div>
              <label v-if="!logViewMax" class="radio-inline"><input v-model="activeLog.matchCase" type="checkbox" /> 区分大小写</label>
              <input v-if="!logViewMax" v-model="minePkg" style="width:130px" placeholder="我的包名" @change="saveMinePkg" title="package:mine 查询使用的包名" />
              <button v-if="!logViewMax" class="btn btn-small btn-gray" @click="rememberLogQuery">收藏</button>
              <select v-if="!logViewMax && logQueryHistory.length" v-model="activeLog.query" style="width:200px" @change="activeLog.query = $event.target.value">
                <option v-for="q in logQueryHistory" :key="q" :value="q">{{ q }}</option>
              </select>
              <span class="ctl-label">忽略标签</span>
              <input v-model="ignoreTags" style="width:200px" placeholder="如 UserMessagingPlatform，逗号分隔" @change="saveIgnoreTags" title="匹配的标签将不显示" />
              <button class="btn btn-small btn-gray" @click="logViewMax = !logViewMax">{{ logViewMax ? '缩小' : '全屏' }}</button>
            </div>
            <p v-if="logQueryError" class="error-text" style="margin-top:6px">{{ logQueryError }}；当前按整句文本搜索</p>
            <template v-if="!wrapMode">
              <div class="log-table-scroll">
                <div class="log-table" :style="logColStyle">
                  <div class="log-thead">
                    <span class="log-th" @mousedown="startColResize('time', $event)">时间</span>
                    <span class="log-th" @mousedown="startColResize('lv', $event)">级别</span>
                    <span class="log-th" @mousedown="startColResize('proc', $event)">进程</span>
                    <span class="log-th" @mousedown="startColResize('tid', $event)">TID</span>
                    <span class="log-th" @mousedown="startColResize('tag', $event)">标签</span>
                    <span class="log-th log-th-msg">消息</span>
                  </div>
                  <div class="logcat-out" ref="logViewBox" @scroll.passive="onLogScroll">
                    <div class="log-spacer" :style="{ height: logRows.length * LOG_ROW_H + 'px' }">
                      <div class="log-window" :style="{ transform: 'translateY(' + logVirtual.offsetTop + 'px)' }">
                        <div v-for="row in visibleRows" :key="row.key" :class="['log-line', 'lv-' + (row.lv || 'V'), row.isStack ? 'log-stack' : '']">
                          <template v-if="row.kind === 'cont'">
                            <span class="log-cell log-cell-cont">{{ fmtMsg(row.text) }}</span>
                          </template>
                          <template v-else-if="row.p">
                            <span class="log-cell" :title="row.p.time">{{ row.p.time }}</span>
                            <span class="log-cell log-cell-lv">{{ row.p.level }}</span>
                            <span class="log-cell" :title="row.p.pid">{{ row.p.processName || row.p.pid }}</span>
                            <span class="log-cell">{{ row.p.tid }}</span>
                            <span class="log-cell" :title="row.p.tag">{{ row.p.tag }}</span>
                            <span class="log-cell log-cell-msg" :title="fmtMsg(row.p.message)">{{ fmtMsg(row.p.message) }}</span>
                          </template>
                          <template v-else>
                            <span class="log-cell log-cell-wide">{{ row.text }}</span>
                          </template>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </template>
            <template v-else>
              <div class="log-table" :style="logColStyle">
                <div class="log-thead">
                  <span class="log-th">时间</span>
                  <span class="log-th">级别</span>
                  <span class="log-th">进程</span>
                  <span class="log-th">TID</span>
                  <span class="log-th">标签</span>
                  <span class="log-th log-th-msg">消息</span>
                </div>
                <div class="logcat-out logcat-wrap" ref="wrapBox" @scroll.passive="onWrapScroll">
                  <div v-for="row in wrapRows" :key="row.key" :class="['log-line', 'lv-' + (row.lv || 'V'), row.isStack ? 'log-stack' : '']">
                    <template v-if="row.kind === 'cont'">
                      <span class="log-cell log-cell-cont">{{ fmtMsg(row.text) }}</span>
                    </template>
                    <template v-else-if="row.p">
                      <span class="log-cell" :title="row.p.time">{{ row.p.time }}</span>
                      <span class="log-cell log-cell-lv">{{ row.p.level }}</span>
                      <span class="log-cell" :title="row.p.pid">{{ row.p.processName || row.p.pid }}</span>
                      <span class="log-cell">{{ row.p.tid }}</span>
                      <span class="log-cell" :title="row.p.tag">{{ row.p.tag }}</span>
                      <span class="log-cell log-cell-msg" :title="fmtMsg(row.p.message)">{{ fmtMsg(row.p.message) }}</span>
                    </template>
                    <template v-else>
                      <span class="log-cell log-cell-wide">{{ row.text }}</span>
                    </template>
                  </div>
                </div>
              </div>
            </template>
          </div>
          <p v-if="!activeLog.running" class="muted" style="margin-top:6px">点击「开始采集」后按视图实时显示</p>
        </div>
        <div class="card">
          <div v-if="analysisReport" class="an-report">
            <div class="an-summary">{{ analysisReport.summary }}</div>
            <div class="an-counts">
              <span>ANR: <b style="color:#f59e0b">{{ analysisReport.counts.ANR }}</b></span>
              <span>崩溃: <b style="color:#ef4444">{{ analysisReport.counts.CRASH + analysisReport.counts.NATIVE_CRASH }}</b></span>
              <span>死亡: <b>{{ analysisReport.counts.PROCESS_DIED }}</b></span>
              <span>E级日志: <b>{{ errorCount }}</b></span>
              <span>风险等级: <b :style="{ color: riskColor }">{{ riskLevel }}</b></span>
            </div>
            <div class="an-issues">
              <div v-for="iss in analysisReport.issues" :key="iss.id" class="an-issue" :class="'sev-' + iss.severity">[{{ iss.type }}] {{ iss.line }}</div>
              <div v-if="!analysisReport.issues.length" class="muted">未发现明显异常。</div>
            </div>
          </div>
          <div v-if="analyzeResult" class="ai-result">
            <div class="form-row" style="margin-bottom:6px">
              <b>AI 诊断结论</b><span class="muted">{{ analyzeModelName }}</span>
              <button class="btn btn-small btn-gray" @click="analyzeResult = ''">清空</button>
            </div>
            <pre class="ai-pre">{{ analyzeResult }}</pre>
          </div>
        </div>
      </div>

      <!-- ============ Monkey 测试 ============ -->
      <div v-show="cat === 'monkey'">
        <div class="card">
          <div class="sec-title">Monkey 伪随机压力测试</div>
          <div class="form-row">
            <span class="ctl-label">目标包名</span>
            <input v-model="monkeyPkg" style="flex:1" placeholder="com.example.app" />
            <select v-model="monkeyPkg" style="width:220px">
              <option value="">随机（全系统）</option>
              <option v-for="p in apps" :key="p" :value="p">{{ p }}</option>
            </select>
            <span class="ctl-label">事件数</span>
            <input v-model.number="monkeyEvents" type="number" min="1" max="10000" style="width:90px" />
            <span class="ctl-label">节流ms</span>
            <input v-model.number="monkeyThrottle" type="number" min="0" style="width:80px" />
          </div>
          <div class="ctl-label" style="margin-bottom:8px">随机事件占比</div>
          <div class="monkey-event-grid">
            <label v-for="event in monkeyEventTypes" :key="event.key" class="monkey-event" :title="event.description">
              <span>{{ event.label }}</span>
              <input v-model.number="monkeyRatios[event.key]" type="number" min="0" max="100" step="1" placeholder="自动" />
              <span>%</span>
            </label>
          </div>
          <p class="muted" style="margin:8px 0">已指定 {{ monkeyRatioTotal }}%；留空由 Monkey 分配剩余比例，填 0 表示禁用。设备系统版本可能不支持部分事件类型。</p>
          <div class="form-row">
            <label class="radio-inline"><input type="checkbox" v-model="monkeyIgnore" />忽略崩溃/超时/安全异常</label>
            <button class="btn" @click="runMonkey" :disabled="!!busy">{{ busy || '开始 Monkey 压力测试' }}</button>
            <button class="btn btn-danger" @click="checkAndStopMonkey" :disabled="monkeyControlBusy || !selected">{{ monkeyControlBusy ? '检测中…' : '检测并停止 Monkey 测试' }}</button>
            <span class="muted">{{ monkeyStatusText }}</span>
          </div>
          <pre class="shell-out" v-if="monkeyOut">{{ monkeyOut }}</pre>
        </div>
        <div class="card">
          <div class="form-row">
            <span class="sec-title" style="margin-bottom:0">测试报告</span>
            <button class="btn btn-small btn-gray" @click="loadMonkeyReports">刷新</button>
            <span v-if="monkeyReportsLoading" class="muted">加载中…</span>
          </div>
          <p v-if="monkeyReportDir" class="muted" style="word-break:break-all">保存位置：{{ monkeyReportDir }}</p>
          <table v-if="monkeyReports.length" class="tbl">
            <thead><tr><th>报告文件</th><th>生成时间</th><th>大小</th><th>操作</th></tr></thead>
            <tbody>
              <tr v-for="report in monkeyReports" :key="report.name">
                <td>{{ report.name }}</td>
                <td>{{ new Date(report.created_at).toLocaleString('zh-CN') }}</td>
                <td>{{ fmtSize(report.size) }}</td>
                <td>
                  <button class="btn btn-small btn-gray" @click="monkeyPreview = { url: report.url, name: report.name }">查看</button>
                  <button class="btn btn-small btn-danger" style="margin-left:6px" @click="deleteMonkeyReport(report)">删除</button>
                </td>
              </tr>
            </tbody>
          </table>
          <p v-else-if="!monkeyReportsLoading" class="muted">暂无测试报告</p>
        </div>
        <AttachmentPreview :url="monkeyPreview?.url" :name="monkeyPreview?.name" :visible="!!monkeyPreview" @close="monkeyPreview = null" />
      </div>

      <!-- ============ 通知触发（黑盒快速触发定时通知） ============ -->
      <div v-show="cat === 'notify'">
        <div class="card">
          <div class="sec-title">通知触发</div>
          <div class="form-row">
            <span class="ctl-label">目标应用</span>
            <input v-model="notifyPkg" style="width:230px" placeholder="输入目标应用包名" />
            <button class="btn" @click="loadNotifyJobs" :disabled="notifyLoading">{{ notifyLoading ? '解析中…' : '解析任务 ID' }}</button>
            <span class="muted">读取 dumpsys jobscheduler，按通知类型自动分类</span>
          </div>
          <div class="form-row">
            <div class="notify-type">
              <div class="notify-type-head">
                <b>30 分钟通知</b><span class="muted">JobScheduler · UsageReminderJobService</span>
              </div>
              <div class="form-row">
                <span class="ctl-label">任务 ID</span>
                <span class="job-id">{{ notifyJob30 === null ? '未解析' : notifyJob30 }}</span>
                <button class="btn" :disabled="!!notifyBusy" @click="triggerNotify(1)">{{ notifyBusy === 1 ? '触发中…' : '立即触发' }}</button>
              </div>
            </div>
            <div class="notify-type">
              <div class="notify-type-head">
                <b>15 分钟循环通知</b><span class="muted">WorkManager · SystemJobService（自动时区欺骗→强弹→恢复）</span>
              </div>
              <div class="form-row">
                <span class="ctl-label">任务 ID</span>
                <span class="job-id">{{ notifyJob15 === null ? '未解析' : notifyJob15 }}</span>
                <button class="btn" :disabled="!!notifyBusy" @click="triggerNotify(2)">{{ notifyBusy === 2 ? '触发中…' : '立即触发' }}</button>
              </div>
            </div>
          </div>
          <pre class="shell-out" v-if="notifyOut">{{ notifyOut }}</pre>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { loadLogQueryHistory, saveLogQueryHistory, LOG_HISTORY_MAX } from '../utils/log-history'
import { adbApi } from '../api'
import AttachmentPreview from '../components/AttachmentPreview.vue'
import { compileLogMatcher, decodeLogcatEvent, recordHasPackage, isStackLine } from '../utils/logcat'
import JMuxer from 'jmuxer'

const categories = [
  { id: 'mirror', name: '屏幕镜像' },
  { id: 'device', name: '设备管理' },
  { id: 'app', name: '应用控制' },
  { id: 'file', name: '文件传输' },
  { id: 'debug', name: '性能与服务' },
  { id: 'logcat2', name: '日志分析' },
  { id: 'utils', name: '实用工具' },
  { id: 'monkey', name: 'Monkey 测试' },
  { id: 'notify', name: '通知触发' },
]
const cat = ref('device')
const appSub = ref('control')
const debugSub = ref('logcat')
const utilsSub = ref('media')

const devices = ref([])
const loaded = ref(false)
const adbError = ref('')
const selected = ref('')
const connHost = ref('')
const connPort = ref(5555)
const lastRefresh = ref('')
const deviceInfo = ref(null)
const currentActivity = ref('')
const screenUrl = ref('')
const busy = ref('')
const appKw = ref('')
const apps = ref([])
const shellCmd = ref('')
const shellOut = ref('')
const logRunning = ref(false)
const logLines = ref([])
const logFilter = ref('')
const logBox = ref(null)
let ws = null

// 投屏
const castOn = ref(false)
const casting = ref(false)
const castError = ref('')
const resolution = ref('')
const videoEl = ref(null)
const inputText = ref('')
const keyBtns = [
  { name: 'HOME', code: 3 }, { name: '任务栏', code: 187 },
  { name: '返回', code: 4 }, { name: '电源', code: 26 },
]
let castWs = null
let ctrlWs = null
let jmuxer = null
let castDeviceW = 1080
let castDeviceH = 2340
const pointer = ref(null)
let longTimer = null

// 设备管理
const powerOut = ref('')
const devOut = ref('')
// 应用控制
const apkPath = ref('')
const pkgName = ref('')
const activityName = ref('')
const appOut = ref('')
const activityOut = ref('')
// 文件
const fsPath = ref('/sdcard')
const fsItems = ref([])
const fsLoaded = ref(false)
const mkdirPath = ref('/sdcard/test')
const pushFile = ref(null)
const pushing = ref(false)
const fileOut = ref('')
// 日志分析（系统调试内）
const analysisPkg = ref('')
const analysisReport = ref(null)
const errorCount = ref(0)
const riskLevel = ref('无')
const analyzeModels = ref([])
const analyzeModelId = ref(0)
const analyzeResult = ref('')
const analyzeModelName = ref('')
const analyzing = ref(false)
const monitoring = ref(false)
let monitorTimer = null
// 注：自监测已去除（用户要求），monitoring 保留兼容引用
const logMaximized = ref(false)
// 日志分析（独立视图）
const LOG_VIEW_MAX = 4 // 同时打开的视图上限
function createLogView(id, name) {
  return {
    id, name,
    ws: null, running: false, // 每个视图独立 WebSocket 与运行状态
    buffer: 'all', level: '', procName: '',
    mergeMode: false, matchCase: false,
    paused: false, pausedCount: 0, pausedLines: [],
    lines: [], // 视图独立日志列表
    seq: 0, // 行号自增，用作渲染稳定 key（避免索引 key 导致全量重渲染）
    query: '',
  }
}
const logViews = ref([createLogView(1, 'Logcat 1')])
const logActiveId = ref(1)
const activeLog = computed(() => logViews.value.find((v) => v.id === logActiveId.value) || logViews.value[0])
const logQueryHistory = ref(loadLogQueryHistory())
const logViewMax = ref(false)
const logViewBox = ref(null)
// "我的包名"：package:mine 查询使用；localStorage 持久化，异常数据不影响页面
const minePkg = ref('')
try { minePkg.value = localStorage.getItem('twb_log_mine_pkg') || '' } catch { /* noop */ }
// 默认关联应用控制中的目标应用包名：用户未手动设置过时，应用控制包名变化自动同步
watch(pkgName, (v) => {
  if (!v) return
  let saved = ''
  try { saved = localStorage.getItem('twb_log_mine_pkg') || '' } catch { /* noop */ }
  if (!saved) minePkg.value = v
})
function saveMinePkg() {
  try { localStorage.setItem('twb_log_mine_pkg', minePkg.value.trim()) } catch { /* noop */ }
  resetLogFilter()
}
// 性能
const memPkg = ref('')
const serviceName = ref('')
// 实用工具
const shotName = ref('')
const recDuration = ref(10)
const recResolution = ref('')
const recName = ref('')
const recording = ref(false)
const recUrl = ref('')
const recTimer = ref('00 : 00')
const stopping = ref(false)
let recTimerInt = null
let recElapsed = 0
const customCmd = ref('')
const execOut = ref('')
const tsInput = ref('')
const tsOutput = ref('')
const tsError = ref('')
// Monkey
const monkeyPkg = ref('')
const monkeyEvents = ref(1000)
const monkeyThrottle = ref(100)
const monkeyEventTypes = [
  { key: 'pct_touch', label: '触摸', description: '单点触摸' },
  { key: 'pct_motion', label: '滑动', description: '手指移动与拖动' },
  { key: 'pct_pinchzoom', label: '双指缩放', description: '双指捏合与缩放' },
  { key: 'pct_rotation', label: '屏幕旋转', description: '切换屏幕方向' },
  { key: 'pct_nav', label: '普通导航', description: '方向键上、下、左、右' },
  { key: 'pct_majornav', label: '主要导航', description: '返回、菜单、方向键确认等' },
  { key: 'pct_syskeys', label: '系统按键', description: 'Home、音量等系统按键' },
  { key: 'pct_appswitch', label: '应用切换', description: '随机启动目标包内的 Activity' },
  { key: 'pct_permission', label: '运行时权限', description: '随机切换应用的运行时权限' },
  { key: 'pct_anyevent', label: '其他事件', description: '其他按键及较少使用的事件' },
]
const monkeyRatios = reactive({
  pct_touch: 35, pct_motion: 20, pct_nav: 10, pct_majornav: 15,
  pct_pinchzoom: '', pct_rotation: '', pct_syskeys: '',
  pct_appswitch: '', pct_permission: '', pct_anyevent: '',
})
const monkeyRatioTotal = computed(() => monkeyEventTypes.reduce((sum, event) => {
  const value = monkeyRatios[event.key]
  return sum + (value === '' || value === null ? 0 : Number(value) || 0)
}, 0))
const monkeyIgnore = ref(true)
const monkeyOut = ref('')
const monkeyReports = ref([])
const monkeyReportsLoading = ref(false)
const monkeyReportDir = ref('')
const monkeyPreview = ref(null)
const monkeyStatusText = ref('未检测')
const monkeyControlBusy = ref(false)
const monkeyStoppedByUser = ref(false)

const device = computed(() => devices.value.find((d) => d.serial === selected.value))
const filteredApps = computed(() => {
  const kw = appKw.value.trim().toLowerCase()
  if (!kw) return apps.value
  return apps.value.filter((p) => p.toLowerCase().includes(kw))
})
const filteredLog = computed(() => {
  if (!logFilter.value.trim()) return logLines.value
  const kws = logFilter.value.trim().split(/\s+/)
  return logLines.value.filter((ln) => kws.every((k) => ln.toLowerCase().includes(k.toLowerCase())))
})
const riskColor = computed(() => ({ 高: '#ef4444', 中: '#f59e0b', 低: '#3b82f6', 无: '#64748b' }[riskLevel.value] || '#64748b'))

// ---------- 设备 ----------
async function loadDevices() {
  adbError.value = ''
  try {
    const r = await adbApi.devices()
    devices.value = r.data.devices || []
    if (!r.data.adb_installed) adbError.value = r.data.error || '未检测到 adb'
    const t = new Date()
    lastRefresh.value = `更新于 ${t.getHours()}:${String(t.getMinutes()).padStart(2, '0')}:${String(t.getSeconds()).padStart(2, '0')}`
    if (selected.value && !devices.value.some((d) => d.serial === selected.value)) {
      selected.value = ''
      deviceInfo.value = null
    }
    if (!selected.value) {
      const remembered = localStorage.getItem('twb_adb_serial') || ''
      const candidate = devices.value.find((d) => d.state === 'device' && d.serial === remembered)
        || (devices.value.filter((d) => d.state === 'device').length === 1
          ? devices.value.find((d) => d.state === 'device')
          : null)
      if (candidate) await selectDevice(candidate.serial)
    }
  } catch (e) {
    adbError.value = e.response?.data?.detail || e.message || '加载失败'
  }
  loaded.value = true
}

async function connect() {
  if (!connHost.value) return window.$toast.warning('请填写设备 IP')
  try {
    await adbApi.connect(connHost.value, connPort.value)
    window.$toast.success('连接指令已发送')
    await loadDevices()
  } catch (e) {
    window.$toast.error(e.response?.data?.detail || '连接失败')
  }
}
async function disconnectAll() { await adbApi.disconnect(''); await loadDevices() }
async function disconnectOne(serial) { await adbApi.disconnect(serial); if (selected.value === serial) selected.value = ''; await loadDevices() }

async function selectDevice(serial) {
  selected.value = serial
  localStorage.setItem('twb_adb_serial', serial)
  deviceInfo.value = null
  currentActivity.value = ''
  screenUrl.value = ''
  apps.value = []
  shellOut.value = ''
  logLines.value = []
  analysisReport.value = null
  analyzeResult.value = ''
  if (logRunning.value) stopLogcat()
  stopAllLogViews()
  if (castOn.value) stopCast()
  await loadInfo()
}

async function loadInfo() {
  if (!selected.value) return
  try {
    const info = await adbApi.info(selected.value)
    deviceInfo.value = info.data
    const act = await adbApi.activity(selected.value)
    currentActivity.value = act.data.activity
    const a = await adbApi.apps(selected.value)
    apps.value = a.data.packages
    loadFs()
    loadAnalyzeModels()
  } catch (e) {
    window.$toast.error(e.response?.data?.detail || '加载设备信息失败')
  }
}

async function getFullInfo() {
  const runs = [
    'shell getprop ro.product.brand',
    'shell getprop ro.product.model',
    'shell getprop ro.build.version.release',
    'shell getprop ro.build.version.sdk',
    'shell wm size',
  ]
  try {
    const outs = []
    for (const c of runs) {
      const r = await adbApi.execute(selected.value, c)
      outs.push((r.data.output || '').trim())
    }
    const [brand, model, release, sdk, sizeRaw] = outs
    const sizeMatch = (sizeRaw || '').match(/(\d+x\d+)/)
    devOut.value = `品牌: ${brand || '未知'}  型号: ${model || '未知'}  系统: Android ${release || '?'} (SDK ${sdk || '?'})  分辨率: ${sizeMatch?.[1] || '未知'}`
  } catch (e) {
    window.$toast.error(e.response?.data?.detail || '获取设备信息失败')
  }
}

// 设备参数命令：输出到设备管理分类下
async function runDevExec(cmd) {
  if (!cmd || !cmd.trim()) return
  try {
    const r = await adbApi.execute(selected.value, cmd.trim())
    devOut.value = r.data.output
  } catch (e) {
    window.$toast.error(e.response?.data?.detail || '命令执行失败')
  }
}

// 通用执行（对应本地 executeCommand）
async function runExec(cmd, pretty = false) {
  if (!cmd || !cmd.trim()) return
  try {
    const r = await adbApi.execute(selected.value, cmd.trim())
    execOut.value = r.data.output
    if (pretty) {
      const lines = r.data.output.split('\n')
      powerOut.value = lines.slice(-3).join('\n')
      currentActivity.value = ''
    }
  } catch (e) {
    window.$toast.error(e.response?.data?.detail || '命令执行失败')
  }
}

// ---------- 电源 ----------
async function doReboot(mode) {
  const name = { normal: '重启设备', bootloader: '重启到 Bootloader', recovery: '重启到 Recovery' }[mode]
  if (!(await window.$confirm(`确认${name}？设备会暂时断开。`, { danger: true }))) return
  try {
    const r = await adbApi.reboot(selected.value, mode)
    powerOut.value = r.data.output || name + '指令已发送'
    window.$toast.success(name + '指令已发送')
  } catch (e) {
    window.$toast.error(e.response?.data?.detail || '操作失败')
  }
}
async function doShutdown() {
  if (!(await window.$confirm('确认关机？设备会断电。', { danger: true }))) return
  try {
    const r = await adbApi.shutdown(selected.value)
    powerOut.value = r.data.output
    window.$toast.success('关机指令已发送')
  } catch (e) {
    window.$toast.error(e.response?.data?.detail || '关机失败')
  }
}

// ---------- 应用控制 ----------
const selectedApkFile = ref(null)
function onApkPick(ev) {
  const f = ev.target.files[0]
  ev.target.value = ''
  if (f) {
    apkPath.value = f.name
    selectedApkFile.value = f
  }
}
async function installApk(flag) {
  if (!selectedApkFile.value) return window.$toast.warning('请先选择 APK 文件')
  busy.value = '安装中…'
  try {
    const r = await adbApi.install(selected.value, selectedApkFile.value, flag)
    window.$toast[r.data.ok ? 'success' : 'error'](r.data.ok ? '安装成功' : '安装失败：' + (r.data.output || '').slice(-200))
  } catch (e) {
    window.$toast.error(e.response?.data?.detail || '安装失败')
  } finally { busy.value = '' }
}
async function analyzeApk() {
  if (!selectedApkFile.value) return window.$toast.warning('请先选择 APK 文件')
  try {
    const r = await adbApi.analyzeApk(selected.value, selectedApkFile.value)
    if (r.data.packageName) { pkgName.value = r.data.packageName; window.$toast.success('包名已解析：' + r.data.packageName) }
    else window.$toast.error('未能解析包名')
  } catch (e) { window.$toast.error(e.response?.data?.detail || '解析失败') }
}
async function uninstallApp(flag) {
  if (!pkgName.value) return window.$toast.warning('请先填写包名')
  if (!(await window.$confirm(`确认卸载 ${pkgName.value}？`))) return
  const r = await adbApi.uninstall(selected.value, pkgName.value, flag)
  window.$toast[r.data.ok ? 'success' : 'error'](r.data.ok ? '卸载成功' : '卸载失败：' + (r.data.output || '').slice(-200))
  loadInfo()
}
async function clearPkg() {
  if (!pkgName.value) return window.$toast.warning('请先填写包名')
  await adbApi.clear(selected.value, pkgName.value)
  window.$toast.success('已清空数据')
}
async function forceStop() {
  if (!pkgName.value) return window.$toast.warning('请先填写包名')
  const r = await adbApi.execute(selected.value, `shell am force-stop ${pkgName.value}`)
  window.$toast.success('已强制停止')
}
async function launchPkg() {
  if (!pkgName.value) return window.$toast.warning('请先填写包名')
  await adbApi.launch(selected.value, pkgName.value)
  window.$toast.success('已发送启动指令')
  setTimeout(() => loadInfo(), 1500)
}
function pickPkg(p) { pkgName.value = p }
async function launchPkgBy(p) { pkgName.value = p; await launchPkg() }
async function clearPkgBy(p) { pkgName.value = p; await clearPkg() }
async function uninstallBy(p) { pkgName.value = p; await uninstallApp('') }

// Activity 诊断
async function getCurrentActivity() {
  const r = await adbApi.activity(selected.value)
  currentActivity.value = r.data.activity || '未识别'
  activityOut.value = '当前前台 Activity: ' + (r.data.activity || '未识别（可能是桌面/锁屏/通知栏）')
}
async function getLaunchActivity() {
  if (!pkgName.value) return window.$toast.warning('请先填写包名')
  const r = await adbApi.execute(selected.value, `shell cmd package resolve-activity --brief ${pkgName.value}`)
  const line = (r.data.output || '').split('\n').map((l) => l.trim()).find((l) => l.includes('/'))
  activityOut.value = line ? `启动页 Activity: ${line}` : '未能识别启动页 Activity'
}
async function startActivity() {
  if (!pkgName.value) return window.$toast.warning('请先填写包名')
  const r = await adbApi.execute(selected.value, activityName.value
    ? `shell am start -n ${pkgName.value}/${activityName.value}`
    : `shell monkey -p ${pkgName.value} -c android.intent.category.LAUNCHER 1`)
  activityOut.value = r.data.output.slice(-300) || '已发送启动指令'
  setTimeout(() => loadInfo(), 1500)
}

// ---------- 文件 ----------
async function loadFs() {
  if (!selected.value) return
  try {
    const r = await adbApi.fsList(selected.value, fsPath.value || '/')
    fsPath.value = r.data.path
    fsItems.value = r.data.items
    fsLoaded.value = true
  } catch (e) { window.$toast.error(e.response?.data?.detail || '读取目录失败') }
}
function fsUp() {
  let p = fsPath.value.replace(/\/+$/, '')
  if (!p) return
  const idx = p.lastIndexOf('/')
  fsPath.value = idx > 0 ? p.slice(0, idx) : '/'
  loadFs()
}
function fsOpen(it) {
  if (it.type !== 'dir') return
  fsPath.value = (fsPath.value.replace(/\/+$/, '') + '/' + it.name).replace(/\/+/g, '/')
  loadFs()
}
async function fsPull(it) {
  try {
    const full = (fsPath.value.replace(/\/+$/, '') + '/' + it.name).replace(/\/+/g, '/')
    const r = await adbApi.fsPull(selected.value, full)
    window.$toast.success('已拉取到平台：' + r.data.name)
  } catch (e) { window.$toast.error(e.response?.data?.detail || '拉取失败') }
}
function fmtSize(n) {
  if (n >= 1024 * 1024) return (n / 1024 / 1024).toFixed(1) + ' MB'
  if (n >= 1024) return (n / 1024).toFixed(1) + ' KB'
  return n + ' B'
}
async function doMkdir() {
  if (!mkdirPath.value.trim()) return
  const r = await adbApi.execute(selected.value, `shell mkdir -p ${mkdirPath.value.trim()}`)
  fileOut.value = r.data.output || '目录已创建'
  loadFs()
}
function onPushPick(ev) {
  pushFile.value = ev.target.files?.[0] || null
  fileOut.value = ''
}
async function doPush() {
  if (!pushFile.value) return window.$toast.warning('请先选择本地文件')
  if (!selected.value) return window.$toast.warning('请先选择设备')
  if (pushing.value) return
  const file = pushFile.value
  const targetDir = fsPath.value
  pushing.value = true
  fileOut.value = ''
  try {
    const r = await adbApi.fsPush(selected.value, targetDir, file)
    fileOut.value = r.data.ok
      ? `推送成功：${file.name} → ${targetDir}`
      : '推送失败：' + (r.data.output || '设备未接受文件').slice(-200)
    window.$toast[r.data.ok ? 'success' : 'error'](fileOut.value)
    if (r.data.ok) await loadFs()
  } catch (e) {
    fileOut.value = '推送失败：' + (e.response?.data?.detail || e.message || '请求失败')
    window.$toast.error(fileOut.value)
  } finally {
    pushing.value = false
  }
}

// ---------- 日志 ----------
async function startLogcat() {
  if (!selected.value) return
  logLines.value = []
  logRunning.value = true
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  ws = new WebSocket(`${proto}://${location.host}/ws/adb/${selected.value}/logcat`)
  ws.onmessage = (ev) => {
    logLines.value.push(decodeLogcatEvent(ev.data).raw)
    if (logLines.value.length > 2000) logLines.value.splice(0, logLines.value.length - 2000)
    nextTick(() => { if (logBox.value) logBox.value.scrollTop = logBox.value.scrollHeight })
  }
  ws.onclose = () => { logRunning.value = false }
  ws.onerror = () => { window.$toast.error('日志流连接失败'); logRunning.value = false }
}
function stopLogcat() {
  if (ws) { try { ws.close() } catch { /* noop */ } ws = null }
  logRunning.value = false
}
function applyFilter() { /* computed 已实时过滤 */ }
async function dumpLogcat() {
  const r = await adbApi.logcatDump(selected.value, 500)
  window.$toast.success('已导出 ' + (r.data.output || '').split('\n').length + ' 行日志')
  const blob = new Blob([r.data.output], { type: 'text/plain' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `logcat_${Date.now()}.txt`
  a.click()
  URL.revokeObjectURL(a.href)
}
async function clearLogcat() {
  if (!(await window.$confirm('确认清空设备 logcat 缓冲区？'))) return
  const r = await adbApi.logcatClear(selected.value)
  window.$toast.success('已清空')
}

// 本地规则分析（ANR/崩溃/死亡/FATAL/Watchdog）
const ISSUE_PATTERNS = [
  { type: 'ANR', severity: 'critical', re: /ANR in\s+([A-Za-z0-9._$]+)/i },
  { type: 'ANR', severity: 'critical', re: /Application Not Responding/i },
  { type: 'CRASH', severity: 'critical', re: /FATAL EXCEPTION/i },
  { type: 'NATIVE_CRASH', severity: 'critical', re: /signal\s+\d+\s+\(SIG[A-Z0-9]+\)/i },
  { type: 'FATAL', severity: 'high', re: /\b(AndroidRuntime|RuntimeException|IllegalStateException|NullPointerException)\b/i },
  { type: 'PROCESS_DIED', severity: 'high', re: /Process\s+[A-Za-z0-9._:$]+\s+has died/i },
  { type: 'WATCHDOG', severity: 'medium', re: /\bwatchdog\b/i },
]
function analyzeLocal() {
  const pkg = analysisPkg.value
  const records = activeLog.value.lines
  const filteredRecords = pkg
    ? records.filter((record) => recordHasPackage(record, pkg) || (!record.applicationId && record.raw.toLowerCase().includes(pkg.toLowerCase())))
    : records
  const lines = records.map((record) => record.raw)
  const filtered = filteredRecords.map((record) => record.raw)
  errorCount.value = records.filter((record) => record.level === 'E' || record.level === 'F').length
  const issues = []
  const counts = { ANR: 0, CRASH: 0, NATIVE_CRASH: 0, FATAL: 0, PROCESS_DIED: 0, WATCHDOG: 0 }
  const seen = new Set()
  for (const line of filtered) {
    for (const rule of ISSUE_PATTERNS) {
      if (!rule.re.test(line)) continue
      const id = rule.type + ':' + line.trim()
      if (seen.has(id)) continue
      seen.add(id)
      counts[rule.type] += 1
      issues.push({ id, type: rule.type, severity: rule.severity, line: line.slice(0, 200) })
    }
  }
  const crit = issues.filter((i) => i.severity === 'critical').length
  const high = issues.filter((i) => i.severity === 'high').length
  riskLevel.value = crit > 0 ? '高' : high > 0 ? '中' : issues.length ? '低' : '无'
  analysisReport.value = {
    summary: `扫描 ${lines.length} 行，包名匹配 ${filtered.length} 行，发现 ${issues.length} 条风险。`,
    counts, issues: issues.slice(0, 100),
  }
}

// ---------- 日志分析（独立视图，多视图/缓冲区/级别/进程/暂停/过滤/合并） ----------
const logRenderLimit = 2000
// 消息 JSON 格式化：消息中包含可解析的 JSON（{ 或 [ 起始）则缩进展示（缓存复用，避免渲染期反复 parse）
const _msgFmtCache = new Map()
function formatLogMessage(msg) {
  if (typeof msg !== 'string' || !msg) return msg
  const hit = _msgFmtCache.get(msg)
  if (hit !== undefined) return hit
  let out = msg
  const idx = msg.search(/[[{]/)
  if (idx >= 0) {
    try {
      const pretty = JSON.stringify(JSON.parse(msg.slice(idx)), null, 2)
      out = pretty ? msg.slice(0, idx) + pretty : msg
    } catch { out = msg }
  }
  if (_msgFmtCache.size > 2000) _msgFmtCache.clear()
  _msgFmtCache.set(msg, out)
  return out
}
function fmtMsg(m) { return formatLogMessage(m) }
const LOG_LINES_MAX = 20000 // 日志列表与暂停缓存的上限（超出淘汰最旧，保留最新）
const logProcs = ref([])
let procTimer = null
const logProcOptions = computed(() =>
  logProcs.value
    .filter((p) => p.name.includes('.') && !p.name.startsWith('[')) // 应用进程（包名特征），对齐 Android Studio
    .map((p) => ({ val: `${p.name}|${p.pid}`, label: `${p.name} (${p.pid})` })),
)
// 进程筛选：单击下拉选择，双击进入关键字搜索（对齐"模块/版本"下拉交互）
const procOpen = ref(false)
const procSearchMode = ref(false)
const procSearchText = ref('')
const procSearchInput = ref(null)
const filteredProcOptions = computed(() => {
  const kw = procSearchText.value.trim().toLowerCase()
  if (!kw) return logProcOptions.value
  return logProcOptions.value.filter((p) => p.label.toLowerCase().includes(kw) || p.val.toLowerCase().includes(kw))
})
function enterProcSearch() {
  procSearchMode.value = true
  procOpen.value = true
  procSearchText.value = ''
  nextTick(() => procSearchInput.value && procSearchInput.value.focus())
}
function applyProcSearch() {
  const list = filteredProcOptions.value
  if (list.length) setLogProc(list[0].val)
}
function setLogProc(val) {
  activeLog.value.procName = val
  procOpen.value = false
  procSearchMode.value = false
  procSearchText.value = ''
}
// 节流重算的过滤结果；logQueryPlan 仅为模板/调试兼容保留
const logFilteredData = ref([])
// 合并模式结果（组数组）与省略计数：由 reconcileLogView 增量维护，避免每条日志全量遍历
const logMergeData = ref([])
const logOmitted = ref(0)
const logQueryError = ref('')
// 忽略标签：匹配的日志直接不显示（如 UserMessagingPlatform 刷屏），localStorage 持久化
const ignoreTags = ref('')
try { ignoreTags.value = localStorage.getItem('twb_log_ignore_tags') || '' } catch { /* noop */ }
function saveIgnoreTags() {
  try { localStorage.setItem('twb_log_ignore_tags', ignoreTags.value) } catch { /* noop */ }
  // ignoreTags 已由下方 watch 监听，赋值后自动触发 resetLogFilter
}
const ignoreTagSet = computed(() => new Set(ignoreTags.value.split(/[,，]/).map((s) => s.trim()).filter(Boolean)))
// 查询过滤下拉：字段列表 + 追加到输入框末尾（不覆盖已有内容）
const queryFields = [
  { v: 'tag:', d: '标签过滤，如 tag:Worker' },
  { v: 'package:', d: '包名过滤，如 package:com.example' },
  { v: 'package:mine', d: '我的包名（需设置"我的包名"）' },
  { v: 'process:', d: '进程过滤，如 process:com.example' },
  { v: 'message:', d: '消息过滤，如 message:Exception' },
  { v: 'line:', d: '整行过滤，如 line:hello' },
  { v: 'pid:', d: '进程 ID，如 pid:1234' },
  { v: 'level:', d: '级别阈值，如 level:ERROR' },
  { v: 'age:', d: '时间范围，如 age:5m' },
  { v: 'is:crash', d: '崩溃日志' },
  { v: 'is:stacktrace', d: '堆栈日志' },
  { v: '-tag:', d: '排除字段，如 -tag:Worker' },
  { v: 'tag~:', d: '正则匹配，如 tag~:Ex.*ion' },
  { v: 'tag=:', d: '精确匹配，如 tag=:Name' },
]
const queryOpen = ref(false)
function appendQueryField(f) {
  const cur = activeLog.value.query
  activeLog.value.query = cur ? (cur.trimEnd() + ' ' + f) : f
  queryOpen.value = false
}
let logFilterTimer = null
// 查询计划缓存：过滤字段未变化时复用编译结果（采集进行中改查询/级别等不再每次重编译正则）
let _planCacheKey = ''
let _planCachePlan = null
function compileLogMatcherCached(q, level, pid, cs, mine) {
  const key = q + '\u0001' + level + '\u0001' + pid + '\u0001' + (cs ? 1 : 0) + '\u0001' + mine
  if (key === _planCacheKey && _planCachePlan) return _planCachePlan
  const plan = compileLogMatcher(q, level, pid, cs, mine)
  _planCacheKey = key
  _planCachePlan = plan
  return plan
}
// 每视图增量缓存：新日志只对新增行做匹配/合并（lastId 定位），条件变化才全量重建
const viewCaches = new WeakMap()
function getViewCache(v) {
  let c = viewCaches.get(v)
  if (!c) { c = { lastId: 0, filtered: [], groups: [], cur: null }; viewCaches.set(v, c) }
  return c
}
function reconcileLogView() {
  const v = activeLog.value
  if (!v) return
  const processPid = v.procName ? v.procName.split('|')[1] : ''
  const plan = compileLogMatcherCached(v.query, v.level, processPid, v.matchCase, minePkg.value)
  logQueryError.value = plan.error || ''
  const ignore = ignoreTagSet.value
  const cache = getViewCache(v)
  const lines = v.lines
  // 定位上次处理位置：新行集中在尾部，从后往前找 lastId（通常 O(1) 命中最后一条）
  let start = 0
  if (cache.lastId) {
    for (let j = lines.length - 1; j >= 0; j--) {
      if (lines[j]._id === cache.lastId) { start = j + 1; break }
    }
    if (!start && lines.length && lines[lines.length - 1]._id !== cache.lastId) {
      // lastId 已被淘汰（超 LOG_LINES_MAX 后头部 splice）：清缓存全量重建
      cache.filtered = []; cache.groups = []; cache.cur = null
    }
  }
  if (!v.mergeMode) {
    // 淘汰残留清理：filtered 与 lines 保持同量级（输出只取尾部，不影响正确性）
    if (cache.filtered.length > lines.length + 64) cache.filtered = cache.filtered.slice(-LOG_LINES_MAX)
    for (let i = start; i < lines.length; i++) {
      const record = lines[i]
      if (plan.predicate(record) && (!ignore.size || !record.parsed || !ignore.has(record.tag))) {
        cache.filtered.push({ id: record._id, ln: record.raw, parsed: record.parsed ? record : null })
      }
    }
  } else {
    // 合并模式：同现有语义（同 tag + 同时间戳 → 同一条日志组，续行归组），但只增量处理新行
    if (cache.groups.length > lines.length + 64) {
      cache.groups = cache.groups.slice(-LOG_LINES_MAX); cache.cur = null
    }
    for (let i = start; i < lines.length; i++) {
      const record = lines[i]
      if (!record.parsed) {
        // 续行（无时间戳、冒号开头，如 JSON 数组/长消息换行）归入当前组，作为缩进续行
        if (cache.cur && /^\s*:/.test(record.raw)) {
          cache.cur.lines.push({ id: record._id, parsed: { message: record.raw.replace(/^\s*:\s*/, '') } })
          if (plan.predicate(record)) cache.cur.matched = true
          continue
        }
        cache.cur = null
        cache.groups.push({
          key: record._id,
          head: { id: record._id, ln: record.raw, parsed: null },
          lines: [], matched: plan.predicate(record),
        })
        continue
      }
      const mergeKey = `${record.time}|${record.tag}`
      const row = { id: record._id, ln: record.raw, parsed: record }
      const hit = plan.predicate(record) && !ignore.has(record.tag)
      if (cache.cur && cache.cur.mergeKey === mergeKey) {
        cache.cur.lines.push(row)
        if (hit) cache.cur.matched = true
      } else {
        cache.cur = { mergeKey, key: record._id, head: row, lines: [], matched: hit }
        cache.groups.push(cache.cur)
      }
    }
  }
  if (lines.length) cache.lastId = lines[lines.length - 1]._id
  // 输出：仅布尔遍历 + 尾部截取（轻量），不再每条日志全量重算
  if (!v.mergeMode) {
    const total = cache.filtered.length
    // 必须返回新数组引用：computed 用 === 比较新旧值，同引用会导致 logRows/wrapRows 不失效
    logFilteredData.value = total > logRenderLimit
      ? cache.filtered.slice(total - logRenderLimit)
      : cache.filtered.slice()
    logOmitted.value = Math.max(0, total - logRenderLimit)
  } else {
    let matched = 0
    for (const g of cache.groups) if (g.matched) matched++
    let out
    if (matched > logRenderLimit) {
      out = []
      for (let i = cache.groups.length - 1; i >= 0 && out.length < logRenderLimit; i--) {
        if (cache.groups[i].matched) out.unshift(cache.groups[i])
      }
    } else {
      out = []
      for (const g of cache.groups) if (g.matched) out.push(g)
    }
    logMergeData.value = out
    logOmitted.value = Math.max(0, matched - logRenderLimit)
  }
}
function scheduleLogFilter() {
  if (logFilterTimer) return
  logFilterTimer = setTimeout(() => { logFilterTimer = null; reconcileLogView() }, 80)
}
function resetLogFilter() {
  if (logFilterTimer) { clearTimeout(logFilterTimer); logFilterTimer = null }
  const v = activeLog.value
  if (v) { const c = getViewCache(v); c.filtered = []; c.groups = []; c.cur = null; c.lastId = 0 }
  reconcileLogView()
}
const logFiltered = computed(() => logFilteredData.value)
const logRendered = computed(() => (activeLog.value && activeLog.value.mergeMode ? logMergeData.value : logFilteredData.value))
const logRenderOmitted = computed(() => logOmitted.value)
// ---- 虚拟滚动：只渲染可视区行，固定行高，日志流再快也稳定 ----
const LOG_ROW_H = 20 // 每行固定高度（px），与 .log-line 的 height/line-height 一致
const VIRTUAL_BUFFER = 20 // 可视区上下各多渲染的行数（滚动缓冲）
// ---- 表格列宽：可拖拽调整，持久化到 localStorage（对齐 Android Studio Logcat 列布局） ----
const DEFAULT_COL_W = { time: 152, lv: 26, proc: 120, tid: 50, tag: 140 }
const logColW = reactive(loadLogColW())
function loadLogColW() {
  try {
    return Object.assign({}, DEFAULT_COL_W, JSON.parse(localStorage.getItem('twb_log_col_w') || '{}'))
  } catch { return { ...DEFAULT_COL_W } }
}
function saveLogColW() {
  try { localStorage.setItem('twb_log_col_w', JSON.stringify({ ...logColW })) } catch { /* noop */ }
}
const logColStyle = computed(() => ({
  '--w-time': logColW.time + 'px',
  '--w-lv': logColW.lv + 'px',
  '--w-proc': logColW.proc + 'px',
  '--w-tid': logColW.tid + 'px',
  '--w-tag': logColW.tag + 'px',
}))
let colResizing = null
function startColResize(col, ev) {
  if (colResizing) return
  colResizing = { col, x: ev.clientX, w: logColW[col] }
  document.body.classList.add('log-resizing')
  window.addEventListener('mousemove', onColResize)
  window.addEventListener('mouseup', stopColResize)
  ev.preventDefault()
}
function onColResize(ev) {
  if (!colResizing) return
  logColW[colResizing.col] = Math.max(36, colResizing.w + (ev.clientX - colResizing.x))
}
function stopColResize() {
  if (!colResizing) return
  window.removeEventListener('mousemove', onColResize)
  window.removeEventListener('mouseup', stopColResize)
  document.body.classList.remove('log-resizing')
  saveLogColW()
  colResizing = null
}
const vScrollTop = ref(0)
const vViewportH = ref(600)
let logAtBottom = true // 贴底时新日志自动跟随；翻看历史时不强制拉底
const logRows = computed(() => {
  const items = logRendered.value
  if (!activeLog.value.mergeMode) {
    return items.map((it) => ({
      key: it.id, kind: 'line', text: it.ln, p: it.parsed,
      lv: it.parsed ? it.parsed.level : 'V',
      isStack: it.parsed ? isStackLine(it.parsed.message) : false,
    }))
  }
  // 合并模式：组显示为 head 行 + 续行平铺（对齐 Android Studio：续行缩进在 head 下方，同组完整展示）
  const rows = []
  for (const g of items) {
    const head = g.head
    rows.push({
      key: 'h' + g.key, kind: 'head', text: head.ln, p: head.parsed,
      lv: head.parsed ? head.parsed.level : 'V',
      isStack: head.parsed ? isStackLine(head.parsed.message) : false,
    })
    for (const line of g.lines) rows.push({ key: 'c' + g.key + '_' + line.id, kind: 'cont', text: line.parsed.message, lv: line.parsed.level })
  }
  return rows})
const logVirtual = computed(() => {
  const total = logRows.value.length
  const first = Math.max(0, Math.floor(vScrollTop.value / LOG_ROW_H) - VIRTUAL_BUFFER)
  const vis = Math.ceil(vViewportH.value / LOG_ROW_H)
  const end = Math.min(total, first + vis + VIRTUAL_BUFFER * 2)
  return { start: first, end, offsetTop: first * LOG_ROW_H }
})
const visibleRows = computed(() => logRows.value.slice(logVirtual.value.start, logVirtual.value.end))
// ---- 自动换行模式：长消息换行展示（渲染最近 N 行，行高自适应，不参与虚拟滚动） ----
const LOG_WRAP_LIMIT = 500
const wrapMode = ref(false)
try { wrapMode.value = localStorage.getItem('twb_log_wrap') === '1' } catch { /* noop */ }
function toggleLogWrap() {
  wrapMode.value = !wrapMode.value
  try { localStorage.setItem('twb_log_wrap', wrapMode.value ? '1' : '0') } catch { /* noop */ }
  if (wrapMode.value) {
    wrapAtBottom = true
    nextTick(() => { const el = wrapBox.value; if (el) el.scrollTop = el.scrollHeight })
  }
}
const wrapBox = ref(null)
const wrapRows = computed(() => {
  const rows = logRows.value
  // 合并模式：按组边界从末尾截取，head 行与其续行必须完整同组，避免 head 被 slice 切掉后只剩续行
  if (activeLog.value.mergeMode) {
    const out = []
    let groupTail = []
    for (let i = rows.length - 1; i >= 0; i--) {
      const row = rows[i]
      if (row.kind === 'head') {
        const group = [row, ...groupTail]
        if (out.length + group.length > LOG_WRAP_LIMIT && out.length > 0) break
        out.unshift(...group)
        groupTail = []
        if (out.length >= LOG_WRAP_LIMIT) break
      } else if (row.kind === 'cont') {
        groupTail.unshift(row)
      } else {
        out.unshift(row)
        groupTail = []
        if (out.length >= LOG_WRAP_LIMIT) break
      }
    }
    return out
  }
  return rows.slice(-LOG_WRAP_LIMIT)
})
let wrapAtBottom = true
function onWrapScroll() {
  const el = wrapBox.value
  if (el) wrapAtBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40
}
watch(wrapRows, () => {
  if (!wrapAtBottom) return
  nextTick(() => { const el = wrapBox.value; if (el) el.scrollTop = el.scrollHeight })
})
let logScrollTick = 0
function onLogScroll() {
  if (logScrollTick) return
  logScrollTick = requestAnimationFrame(() => {
    logScrollTick = 0
    const el = logViewBox.value
    if (!el) return
    vScrollTop.value = el.scrollTop
    const ch = el.clientHeight
    if (ch) vViewportH.value = ch
    logAtBottom = el.scrollHeight - el.scrollTop - ch < LOG_ROW_H * 3
  })
}
function measureViewport() {
  const el = logViewBox.value
  if (el && el.clientHeight) vViewportH.value = el.clientHeight
}
// 查询/级别/进程/合并/忽略/大小写等条件变化时，重置虚拟滚动到顶部——筛选结果从头展示，避免视口停在上一个大组中间看不到 head 行
watch(
  () => [activeLog.value.query, activeLog.value.level, activeLog.value.procName, activeLog.value.mergeMode, activeLog.value.matchCase, ignoreTags.value],
  () => {
    vScrollTop.value = 0
    logAtBottom = true
    nextTick(() => scrollLogView(true))
  }
)
let logScrollRaf = 0
function scrollLogView(force) {
  // rAF 节流：高频日志流下每帧最多触发一次滚动；force=true 强制到底（恢复/清屏/切视图后）
  if (logScrollRaf) return
  logScrollRaf = requestAnimationFrame(() => {
    logScrollRaf = 0
    const el = logViewBox.value
    if (!el) return
    if (force || logAtBottom) el.scrollTop = el.scrollHeight
  })
}
function scrollLogToBottom() {
  nextTick(() => scrollLogView(true))
}
async function loadLogProcesses() {
  if (!selected.value) return
  try {
    const res = await fetch(`/api/v1/adb/devices/${selected.value}/processes`, { credentials: 'same-origin' })
    if (res.ok) {
      const data = await res.json()
      if (data.processes) {
        logProcs.value = data.processes
        const v = activeLog.value
        if (v.procName && !logProcs.value.some((p) => `${p.name}|${p.pid}` === v.procName)) {
          v.procName = ''
        }
      }
    }
  } catch { /* 静默：进程列表刷新失败不阻塞日志显示 */ }
}
function startProcTimer() {
  stopProcTimer()
  loadLogProcesses()
  procTimer = setInterval(loadLogProcesses, 5000)
}
function stopProcTimer() {
  if (procTimer) { clearInterval(procTimer); procTimer = null }
}
async function startLogcat2(view) {
  if (!selected.value) return
  view.lines = []
  view.pausedCount = 0
  view.pausedLines = []
  view.paused = false
  view.running = true
  if (logActiveId.value === view.id) { resetLogFilter(); vScrollTop.value = 0; logAtBottom = true }
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  const ws = new WebSocket(`${proto}://${location.host}/ws/adb/${selected.value}/logcat?buffer=${view.buffer}`)
  view.ws = ws
  ws.onmessage = (ev) => {
    // 后端主动推送的错误（如设备掉线）：停止采集并提示，避免日志"冻"在旧数据上
    if (typeof ev.data === 'string' && ev.data.startsWith('{')) {
      try {
        const msg = JSON.parse(ev.data)
        if (msg && msg.type === 'error') {
          window.$toast.error(msg.error || '日志流已中断')
          view.running = false
          try { ws.close() } catch { /* noop */ }
          return
        }
      } catch { /* 非错误消息，按普通日志行处理 */ }
    }
    const record = decodeLogcatEvent(ev.data)
    record._id = ++view.seq // 稳定 key：新增行只挂载新节点，不再整列重渲染
    if (view.paused) {
      // 暂停：仍在接收日志，只进缓存不刷新列表
      view.pausedCount += 1
      view.pausedLines.push(record)
      if (view.pausedLines.length > LOG_LINES_MAX) view.pausedLines.shift()
      return
    }
    view.lines.push(record)
    if (view.lines.length > LOG_LINES_MAX) view.lines.splice(0, view.lines.length - LOG_LINES_MAX)
    // 只对活动视图节流重算过滤并滚动，后台视图接收时不抢资源
    if (logActiveId.value === view.id) { scheduleLogFilter(); scrollLogView() }
  }
  ws.onclose = () => { view.running = false }
  ws.onerror = () => { window.$toast.error('日志视图连接失败'); view.running = false }
}
function stopLogcat2(view) {
  if (view.ws) { try { view.ws.close() } catch { /* noop */ } view.ws = null }
  view.running = false
}
function stopAllLogViews() {
  logViews.value.forEach((v) => stopLogcat2(v))
}
function toggleLogCollect() {
  const v = activeLog.value
  if (v.running) stopLogcat2(v)
  else startLogcat2(v)
}
function restartLogView() {
  const v = activeLog.value
  if (!v.running) return
  stopLogcat2(v)
  startLogcat2(v)
}
function addLogView() {
  if (logViews.value.length >= LOG_VIEW_MAX) return window.$toast.warning(`最多同时打开 ${LOG_VIEW_MAX} 个视图`)
  const id = Date.now()
  const view = createLogView(id, `Logcat ${logViews.value.length + 1}`)
  logViews.value.push(view)
  logActiveId.value = id
  // 新视图默认不自动采集，由「开始采集」手动开启
}
function closeLogView() {
  if (logViews.value.length <= 1) return window.$toast.warning('至少保留一个视图')
  const idx = logViews.value.findIndex((v) => v.id === logActiveId.value)
  const closing = logViews.value[idx]
  stopLogcat2(closing) // 只关闭被删视图自己的 WebSocket，不影响其他视图
  logViews.value = logViews.value.filter((v) => v.id !== logActiveId.value)
  logActiveId.value = logViews.value[Math.min(idx, logViews.value.length - 1)].id
}
function clearLogView() {
  const v = activeLog.value
  v.lines = []
  v.pausedLines = []
  v.pausedCount = 0
  vScrollTop.value = 0
  logAtBottom = true
  resetLogFilter()
  nextTick(() => {
    const el = logViewBox.value
    if (el) el.scrollTop = 0
    measureViewport()
  })
}
function rememberLogQuery() {
  const q = activeLog.value.query.trim()
  if (!q) return
  logQueryHistory.value = [q, ...logQueryHistory.value.filter((x) => x !== q)].slice(0, LOG_HISTORY_MAX)
  saveLogQueryHistory(logQueryHistory.value)
}

// AI 分析
async function loadAnalyzeModels() {
  try {
    const r = await adbApi.logAnalyzeModels()
    analyzeModels.value = r.data
    if (analyzeModels.value.length && !analyzeModelId.value) analyzeModelId.value = analyzeModels.value[0].id
  } catch { /* noop */ }
}
async function analyzeLog() {
  analyzeLocal()
  if (!analyzeModels.value.length) return window.$toast.warning('请先启用 AI 模型')
  if (!activeLog.value.lines.length) return window.$toast.warning('请先开始采集日志')
  analyzing.value = true
  analyzeResult.value = ''
  try {
    const lines = activeLog.value.lines.slice(-400).map((record) => record.raw)
    const r = await adbApi.logAnalyze(selected.value, lines, analyzeModelId.value)
    if (!r.data.ok) { window.$toast.error(r.data.error || '分析失败'); return }
    analyzeResult.value = r.data.result
    analyzeModelName.value = r.data.model
  } catch (e) {
    window.$toast.error(e.response?.data?.detail || '分析失败')
  } finally { analyzing.value = false }
}

// ---------- 保存目录设置 ----------
const saveDir = ref('')
async function loadSaveDir() {
  try {
    const r = await adbApi.getSettings()
    saveDir.value = r.data.save_dir || ''
  } catch (e) {
    window.$toast.error(e.response?.data?.detail || '读取设置失败')
  }
}
async function saveDirSetting() {
  try {
    const r = await adbApi.setSettings(saveDir.value)
    saveDir.value = r.data.save_dir || ''
    window.$toast.success('保存目录已更新')
  } catch (e) {
    window.$toast.error(e.response?.data?.detail || '保存目录设置失败')
  }
}
// 本机目录浏览（网页内逐级选择）
const browseVisible = ref(false)
const browsePath = ref('')
const browseParent = ref('')
const browseItems = ref([])
async function openBrowse() {
  browseVisible.value = true
  browsePath.value = ''
  browseParent.value = ''
  browseItems.value = []
  // 若当前保存目录已是本机绝对路径，直接定位到该目录
  const init = /^[A-Za-z]:[\\/]/.test(saveDir.value) ? saveDir.value : ''
  await browseGo(init)
}
async function browseGo(path) {
  try {
    const r = await adbApi.browseDir(path || '')
    browsePath.value = r.data.path || ''
    browseParent.value = r.data.parent || ''
    browseItems.value = r.data.items || []
  } catch (e) {
    window.$toast.error(e.response?.data?.detail || '读取目录失败')
  }
}
function browsePick() {
  if (!browsePath.value) return window.$toast.warning('请先进入一个目录')
  saveDir.value = browsePath.value
  browseVisible.value = false
}

// ---------- 实用工具 ----------
async function takeScreenshot() {
  screenUrl.value = adbApi.screencapUrl(selected.value) + '?t=' + Date.now()
}
async function startRecord() {
  try {
    const r = await adbApi.recordStart(selected.value, { resolution: recResolution.value, filename: recName.value })
    if (!r.data.ok) return window.$toast.error('开始录屏失败')
    recording.value = true
    recUrl.value = ''
    recElapsed = 0
    recTimer.value = '00 : 00'
    if (recTimerInt) clearInterval(recTimerInt)
    recTimerInt = setInterval(() => {
      recElapsed++
      const m = String(Math.floor(recElapsed / 60)).padStart(2, '0')
      const s = String(recElapsed % 60).padStart(2, '0')
      recTimer.value = `${m} : ${s}`
    }, 1000)
    window.$toast.success('录屏已开始')
  } catch (e) {
    window.$toast.error(e.response?.data?.detail || '开始录屏失败')
  }
}
async function stopRecord() {
  if (stopping.value) return
  stopping.value = true
  // 立即停表，进入停止中状态
  recording.value = false
  if (recTimerInt) { clearInterval(recTimerInt); recTimerInt = null }
  try {
    const r = await adbApi.recordStop(selected.value)
    recName.value = r.data.name || recName.value
    if (r.data.local_path) window.$toast.success('录屏完成，已保存：' + r.data.local_path)
    else if (r.data.url) window.$toast.success('录屏完成')
    else window.$toast.success('录屏完成')
  } catch (e) {
    window.$toast.error(e.response?.data?.detail || '结束录屏失败')
  } finally {
    stopping.value = false
  }
}
function convertTs() {
  tsError.value = ''
  const raw = tsInput.value.trim()
  if (!raw) { tsOutput.value = String(Date.now()); return }
  const norm = raw.replace('T', ' ')
  const m = norm.match(/^(\d{4})-(\d{2})-(\d{2})(?:\s+(\d{2}):(\d{2})(?::(\d{2})(?:\.(\d{1,3}))?)?)?$/)
  if (!m) { tsOutput.value = ''; tsError.value = '时间格式错误，请输入：YYYY-MM-DD HH:mm:ss.SSS'; return }
  const iso = `${m[1]}-${m[2]}-${m[3]}T${m[4] || '00'}:${m[5] || '00'}:${m[6] || '00'}.${(m[7] || '0').padEnd(3, '0')}+08:00`
  const ts = Date.parse(iso)
  if (Number.isNaN(ts)) { tsOutput.value = ''; tsError.value = '无法解析该时间'; return }
  tsOutput.value = String(ts)
}

// ---------- Monkey ----------
async function loadMonkeyStatus(serial = selected.value) {
  if (!serial) return null
  try {
    const r = await adbApi.monkeyStatus(serial)
    if (serial === selected.value) monkeyStatusText.value = r.data.running ? '设备上的 Monkey 正在运行' : '设备上的 Monkey 未运行'
    return r.data
  } catch (e) {
    if (serial === selected.value) monkeyStatusText.value = '无法确认 Monkey 状态'
    throw e
  }
}
async function checkAndStopMonkey() {
  const serial = selected.value
  if (!serial) return window.$toast.warning('请先选择设备')
  monkeyControlBusy.value = true
  try {
    const status = await loadMonkeyStatus(serial)
    if (!status.running) return window.$toast.info('设备上没有运行中的 Monkey 测试')
    const r = await adbApi.monkeyStop(serial)
    await loadMonkeyStatus(serial)
    if (r.data.stopped) monkeyStoppedByUser.value = true
    window.$toast.success(r.data.stopped ? '已停止设备上的 Monkey 测试' : 'Monkey 测试已结束')
  } catch (e) {
    window.$toast.error(e.response?.data?.detail || '检测或停止 Monkey 失败')
  } finally {
    monkeyControlBusy.value = false
  }
}
async function loadMonkeyReports(serial = selected.value) {
  if (!serial) return
  monkeyReportsLoading.value = true
  try {
    const r = await adbApi.monkeyReports(serial)
    if (serial !== selected.value) return
    monkeyReports.value = r.data.reports || []
    monkeyReportDir.value = r.data.directory || ''
  } catch (e) {
    window.$toast.error(e.response?.data?.detail || '加载测试报告失败')
  } finally {
    monkeyReportsLoading.value = false
  }
}
async function deleteMonkeyReport(report) {
  if (!(await window.$confirm(`确认删除测试报告 ${report.name}？`, { danger: true }))) return
  try {
    await adbApi.deleteMonkeyReport(selected.value, report.name)
    if (monkeyPreview.value?.name === report.name) monkeyPreview.value = null
    await loadMonkeyReports()
    window.$toast.success('报告已删除')
  } catch (e) {
    window.$toast.error(e.response?.data?.detail || '删除报告失败')
  }
}
async function runMonkey() {
  const ratios = {}
  for (const event of monkeyEventTypes) {
    const value = monkeyRatios[event.key]
    if (value === '' || value === null) continue
    const number = Number(value)
    if (!Number.isInteger(number) || number < 0 || number > 100) {
      return window.$toast.warning(`${event.label}占比需为 0-100 的整数`)
    }
    ratios[event.key] = number
  }
  const total = Object.values(ratios).reduce((sum, value) => sum + value, 0)
  if (total > 100 || (Object.keys(ratios).length === monkeyEventTypes.length && total !== 100)) {
    return window.$toast.warning('事件占比总和不能超过 100%；全部填写时总和必须为 100%')
  }
  busy.value = 'Monkey 运行中…'
  monkeyOut.value = ''
  monkeyStoppedByUser.value = false
  const serial = selected.value
  try {
    const r = await adbApi.monkey(serial, {
      package: monkeyPkg.value, events: monkeyEvents.value, throttle: monkeyThrottle.value,
      ...ratios, ignore: monkeyIgnore.value,
    })
    monkeyOut.value = r.data.output
    await loadMonkeyReports(serial)
    try {
      const status = await loadMonkeyStatus(serial)
      if (status.running) return window.$toast.error('设备上的 Monkey 仍在运行，请点击“检测并停止”')
      if (monkeyStoppedByUser.value) return window.$toast.info('Monkey 测试已手动停止')
      window.$toast[r.data.ok ? 'success' : 'error'](r.data.ok ? 'Monkey 执行完成' : 'Monkey 执行出错，设备上的 Monkey 已停止')
    } catch {
      window.$toast.error('无法确认设备上的 Monkey 已停止，请点击“检测并停止”')
    }
  } catch (e) {
    window.$toast.error(e.response?.data?.detail || 'Monkey 执行失败')
    await loadMonkeyReports(serial)
  } finally { busy.value = '' }
}

// ---------- 通知触发（黑盒快速触发定时通知） ----------
const notifyPkg = ref('com.kjshd.calu.test')
const notifyJob30 = ref(null) // 30 分钟通知（UsageReminderJobService）
const notifyJob15 = ref(null) // 15 分钟循环通知（SystemJobService / WorkManager）
const notifyLoading = ref(false)
const notifyBusy = ref(0)
const notifyOut = ref('')
async function loadNotifyJobs() {
  if (!selected.value) return window.$toast.warning('请先选择设备')
  notifyLoading.value = true
  notifyJob30.value = null
  notifyJob15.value = null
  notifyOut.value = ''
  try {
    const r = await adbApi.notifyJobs(selected.value, notifyPkg.value.trim())
    if (!r.data.ok) return window.$toast.error(r.data.detail || '解析失败')
    const jobs = r.data.jobs || []
    const hit30 = jobs.find((j) => j.type === 1)
    const hit15 = jobs.find((j) => j.type === 2)
    if (hit30) notifyJob30.value = hit30.id
    if (hit15) notifyJob15.value = hit15.id
    const lines = []
    if (jobs.length) lines.push('解析到 ' + notifyPkg.value + ' 的任务：')
    jobs.forEach((j) => lines.push(`  [${j.type === 1 ? '30分钟' : j.type === 2 ? '15分钟循环' : '其他'}] id=${j.id}  ${j.service}`))
    if (!hit30) lines.push('30 分钟通知：任务未在调度队列（该任务由应用打开满 30 分钟时注册；被强弹消费后需等待重新注册，可重启应用后重新解析）')
    if (!hit15) lines.push('15 分钟循环：任务未在调度队列（WorkManager 强弹后通常会重新调度，可稍后重新解析）')
    if (!jobs.length && hit30 === null && hit15 === null) lines.unshift('未发现 ' + notifyPkg.value + ' 的定时任务，可能原因：')
    notifyOut.value = lines.join('\n')
    window.$toast[hit30 || hit15 ? 'success' : 'warning'](hit30 || hit15 ? '任务解析成功' : '未发现定时任务（任务需在调度队列中）')
  } catch (e) {
    window.$toast.error(e.response?.data?.detail || '解析失败')
  } finally { notifyLoading.value = false }
}
async function triggerNotify(type) {
  if (!selected.value) return window.$toast.warning('请先选择设备')
  let jobId = type === 1 ? notifyJob30.value : notifyJob15.value
  if (jobId === null) {
    // ID 为空（页面刷新/切换设备后状态丢失）：自动先解析一次，解析到再触发
    window.$toast.info('任务 ID 为空，自动解析中…')
    await loadNotifyJobs()
    jobId = type === 1 ? notifyJob30.value : notifyJob15.value
    if (jobId === null) {
      return window.$toast.warning('任务未在调度队列，无法触发（' + (type === 1 ? '30 分钟任务需应用打开满 30 分钟注册' : '15 分钟任务可稍后重新解析') + '）')
    }
  }
  notifyBusy.value = type
  notifyOut.value = ''
  try {
    const r = await adbApi.notifyTrigger(selected.value, type, jobId, notifyPkg.value.trim())
    notifyOut.value = (r.data.steps || []).map((s) => `■ ${s.cmd}\n   ${s.ok ? '成功' : '失败'}: ${s.out || '（无输出）'}`).join('\n\n')
    window.$toast[r.data.ok ? 'success' : 'error'](r.data.ok ? '通知已触发' : '触发过程有步骤失败，请查看输出')
  } catch (e) {
    window.$toast.error(e.response?.data?.detail || '触发失败')
  } finally { notifyBusy.value = 0 }
}

// ---------- 屏幕镜像 ----------
function castPos(ev) {
  const el = videoEl.value
  if (!el) return null
  const rect = el.getBoundingClientRect()
  if (rect.width <= 0 || rect.height <= 0) return null
  const x = ((ev.clientX - rect.left) / rect.width) * castDeviceW
  const y = ((ev.clientY - rect.top) / rect.height) * castDeviceH
  return { x: Math.round(Math.min(Math.max(x, 0), castDeviceW)), y: Math.round(Math.min(Math.max(y, 0), castDeviceH)) }
}
// 投屏悬浮面板：位置/大小/拖动/缩放
const panelPos = ref({ x: 0, y: 70 })
const panelW = ref(300)
const panelH = ref(650) // 约 9:19.5 手机比例，默认适配 1080p 窗口完整展示
let dragStart = null
let resizeStart = null
const panelStyle = computed(() => ({
  left: panelPos.value.x + 'px',
  top: panelPos.value.y + 'px',
  width: panelW.value + 'px',
  height: panelH.value + 'px',
}))
function startDrag(e) {
  if (e.target.closest('button')) return
  dragStart = { mx: e.clientX, my: e.clientY, px: panelPos.value.x, py: panelPos.value.y }
  window.addEventListener('mousemove', onDrag)
  window.addEventListener('mouseup', endDrag)
  e.preventDefault()
}
function onDrag(e) {
  if (!dragStart) return
  panelPos.value.x = Math.min(Math.max(dragStart.px + e.clientX - dragStart.mx, -panelW.value + 80), window.innerWidth - 80)
  panelPos.value.y = Math.min(Math.max(dragStart.py + e.clientY - dragStart.my, 0), window.innerHeight - 60)
}
function endDrag() {
  dragStart = null
  window.removeEventListener('mousemove', onDrag)
  window.removeEventListener('mouseup', endDrag)
}
function startResize(e) {
  resizeStart = { mx: e.clientX, my: e.clientY, w: panelW.value, h: panelH.value }
  window.addEventListener('mousemove', onResize)
  window.addEventListener('mouseup', endResize)
  e.preventDefault()
  e.stopPropagation()
}
function onResize(e) {
  if (!resizeStart) return
  const ratio = 9 / 19.5
  let w = resizeStart.w + (e.clientX - resizeStart.mx)
  w = Math.min(Math.max(w, 220), 620)
  panelW.value = w
  panelH.value = Math.round(w / ratio)
}
function endResize() {
  resizeStart = null
  window.removeEventListener('mousemove', onResize)
  window.removeEventListener('mouseup', endResize)
}

async function startCast() {
  if (!selected.value) return
  // 默认展示在页面右侧，高度适配视口保证完整展示
  const topY = 70
  const maxH = Math.min(650, window.innerHeight - topY - 16)
  panelH.value = Math.max(240, maxH)
  panelW.value = Math.round(panelH.value * 9 / 19.5)
  panelPos.value.y = topY
  panelPos.value.x = Math.max(window.innerWidth - panelW.value - 28, 0)
  castError.value = ''
  // 先唤醒设备屏幕（熄屏时 screenrecord 只输出参数集导致黑屏）
  try { await adbApi.execute(selected.value, 'shell input keyevent 224') } catch { /* noop */ }
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  const base = `${proto}://${location.host}`
  casting.value = true
  try {
    ctrlWs = new WebSocket(`${base}/ws/adb/${selected.value}/control`)
    await new Promise((res, rej) => { ctrlWs.onopen = res; ctrlWs.onerror = () => rej(new Error('控制通道连接失败')) })
    castWs = new WebSocket(`${base}/ws/adb/${selected.value}/stream`)
    castWs.binaryType = 'arraybuffer'
    castWs.onmessage = (ev) => {
      if (typeof ev.data === 'string') {
        try {
          const m = JSON.parse(ev.data)
          if (m.type === 'meta' && m.resolution) {
            resolution.value = m.resolution
            const mm = m.resolution.split('x')
            castDeviceW = parseInt(mm[0]); castDeviceH = parseInt(mm[1])
          }
        } catch { /* noop */ }
        return
      }
      if (jmuxer && ev.data instanceof ArrayBuffer) jmuxer.feed({ video: new Uint8Array(ev.data) })
    }
    castWs.onclose = () => { if (castOn.value) castError.value = '画面通道断开' }
    castWs.onerror = () => { if (castOn.value) castError.value = '画面通道连接失败' }
    await new Promise((res, rej) => { castWs.onopen = res; castWs.onerror = () => rej(new Error('画面通道连接失败')) })
    jmuxer = new JMuxer({ node: videoEl.value, mode: 'video', flushingTime: 0, fps: 60, debug: false })
    castOn.value = true
  } catch (e) {
    castError.value = e.message
    stopCast()
  } finally { casting.value = false }
}
function stopCast() {
  castOn.value = false
  casting.value = false
  if (jmuxer) { try { jmuxer.destroy() } catch { /* noop */ } jmuxer = null }
  if (castWs) { try { castWs.close() } catch { /* noop */ } castWs = null }
  if (ctrlWs) { try { ctrlWs.close() } catch { /* noop */ } ctrlWs = null }
  if (longTimer) { clearTimeout(longTimer); longTimer = null }
  if (keyTimer) { clearTimeout(keyTimer); keyTimer = null }
  keyBuf = ''
  pointer.value = null
}

// 唤醒设备屏幕（熄屏时 screenrecord 无画面）
async function wakeScreen() {
  if (!selected.value) return
  try { await adbApi.execute(selected.value, 'shell input keyevent 224'); window.$toast.success('已发送唤醒指令') }
  catch (e) { window.$toast.error(e.response?.data?.detail || '唤醒失败') }
}
function sendCtrl(msg) {
  if (ctrlWs && ctrlWs.readyState === WebSocket.OPEN) ctrlWs.send(JSON.stringify(msg))
}
function sendText() {
  if (!inputText.value) return
  // 含中文等非 ASCII 走剪贴板粘贴通道，其余走 input text
  const txt = inputText.value
  inputText.value = ''
  sendCtrl({ type: /[^\x00-\x7f]/.test(txt) ? 'paste' : 'text', text: txt })
}
function sendKey(code) { sendCtrl({ type: 'keyevent', keycode: code }) }

// ---------- 镜像键盘输入（聚焦画面后直输 / 剪贴板粘贴） ----------
const castFocus = ref(false)
let keyBuf = ''
let keyTimer = null
// 浏览器键盘码 → Android keycode（常用键）
const KEY_MAP = {
  Enter: 66, Backspace: 67, Tab: 61, Escape: 111, Delete: 112,
  Home: 3, End: 123, PageUp: 92, PageDown: 93,
  ArrowUp: 19, ArrowDown: 20, ArrowLeft: 21, ArrowRight: 22,
  ' ': 62,
  '0': 7, '1': 8, '2': 9, '3': 10, '4': 11, '5': 12, '6': 13, '7': 14, '8': 15, '9': 16,
}
function flushKeyBuf() {
  if (!keyBuf) return
  const txt = keyBuf
  keyBuf = ''
  keyTimer = null
  sendCtrl({ type: /[^\x00-\x7f]/.test(txt) ? 'paste' : 'text', text: txt })
}
function onCastKey(ev) {
  const ae = document.activeElement
  // 页面其他输入框/文本域聚焦时不拦截键盘
  if (ae && (ae.tagName === 'INPUT' || ae.tagName === 'TEXTAREA' || ae.isContentEditable)) return
  // 组合键：仅处理 Ctrl/Cmd+V 粘贴，其余组合键忽略
  if (ev.ctrlKey || ev.metaKey) {
    if ((ev.key === 'v' || ev.key === 'V') && !ev.shiftKey && !ev.altKey) {
      ev.preventDefault()
      doCastPaste()
    }
    return
  }
  if (ev.altKey) return
  if (ev.key === 'Shift' || ev.key === 'Control' || ev.key === 'Meta' || ev.key === 'Alt' || ev.key === 'CapsLock') return
  const kc = KEY_MAP[ev.key]
  if (kc !== undefined) {
    ev.preventDefault()
    // 先清未发送的字符缓冲，再发按键
    if (keyBuf) flushKeyBuf()
    sendCtrl({ type: 'keyevent', keycode: kc })
    return
  }
  if (ev.key.length === 1) {
    ev.preventDefault()
    keyBuf += ev.key
    if (keyTimer) clearTimeout(keyTimer)
    keyTimer = setTimeout(flushKeyBuf, 60)
  }
}
async function doCastPaste() {
  try {
    let txt = ''
    if (navigator.clipboard && navigator.clipboard.readText) txt = await navigator.clipboard.readText()
    if (!txt) {
      window.$toast.warning('剪贴板为空或无法读取')
      return
    }
    if (keyBuf) flushKeyBuf()
    sendCtrl({ type: 'paste', text: txt.slice(0, 2000) })
  } catch {
    window.$toast.error('浏览器未授权读取剪贴板，请先在地址栏允许剪贴板权限')
  }
}

// ---------- 触控：真实连续触摸流（input motionevent，对标 scrcpy） ----------
// DOWN → MOVE×N → UP 为一个触摸手势：点击/拖动/长按/惯性滚动全部由系统识别，跟手且不再误判
function onMouseDown(ev) {
  const p = castPos(ev)
  if (!p) return
  pointer.value = { x: p.x, y: p.y, t0: Date.now(), moved: false, longFired: false, lastT: 0 }
  sendCtrl({ type: 'drag', action: 'down', x: p.x, y: p.y })
  longTimer = setTimeout(() => {
    // DOWN 停留 500ms 未移动 = 长按，系统已自行识别（无需额外命令），仅标记避免发多余 MOVE
    if (pointer.value && !pointer.value.moved) pointer.value.longFired = true
  }, 500)
}
function onMouseMove(ev) {
  if (!pointer.value) return
  const p = castPos(ev)
  if (!p) return
  const pt = pointer.value
  const now = Date.now()
  const dx = p.x - pt.x
  const dy = p.y - pt.y
  const dist = Math.hypot(dx, dy)
  // 位移超过阈值即判定为拖动（抑制长按），节流发送 MOVE 保持跟手又不堆积
  if (pt.longFired) return
  if (dist >= 8 && now - pt.lastT >= 20) {
    pt.lastT = now
    pt.moved = true
    pt.x = p.x
    pt.y = p.y
    sendCtrl({ type: 'drag', action: 'move', x: p.x, y: p.y })
  }
}
function onMouseUp() {
  if (!pointer.value) return
  if (longTimer) { clearTimeout(longTimer); longTimer = null }
  const pt = pointer.value
  pointer.value = null
  sendCtrl({ type: 'drag', action: 'up', x: pt.x, y: pt.y })
}
function onMouseLeave() {
  // 按住画布时鼠标移出：取消触摸，避免设备端触摸卡住
  if (!pointer.value) return
  if (longTimer) { clearTimeout(longTimer); longTimer = null }
  sendCtrl({ type: 'drag', action: 'cancel', x: pointer.value.x, y: pointer.value.y })
  pointer.value = null
}

// 进入/离开日志分析分类不自动开始/停止采集：由「开始采集/停止采集」按钮手动控制；切走保留视图数据
watch(cat, (v) => {
  if (v === 'logcat2') { startProcTimer(); nextTick(measureViewport) }
  else stopProcTimer()
})
watch([selected, cat], ([serial, category]) => {
  monkeyPreview.value = null
  if (serial && category === 'monkey') {
    loadMonkeyReports()
    loadMonkeyStatus().catch(() => {})
  } else { monkeyReports.value = []; monkeyReportDir.value = ''; monkeyStatusText.value = '未检测' }
})

// 过滤条件变化立即重算（用户输入时即时反馈）
watch(() => [activeLog.value.query, activeLog.value.level, activeLog.value.procName, activeLog.value.matchCase], resetLogFilter)
// 切换视图：增量补齐目标视图的过滤结果（保留该视图期间的缓存），滚到底部
watch(logActiveId, () => {
  reconcileLogView()
  vScrollTop.value = 0
  logAtBottom = true
  nextTick(() => { measureViewport(); scrollLogView(true) })
})
// 全屏/缩小时容器高度变化，重测视口并跟随到底
watch(logViewMax, () => nextTick(() => { measureViewport(); scrollLogView(true) }))

onMounted(() => { loadDevices(); loadSaveDir(); nextTick(measureViewport) })
onBeforeUnmount(() => { stopLogcat(); stopAllLogViews(); stopCast(); stopProcTimer(); if (logFilterTimer) clearTimeout(logFilterTimer) })
</script>

<style scoped>
.tbl { width: 100%; border-collapse: collapse; margin-top: 8px; }
.tbl th, .tbl td { border: 1px solid #e5e7eb; padding: 6px 10px; text-align: left; font-size: 13px; }
.tbl th { background: #f9fafb; font-weight: 600; }
.row-selected { background: #eff6ff !important; }
.dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; }
.dot-ok { background: #22c55e; }
.dot-bad { background: #ef4444; }
.error-text { color: #dc2626; font-size: 13px; margin-top: 8px; }
.cat-nav { display: flex; gap: 8px; margin: 12px 0; flex-wrap: wrap; }
.browse-mask { position: fixed; inset: 0; background: rgba(15,23,42,.45); z-index: 1001; display: flex; align-items: center; justify-content: center; }
.browse-box { width: 480px; max-width: 92vw; background: #fff; border-radius: 10px; box-shadow: 0 12px 40px rgba(0,0,0,.25); display: flex; flex-direction: column; overflow: hidden; font-family: 'Microsoft YaHei', '微软雅黑', sans-serif; }
.browse-head { display: flex; align-items: center; justify-content: space-between; padding: 10px 14px; background: #f8fafc; border-bottom: 1px solid #e5e7eb; font-size: 14px; font-weight: 600; color: #1f2937; }
.browse-path { padding: 8px 14px; font-size: 12px; color: #2563eb; background: #eff6ff; border-bottom: 1px solid #e5e7eb; word-break: break-all; }
.browse-list { max-height: 300px; overflow-y: auto; padding: 8px; display: flex; flex-direction: column; gap: 2px; }
.browse-item { text-align: left; padding: 7px 10px; border: none; background: transparent; border-radius: 6px; font-size: 13px; cursor: pointer; color: #374151; font-family: inherit; }
.browse-item:hover { background: #eff6ff; color: #1d4ed8; }
.browse-foot { display: flex; align-items: center; justify-content: flex-end; gap: 8px; padding: 10px 14px; border-top: 1px solid #e5e7eb; }
.cat-btn { padding: 7px 16px; border: 1px solid var(--border-color, #e5e7eb); background: var(--bg-card, #fff); border-radius: 6px; font-size: 13px; cursor: pointer; color: var(--text-main, #374151); transition: all 0.15s ease; }
.cat-btn:hover { border-color: var(--border-focus, #059669); color: var(--accent-primary, #059669); }
.cat-btn.active { background: var(--accent-primary, #059669); color: var(--text-inverse, #fff); border-color: var(--accent-primary, #059669); }
.sub-nav { display: flex; gap: 6px; margin-bottom: 10px; }
.sub-btn { padding: 5px 14px; border: 1px solid var(--border-color, #e5e7eb); background: var(--bg-card, #fff); border-radius: 6px; font-size: 13px; cursor: pointer; color: var(--text-main, #374151); transition: all 0.15s ease; }
.sub-btn:hover { border-color: var(--border-focus, #059669); color: var(--accent-primary, #059669); }
.sub-btn.active { background: var(--accent-primary, #059669); color: var(--text-inverse, #fff); border-color: var(--accent-primary, #059669); }
.sec-title { font-weight: 600; font-size: 14px; margin-bottom: 10px; color: #1f2937; }
.grid-btns { display: flex; gap: 8px; flex-wrap: wrap; }
.monkey-event-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 8px 14px; }
.monkey-event { display: flex; align-items: center; gap: 6px; font-size: 13px; }
.monkey-event span:first-child { flex: 1; }
.monkey-event input { width: 64px; min-width: 0; }
.mono-out { background: #0f172a; color: #e2e8f0; padding: 10px; border-radius: 6px; font-size: 12px; max-height: 220px; overflow: auto; margin-top: 8px; white-space: pre-wrap; word-break: break-all; }
.shell-out { background: #0f172a; color: #e2e8f0; padding: 10px; border-radius: 6px; font-size: 12px; max-height: 260px; overflow: auto; margin-top: 8px; white-space: pre-wrap; word-break: break-all; }
.notify-type { flex: 1; min-width: 300px; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 12px; }
.notify-type-head { display: flex; align-items: baseline; gap: 8px; margin-bottom: 6px; }
.job-id { font-family: Consolas, monospace; font-size: 14px; font-weight: 600; color: #1d4ed8; min-width: 40px; }
.log-table { position: relative; margin-top: 8px; border: 1px solid rgba(148,163,184,0.2); border-radius: 6px; overflow: hidden; background: #0f172a; }
.log-table-scroll { margin-top: 8px; border: 1px solid rgba(148,163,184,0.2); border-radius: 6px; background: #0f172a; overflow-x: auto; overflow-y: hidden; }
.log-table-scroll .log-table { margin-top: 0; border: none; border-radius: 0; min-width: 920px; }
.logcat-wrap { height: 560px; overflow-y: auto; overflow-x: hidden; }
.logcat-wrap .log-line { height: auto; min-height: 20px; line-height: 20px; align-items: start; padding: 2px 0; }
.logcat-wrap .log-cell-msg { white-space: pre-wrap; word-break: break-all; overflow: visible; text-overflow: clip; }
.logcat-wrap .log-cell-cont { white-space: pre-wrap; word-break: break-all; overflow: visible; }
/* 全屏：过滤行中灰背景，输入框保持白底；文字浅色 */
.log-view-box.log-max .q-row { background: #475569; border: 1px solid rgba(148,163,184,0.25); border-radius: 6px; padding: 8px 10px; margin-bottom: 8px; flex: none; }
.log-view-box.log-max .q-row .ctl-label { color: #cbd5e1; }
.log-view-box.log-max .q-row input, .log-view-box.log-max .q-row select { background: #fff; }
/* 勾选框不被 .form-row input 的 min-width 撑大 */
.form-row input[type="checkbox"] { min-width: 0; width: 14px; height: 14px; }
.log-thead { display: grid; grid-template-columns: var(--w-time) var(--w-lv) var(--w-proc) var(--w-tid) var(--w-tag) 1fr; background: rgba(148,163,184,0.14); color: #cbd5e1; font-size: 12px; line-height: 24px; border-bottom: 1px solid rgba(148,163,184,0.25); user-select: none; position: relative; z-index: 2; }
.log-th { position: relative; padding: 0 6px; white-space: nowrap; overflow: hidden; cursor: col-resize; }
.log-th:not(:last-child)::after { content: ''; position: absolute; right: 0; top: 4px; bottom: 4px; width: 1px; background: rgba(148,163,184,0.25); }
.log-th-msg { cursor: default; }
.logcat-out { background: #0f172a; color: #e2e8f0; padding: 0 0 0 0; border-radius: 0 0 6px 6px; font-size: 12px; height: 560px; overflow: auto; }
.log-spacer { position: relative; }
.log-window { position: absolute; left: 0; right: 0; top: 0; will-change: transform; }
.log-line { display: grid; grid-template-columns: var(--w-time) var(--w-lv) var(--w-proc) var(--w-tid) var(--w-tag) 1fr; height: 20px; line-height: 20px; align-items: center; white-space: nowrap; font-family: Consolas, 'Microsoft YaHei', monospace; font-size: 12px; }
.log-line:hover { background: rgba(255,255,255,0.05); }
.log-cell { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; padding: 0 6px; }
.log-cell-lv { font-weight: 700; }
.log-cell-msg { min-width: 0; }
.log-cont { color: #94a3b8; }
.log-cell-cont { grid-column: 6; justify-self: stretch; width: 100%; padding-left: 14px; border-left: 2px solid rgba(148,163,184,0.25); box-sizing: border-box; }
.log-cell-wide { grid-column: 1 / -1; color: #94a3b8; }
.log-stack { color: #fca5a5; background: rgba(239,68,68,0.06); }
.log-resizing, .log-resizing * { cursor: col-resize !important; user-select: none !important; }
.lv-V { color: #9ca3af; }
.lv-D { color: #60a5fa; }
.lv-I { color: #34d399; }
.lv-W { color: #fbbf24; }
.lv-E { color: #f87171; }
.lv-F { color: #ef4444; font-weight: 600; }
.log-view-box { position: relative; }
.log-view-box.log-max { position: fixed; inset: 0; z-index: 90; display: flex; flex-direction: column; padding: 10px 14px; box-sizing: border-box; }
.log-view-box.log-max .log-table { flex: 1; min-height: 0; display: flex; flex-direction: column; margin-top: 0; }
.log-view-box.log-max .log-table-scroll { flex: 1; min-height: 0; display: flex; flex-direction: column; margin-top: 0; overflow-x: auto; }
.log-view-box.log-max .log-table-scroll .log-table { flex: 1; min-height: 0; display: flex; flex-direction: column; }
.log-view-box.log-max .log-table-scroll .logcat-out { flex: 1; min-height: 0; }
.log-view-box.log-max .log-thead { flex: none; }
.log-view-box.log-max .logcat-out { flex: 1; min-height: 0; border-radius: 0 0 6px 6px; font-size: 13px; }
.log-max-close { position: absolute; top: 10px; right: 14px; z-index: 95; }
.rec-timer { font-family: Consolas, monospace; font-size: 14px; font-weight: 700; color: #dc2626; padding: 4px 10px; border: 1px solid #fca5a5; border-radius: 6px; background: #fef2f2; white-space: nowrap; }
.rec-stopping { color: #2563eb; border-color: #93c5fd; background: #eff6ff; }
.log-view-head { display: flex; align-items: center; gap: 12px; font-size: 12px; color: #64748b; margin-top: 8px; }
/* 进程筛选：单击选择 / 双击搜索（样式与 .form-row select 对齐） */
.sel-search { position: relative; display: inline-block; width: 200px; }
.sel-search-input { width: 100%; padding: 7px 10px; font-size: 13px; border: 1px solid #d0d7de; border-radius: 6px; background: #fff; color: #1e293b; box-sizing: border-box; outline: none; }
.sel-search-input:focus { border-color: #3b82f6; }
.sel-search-read { cursor: pointer; display: flex; align-items: center; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; user-select: none; }
.sel-search-menu { position: absolute; top: calc(100% + 2px); left: 0; right: 0; max-height: 240px; overflow-y: auto; background: #fff; border: 1px solid #d0d7de; border-radius: 6px; box-shadow: 0 4px 12px rgba(0,0,0,.12); z-index: 60; padding: 4px 0; }
.sel-search-item { padding: 6px 10px; font-size: 13px; color: #1e293b; cursor: pointer; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.sel-search-item:hover { background: #eff6ff; }
.sel-search-item.on { background: #dbeafe; color: #1d4ed8; }
.sel-search-empty { padding: 6px 10px; font-size: 12px; color: #94a3b8; }
/* 查询过滤下拉：▾ 展开语法字段，点击追加到输入框末尾 */
.q-filter { position: relative; display: flex; flex: 1; align-items: center; min-width: 0; }
.q-filter > input { flex: 1; min-width: 0; }
.q-toggle { height: 33px; padding: 0 8px; margin-left: 4px; border: 1px solid #d0d7de; border-radius: 6px; background: #fff; color: #475569; font-size: 12px; cursor: pointer; line-height: 1; flex: none; }
.q-toggle:hover { border-color: #3b82f6; color: #3b82f6; }
.q-menu { position: absolute; top: calc(100% + 2px); left: 0; width: 320px; max-height: 260px; overflow-y: auto; background: #fff; border: 1px solid #d0d7de; border-radius: 6px; box-shadow: 0 4px 12px rgba(0,0,0,.12); z-index: 60; padding: 4px 0; }
.q-item { display: flex; align-items: baseline; gap: 10px; padding: 6px 10px; font-size: 13px; color: #1e293b; cursor: pointer; }
.q-item:hover { background: #eff6ff; }
.q-item code { color: #1d4ed8; font-family: Consolas, monospace; flex: none; }
.q-desc { color: #64748b; font-size: 12px; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
.app-list { max-height: 260px; overflow-y: auto; margin-top: 10px; border: 1px solid #eef2f7; border-radius: 6px; }
.app-item { display: flex; align-items: center; padding: 5px 10px; border-bottom: 1px solid #f1f5f9; }
.app-name { flex: 1; font-size: 13px; font-family: Consolas, monospace; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.app-ops { display: flex; gap: 6px; }
.fs-list { max-height: 260px; overflow-y: auto; margin-top: 8px; border: 1px solid #eef2f7; border-radius: 6px; }
.fs-item { display: flex; align-items: center; padding: 5px 10px; border-bottom: 1px solid #f1f5f9; font-size: 13px; }
.fs-name { flex: 1; cursor: pointer; }
.fs-name.fs-dir { color: #1d4ed8; }
.fs-name.fs-link { color: #9333ea; }
.fs-size { width: 90px; text-align: right; color: #64748b; font-size: 12px; }
.fs-ops { width: 110px; text-align: right; }
.an-report { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; margin-top: 10px; }
.an-summary { font-size: 13px; color: #0e7490; margin-bottom: 8px; }
.an-counts { display: flex; gap: 16px; font-size: 13px; margin-bottom: 8px; }
.an-issues { max-height: 200px; overflow-y: auto; display: flex; flex-direction: column; gap: 4px; }
.an-issue { font-size: 12px; border-radius: 6px; padding: 4px 8px; word-break: break-all; }
.sev-critical { background: #fef2f2; color: #dc2626; }
.sev-high { background: #fff7ed; color: #ea580c; }
.sev-medium { background: #fffbeb; color: #d97706; }
.ai-result { margin-top: 10px; }
.ai-pre { background: #0f172a; color: #e2e8f0; padding: 12px; border-radius: 6px; font-size: 13px; max-height: 320px; overflow: auto; white-space: pre-wrap; word-break: break-all; }
.ts-out { font-family: Consolas, monospace; font-size: 13px; color: #0891b2; margin-top: 8px; }
.cast-box { position: relative; flex: 1; min-height: 0; width: 100%; outline: none; }
.cast-box.focused { box-shadow: inset 0 0 0 2px #3b82f6; }
.cast-video { width: 100%; height: 100%; background: #000; border-radius: 0; display: block; cursor: crosshair; object-fit: fill; }
.cast-err { position: absolute; left: 0; right: 0; top: 50%; transform: translateY(-50%); text-align: center; color: #f87171; font-size: 13px; }
/* 投屏悬浮面板 */
.cast-panel { position: fixed; z-index: 1000; display: flex; flex-direction: column; background: #fff; border: 1px solid #d1d5db; border-radius: 10px; box-shadow: 0 8px 28px rgba(15, 23, 42, .22); overflow: hidden; }
.cast-panel-head { display: flex; align-items: center; gap: 6px; padding: 6px 10px; background: #1e293b; color: #e2e8f0; font-size: 12px; cursor: move; user-select: none; white-space: nowrap; flex-wrap: nowrap; }
.cast-panel-head .cast-title { overflow: hidden; text-overflow: ellipsis; max-width: 45%; flex-shrink: 1; }
.cast-panel-head .cast-spacer { flex: 1; }
.cast-panel-head .cast-btn { flex-shrink: 0; white-space: nowrap; }
.cast-panel-body { flex: 1; min-height: 0; display: flex; flex-direction: column; }
.cast-panel-ctrl { display: flex; align-items: center; gap: 5px; padding: 6px 8px; border-top: 1px solid #e5e7eb; background: #f8fafc; flex-wrap: nowrap; }
.cast-panel-ctrl .btn-small { padding: 2px 7px; font-size: 12px; white-space: nowrap; }
.cast-panel-ctrl input { font-size: 12px; min-width: 0; }
.cast-resize { position: absolute; right: 0; bottom: 0; width: 18px; height: 18px; cursor: nwse-resize; z-index: 5; }
.cast-resize::after { content: ''; position: absolute; right: 3px; bottom: 3px; width: 8px; height: 8px; border-right: 2px solid #94a3b8; border-bottom: 2px solid #94a3b8; }
.screen-box { margin-top: 10px; }
.screen-img { max-width: 300px; max-height: 600px; border: 1px solid #e5e7eb; border-radius: 6px; }
.screen-box video { width: 100%; max-width: 560px; background: #000; border-radius: 8px; display: block; }
.attach-link { color: #2563eb; text-decoration: underline; cursor: pointer; font-size: 13px; }
</style>
