#!/usr/bin/env python3
"""Nhận diện màn hình Hành Trình AFK (bản VN) từ ảnh chụp màn hình.

Không phụ thuộc ADB: nhận ảnh (BGR, như cv2.imread) và trả về tên màn hình cùng vị trí các nút để bấm.

Ví dụ:
    .venv/bin/python nhan_dien.py samples/tab_s7_man_afk.png      # in tên màn hình và các nút tìm thấy
    .venv/bin/python nhan_dien.py --diem samples/*.png              # in điểm khớp của mọi mẫu (để chỉnh ngưỡng)
    .venv/bin/python nhan_dien.py --ve debug/ samples/*.png         # lưu ảnh có đánh dấu vị trí nút
"""
import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

import cv2

BASE = Path(__file__).resolve().parent
TPL_DIR = BASE / "templates" / "vi"
SAMPLES = BASE / "samples"

# Toạ độ đo trên máy gốc 1600x2560 (Tab S7). Game co giãn giao diện theo chiều ngang (tỉ lệ = rộng màn hình / 1600);
# theo chiều dọc, mỗi mẫu bám vào mép trên, mép dưới hoặc giữa màn hình (neo), vì máy dài hơn thì phần giữa giãn ra.
REF_W, REF_H = 1600, 2560
# Tìm mẫu trên ảnh thu nhỏ về WORK_W px chiều ngang (= 1/2 máy gốc): nhanh mà vẫn đủ chi tiết.
WORK_W = 800
WORK = WORK_W / REF_W
MATCH_THRESHOLD = 0.80
# Lớp khóa "GameBooster Lock Screen" của Samsung làm tối cả màn hình: độ sáng trung bình 35-42 khi bị khóa,
# các màn hình bình thường >= 84 (đo trên 32 ảnh mẫu Tab S7).
LOCKED_BRIGHTNESS = 60


@dataclass(frozen=True)
class Mau:
    """Mẫu ảnh: cắt từ ảnh mẫu `nguon` (samples/<nguon>.png) vùng hop (x0, y0, x1, y1) theo máy gốc.
    neo: 'tren' | 'duoi' | 'giua' - mốc theo chiều dọc. le: khoảng tìm thêm quanh vị trí gốc (px máy gốc)."""
    nguon: str
    hop: tuple
    neo: str
    le: int = 80
    nguong: float = MATCH_THRESHOLD


