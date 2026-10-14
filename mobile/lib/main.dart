import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:webview_flutter/webview_flutter.dart';

/// CausaLab 安卓客户端：一个极薄的 WebView 壳。
///
/// 页面与数据由你电脑上运行的 CausaLab 后端提供（同一局域网）——
/// 首次启动填写电脑地址（形如 http://192.168.1.100:8000），之后可随时在右上角修改。
///
/// 前置条件（电脑端，见仓库 README）：
///   1) 运行 `启动CausaLab.bat`，或手动启动后端（uvicorn :8000）；
///   2) 静态页面形态：前端执行过一次 `npm run build:static`（后端会自动同源托管 frontend/out）。
const _kServerKey = 'causalab.server_url';

void main() {
  runApp(const CausaLabApp());
}

class CausaLabApp extends StatelessWidget {
  const CausaLabApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'CausaLab',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorSchemeSeed: const Color(0xFF6366F1),
        useMaterial3: true,
      ),
      home: const RootPage(),
    );
  }
}

/// 根页面：读取已保存的服务器地址 → 没有则先配置，有则直接进 WebView。
class RootPage extends StatefulWidget {
  const RootPage({super.key});

  @override
  State<RootPage> createState() => _RootPageState();
}

class _RootPageState extends State<RootPage> {
  bool _loaded = false;
  String? _server;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final sp = await SharedPreferences.getInstance();
    setState(() {
      _server = sp.getString(_kServerKey);
      _loaded = true;
    });
  }

  @override
  Widget build(BuildContext context) {
    if (!_loaded) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    final server = _server;
    if (server == null || server.isEmpty) {
      return SetupPage(
        initial: server,
        onSaved: (url) => setState(() => _server = url),
      );
    }
    return WebViewPage(
      server: server,
      onChangeServer: () => setState(() => _server = null),
    );
  }
}

/// 服务器地址配置页。
class SetupPage extends StatefulWidget {
  const SetupPage({super.key, this.initial, required this.onSaved});

  final String? initial;
  final ValueChanged<String> onSaved;

  @override
  State<SetupPage> createState() => _SetupPageState();
}

class _SetupPageState extends State<SetupPage> {
  late final TextEditingController _controller;
  String? _error;

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController(text: widget.initial ?? '');
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  /// 规范化地址：补 http:// 前缀，只保留 协议+主机+端口（去掉多余路径与结尾斜杠）。
  String? _normalize(String raw) {
    var s = raw.trim();
    if (s.isEmpty) return null;
    if (!s.startsWith('http://') && !s.startsWith('https://')) {
      s = 'http://$s';
    }
    final uri = Uri.tryParse(s);
    if (uri == null || uri.host.isEmpty) return null;
    final port = uri.hasPort ? ':${uri.port}' : '';
    return '${uri.scheme}://${uri.host}$port';
  }

