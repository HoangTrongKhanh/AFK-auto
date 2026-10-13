#!/usr/bin/env python3
"""Đọc đội đang hiện trong bảng Thành Tích: tên người chơi (dạng chữ ký ảnh), lực chiến, các nhãn.

Thứ tự 10 đội trong Thành Tích đổi giữa các lần mở bảng, nên bot nhận ra đội theo nội dung (chữ ký tên + lực chiến)
chứ không theo vị trí.

    .venv/bin/python thanh_tich.py samples/thanh_tich/*.png
"""
import sys
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from nhan_dien import REF_W, TPL_DIR, NhanDien
from so_ai import ChuSo, cat as _cat, chuan_hoa, hsv_mask as _hsv_mask

# Toạ độ máy gốc 1600x2560, đo trên Tab S7 khi bảng Thành Tích không bị lệch. Mọi vùng được dời theo vị trí tìm thấy
# của biểu tượng nắm đấm cạnh lực chiến (MOC), vì bảng có thể nằm cao thấp khác nhau trên máy khác.
MOC = (285, 672, 365, 772)                  # biểu tượng nắm đấm (mẫu "tt_nam_dam")
VUNG_LUC_CHIEN = (368, 692, 560, 758)       # "287M"
VUNG_NHAN = (660, 680, 1320, 775)           # Chưa Xếp Hạng / Cực Hạn / Phù Hợp Với Tướng / (trống)
DAI_THE = (100, 520, 1500, 545)             # dải ngang trong thanh thẻ người chơi để tìm thẻ đang chọn (màu cam)
TEN_Y = (418, 462)                          # ô tên trong thẻ (nền trắng, chữ nâu)
THU_CONG_Y = (466, 512)                     # dòng "✕ Chiến Đấu Thủ Công" dưới tên
LY_TUONG_Y = (365, 405)                     # nhãn xanh "Lý Tưởng" trên thẻ
RONG_THE = 490                              # bề rộng một thẻ người chơi
TEN_TU_MEP = 150                            # ô tên bắt đầu cách mép trái thẻ bấy nhiêu px (sau ảnh đại diện)
O_LOC = (55, 40, 140, 115)                  # ô "Chỉ hiển thị đội hình đã sở hữu" (bám mép trên)
RONG_SO = 0.67                              # bề rộng một chữ số lực chiến so với chiều cao (đo: 27-29 / 43 px)
RONG_M = 1.28                               # bề rộng chữ M cuối (55 / 43 px)
RONG_K = 0.95                               # bề rộng chữ K cuối của lực chiến đội ở màn đội hình (33 / 35 px)
# Lực chiến đội của bạn ở góc trên trái màn đội hình, ví dụ "338,210K" (bám mép trên; dấu phẩy thấp nên tự bị loại).
VUNG_LUC_DOI = (105, 63, 320, 110)
LUC_DOI_TOI_THIEU = 1.0                     # lực chiến đội (triệu) thấp hơn mức này là đọc sai
CHU_KY = (128, 24)                          # chữ ký tên: ảnh nhị phân rộng x cao
GIONG_TEN = 0.85                            # 2 chữ ký giống nhau >= mức này coi là cùng tên
# Dải dưới sơ đồ ô: cổ vật (+ vật phẩm Huyền Linh) rồi 5 thẻ tướng. Vị trí thẻ tướng đổi theo số vật phẩm nên lưu cả dải.
DAI_TUONG = (245, 1690, 1345, 1895)


@dataclass
class DoiThanhTich:
    chu_ky: np.ndarray | None       # chữ ký ảnh của tên người chơi (bool CHU_KY[1] x CHU_KY[0])
    luc_chien: str | None           # ví dụ "287M"; None nếu không đọc được
    nhan: str | None                # "chua_xep_hang" | "cuc_han" | "phu_hop" | None (không có nhãn)
    ly_tuong: bool
    thu_cong: bool
    loc_bat: bool | None            # ô lọc "chỉ đội đã sở hữu" đang bật?
    thieu_khung: list | None = None  # tướng mà bản ghi có khung còn của bạn không khung (leo_ai điền, xem SoKhung)

    def __str__(self):
        co = [n for n, b in (("lý tưởng", self.ly_tuong), ("thủ công", self.thu_cong)) if b]
        return f"{self.luc_chien or '?'} {self.nhan or '-'} {' '.join(co)} lọc={self.loc_bat}"


