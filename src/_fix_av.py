import os

f = r'D:\DevGitee\agent-space\QQMsgForward\src\wecom_ui.py'
c = open(f, 'r', encoding='utf-8').read()

# Replace GMEM_MOVEABLE + GlobalLock pattern with GMEM_FIXED (no lock needed)
# Both win32clipboard and ctypes fallback paths

old = (
    "        GMEM_MOVEABLE = 0x0002\n"
    "        CF_HDROP = 15\n"
    "        ctypes.windll.kernel32.GlobalAlloc.restype = ctypes.c_void_p\n"
    "        ctypes.windll.kernel32.GlobalLock.restype = ctypes.c_void_p\n"
    "        if win32clipboard:\n"
    "            hMem = ctypes.windll.kernel32.GlobalAlloc(GMEM_MOVEABLE, total_size)\n"
    "            if hMem:\n"
    "                pMem = ctypes.windll.kernel32.GlobalLock(hMem)\n"
    "                if not pMem:\n"
    '                    logger.error("[WECOM_UI] GlobalLock failed (win32clipboard)")\n'
    "                    return\n"
    "                ctypes.memmove(ctypes.cast(pMem, ctypes.c_char_p), total_data, total_size)\n"
    "                ctypes.windll.kernel32.GlobalUnlock(hMem)"
)
new = (
    "        CF_HDROP = 15\n"
    "        ctypes.windll.kernel32.GlobalAlloc.restype = ctypes.c_void_p\n"
    "        if win32clipboard:\n"
    "            hMem = ctypes.windll.kernel32.GlobalAlloc(0x0040, total_size)  # GMEM_ZEROINIT\n"
    "            if hMem:\n"
    "                ctypes.memmove(hMem, total_data, total_size)\n"
    "                ctypes.windll.kernel32.GlobalUnlock(hMem)"
)
if old in c:
    c = c.replace(old, new)
    print("fix1 applied")
else:
    print("fix1 NOT found")

# ctypes fallback path
old2 = (
    "        try:\n"
    "            hMem = ctypes.windll.kernel32.GlobalAlloc(GMEM_MOVEABLE, total_size)\n"
    "            if hMem:\n"
    "                pMem = ctypes.windll.kernel32.GlobalLock(hMem)\n"
    "                if not pMem:\n"
    '                    logger.error("[WECOM_UI] GlobalLock failed (ctypes fallback)")\n'
    "                    return\n"
    "                ctypes.memmove(ctypes.cast(pMem, ctypes.c_char_p), total_data, total_size)\n"
    "                ctypes.windll.kernel32.GlobalUnlock(hMem)\n"
    "                user32.OpenClipboard(None)"
)
new2 = (
    "        try:\n"
    "            hMem = ctypes.windll.kernel32.GlobalAlloc(0x0040, total_size)  # GMEM_ZEROINIT\n"
    "            if hMem:\n"
    "                ctypes.memmove(hMem, total_data, total_size)\n"
    "                ctypes.windll.kernel32.GlobalUnlock(hMem)\n"
    "                user32.OpenClipboard(None)"
)
if old2 in c:
    c = c.replace(old2, new2)
    print("fix2 applied")
else:
    print("fix2 NOT found")

open(f, 'w', encoding='utf-8').write(c)
print("done")
