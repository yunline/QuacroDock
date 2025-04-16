@echo off

call "%VSINSTALLDIR%\VC\Auxiliary\Build\vcvarsall.bat" x64

if not exist ".\build" (
    mkdir ".\build"
)

cl /Fo"./build/" /Fd"./build/" /Fe"./build/" /LD /MD /O2 src_c/quacro_utils.c

if %errorlevel% == 0 (
    copy ".\build\quacro_utils.dll" ".\"
)

cl /Fo"./build/" /Fd"./build/" /Fe"./build/" /LD /MD /O2 src_c/quacro_hook_proc.c ^
    /link /NODEFAULTLIB:msvcrt.lib /ENTRY:DllMain

if %errorlevel% == 0 (
    copy ".\build\quacro_hook_proc.dll" ".\"
)