  Future<void> _save() async {
    final url = _normalize(_controller.text);
    if (url == null) {
      setState(() => _error = '地址格式不对，示例：http://192.168.1.100:8000');
      return;
    }
    final sp = await SharedPreferences.getInstance();
    await sp.setString(_kServerKey, url);
    if (!mounted) return;
    widget.onSaved(url);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 460),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Icon(Icons.science_outlined, size: 56, color: theme.colorScheme.primary),
                  const SizedBox(height: 12),
                  Text('CausaLab', textAlign: TextAlign.center, style: theme.textTheme.headlineMedium),
                  const SizedBox(height: 8),
                  Text(
                    '连接你电脑上的 CausaLab',
                    textAlign: TextAlign.center,
                    style: theme.textTheme.bodyLarge,
                  ),
                  const SizedBox(height: 24),
                  TextField(
                    controller: _controller,
                    autofocus: true,
                    keyboardType: TextInputType.url,
                    textInputAction: TextInputAction.done,
                    onSubmitted: (_) => _save(),
                    decoration: InputDecoration(
                      labelText: '服务器地址',
                      hintText: 'http://192.168.1.100:8000',
                      border: const OutlineInputBorder(),
                      errorText: _error,
                    ),
                  ),
                  const SizedBox(height: 16),
                  FilledButton.icon(
                    onPressed: _save,
                    icon: const Icon(Icons.link),
                    label: const Text('保存并连接'),
                  ),
                  const SizedBox(height: 28),
                  Container(
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: theme.colorScheme.surfaceContainerHighest.withValues(alpha: 0.6),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      '使用说明\n'
                      '1. 在电脑上运行 CausaLab（双击「启动CausaLab.bat」）；\n'
                      '2. 手机与电脑连接同一个 Wi-Fi；\n'
                      '3. 在电脑上执行 ipconfig 查看 IPv4 地址（形如 192.168.1.100），'
                      '按 http://<电脑IP>:8000 填写；\n'
                      '4. 电脑端首次使用请先构建一次静态页面（npm run build:static），'
                      '否则后端只提供 API（也可填开发服务地址 http://<电脑IP>:3000）。',
                      style: theme.textTheme.bodySmall?.copyWith(height: 1.6),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// 全屏 WebView：加载 CausaLab 页面；失败时可重试或修改服务器地址。
class WebViewPage extends StatefulWidget {
  const WebViewPage({super.key, required this.server, required this.onChangeServer});

  final String server;
  final VoidCallback onChangeServer;

  @override
  State<WebViewPage> createState() => _WebViewPageState();
}

class _WebViewPageState extends State<WebViewPage> {
  late final WebViewController _controller;
  bool _hasError = false;
  String _errorText = '';

  @override
  void initState() {
    super.initState();
    _controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setNavigationDelegate(
        NavigationDelegate(
          onPageStarted: (_) {
            if (_hasError) setState(() => _hasError = false);
          },
          onWebResourceError: (error) {
            if (error.isForMainFrame ?? true) {
              setState(() {
                _hasError = true;
                _errorText = error.description;
              });
            }
          },
        ),
      )
      ..loadRequest(Uri.parse('${widget.server}/'));
  }

  Future<void> _reload() async {
    setState(() => _hasError = false);
    await _controller.loadRequest(Uri.parse('${widget.server}/'));
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final host = Uri.tryParse(widget.server)?.host ?? widget.server;
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, _) async {
        if (didPop) return;
        if (await _controller.canGoBack()) {
          await _controller.goBack();
        } else {
          await SystemNavigator.pop(); // 已在起始页 → 退出应用
        }
      },
      child: Scaffold(
        appBar: AppBar(
          title: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('CausaLab'),
              Text(
                host,
                style: theme.textTheme.labelSmall?.copyWith(color: theme.colorScheme.onSurfaceVariant),
              ),
            ],
          ),
          actions: [
            IconButton(
              tooltip: '刷新',
              onPressed: _reload,
              icon: const Icon(Icons.refresh),
            ),
            IconButton(
              tooltip: '修改服务器地址',
              onPressed: widget.onChangeServer,
              icon: const Icon(Icons.settings_outlined),
            ),
          ],
        ),
        body: _hasError
            ? Center(
                child: Padding(
                  padding: const EdgeInsets.all(28),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.wifi_off, size: 52, color: theme.colorScheme.error),
                      const SizedBox(height: 14),
                      Text('无法连接服务器', style: theme.textTheme.titleMedium),
                      const SizedBox(height: 6),
                      Text(
                        widget.server,
                        style: theme.textTheme.bodySmall?.copyWith(color: theme.colorScheme.onSurfaceVariant),
                      ),
                      const SizedBox(height: 14),
                      Text(
                        '请确认：电脑端 CausaLab 正在运行；手机与电脑在同一局域网；地址与端口正确。\n（$_errorText）',
                        textAlign: TextAlign.center,
                        style: theme.textTheme.bodySmall,
                      ),
                      const SizedBox(height: 20),
                      FilledButton.icon(
                        onPressed: _reload,
                        icon: const Icon(Icons.refresh),
                        label: const Text('重试'),
                      ),
                      TextButton(
                        onPressed: widget.onChangeServer,
                        child: const Text('修改服务器地址'),
                      ),
                    ],
                  ),
                ),
              )
            : WebViewWidget(controller: _controller),
      ),
    );
  }
}
