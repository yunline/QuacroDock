#include "commons.c"

#pragma comment(lib, "user32.lib")

BOOL WINAPI DllMain(HINSTANCE hinstDLL, DWORD fdwReason, LPVOID lpvReserved)
{
    switch (fdwReason)
    {
        case DLL_PROCESS_ATTACH:
            if(!setup_ipc_queue()) {
                return FALSE;
            }
            break;

        case DLL_PROCESS_DETACH:
            destroy_ipc_queue();
            break;
 
        default:
          break;
     }

    return TRUE;
    UNREFERENCED_PARAMETER(hinstDLL);
    UNREFERENCED_PARAMETER(lpvReserved);
}

int put_hook_event(IPCQueueItem *event) {
    uint16_t queue_head_ind;
    DWORD result = WaitForSingleObject(ipc_queue_mutex, INFINITE);
    if (result!=WAIT_OBJECT_0) {
        return -1;
    }
    if (ipc_area->queue_size==IPC_QUEUE_MAX_SIZE) {
        ReleaseMutex(ipc_queue_mutex);
        return -1;
    }

    queue_head_ind = ipc_area->queue_tail_ind + ipc_area->queue_size;
    if(queue_head_ind>=IPC_QUEUE_MAX_SIZE) {
        queue_head_ind-=IPC_QUEUE_MAX_SIZE;
    }
    ipc_area->queue_size+=1;

    ipc_area->queue_buffer[queue_head_ind] = event[0];

    SetEvent(ipc_queue_event);
    
    ReleaseMutex(ipc_queue_mutex);
    return 0;
}

__declspec(dllexport) void get_version(BinaryVersion *version) {
    if(version){
        *version = binary_version;
    }
}

__declspec(dllexport) LRESULT CALLBACK hook_proc(int nCode, WPARAM wParam, LPARAM lParam) {
    if(nCode<0) {
        goto end;
    }

    CWPSTRUCT* pMsg = (CWPSTRUCT*)lParam;
    if(!IS_TOPLEVEL_WINDOW(pMsg->hwnd)) {
        goto end;
    }

    IPCQueueItem event;
    switch (pMsg->message)
    {
        case WM_MOVING:
        case WM_SIZING:
            event.event_type = EVENT_TYPE_MOVE_SIZE;
            event.hwnd = pMsg->hwnd;
            event.rect = *(RECT *)(pMsg->lParam);
            put_hook_event(&event);
            break;
        case WM_ACTIVATE:
            event.event_type = EVENT_TYPE_ACTIVATE;
            event.inactive = LOWORD(pMsg->wParam)==WA_INACTIVE;
            event.minimized = HIWORD(pMsg->wParam)!=0;
            event.hwnd = pMsg->hwnd;
            put_hook_event(&event);
            break;
        case WM_CREATE:
            event.event_type = EVENT_TYPE_CREATE_WINDOW;
            event.hwnd = pMsg->hwnd;
            put_hook_event(&event);
            break;
        case WM_DESTROY:
            event.event_type = EVENT_TYPE_DESTROY_WINDOW;
            event.hwnd = pMsg->hwnd;
            put_hook_event(&event);
            break;
        case WM_SETICON:
        case WM_SETTEXT:
            event.event_type = EVENT_TYPE_ICON_TITLE_UPDATE;
            event.hwnd = pMsg->hwnd;
            put_hook_event(&event);
        default:
            break;
    }

end:
    return CallNextHookEx(NULL, nCode, wParam, lParam);
}