MAU = {
    # Màn AFK
    "man_afk_tieu_de": Mau("tab_s7_man_afk", (114, 1195, 490, 1290), "giua", 200),
    "man_afk_chien_dau": Mau("tab_s7_man_afk", (1043, 2095, 1490, 2190), "duoi"),
    "man_afk_huyen_linh": Mau("tab_s7_man_afk", (228, 2060, 735, 2130), "duoi"),
    # Màn đội hình (sau khi bấm Chiến Đấu / Thách Đấu Huyền Linh)
    "doi_hinh_thanh_tich": Mau("tab_s7_doi_hinh_man_afk", (290, 2320, 510, 2465), "duoi"),
    "doi_hinh_tu_dong": Mau("tab_s7_doi_hinh_man_afk", (560, 2340, 1010, 2420), "duoi"),
    "doi_hinh_chien_dau": Mau("tab_s7_doi_hinh_man_afk", (1120, 2320, 1505, 2450), "duoi"),
    "tieu_de_mua_giai": Mau("tab_s7_doi_hinh_man_afk", (895, 45, 1070, 95), "tren", 40),
    "tieu_de_huyen": Mau("tab_s7_doi_hinh_huyen_linh", (945, 45, 1040, 95), "tren", 40),
    # Bảng Thành Tích
    "tt_sao_chep": Mau("tab_s7_thanh_tich_doi_1", (750, 2075, 1090, 2175), "duoi"),
    "tt_nhan_de_dong": Mau("tab_s7_thanh_tich_doi_1", (640, 2380, 960, 2455), "duoi", nguong=0.9),
    "tt_o_loc_chu": Mau("tab_s7_thanh_tich_doi_1", (150, 40, 820, 115), "tren", 40),
    "tt_mui_ten_phai": Mau("tab_s7_thanh_tich_doi_2", (1320, 1290, 1480, 1450), "giua", 200),
    "tt_mui_ten_trai": Mau("tab_s7_thanh_tich_doi_2", (95, 1290, 250, 1450), "giua", 200),
    # Bảng trống "Không có bản ghi phù hợp" (ô lọc bật mà mọi bản ghi đều có tướng chưa sở hữu); nút Sao chép bị mờ.
    "tt_khong_ban_ghi": Mau("tab_s7_thanh_tich_khong_co_ban_ghi", (500, 432, 1100, 508), "tren", 120),
    "tt_nam_dam": Mau("tab_s7_thanh_tich_doi_1", (285, 672, 365, 772), "giua", 300),      # mốc để đọc đội (thanh_tich.py)
    # Đang đánh
    "danh_giay": Mau("tab_s7_dang_danh", (1420, 30, 1590, 150), "tren", 40, nguong=0.9),
    "danh_toc_do": Mau("tab_s7_dang_danh", (1060, 1960, 1500, 2100), "duoi"),
    "danh_tam_dung": Mau("tab_s7_dang_danh", (100, 1960, 260, 2100), "duoi"),
    # Dải chữ "Tự Động Chiến Đấu..." ở đáy màn hình khi đang bật Chiến Đấu Tự Động
    "tu_dong_chien_dau": Mau("tab_s7_tran_bat_dau_tu_dong", (450, 2333, 1050, 2407), "duoi"),
    # Kết quả
    "bai_loi_khuyen": Mau("tab_s7_ket_qua_bai_thu_lai", (520, 1165, 1080, 1235), "giua", 200),
    "bai_thu_lai": Mau("tab_s7_ket_qua_bai_thu_lai", (960, 2370, 1290, 2475), "duoi"),
    "thang_da_tang": Mau("tab_s7_ket_qua_thang", (415, 1612, 1185, 1698), "giua", 200),
    "thang_chien_dau": Mau("tab_s7_ket_qua_thang", (900, 2360, 1320, 2450), "duoi"),
    "nut_quay_lai": Mau("tab_s7_ket_qua_bai_thu_lai", (40, 2340, 260, 2510), "duoi"),
    # Bảng "Chiến Đấu Tự Động Hoàn Tất / Đã hoàn thành màn xN" hiện khi tắt chuỗi Chiến Đấu Tự Động (13/10)
    "tu_dong_hoan_tat": Mau("tab_s7_tu_dong_hoan_tat", (300, 590, 1300, 700), "giua", 200),
    # Tự Động Xử Lý (13/10): trong trận Chiến Đấu Tự Động có nút "Tự Động Xử Lý" bên phải; bấm vào thì game về bản đồ
    # thế giới (hoặc Màn AFK) và đánh ngầm tiếp các ải, không vẽ cảnh đánh. Lúc đó góc dưới trái bản đồ ghi
    # "Tự Động Xử Lý..." còn Màn AFK có dải "Đang Tự Động Xử Lý..." thay cho các nút Chiến Đấu.
    "nut_tu_dong_xu_ly": Mau("tab_s7_dang_danh_tu_dong_xu_ly", (1320, 1540, 1490, 1600), "giua", 200),
    "xu_ly_ban_do": Mau("tab_s7_ban_do_tu_dong_xu_ly", (5, 2460, 235, 2496), "duoi"),
    "xu_ly_man_afk": Mau("tab_s7_man_afk_tu_dong_xu_ly", (490, 2125, 1140, 2190), "duoi"),
    # Chuỗi đánh ngầm đã dừng (thua): bản đồ có bong bóng "Đã hoàn thành Màn xN!" và nút góc dưới trái ghi "Tự Động Xử Lý
    # Đã Hoàn Thành!"; bấm nút đó mở bảng "Đã Hoàn Thành Tự Động Xử Lý" (giống bảng Chiến Đấu Tự Động Hoàn Tất).
    "xu_ly_xong_bong": Mau("tab_s7_ban_do_xu_ly_xong", (75, 2180, 375, 2225), "duoi"),
    "xu_ly_xong_nut": Mau("tab_s7_ban_do_xu_ly_xong", (90, 2515, 170, 2550), "duoi"),
    "xu_ly_xong_nut_2": Mau("tab_s7_ban_do_xu_ly_xong_2", (75, 2500, 195, 2545), "duoi"),     # "Tự Động Xử Lý Xong!"
    "xu_ly_hoan_tat": Mau("tab_s7_xu_ly_hoan_tat", (165, 600, 775, 690), "giua", 200),
    # Bảng bán gói (Kim cương) bật lên khi đạt mốc ải, ví dụ "Gói Lầu Ngắm Sao" ở Đỉnh Cao 600 (14/10). Bot chỉ bấm dòng
    # "Nhấn để thoát" ở đáy, không bao giờ bấm nút mua.
    "nhan_de_thoat": Mau("tab_s7_goi_ban_nhan_de_thoat", (645, 2385, 955, 2445), "duoi", nguong=0.9),
    # Màn nghỉ của game, bảng phần thưởng AFK, bản đồ thế giới
    # "Nhấn để tiếp tục" giống "Nhấn để đóng" của bảng Thành Tích tới 0.77 nên cần ngưỡng cao.
    "nghi_nhan_tiep_tuc": Mau("tab_s7_game_tiet_kiem_pin_nhan_de_tiep_tuc", (600, 2380, 1000, 2460), "duoi", nguong=0.9),
    "thuong_nhan": Mau("tab_s7_bang_phan_thuong_afk", (680, 1370, 920, 1500), "giua", 200),
    "thuong_thoi_gian": Mau("tab_s7_bang_phan_thuong_afk", (1080, 800, 1410, 880), "giua", 200),
    "ban_do_nut_man_afk": Mau("tab_s7_ban_do_dinh_cao", (10, 2462, 232, 2498), "duoi", nguong=0.7),     # chữ "Màn Chơi Đỉnh Cao" (hình và số ải đổi)
    "ban_do_che_do": Mau("tab_s7_ban_do_the_gioi", (600, 2400, 800, 2550), "duoi"),
}

