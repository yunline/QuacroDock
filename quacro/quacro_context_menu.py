import logging
import traceback
import threading

import webview
import clr

from .quacro_logging import warn_tb

logger = logging.getLogger("context_menu")

from System import Func, Type # type:ignore
from System.Threading.Tasks import Task # type:ignore
from Microsoft.Web.WebView2.Core import CoreWebView2ContextMenuItemKind # type:ignore

MENU_ITEM_KEY_CLOSE = "close"
MENU_ITEM_KEY_CLOSE_ALL = "close_all"
MENU_ITEM_KEY_CLOSE_OTHERS = "close_others"
MENU_ITEM_KEY_RELAOD_ICON_TITLE = "reload_icon_title"

menu_item_names = {
    MENU_ITEM_KEY_CLOSE: "Close Tab",
    MENU_ITEM_KEY_CLOSE_ALL: "Close All",
    MENU_ITEM_KEY_CLOSE_OTHERS: "Close Others",
    MENU_ITEM_KEY_RELAOD_ICON_TITLE: "Reload Icon && Title"
}


def callback(fn):
    def _fn(*args):
        try:
            fn(*args)
        except Exception as err:
            tb_list = traceback.format_exception(type(err), err, err.__traceback__)
            logger.error(
                "Error occured in context menu callback:\n"+("".join(tb_list))
            )
    return _fn

def init_context_menu(window:webview.Window):
    if window.native is None:
        raise RuntimeError(f"Window {window} is not initiallized")
    if window.native.webview is None:
        raise RuntimeError(f"Window {window} webview is not initiallized")

    @callback
    def on_context_menu_requested(sender, event):
        deferral = event.GetDeferral()
        menuItems = event.MenuItems

        @callback
        def set_menu(menu):
            if type(menu) is not list:
                if menu is not None:
                    warn_tb(logger, f"Ignoring unknown menu type '{type(menu).__name__}'. A 'list' was aexpected")
                event.Handled=True
                deferral.Complete()
                return

            # remove default menu items
            menuItems.Clear()

            for menu_item_key in menu:
                if menu_item_key is None:
                    new_item = sender.Environment.CreateContextMenuItem(
                        None, None, CoreWebView2ContextMenuItemKind.Separator
                    )
                    menuItems.Add(new_item)
                    continue
            
                if type(menu_item_key) is not str:
                    warn_tb(logger, f"Ignoring unknown menu item type '{type(menu).__name__}'. A 'str' was aexpected")
                    continue

                new_item = sender.Environment.CreateContextMenuItem(
                    menu_item_names.get(menu_item_key, "Unknown Menu Item Key"),
                    None,
                    CoreWebView2ContextMenuItemKind.Command
                )
                new_item.CustomItemSelected += (lambda _item_str:\
                    # wrap callback lambda with an outer lambda
                    # to solve a closure problem
                    lambda _sender,_event:sender.ExecuteScriptAsync(f"tab_lst.execute_menu_item_cmd('{_item_str}')")
                )(menu_item_key)
                menuItems.Add(new_item)

            deferral.Complete()

        # END def set_menu

        @callback
        def get_menu():
            menu = window.evaluate_js("tab_lst.get_context_menu()")
            window.native.webview.Invoke(Func[Type](lambda:set_menu(menu)))

        threading.Thread(target=get_menu).start()

    # END def on_context_menu_requested

    webview_obj = window.native.webview

    @callback
    def setup_context_menu():
        webview_obj.CoreWebView2.ContextMenuRequested+=on_context_menu_requested

    if webview_obj.InvokeRequired:
        webview_obj.Invoke(
            Func[Type](setup_context_menu)
        )
    else:
        setup_context_menu()

# END def init_context_menu
