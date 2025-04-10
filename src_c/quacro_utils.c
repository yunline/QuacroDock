#include "commons.c"

#pragma comment(lib, "user32.lib")
#pragma comment(lib, "gdi32.lib")

typedef void (*enum_toplevel_window_callback)(HWND hwnd);

__declspec(dllexport) void get_error(WCHAR **buf_pointer);
__declspec(dllexport) int event_queue_init();
__declspec(dllexport) void event_queue_deinit();
__declspec(dllexport) int wait_for_hook_event(IPCQueueItem* event);
__declspec(dllexport) void send_stop_event();
__declspec(dllexport) int load_hook_proc_dll(WCHAR *hook_proc_dll_path);
__declspec(dllexport) int setup_hook();
__declspec(dllexport) void unins_hook();
__declspec(dllexport) int enum_toplevel_window(enum_toplevel_window_callback cb);
__declspec(dllexport) uint8_t* read_window_icon(HWND hwnd, int *out_length);
__declspec(dllexport) void free_png_buffer(uint8_t *buf);

static HHOOK hook_handle = NULL;
static HANDLE stop_event = NULL;
static BOOL event_queue_ready = FALSE;

#define ERR_MSG_BUF_MAX_SIZE 256
static WCHAR err_msg_buf[ERR_MSG_BUF_MAX_SIZE] = {0};

#define SET_ERROR(err) wcsncpy(err_msg_buf, err, ERR_MSG_BUF_MAX_SIZE)
#define SET_FORMAT_ERROR(fmt,...) _snwprintf(err_msg_buf, ERR_MSG_BUF_MAX_SIZE, fmt, __VA_ARGS__)
#define CHECK_READY() {if(!event_queue_ready){SET_ERROR(TEXT("ipc event queue is not initialized"));return -1;}}

__declspec(dllexport) void get_error(WCHAR **buf_pointer) {
    buf_pointer[0] = err_msg_buf;
}

void set_error_from_win32(){
    DWORD error_code = GetLastError();
    LPWSTR error_msg = NULL;
    FormatMessage(
        FORMAT_MESSAGE_ALLOCATE_BUFFER | 
        FORMAT_MESSAGE_FROM_SYSTEM |
        FORMAT_MESSAGE_IGNORE_INSERTS,
        NULL,
        error_code,
        MAKELANGID(LANG_NEUTRAL, SUBLANG_DEFAULT),
        (LPWSTR)&error_msg,
        0,
        NULL
    );
    if(!error_msg) {
        error_msg = TEXT("(null)");
    }
    SET_FORMAT_ERROR(
        TEXT("win32 error: %u\r\n%s"),
        error_code,
        error_msg
    );
}

__declspec(dllexport) int event_queue_init() {
    if(!setup_ipc_queue()) {
        set_error_from_win32();
        return -1;
    }
    ipc_area->queue_size=0;
    ipc_area->queue_tail_ind=0;

    // setup STOP event
    stop_event = CreateEvent(NULL, FALSE, FALSE, NULL);
    if(!stop_event) {
        set_error_from_win32();
        return -1;
    }

    event_queue_ready = TRUE;
    return 0;
}

__declspec(dllexport) void event_queue_deinit() {
    event_queue_ready = FALSE;
    destroy_ipc_queue();
    if(stop_event) {
        CloseHandle(stop_event);
        stop_event = NULL;
    }
}

int read_hook_event(IPCQueueItem* event) {
    DWORD result = WaitForSingleObject(ipc_queue_mutex, INFINITE);
    if (result!=WAIT_OBJECT_0) {
        if (result == WAIT_FAILED) {
            set_error_from_win32();
        }
        else {
            SET_ERROR(TEXT("failed to wait ipc queue mutex"));
        }
        return -1;
    }
    if (ipc_area->queue_size==0) {
        ReleaseMutex(ipc_queue_mutex);
        SET_ERROR(TEXT("queue is empty"));
        return -1;
    }

    // read the queue
    event[0] = ipc_area->queue_buffer[ipc_area->queue_tail_ind];

    ipc_area->queue_tail_ind+=1;
    if(ipc_area->queue_tail_ind==IPC_QUEUE_MAX_SIZE) {
        ipc_area->queue_tail_ind = 0;
    }
    ipc_area->queue_size-=1;

    ResetEvent(ipc_queue_event);

    ReleaseMutex(ipc_queue_mutex);
    return event->event_type;
}

__declspec(dllexport) int wait_for_hook_event(IPCQueueItem* event) {
    CHECK_READY();
    if(ipc_area->queue_size) {
        return read_hook_event(event);
    }
    HANDLE event_handles[] = {stop_event, ipc_queue_event};
    DWORD result = WaitForMultipleObjects(2, event_handles, FALSE, INFINITE);
    if (result==WAIT_OBJECT_0) {
        return EVENT_TYPE_STOP;
    }
    if (result==1+WAIT_OBJECT_0) {
        return read_hook_event(event);
    }
    if (result==WAIT_FAILED) {
        set_error_from_win32();
        return -1;
    }
    SET_ERROR(TEXT("failed to wait ipc queue event or stop event"));
    return -1;
}

__declspec(dllexport) void send_stop_event() {
    if (event_queue_ready){
        SetEvent(stop_event);
    }
}