# Tên màn hình: (các mẫu phải thấy hết, ưu tiên). Xét theo thứ tự; màn đầu tiên đủ mẫu là kết quả.
MAN_HINH = [
    ("nghi", ["nghi_nhan_tiep_tuc"]),
    ("phan_thuong_afk", ["thuong_nhan", "thuong_thoi_gian"]),
    ("bang_ban_goi", ["nhan_de_thoat"]),
    ("xu_ly_ngam", ["xu_ly_man_afk"]),
    ("xu_ly_ngam", ["xu_ly_ban_do"]),
    ("thanh_tich_trong", ["tt_khong_ban_ghi", "tt_o_loc_chu"]),
    ("tu_dong_hoan_tat", ["tu_dong_hoan_tat"]),
    ("tu_dong_hoan_tat", ["xu_ly_hoan_tat"]),
    ("xu_ly_xong", ["xu_ly_xong_bong"]),
    ("xu_ly_xong", ["xu_ly_xong_nut"]),
    ("xu_ly_xong", ["xu_ly_xong_nut_2"]),
    ("thanh_tich", ["tt_sao_chep", "tt_nhan_de_dong"]),
    # Nút "Thử Lại" chỉ có ở màn BẠI; mục "Lời Khuyên Chiến Trận" có lúc không hiện (chỉ còn "Tăng Sức Mạnh").
    ("bai", ["bai_thu_lai"]),
    ("thang", ["thang_da_tang", "thang_chien_dau"]),
    # Đồng hồ "NNgiây" ở góc trên phải; cụm nút tốc độ có lúc bị chiêu cuối của tướng che nên không bắt buộc.
    ("dang_danh", ["danh_giay"]),
    ("dang_danh", ["tu_dong_chien_dau"]),
    ("doi_hinh", ["doi_hinh_thanh_tich", "doi_hinh_tu_dong", "doi_hinh_chien_dau"]),
    # Theo tiêu đề "Màn AFK": khi một phần (Chiến Đấu hoặc Thách Đấu Huyền Linh) hết ải, game chỉ còn 1 nút ngang.
    ("man_afk", ["man_afk_tieu_de"]),
    ("ban_do", ["ban_do_che_do", "ban_do_nut_man_afk"]),
]
# Mẫu cần tìm thêm (để lấy vị trí bấm) khi đã biết màn hình.
XU_LY_TOI = ["xu_ly_ban_do", "xu_ly_man_afk"]     # mẫu vẫn dò khi màn hình tối (bị khóa)