def giong_ten(a, b):
    """Mức giống nhau (0-1) của 2 chữ ký tên: phần nét chữ của ảnh này nằm trong nét chữ (nới rộng 1px) của ảnh kia,
    lấy chiều thấp hơn. Trên 22 ảnh mẫu: cùng tên >= 0.97, khác tên <= 0.58."""
    if a is None or b is None:
        return 0.0
    a, b = a.astype(np.uint8), b.astype(np.uint8)
    k = np.ones((3, 3), np.uint8)
    da, db = cv2.dilate(a, k), cv2.dilate(b, k)
    return float(min((da & b).sum() / max(1, b.sum()), (db & a).sum() / max(1, a.sum())))


def o_loc_bat(img):
    """Ô lọc "Chỉ hiển thị đội hình đã sở hữu" (bám mép trên, không dời theo bảng) đang bật? Bật thì có dấu tích xanh
    lá. None nếu không đọc được."""
    k = REF_W / img.shape[1]
    ref = cv2.resize(img, None, fx=k, fy=k, interpolation=cv2.INTER_AREA) if k != 1 else img
    vo = _cat(ref, O_LOC)
    return bool(_hsv_mask(vo, (35, 80, 80), (85, 255, 255)).mean() > 0.2) if vo.size else None


def cung_doi(x: "DoiThanhTich", y: "DoiThanhTich"):
    """Hai lần đọc là cùng một đội trong Thành Tích: cùng tên (chữ ký) và cùng lực chiến."""
    return giong_ten(x.chu_ky, y.chu_ky) >= GIONG_TEN and x.luc_chien == y.luc_chien


def _ky_tu(binary, rong_cuoi=RONG_M):
    """Tách ký tự (thành phần liên thông cao) trong ảnh nhị phân, trái sang phải. Trả về list ảnh ký tự đã chuẩn hoá."""
    n, lab, stats, _ = cv2.connectedComponentsWithStats(binary.astype(np.uint8), connectivity=8)
    h = binary.shape[0]
    hops = [stats[i] for i in range(1, n) if stats[i][3] >= h * 0.45 and stats[i][4] >= 20]
    hops.sort(key=lambda s: s[0])
    out = []
    for i, (x, y, w, hh, _) in enumerate(hops):
        # Lấy trọn chiều cao các cột của ký tự: ở độ phân giải thấp nét chữ có thể đứt thành mẩu rời (đuôi số 9).
        mien = binary[:, x:x + w]
        # Các ký tự có thể dính nhau thành một khối (ví dụ "344" hay "7M"). Ước lượng số ký tự trong khối theo bề rộng
        # (chữ số ~RONG_SO x cao, chữ M cuối ~RONG_M x cao) rồi cắt ở cột ít điểm ảnh nhất gần mỗi ranh giới dự kiến.
        cuoi = i == len(hops) - 1
        rong_m = min(w, rong_cuoi * hh) if cuoi else 0    # lực chiến luôn kết thúc bằng chữ M (triệu) hoặc K
        so_chu_so = max(0, round((w - rong_m) / (RONG_SO * hh))) if rong_m else max(1, round(w / (RONG_SO * hh)))
        bien = []
        if rong_m or so_chu_so > 1:
            cot = mien.sum(axis=0)
            buoc = (w - rong_m) / max(1, so_chu_so)
            for j in range(1, so_chu_so + (1 if rong_m else 0)):
                du_kien = int(j * buoc)
                lo, hi = max(1, du_kien - int(buoc * 0.3)), min(w - 1, du_kien + int(buoc * 0.3))
                bien.append(lo + int(np.argmin(cot[lo:hi])))
        cac_bien = [0] + bien + [w]
        for c0, c1 in zip(cac_bien, cac_bien[1:]):
            if mien[:, c0:c1].any():
                out.append(chuan_hoa(mien[:, c0:c1]))
    return out


