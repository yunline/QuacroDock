#define WIN32_LEAN_AND_MEAN
#define UNICODE
#define _UNICODE 
#include <Windows.h>
#include <stdint.h>
#include <stdio.h>

#define EVENT_TYPE_STOP 0
#define EVENT_TYPE_CREATE_WINDOW 1
#define EVENT_TYPE_DESTROY_WINDOW 2
#define EVENT_TYPE_MOVE_SIZE 3
#define EVENT_TYPE_ACTIVATE 4
#define EVENT_TYPE_ICON_TITLE_UPDATE 5

typedef struct {
    int32_t event_type;
    HWND hwnd;
    union data {
        // Used by EVENT_TYPE_MOVESIZE
        RECT rect;
        // Used by EVENT_TYPE_ACTIVATE
        struct activate_info{
            BOOL inactive;
            BOOL minimized;
        };
        
    };
} IPCQueueItem;

#define IPC_QUEUE_MAX_SIZE 256

typedef struct{
    uint16_t queue_size;
    uint16_t queue_tail_ind;
    IPCQueueItem queue_buffer[IPC_QUEUE_MAX_SIZE];
} IPCArea;

#define SHARE_MEM_SIZE sizeof(IPCArea)
#define SHARE_FIEL_MAPPING_NAME TEXT("quacro_memfilemap")

#define IPC_QUEUE_EVENT_NAME TEXT("quacro_queuenonemptyevent")
#define IPC_QUEUE_MUTEX_NAME TEXT("quacro_queuemutex")

static HANDLE hMapObject = NULL; // handle to file mapping
static IPCArea* ipc_area = NULL;
static HANDLE ipc_queue_event = NULL;
static HANDLE ipc_queue_mutex = NULL;

BOOL setup_ipc_queue() {
    hMapObject = CreateFileMapping(
        INVALID_HANDLE_VALUE,   // use paging file
        NULL,                   // default security attributes
        PAGE_READWRITE,         // read/write access
        0,                      // size: high 32-bits
        SHARE_MEM_SIZE,         // size: low 32-bits
        SHARE_FIEL_MAPPING_NAME); // name of map object
    if (hMapObject == NULL)
        return FALSE;

    ipc_area = (IPCArea*) MapViewOfFile(
        hMapObject,     // object to map view of
        FILE_MAP_ALL_ACCESS, // read/write access
        0,              // high offset:  map from
        0,              // low offset:   beginning
        0);             // default: map entire file
    if (ipc_area == NULL)
        return FALSE;
    
    ipc_queue_event = CreateEvent(NULL, FALSE, FALSE,IPC_QUEUE_EVENT_NAME);
    if (ipc_queue_event==NULL) {
        return FALSE;
    }

    ipc_queue_mutex = CreateMutex(NULL, FALSE, IPC_QUEUE_MUTEX_NAME);
    if (ipc_queue_mutex==NULL) {
        return FALSE;
    }
    
    return TRUE;
}

void destroy_ipc_queue() {
    CloseHandle(ipc_queue_event);
    CloseHandle(ipc_queue_mutex);
    UnmapViewOfFile(ipc_area);
    CloseHandle(hMapObject);
}

#define IS_TOPLEVEL_WINDOW(hwnd) (!(GetWindowLongPtr(hwnd, GWL_STYLE) & (WS_CHILD|WS_POPUP)))

typedef struct{
    uint8_t major;
    uint8_t minor;
    uint8_t micro;
} BinaryVersion;

const BinaryVersion binary_version = {0,0,1};

typedef void (*get_version_fp)(BinaryVersion *);