NUT_THEM = {
    "man_afk": ["man_afk_chien_dau", "man_afk_huyen_linh", "nut_quay_lai"],
    "doi_hinh": ["tieu_de_mua_giai", "tieu_de_huyen", "nut_quay_lai"],
    "thanh_tich": ["tt_mui_ten_phai", "tt_mui_ten_trai", "tt_o_loc_chu", "tt_nam_dam"],
    "bai": ["nut_quay_lai", "bai_loi_khuyen"],
    "thang": ["nut_quay_lai"],
    "dang_danh": ["danh_toc_do", "danh_tam_dung", "tu_dong_chien_dau", "nut_tu_dong_xu_ly"],
}


@dataclass
class KetQua:
    man_hinh: str                                   # tên màn hình, "khoa" (Game Booster) hoặc "khong_ro"
    nut: dict = field(default_factory=dict)        # tên mẫu -> (x, y) tâm mẫu trên ảnh gốc (để bấm)
    diem: dict = field(default_factory=dict)       # tên mẫu -> điểm khớp
    do_sang: float = 0.0
    che_do: str | None = None                       # màn đội hình: "afk" | "huyen_linh" (nếu nhận ra)

    @property
    def tu_dong(self):
        """Đang bật Chiến Đấu Tự Động (thấy dải chữ "Tự Động Chiến Đấu...")."""
        return "tu_dong_chien_dau" in self.nut

    def __str__(self):
        extra = f" ({self.che_do})" if self.che_do else ""
        extra += " [tự động]" if self.tu_dong else ""
        nut = ", ".join(f"{k}@{x},{y}" for k, (x, y) in self.nut.items())
        return f"{self.man_hinh}{extra} | sáng {self.do_sang:.0f} | {nut}"


