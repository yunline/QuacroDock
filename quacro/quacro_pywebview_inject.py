import sys
import types

def inject():
    # Inject a fake module to replace the original module
    # since we don't use them.
    # By doing this, we saved a lot of size of exe.
    fake_http_module = types.ModuleType('webview.http')
    setattr(fake_http_module, "global_server", None)
    setattr(fake_http_module, "BottleServer", None)
    sys.modules['webview.http'] = fake_http_module

    fake_webbrowser_module = types.ModuleType('webbrowser')
    setattr(fake_webbrowser_module, "open", lambda s:None)
    sys.modules['webbrowser'] = fake_webbrowser_module

    # Inject to enable context menu for pywebview
    from webview.platforms import edgechromium
    original_on_webview_ready = edgechromium.EdgeChrome.on_webview_ready
    def on_webview_ready(self, sender, args):
        original_on_webview_ready(self, sender, args)
        # Enable context menu
        sender.CoreWebView2.Settings.AreDefaultContextMenusEnabled = True
    edgechromium.EdgeChrome.on_webview_ready = on_webview_ready
