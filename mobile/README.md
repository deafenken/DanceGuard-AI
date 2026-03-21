# DanceGuard Mobile

这是项目的手机端前端目录，目标是复用现有 `Python + MindSpore + VMC` 后端，提供可打包 APK 的移动端界面。

## 目录结构
- `www/`：手机端静态页面
- `capacitor.config.json`：Capacitor 配置
- `package.json`：打包依赖与脚本

## 本地预览
当前后端会直接托管手机端页面：
- `http://127.0.0.1:8000/mobile/`

启动方式仍然是项目根目录的：
- `start.bat`

## 打包为 APK
推荐方式是远程页面模式，让 Android WebView 直接加载你部署好的后端 `/mobile/` 页面。

### 1. 安装依赖
在 `mobile/` 目录执行：
```powershell
npm install
```

### 2. 增加 Android 平台
```powershell
npx cap add android
```

### 3. 设置远程页面地址
将 `capacitor.config.json` 改成类似：
```json
{
  "appId": "ai.danceguard.mobile",
  "appName": "DanceGuard Mobile",
  "webDir": "www",
  "bundledWebRuntime": false,
  "server": {
    "url": "http://你的后端IP:8000/mobile/",
    "cleartext": true,
    "androidScheme": "http"
  }
}
```

### 4. 同步并打开 Android Studio
```powershell
npx cap sync android
npx cap open android
```

## 为什么采用远程页面模式
- 评分后端是 Python 进程，不会直接跑在 Android 里
- 手机端需要访问同一套 `/api/*` 和 `/assets/*`
- 所以 APK 最稳的做法是包装移动端页面，后端仍部署在电脑或服务器上

## 当前功能
- 实时评估
- 视频预览
- 标准视频对照
- 评分总览
- CFPI 四维与文化动作
- 历史记录
- 离线导入
- 设备监控
- 账号中心
