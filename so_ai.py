#!/usr/bin/env python3
"""Đọc chữ số trong game và số ải.

- ChuSo: nhận dạng một ký tự (0-9, M) bằng mẫu cắt từ lực chiến trong Thành Tích (templates/vi/luc_chien/).
  Các con số khác của game (số ải, "751 → 752") dùng cùng họ font có chân nên dùng chung mẫu này được.
- DocSoAi: số ải hiện tại ở Màn AFK (ô đỏ trên đường ải) và "Tiến Trình Màn Chơi Đỉnh Cao A → B" ở màn THẮNG.

    .venv/bin/python so_ai.py samples/tab_s7_man_afk.png samples/tab_s7_ket_qua_thang.png
"""
import sys
from pathlib import Path

import cv2
import numpy as np

from nhan_dien import REF_W, TPL_DIR, NhanDien

KY_TU_RONG, KY_TU_CAO = 24, 32       # ký tự được chuẩn hoá về kích thước này trước khi so với mẫu
# Nhận ký tự giống nhất nếu tỉ lệ điểm ảnh trùng >= GIONG_KY_TU và hơn ký tự đứng thứ hai >= CACH_BIET. Ở độ phân giải
# thấp (máy rộng 1080) số ải chỉ khớp 0.69-0.79 nhưng vẫn hơn ký tự thứ hai >= 0.08.
GIONG_KY_TU = 0.65
CACH_BIET = 0.05

# Màn AFK (toạ độ máy gốc, dời theo vị trí tìm thấy của mẫu "man_afk_tieu_de" ở (302, 1243)):
MOC_MAN_AFK = (302, 1243)
DAI_DUONG_AI = (0, 1020, 1600, 1110)             # dải số ải dưới đường ải; ải hiện tại nằm trong ô đỏ
# Màn THẮNG (dời theo mẫu "thang_da_tang" ở (800, 1655)):
MOC_THANG = (800, 1655)
SO_TRUOC = (690, 1715, 800, 1790)                # "751" (màu kem)
SO_SAU = (910, 1715, 1035, 1790)                 # "752" (màu xanh lá)
# Bảng "Chiến Đấu Tự Động Hoàn Tất": cùng dải "Tiến Trình Màn Chơi Đỉnh Cao A → B" như màn THẮNG, mốc là dòng tiêu đề.
MOC_TU_DONG = (800, 645)
MOC_XU_LY = (470, 645)                            # bảng "Đã Hoàn Thành Tự Động Xử Lý" (mốc là chữ "Đã Hoàn Thành")
SO_TRUOC_TD = (690, 1135, 800, 1210)
# Màn đội hình: số ải ở cuối dòng 2 của tiêu đề ("Màn Chơi Đỉnh Cao Mùa Giải / 45", "... Huyền / Linh Sinh Vật 178"), dời
# theo mẫu tiêu đề. Bỏ nút "i" bên phải. Chữ màu kem; các chữ cách nhau dưới KHE_CHU px, giữa các từ rộng hơn.
MOC_TIEU_DE = 70                                  # y của mẫu tieu_de_mua_giai / tieu_de_huyen ở máy gốc
DONG_2_TIEU_DE = (480, 80, 1085, 130)
KHE_CHU = 12
SO_SAU_TD = (910, 1135, 1035, 1210)


def chuan_hoa(p):
    ys, xs = np.nonzero(p)
    p = p[ys.min():ys.max() + 1, xs.min():xs.max() + 1].astype(np.uint8) * 255
    return cv2.resize(p, (KY_TU_RONG, KY_TU_CAO), interpolation=cv2.INTER_AREA) > 127


def hsv_mask(img, lo, hi):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    return cv2.inRange(hsv, np.array(lo, np.uint8), np.array(hi, np.uint8)) > 0


def cat(img, box):
    x0, y0, x1, y1 = (int(round(v)) for v in box)
    h, w = img.shape[:2]
    return img[max(0, y0):min(h, y1), max(0, x0):min(w, x1)]


class ChuSo:
    def __init__(self, tpl_dir=TPL_DIR):
        self.mau = []                                       # [(ký tự, ảnh bool)]
        for p in sorted((Path(tpl_dir) / "luc_chien").glob("*.png")):
            self.mau.append((p.stem.split("_")[0], cv2.imread(str(p), cv2.IMREAD_GRAYSCALE) > 127))
        if not self.mau:
            raise FileNotFoundError("thiếu mẫu chữ số trong templates/vi/luc_chien - chạy tao_mau.py")

    def doc_ky_tu(self, m, chi_so=False):
        """Ký tự giống nhất với ảnh m (đã chuẩn hoá), "?" nếu không đủ giống. chi_so: chỉ xét 0-9."""
        tot = {}                                            # ký tự -> điểm cao nhất trong các mẫu của nó
        for c, t in self.mau:
            if not (chi_so and not c.isdigit()):
                tot[c] = max(tot.get(c, 0.0), float((t == m).mean()))
        xep = sorted(tot.items(), key=lambda x: -x[1])
        if not xep or xep[0][1] < GIONG_KY_TU or (len(xep) > 1 and xep[0][1] - xep[1][1] < CACH_BIET):
            return "?"
        return xep[0][0]

    def doc_so(self, binary):
        """Đọc dãy chữ số trong ảnh nhị phân (mỗi chữ số là một thành phần liên thông, không dính nhau).
        Trả về int, hoặc None nếu không đọc được."""
        n, _, st, _ = cv2.connectedComponentsWithStats(binary.astype(np.uint8), connectivity=8)
        h = binary.shape[0]
        hops = sorted((s for s in st[1:] if h * 0.5 <= s[3] <= h * 0.9 and s[4] >= 15), key=lambda s: s[0])
        so = "".join(self.doc_ky_tu(chuan_hoa(binary[y:y + hh, x:x + w]), chi_so=True) for x, y, w, hh, _ in hops)
        return int(so) if so and "?" not in so else None


