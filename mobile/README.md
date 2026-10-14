# CausaLab 安卓客户端（Flutter WebView 壳）

一个极薄的客户端：把「你电脑上运行的 CausaLab」装进手机——页面与数据都由电脑端后端提供，
手机与电脑在同一局域网即可使用（适合在家/办公室随手记录与查看）。

## 使用方式

1. 电脑端运行 CausaLab（双击 `启动CausaLab.bat`，或按 README 启动）；
2. 手机与电脑连接同一个 Wi-Fi；
3. 安装 APK 后首次打开，填写电脑地址：
   - 静态页面形态（推荐）：`http://<电脑IP>:8000` —— 需先在电脑执行过一次 `npm run build:static`；
   - 开发形态：`http://<电脑IP>:3000`（电脑端 `npm run dev` 或一键脚本已包含）；
   - 电脑 IP 用 `ipconfig` 查看（IPv4 地址，形如 192.168.1.100）。
4. 之后随时可在应用右上角「⚙」修改服务器地址。

## 构建（Windows，本机已验证）

```powershell
# 前置：Flutter（D:\flutter）+ JDK 17 + Android SDK；设置环境变量后执行
$env:JAVA_HOME = "D:\jdk17"
$env:ANDROID_HOME = "D:\Android\Sdk"
$env:GRADLE_USER_HOME = "D:\gradle-home"
cd mobile
flutter build apk --release
# 产物：mobile\build\app\outputs\flutter-apk\app-release.apk
```

说明：

- release 包默认用 debug 签名（Flutter 模板行为），可直接侧载安装；上架应用商店需自行配置正式签名；
- 允许明文 HTTP（`usesCleartextTraffic`），因为后端运行在局域网 `http://`；
- 仅打包 Android 平台（iOS 未包含）。