class NhanDien:
    def __init__(self, tpl_dir=TPL_DIR):
        self.mau = {}
        for ten in MAU:
            p = Path(tpl_dir) / f"{ten}.png"
            im = cv2.imread(str(p))
            if im is None:
                raise FileNotFoundError(f"thiếu mẫu {p} - chạy tao_mau.py")
            self.mau[ten] = cv2.resize(im, None, fx=WORK, fy=WORK, interpolation=cv2.INTER_AREA)

    @staticmethod
    def _thu_nho(img):
        k = WORK_W / img.shape[1]
        return cv2.resize(img, None, fx=k, fy=k, interpolation=cv2.INTER_AREA), k

    @staticmethod
    def _vung(m: Mau, h_work):
        """Vùng tìm (x0, y0, x1, y1) trên ảnh thu nhỏ cho mẫu m. Ảnh thu nhỏ rộng WORK_W, cao h_work."""
        x0, y0, x1, y1 = m.hop

        def y(v):
            if m.neo == "tren":
                return v * WORK
            if m.neo == "duoi":
                return h_work - (REF_H - v) * WORK
            return h_work / 2 + (v - REF_H / 2) * WORK

        le = m.le * WORK
        return (max(0, int(x0 * WORK - le)), max(0, int(y(y0) - le)),
                min(WORK_W, int(x1 * WORK + le)), min(int(h_work), int(y(y1) + le)))

    def tim(self, small, ten):
        """(điểm khớp, (x, y) tâm trên ảnh thu nhỏ) của mẫu ten."""
        tpl = self.mau[ten]
        x0, y0, x1, y1 = self._vung(MAU[ten], small.shape[0])
        roi = small[y0:y1, x0:x1]
        if roi.shape[0] < tpl.shape[0] or roi.shape[1] < tpl.shape[1]:
            return 0.0, None
        r = cv2.matchTemplate(roi, tpl, cv2.TM_CCOEFF_NORMED)
        _, score, _, (mx, my) = cv2.minMaxLoc(r)
        return float(score), (x0 + mx + tpl.shape[1] // 2, y0 + my + tpl.shape[0] // 2)

    def nhan_dien(self, img) -> KetQua:
        sang = float(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).mean())
        small, k = self._thu_nho(img)
        if sang < LOCKED_BRIGHTNESS:
            # Lớp khóa Game Booster chỉ làm tối đều màn hình nên mẫu vẫn khớp (TM_CCOEFF_NORMED không đổi khi độ sáng đổi
            # tuyến tính; đo 13/10: "Tự Động Xử Lý..." trên bản đồ bị khóa khớp 0.92). Đang Tự Động Xử Lý thì không cần mở
            # khóa: game tự đánh ngầm, để màn hình tối cho đỡ tốn pin.
            for ten in XU_LY_TOI:
                diem, vt = self.tim(small, ten)
                if diem >= MAU[ten].nguong:
                    return KetQua("xu_ly_ngam", do_sang=sang, nut={ten: (round(vt[0] / k), round(vt[1] / k))})
            return KetQua("khoa", do_sang=sang)
        diem, vitri = {}, {}

        def thay(ten):
            if ten not in diem:
                diem[ten], vitri[ten] = self.tim(small, ten)
            return diem[ten] >= MAU[ten].nguong

        ket = KetQua("khong_ro", do_sang=sang)
        for man, can in MAN_HINH:
            if all(thay(t) for t in can):
                ket.man_hinh = man
                for t in NUT_THEM.get(man, []):
                    thay(t)
                break
        for t, s in diem.items():
            if s >= MAU[t].nguong and vitri[t] is not None:
                ket.nut[t] = (round(vitri[t][0] / k), round(vitri[t][1] / k))
        ket.diem = diem
        if ket.man_hinh == "doi_hinh":
            if "tieu_de_huyen" in ket.nut:
                ket.che_do = "huyen_linh"
            elif "tieu_de_mua_giai" in ket.nut:
                ket.che_do = "afk"
        return ket

    def tat_ca_diem(self, img):
        """Điểm khớp của mọi mẫu (để chỉnh ngưỡng)."""
        small, _ = self._thu_nho(img)
        return {t: self.tim(small, t)[0] for t in MAU}


def ve(img, ket: KetQua):
    out = img.copy()
    for t, (x, y) in ket.nut.items():
        cv2.circle(out, (x, y), 18, (0, 0, 255), 4)
        cv2.putText(out, t, (x + 22, y + 8), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
    cv2.putText(out, ket.man_hinh, (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 0, 255), 4)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("anh", nargs="+", help="ảnh chụp màn hình")
    ap.add_argument("--diem", action="store_true", help="in điểm khớp của mọi mẫu")
    ap.add_argument("--ve", metavar="THU_MUC", help="lưu ảnh có đánh dấu vào thư mục này")
    a = ap.parse_args()
    nd = NhanDien()
    for p in a.anh:
        img = cv2.imread(p)
        if img is None:
            print(f"{p}: không đọc được ảnh", file=sys.stderr)
            continue
        ket = nd.nhan_dien(img)
        print(f"{Path(p).name}: {ket}")
        if a.diem:
            for t, s in sorted(nd.tat_ca_diem(img).items(), key=lambda x: -x[1]):
                print(f"    {s:5.2f} {t}")
        if a.ve:
            Path(a.ve).mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(Path(a.ve) / Path(p).name), ve(img, ket))


if __name__ == "__main__":
    main()
