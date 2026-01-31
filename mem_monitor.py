"""
运行期内存监控小工具
支持监控指定PID的工作集（RSS）内存。
"""

import argparse
import os
import sys
import time


def _try_psutil(pid: int):
    try:
        import psutil  # type: ignore
    except Exception:
        return None
    
    try:
        proc = psutil.Process(pid)
        return proc.memory_info().rss / (1024 * 1024)
    except Exception:
        return None


def _get_rss_windows(pid: int):
    try:
        import ctypes
        from ctypes import wintypes
    except Exception:
        return None
    
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    PROCESS_VM_READ = 0x0010
    
    class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]
    
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    
    OpenProcess = kernel32.OpenProcess
    OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    OpenProcess.restype = wintypes.HANDLE
    
    GetProcessMemoryInfo = psapi.GetProcessMemoryInfo
    GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESS_MEMORY_COUNTERS), wintypes.DWORD]
    GetProcessMemoryInfo.restype = wintypes.BOOL
    
    CloseHandle = kernel32.CloseHandle
    CloseHandle.argtypes = [wintypes.HANDLE]
    CloseHandle.restype = wintypes.BOOL
    
    handle = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_VM_READ, False, pid)
    if not handle:
        return None
    
    counters = PROCESS_MEMORY_COUNTERS()
    counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
    ok = GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb)
    CloseHandle(handle)
    
    if not ok:
        return None
    
    return counters.WorkingSetSize / (1024 * 1024)


def _get_private_windows(pid: int):
    try:
        import ctypes
        from ctypes import wintypes
    except Exception:
        return None
    
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    PROCESS_VM_READ = 0x0010
    
    class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
            ("PrivateUsage", ctypes.c_size_t),
        ]
    
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    
    OpenProcess = kernel32.OpenProcess
    OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    OpenProcess.restype = wintypes.HANDLE
    
    GetProcessMemoryInfo = psapi.GetProcessMemoryInfo
    GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESS_MEMORY_COUNTERS_EX), wintypes.DWORD]
    GetProcessMemoryInfo.restype = wintypes.BOOL
    
    CloseHandle = kernel32.CloseHandle
    CloseHandle.argtypes = [wintypes.HANDLE]
    CloseHandle.restype = wintypes.BOOL
    
    handle = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_VM_READ, False, pid)
    if not handle:
        return None
    
    counters = PROCESS_MEMORY_COUNTERS_EX()
    counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS_EX)
    ok = GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb)
    CloseHandle(handle)
    
    if not ok:
        return None
    
    return counters.PrivateUsage / (1024 * 1024)


def get_rss_mb(pid: int):
    rss = _try_psutil(pid)
    if rss is not None:
        return rss
    
    if sys.platform == "win32":
        return _get_rss_windows(pid)
    
    return None


def get_private_mb(pid: int):
    rss = _try_psutil(pid)
    if rss is not None:
        try:
            import psutil  # type: ignore
            proc = psutil.Process(pid)
            return proc.memory_info().private / (1024 * 1024)
        except Exception:
            pass
    
    if sys.platform == "win32":
        return _get_private_windows(pid)
    
    return None


def get_working_set_mb(pid: int):
    # Working Set 更接近任务管理器“内存”列
    return get_rss_mb(pid)


def main():
    parser = argparse.ArgumentParser(description="运行期内存监控小工具（RSS/工作集）")
    parser.add_argument("--pid", type=int, default=os.getpid(), help="要监控的进程PID")
    parser.add_argument("--interval", type=float, default=2.0, help="采样间隔（秒）")
    args = parser.parse_args()
    
    pid = args.pid
    interval = max(0.2, args.interval)
    
    print(f"开始监控 PID={pid}，采样间隔={interval}s，按 Ctrl+C 退出")
    while True:
        rss = get_rss_mb(pid)
        if rss is None:
            print("无法读取内存占用（可选安装psutil以提高兼容性）")
        else:
            print(f"RSS: {rss:.2f} MB")
        time.sleep(interval)


if __name__ == "__main__":
    main()