def tach_luc_chien(img_vung, rong_cuoi=RONG_M):
    """Ảnh vùng lực chiến (BGR) -> list ký tự. Chữ màu kem sáng trên nền nâu."""
    g = cv2.cvtColor(img_vung, cv2.COLOR_BGR2GRAY)
    return _ky_tu(g > 185, rong_cuoi)


class DocThanhTich:
    def __init__(self, nd: NhanDien | None = None, tpl_dir=TPL_DIR):
        self.nd = nd or NhanDien(tpl_dir)
        self.chu_so = ChuSo(tpl_dir)
        self.thu_cong = cv2.imread(str(Path(tpl_dir) / "tt_thu_cong.png"))
        self.chua_xep_hang = cv2.imread(str(Path(tpl_dir) / "tt_chua_xep_hang.png"))

    def _khop(self, vung, tpl):
        if vung.shape[0] < tpl.shape[0] or vung.shape[1] < tpl.shape[1]:
            return 0.0
        return float(cv2.minMaxLoc(cv2.matchTemplate(vung, tpl, cv2.TM_CCOEFF_NORMED))[1])

    def luc_doi(self, img):
        """Lực chiến đội của bạn ở màn đội hình, tính bằng triệu (vd. "257,943K" -> 257.943); None nếu không đọc được."""
        k = REF_W / img.shape[1]
        ref = cv2.resize(img, None, fx=k, fy=k, interpolation=cv2.INTER_AREA) if k != 1 else img
        s = "".join(self.chu_so.doc_ky_tu(m) for m in tach_luc_chien(_cat(ref, VUNG_LUC_DOI), RONG_K))
        if len(s) < 2 or not s[:-1].isdigit() or s[-1] not in "KM":
            return None
        luc = int(s[:-1]) / 1000 if s[-1] == "K" else float(s[:-1])
        # Banner "18+ Chơi game quá 180 phút..." của game có lúc đè lên các chữ số đầu (13/10, tài khoản thứ 2: "335,055K"
        # chỉ đọc được "5K"): lực chiến đội dưới 1M là đọc sai.
        return luc if luc >= LUC_DOI_TOI_THIEU else None

    def _moc(self, img):
        """Ảnh đã đưa về chiều rộng máy gốc và độ dời (dx, dy) của bảng so với máy gốc; None nếu không thấy bảng."""
        k = REF_W / img.shape[1]
        ref = cv2.resize(img, None, fx=k, fy=k, interpolation=cv2.INTER_AREA) if k != 1 else img
        diem, vt = self.nd.tim(self.nd._thu_nho(img)[0], "tt_nam_dam")
        if diem < 0.8:
            return None
        # Ảnh thu nhỏ của NhanDien rộng 800 = 1/2 máy gốc.
        return ref, vt[0] * 2 - (MOC[0] + MOC[2]) / 2, vt[1] * 2 - (MOC[1] + MOC[3]) / 2

    def dai_tuong(self, img):
        """Ảnh dải cổ vật + thẻ tướng của đội đang chọn (theo toạ độ máy gốc), None nếu không thấy bảng."""
        m = self._moc(img)
        if m is None:
            return None
        ref, dx, dy = m
        return _cat(ref, (DAI_TUONG[0] + dx, DAI_TUONG[1] + dy, DAI_TUONG[2] + dx, DAI_TUONG[3] + dy))

    def doc(self, img) -> DoiThanhTich | None:
        """Đọc đội đang chọn. None nếu không thấy bảng Thành Tích (không thấy biểu tượng nắm đấm)."""
        m = self._moc(img)
        if m is None:
            return None
        ref, dx, dy = m

        def dich(b):
            return (b[0] + dx, b[1] + dy, b[2] + dx, b[3] + dy)

        # Lực chiến
        so = "".join(self.chu_so.doc_ky_tu(m) for m in tach_luc_chien(_cat(ref, dich(VUNG_LUC_CHIEN))))
        luc = so if so and "?" not in so else None

        # Nhãn: theo màu nền (đỏ = Cực Hạn, xanh = Phù Hợp Với Tướng), hoặc mẫu chữ "Chưa Xếp Hạng".
        vn = _cat(ref, dich(VUNG_NHAN))
        do = (_hsv_mask(vn, (0, 120, 150), (8, 255, 255)) | _hsv_mask(vn, (172, 120, 150), (180, 255, 255))).mean()
        xanh = _hsv_mask(vn, (98, 70, 110), (118, 255, 255)).mean()
        if do > 0.25:
            nhan = "cuc_han"
        elif xanh > 0.25:
            nhan = "phu_hop"
        elif self._khop(vn, self.chua_xep_hang) >= 0.8:
            nhan = "chua_xep_hang"
        else:
            nhan = None

        # Thẻ đang chọn: đoạn màu cam dài nhất trên dải ngang của thanh thẻ.
        dai = _cat(ref, dich(DAI_THE))
        cam = _hsv_mask(dai, (10, 140, 200), (24, 255, 255)).mean(axis=0) > 0.5
        doan, bd = None, None
        for x, c in enumerate(list(cam) + [False]):
            if c and bd is None:
                bd = x
            elif not c and bd is not None:
                if doan is None or x - bd > doan[1] - doan[0]:
                    doan = (bd, x)
                bd = None
        chu_ky, thu_cong, ly_tuong = None, False, False
        if doan and doan[1] - doan[0] > 200:
            # Ảnh đại diện ở đầu thẻ không có màu cam nên chỉ mép phải của đoạn cam là chính xác.
            tx1 = doan[1] + DAI_THE[0] + dx
            tx0 = tx1 - RONG_THE
            # Tên: chữ nâu đậm trong ô trắng, cắt sát rồi chuẩn hoá thành ảnh nhị phân.
            o = cv2.cvtColor(_cat(ref, (tx0 + TEN_TU_MEP, TEN_Y[0] + dy, tx1 - 10, TEN_Y[1] + dy)), cv2.COLOR_BGR2GRAY)
            # Bỏ phần ảnh đại diện còn lấn vào: bắt đầu từ cột đầu tiên thuộc ô tên màu trắng.
            trang = np.nonzero((o > 200).mean(axis=0) > 0.5)[0]
            if len(trang):
                o = o[:, trang[0]:]
            chu = o < 140
            ys, xs = np.nonzero(chu)
            if len(xs) > 20:
                chu = chu[ys.min():ys.max() + 1, xs.min():xs.max() + 1].astype(np.uint8) * 255
                chu_ky = cv2.resize(chu, CHU_KY, interpolation=cv2.INTER_AREA) > 100
            vtc = _cat(ref, (tx0 + 100, THU_CONG_Y[0] + dy, tx1, THU_CONG_Y[1] + dy))
            thu_cong = self._khop(vtc, self.thu_cong) >= 0.7
            vlt = _cat(ref, (tx0 + 100, LY_TUONG_Y[0] + dy, tx1, LY_TUONG_Y[1] + dy))
            ly_tuong = _hsv_mask(vlt, (98, 60, 100), (118, 255, 255)).mean() > 0.15

        return DoiThanhTich(chu_ky, luc, nhan, ly_tuong, thu_cong, o_loc_bat(ref))


def main():
    doc = DocThanhTich()
    for p in sys.argv[1:]:
        img = cv2.imread(p)
        print(f"{Path(p).name}: {doc.doc(img)}")


if __name__ == "__main__":
    main()