HMODULE hook_proc_dll = NULL;
HOOKPROC hook_proc = NULL;
__declspec(dllexport) int load_hook_proc_dll(WCHAR *hook_proc_dll_path) {
    HMODULE dll = LoadLibrary(hook_proc_dll_path);
    if (!dll) {
        set_error_from_win32();
        return -1;
    }
    get_version_fp get_version = (get_version_fp)GetProcAddress(dll, "get_version");
    if (!get_version) {
        FreeLibrary(dll);
        set_error_from_win32();
        return -1;
    }

    BinaryVersion hook_proc_version;
    get_version(&hook_proc_version);
    if (
        hook_proc_version.major!=binary_version.major||
        hook_proc_version.minor!=binary_version.minor||
        hook_proc_version.micro!=binary_version.micro
    ){
        SET_FORMAT_ERROR(
            TEXT(
                "the version of quacro_hook_proc.dll (%u.%u.%u) "
                "is not compatible with quacro_utils.dll (%u.%u.%u)"
            ),
            hook_proc_version.major,
            hook_proc_version.minor,
            hook_proc_version.micro,
            binary_version.major,
            binary_version.minor,
            binary_version.micro
        );
        FreeLibrary(dll);
        return -1;
    }

    HOOKPROC proc = (HOOKPROC)GetProcAddress(dll, "hook_proc");
    if (!proc) {
        FreeLibrary(dll);
        set_error_from_win32();
        return -1;
    }

    hook_proc_dll = dll;
    hook_proc = proc;
    return 0;
}

__declspec(dllexport) int setup_hook()
{
    CHECK_READY();

    if (!hook_proc_dll||!hook_proc) {
        SET_ERROR(TEXT("hook proc dll is not loaded"));
        return -1;
    }

    hook_handle = SetWindowsHookEx(WH_CALLWNDPROC, hook_proc, hook_proc_dll, 0);
    if (hook_handle == NULL) {
        set_error_from_win32();
        return -1;
    }

    return 0;
}

__declspec(dllexport) void unins_hook() {
    if(hook_handle) {
        UnhookWindowsHookEx(hook_handle);
        hook_handle=NULL;
    }
}

BOOL CALLBACK enum_window_proc(HWND hwnd, LPARAM lparam) {
    if (!IS_TOPLEVEL_WINDOW(hwnd)){
        return TRUE; // skip child window and popup window
    }
    ((enum_toplevel_window_callback)lparam)(hwnd);
    return TRUE;
}

__declspec(dllexport) int enum_toplevel_window(enum_toplevel_window_callback cb) {
    BOOL result = EnumWindows(enum_window_proc, (LPARAM)cb);
    if(!result){
        set_error_from_win32();
        return -1;
    }
    return 0;
}

#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "ext/stb/stb_image_write.h"

void bgra_to_rgba(int w, int h, int n, int stride, uint8_t *buffer) {
    uint8_t *pixel;
    uint8_t tmp;
    for(int y=0; y<h; y++) {
        for(int x=0; x<w; x++) {
            pixel = &(buffer[y*stride+x*n]);
            tmp = pixel[0];
            pixel[0] = pixel[2];
            pixel[2] = tmp;
        }
    }
}

__declspec(dllexport) uint8_t* read_window_icon(HWND hwnd, int *out_length) {

    HICON hIcon = (HICON)SendMessage(hwnd, WM_GETICON, ICON_BIG, 0);
    if (!hIcon) {
        hIcon = (HICON)SendMessage(hwnd, WM_GETICON, ICON_SMALL, 0);
    }
    if (!hIcon) {
        hIcon = (HICON)GetClassLongPtr(hwnd, GCLP_HICON);
    }
    if (!hIcon) {
        return NULL;
    }

    ICONINFO iconInfo;
    if (!GetIconInfo(hIcon, &iconInfo)) {
        return NULL;
    }

    BITMAP bmp;
    GetObject(iconInfo.hbmColor, sizeof(BITMAP), &bmp);

    int width = bmp.bmWidth;
    int height = bmp.bmHeight;
    int channels = 4; // RGBA
    int stride = width * channels;

    uint8_t* pixels = (uint8_t*)malloc(height * stride);
    if (!pixels) {
        return NULL;
    }

    BITMAPINFOHEADER bmi = {0};
    bmi.biSize = sizeof(BITMAPINFOHEADER);
    bmi.biWidth = width;
    bmi.biHeight = -height;
    bmi.biPlanes = 1;
    bmi.biBitCount = 32;
    bmi.biCompression = BI_RGB;

    HDC hdc = GetDC(NULL);
    if(!hdc) {
        return NULL;
    }
    if (!GetDIBits(hdc, iconInfo.hbmColor, 0, height, pixels, (BITMAPINFO*)&bmi, DIB_RGB_COLORS)) {
        free(pixels);
        ReleaseDC(NULL, hdc);
        return NULL;
    }
    ReleaseDC(NULL, hdc);

    bgra_to_rgba(width, height, channels, stride, pixels);
    uint8_t *result = stbi_write_png_to_mem(pixels, stride, width, height, channels, out_length);

    free(pixels);
    DeleteObject(iconInfo.hbmColor);
    DeleteObject(iconInfo.hbmMask);

    return result;
}

__declspec(dllexport) void free_png_buffer(uint8_t *buf) {
    STBIW_FREE(buf);
}

#define SILOCK_MUTEX_NAME TEXT("QuacroDockDuacroQock")
#define ACQUIRE_SILOCK_SUCCESS 0
#define ACQUIRE_SILOCK_FAILED -1
#define ACQUIRE_SILOCK_OCCUPIED 1
__declspec(dllexport) int acquire_single_instance_lock() {
    // we won't close the mutex handle until the process ends
    // os will close it anyway
    if(!CreateMutex(NULL, FALSE, SILOCK_MUTEX_NAME)) {
        return ACQUIRE_SILOCK_FAILED;
    }
    if(GetLastError()==ERROR_ALREADY_EXISTS) {
        return ACQUIRE_SILOCK_OCCUPIED;
    }
    return ACQUIRE_SILOCK_SUCCESS;
}
