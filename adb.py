"""Điều khiển điện thoại qua ADB: chụp màn hình, chạm, vuốt, đọc trạng thái máy. Chép từ hoa-vien-auto (xoa_nhiem_vu.py)."""
import logging
import struct
import subprocess
import time
import zlib
from pathlib import Path

import cv2
import numpy as np

log = logging.getLogger("leo_ai")

_SDK_ADB = Path.home() / "Android/Sdk/platform-tools/adb"
DEFAULT_ADB = str(_SDK_ADB) if _SDK_ADB.exists() else "adb"


class AdbError(RuntimeError):
    pass


class Adb:
    def __init__(self, adb_path=DEFAULT_ADB, serial=None):
        self.adb_path = adb_path
        self.serial = serial
        self.cmd = [adb_path] + (["-s", serial] if serial else [])

    def run(self, *args, timeout=30, binary=False):
        try:
            p = subprocess.run(self.cmd + list(args), capture_output=True, timeout=timeout)
        except subprocess.TimeoutExpired as e:
            raise AdbError(f"adb hết thời gian chờ: {' '.join(args)}") from e
        if p.returncode != 0:
            raise AdbError(f"adb lỗi ({' '.join(args)}): {p.stderr.decode(errors='replace').strip()}")
        return p.stdout if binary else p.stdout.decode(errors="replace").strip()

    def shell(self, command, timeout=30):
        return self.run("shell", command, timeout=timeout)

    def connected(self):
        try:
            return self.run("get-state", timeout=10) == "device"
        except AdbError:
            return False

    # Ảnh thô RGBA: nén gzip trên máy (đỡ truyền qua USB/Wi-Fi) hoặc không nén. Mỗi cách được đo thử vài lần đầu
    # rồi dùng cách nhanh hơn; lỗi thì lùi về PNG.
    CAPTURE_MODES = {"gzip": "screencap | gzip -1", "raw": "screencap"}
    TRIALS_PER_MODE = 2
    capture_times = None
    capture_mode = None

    def screenshot(self):
        if self.capture_times is None:
            self.capture_times = {m: [] for m in self.CAPTURE_MODES}
        mode = self.capture_mode
        if mode is None:
            mode = min(self.capture_times, key=lambda m: len(self.capture_times[m]))
        if mode != "png":
            try:
                t = time.perf_counter()
                img = self._screenshot_raw(mode)
                if self.capture_mode is None:
                    self.capture_times[mode].append(time.perf_counter() - t)
                    if all(len(v) >= self.TRIALS_PER_MODE for v in self.capture_times.values()):
                        self.capture_mode = min(self.capture_times, key=lambda m: sum(self.capture_times[m]))
                        log.debug("Chụp màn hình bằng cách '%s' (%s).", self.capture_mode, {
                            m: f"{1000 * sum(v) / len(v):.0f}ms" for m, v in self.capture_times.items()})
                return img
            except (AdbError, zlib.error, ValueError) as e:
                log.debug("Chụp '%s' lỗi (%s), chuyển sang PNG.", mode, e)
                self.capture_mode = "png"
        data = self.run("exec-out", "screencap", "-p", binary=True, timeout=30)
        img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            raise AdbError("không giải mã được ảnh chụp màn hình")
        return img

    def _screenshot_raw(self, mode):
        buf = self.run("exec-out", self.CAPTURE_MODES[mode], binary=True, timeout=30)
        if mode == "gzip":
            buf = zlib.decompress(buf, 31)
        w, h = struct.unpack_from("<II", buf, 0)
        size = w * h * 4
        if not (0 < size <= len(buf) - 12):
            raise ValueError("kích thước ảnh thô không hợp lệ")
        px = np.frombuffer(buf, np.uint8, count=size, offset=len(buf) - size).reshape(h, w, 4)
        return cv2.cvtColor(px, cv2.COLOR_RGBA2BGR)

    def tap(self, x, y):
        self.shell(f"input tap {int(x)} {int(y)}")

    def swipe(self, x0, y0, x1, y1, ms):
        self.shell(f"input swipe {int(x0)} {int(y0)} {int(x1)} {int(y1)} {int(ms)}")

    def game_booster_locked(self):
        """Lớp "GameBooster Lock Screen" của Samsung Game Booster đang hiện: tự bật khi để yên lâu trong game,
        làm tối màn hình và chặn mọi thao tác chạm cho tới khi kéo biểu tượng ổ khóa."""
        out = self.shell("dumpsys window windows | awk '/Window #/ {p = /GameBooster Lock Screen/} p' "
                         "| grep -m1 'isVisible=true'; true")
        return "isVisible=true" in out

    def screen_awake(self):
        return "Awake" in self.shell("dumpsys power | grep -m1 mWakefulness=")

    def charging(self):
        return "true" in self.shell("dumpsys battery | grep -E '(AC|USB|Wireless) powered'")

    def foreground_package(self):
        out = self.shell("dumpsys window | grep -m1 mCurrentFocus")
        return out.split("/")[0].split()[-1] if "/" in out else ""

    def get_stay_on(self):
        return self.shell("settings get global stay_on_while_plugged_in")

    def set_stay_on(self, value):
        self.shell(f"settings put global stay_on_while_plugged_in {value}")