class DocSoAi:
    def __init__(self, nd: NhanDien | None = None, tpl_dir=TPL_DIR):
        self.nd = nd or NhanDien(tpl_dir)
        self.chu_so = ChuSo(tpl_dir)

    def _ref(self, img, mau, moc):
        """(ảnh quy về rộng 1600, dx, dy) hoặc None nếu không thấy mẫu mốc."""
        diem, vt = self.nd.tim(self.nd._thu_nho(img)[0], mau)
        if diem < 0.8:
            return None
        k = REF_W / img.shape[1]
        ref = cv2.resize(img, None, fx=k, fy=k, interpolation=cv2.INTER_AREA) if k != 1 else img
        return ref, vt[0] * 2 - moc[0], vt[1] * 2 - moc[1]

    def ai_man_afk(self, img):
        """Số ải hiện tại ở Màn AFK (chữ trắng trong ô đỏ), None nếu không đọc được."""
        r = self._ref(img, "man_afk_tieu_de", MOC_MAN_AFK)
        if r is None:
            return None
        ref, dx, dy = r
        x0, y0, x1, y1 = DAI_DUONG_AI
        dai = cat(ref, (x0 + dx, y0 + dy, x1 + dx, y1 + dy))
        do = (hsv_mask(dai, (0, 100, 150), (10, 255, 255)) | hsv_mask(dai, (170, 100, 150), (180, 255, 255)))
        n, _, st, _ = cv2.connectedComponentsWithStats(do.astype(np.uint8), connectivity=8)
        if n < 2:
            return None
        x, y, w, h, _ = max(st[1:], key=lambda s: s[4])             # ô đỏ lớn nhất
        o = dai[y:y + h, x:x + w]
        return self.chu_so.doc_so(hsv_mask(o, (0, 0, 215), (180, 70, 255)))

    def ai_doi_hinh(self, img):
        """Số ải ở tiêu đề màn đội hình (Màn AFK hoặc Huyền Linh, cả khi leo hộ), None nếu không đọc được."""
        r = self._ref(img, "tieu_de_mua_giai", (0, MOC_TIEU_DE)) or self._ref(img, "tieu_de_huyen", (0, MOC_TIEU_DE))
        if r is None:
            return None
        ref, _, dy = r
        x0, y0, x1, y1 = DONG_2_TIEU_DE
        dong = cv2.cvtColor(cat(ref, (x0, y0 + dy, x1, y1 + dy)), cv2.COLOR_BGR2GRAY) > 190
        _, _, st, _ = cv2.connectedComponentsWithStats(dong.astype(np.uint8), connectivity=8)
        hops = sorted((s for s in st[1:] if s[4] >= 15 and s[3] >= 15), key=lambda s: s[0])
        if not hops:
            return None
        tu = [hops[-1]]                                 # từ cuối cùng của dòng: các chữ sát nhau tính từ phải sang
        for s in reversed(hops[:-1]):
            if tu[0][0] - (s[0] + s[2]) >= KHE_CHU:
                break
            tu.insert(0, s)
        xa, xb = tu[0][0], max(s[0] + s[2] for s in tu)
        ya, yb = min(s[1] for s in tu), max(s[1] + s[3] for s in tu)
        return self.chu_so.doc_so(dong[max(0, ya - 3):yb + 4, xa:xb])

    def tien_trinh_thang(self, img):
        """(ải trước, ải sau) trong "Tiến Trình Màn Chơi Đỉnh Cao A → B" ở màn THẮNG; None nếu không đọc được."""
        return self._tien_trinh(img, "thang_da_tang", MOC_THANG, SO_TRUOC, SO_SAU)

    def tien_trinh_tu_dong(self, img):
        """(ải lúc bắt đầu, ải hiện tại) ở bảng Chiến Đấu Tự Động Hoàn Tất; None nếu không đọc được."""
        return (self._tien_trinh(img, "tu_dong_hoan_tat", MOC_TU_DONG, SO_TRUOC_TD, SO_SAU_TD)
                or self._tien_trinh(img, "xu_ly_hoan_tat", MOC_XU_LY, SO_TRUOC_TD, SO_SAU_TD))

    def _tien_trinh(self, img, mau, moc, so_truoc, so_sau):
        r = self._ref(img, mau, moc)
        if r is None:
            return None
        ref, dx, dy = r

        def dich(b):
            return (b[0] + dx, b[1] + dy, b[2] + dx, b[3] + dy)

        truoc = self.chu_so.doc_so(cv2.cvtColor(cat(ref, dich(so_truoc)), cv2.COLOR_BGR2GRAY) > 200)
        sau = self.chu_so.doc_so(hsv_mask(cat(ref, dich(so_sau)), (35, 80, 200), (85, 255, 255)))
        if truoc is None or sau is None:
            return None
        return truoc, sau


def main():
    d = DocSoAi()
    for p in sys.argv[1:]:
        img = cv2.imread(p)
        print(f"{Path(p).name}: ải {d.ai_man_afk(img)} | thắng {d.tien_trinh_thang(img)} | đội hình {d.ai_doi_hinh(img)}")


if __name__ == "__main__":
    main()
