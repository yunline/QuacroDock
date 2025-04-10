import sys
import types

def inject():
    """
    Inject a fake module to replace the original module
    since we don't use them.
    By doing this, we saved a lot of size of exe.
    """
    fake_http_module = types.ModuleType('webview.http')
    setattr(fake_http_module, "global_server", None)
    setattr(fake_http_module, "BottleServer", None)
    sys.modules['webview.http'] = fake_http_module

    fake_webbrowser_module = types.ModuleType('webbrowser')
    setattr(fake_webbrowser_module, "open", lambda s:None)
    sys.modules['webbrowser'] = fake_webbrowser_module

