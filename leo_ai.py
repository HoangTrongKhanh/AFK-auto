#!/usr/bin/env python3
"""Leo ải tự động cho Hành Trình AFK (bản VN): Màn AFK và Thách Đấu Huyền Linh.

Mỗi vòng: chụp màn hình qua ADB, nhận ra đang ở màn nào (nhan_dien.py) rồi làm đúng một việc ở màn đó:
  - Màn AFK: bấm Chiến Đấu (hoặc Thách Đấu Huyền Linh).
  - Màn đội hình: bắt đầu trận; nếu đội hiện tại đã thua đủ số lần thì mở Thành Tích để chép đội khác.
  - Thành Tích: đọc cả 10 đội, chọn đội chưa thử tốt nhất (Lý Tưởng / Phù Hợp Với Tướng trước, Cực Hạn sau cùng,
    bỏ đội Chiến Đấu Thủ Công), bấm Sao chép. Thứ tự đội đổi giữa các lần mở nên đội được nhận theo tên + lực chiến.
  - THẮNG: ghi nhận tiến trình, bấm Chiến Đấu để đánh ải kế. BẠI: Thử Lại, hoặc về để chép đội khác.
  - Lớp khóa Game Booster, màn nghỉ, bảng phần thưởng AFK, bản đồ thế giới: tự xử lý để về Màn AFK.
Không bao giờ bấm vào chỗ không nhận ra được, không mua hay tiêu tài nguyên.

Ví dụ:
    .venv/bin/python leo_ai.py                          # leo cả 2 chế độ, kẹt bên này thì sang bên kia
    .venv/bin/python leo_ai.py --che-do afk --thu-lai 3
    .venv/bin/python leo_ai.py --mot-tran               # đánh 1 trận rồi dừng (thử)
    .venv/bin/python leo_ai.py --xem-thanh-tich         # chỉ mở Thành Tích, in danh sách đội rồi dừng (không chép)
    .venv/bin/python leo_ai.py --thu-thap-tuong         # leo như thường, mỗi ải mới lưu ảnh tướng của cả 10 bản ghi
    .venv/bin/python leo_ai.py --leo-ho                 # leo hộ người khác (Đại Diện Tác Chiến): mở sẵn phiên rồi chạy
"""
import argparse
import csv
import logging
import logging.handlers
import signal
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from adb import DEFAULT_ADB, Adb, AdbError
from nhan_dien import KetQua, NhanDien
from so_ai import DocSoAi
from thanh_tich import DocThanhTich, DoiThanhTich, cung_doi, o_loc_bat

BASE = Path(__file__).resolve().parent
DEBUG_DIR = BASE / "debug"
GAME_PACKAGE = "com.farlightgames.igame.gp.vn"
log = logging.getLogger("leo_ai")

CHO_SAU_BAM = 1.5           # giây chờ sau mỗi lần bấm để game kịp đổi màn hình
CHO_MUI_TEN = 1.2           # chuyển đội trong Thành Tích (có hiệu ứng trượt)
CHO_DANG_DANH = 3.0         # đang đánh: chụp lại sau bấy nhiêu giây
DOC_LAI_CHUOI = 4           # bảng kết quả Tự Động Xử Lý: đọc lại tối đa bấy nhiêu lần
CHO_XU_LY = 20.0            # đang Tự Động Xử Lý (game đánh ngầm): chụp lại sau bấy nhiêu giây
CHO_KHONG_RO = 2.0          # màn hình chưa nhận ra (đang chuyển cảnh): chờ rồi chụp lại
CHO_MAN_TAT = 20.0          # màn hình tắt / game không ở trên cùng: chờ lâu hơn
TRAN_TOI_DA = 300           # trận kéo dài hơn bấy nhiêu giây coi là bất thường (trận tối đa ~90 giây trong game)
KHONG_RO_TOI_DA = 60        # ở màn không nhận ra bấy nhiêu giây thì lưu ảnh và báo
SO_DOI_TOI_DA = 12          # Thành Tích có 10 đội; quá số này là có gì đó sai
DOC_LAI_TOI_DA = 6          # sau khi bấm mũi tên: chụp tối đa bấy nhiêu lần tới khi đọc được đội đứng yên
DI_TOI_TOI_DA = 3           # số đợt bấm bù khi game bỏ qua lần bấm mũi tên
THIEU_NUT_TOI_DA = 3        # Màn AFK thiếu nút của một phần bấy nhiêu lần liền thì coi phần đó đã hết ải
DOI_LUC_TOI_DA = 8          # sau khi chép: đọc lực chiến đội tối đa bấy nhiêu lần (~1 giây/lần) chờ con số cập nhật
TRAN_CSV = BASE / "tran.csv"    # mỗi trận một dòng: để phân tích chênh lệch lực chiến và tỉ lệ thắng
COT_CSV = ["thoi_gian", "che_do", "ai", "loai", "vi_tri", "doi", "luc_ban_ghi", "luc_doi", "ty_le", "tran_thu",
           "thieu_khung", "ket_qua", "chuoi", "giay"]
# Ô tích lọc nằm bên trái dòng chữ lọc (97 so với 484 ở máy gốc). Bấm vào mép dưới ô (y 108 so với 78 của chữ): băng
# "18+" ở góc trên trái (tài khoản thứ hai, 13/10) che nửa trên ô và chặn lần bấm.
O_LOC_TRAI, O_LOC_DUOI = 387, 30
MAX_DEBUG_IMAGES = 200
# --thu-thap-tuong (đợt thu thập một lần để thống kê tướng, xem thong_ke_tuong.py): mỗi lượt lướt Thành Tích một thư mục
# ảnh trong THU_THAP_DIR, mỗi bản ghi một dòng trong THU_THAP_CSV.
THU_THAP_DIR = BASE / "thu_thap_tuong"
THU_THAP_CSV = THU_THAP_DIR / "ban_ghi.csv"
COT_THU_THAP = ["thoi_gian", "luot", "che_do", "ai", "vi_tri", "luc_chien", "nhan", "ly_tuong", "thu_cong", "chu_ky",
                "anh"]

TEN_CHE_DO = {"afk": "Màn AFK", "huyen_linh": "Thách Đấu Huyền Linh"}
# Nút vào từng chế độ ở Màn AFK; hết ải một phần thì phần còn lại thành 1 nút ngang (mẫu khác).
NUT_CHE_DO = {"afk": ["man_afk_chien_dau", "man_afk_chien_dau_ngang"], "huyen_linh": ["man_afk_huyen_linh"]}
# Leo hộ (Đại Diện Tác Chiến): nút vào từng chế độ ở bảng chọn ải của người nhờ.
NUT_CHE_DO_HO = {"afk": ["dd_chon_chien_dau"], "huyen_linh": ["dd_chon_huyen_linh"]}


class Dung(Exception):
    """Dừng hẳn bot (đã đạt điều kiện dừng hoặc không thể làm tiếp); lý do in cho người dùng."""


@dataclass
class CheDo:
    """Trạng thái leo của một chế độ ở ải hiện tại."""
    ten: str
    doi: DoiThanhTich | None = None         # đội đang dùng (None: đội có sẵn của người chơi)
    da_thu: list = field(default_factory=list)     # các đội đã chép ở ải này
    thua: int = 0                           # số trận thua liên tiếp của đội đang dùng
    can_doi: bool = False                   # thua đủ, lần tới vào màn đội hình thì chép đội khác
    mang_sang: bool = False                 # đội đang dùng là đội vừa thắng ải trước (chưa chép cho ải này)
    ket: bool = False                       # đã thử hết đội trong Thành Tích ở ải này
    het: bool = False                       # phần này đã hết ải trong giai đoạn (Màn AFK không còn nút của nó)
    thieu_nut: int = 0                      # số lần liền vào Màn AFK mà không thấy nút của phần này
    vi_tri: int | None = None               # vị trí trong Thành Tích của đội đang dùng lúc chép (1 = đầu)
    can_thu_thap: bool = True               # --thu-thap-tuong: chưa lưu tướng các bản ghi của ải này
    # Chép thử (--nguong-luc): đội vừa chép mà lực chiến đội bạn thấp hơn ngưỡng so với bản ghi thì chưa đánh, chép thử
    # đội khác; hết đội thì đánh các đội đã hoãn theo tỉ lệ lực chiến giảm dần.
    moi_chep: bool = False                  # vừa chép, chưa vào màn đội hình để đọc lực chiến
    danh_ngay: bool = False                 # đội vừa chép là đội đã hoãn (hoặc vòng sau): đánh luôn, không hoãn nữa
    hoan: list = field(default_factory=list)        # (đội, tỉ lệ lực chiến) đã chép thử nhưng chưa đánh
    ty_le: list = field(default_factory=list)       # (đội, tỉ lệ lực chiến) mọi đội đã chép ở ải này
    vong: int = 0                           # vòng thử đội trong Thành Tích ở ải này (0 = vòng đầu)
    ds_cu: list | None = None               # danh sách Thành Tích đọc lần trước ở ải này
    ai: int | None = None                   # leo hộ: ải của người nhờ ở chế độ này (đọc ở tiêu đề màn đội hình)
    da_danh: bool = True                    # đã đánh trận kể từ lần đọc ds_cu (game có thể đã đổi thứ tự đội)


def mo_ta(d: DoiThanhTich | None):
    if d is None:
        return "đội có sẵn"
    nhan = {"chua_xep_hang": "Chưa Xếp Hạng", "cuc_han": "Cực Hạn", "phu_hop": "Phù Hợp Với Tướng"}.get(d.nhan, "")
    them = [x for x, b in (("Lý Tưởng", d.ly_tuong), ("Thủ Công", d.thu_cong)) if b]
    if d.thieu_khung:
        them.append("thiếu khung " + ", ".join(d.thieu_khung))
    return " · ".join([d.luc_chien or "?"] + ([nhan] if nhan else []) + them)


def tim_o_khoa(img):
    """Tâm biểu tượng ổ khóa xanh của Game Booster (chép từ hoa-vien-auto), None nếu không thấy."""
    h, w = img.shape[:2]
    x0, y0 = int(w * 0.25), int(h * 0.3)
    roi = img[y0:int(h * 0.7), x0:int(w * 0.75)].astype(np.int16)
    b, g, r = roi[:, :, 0], roi[:, :, 1], roi[:, :, 2]
    ys, xs = np.nonzero((b > 180) & (r < 90) & (b - g > 40))
    if len(xs) < (w * h) / 20000:
        return None
    return int(xs.mean()) + x0, int(ys.mean()) + y0


class LeoAi:
    def __init__(self, adb: Adb, a):
        self.adb = adb
        self.a = a
        self.nd = NhanDien()
        self.tt = DocThanhTich(self.nd)
        self.so = DocSoAi(self.nd)
        # Cả hai: Huyền Linh trước (đo 13-14/10 trên tài khoản thứ hai: Huyền Linh leo 350 → 742 trong khi Màn AFK kẹt ở
        # 350, vì ít bản ghi Huyền Linh cần tướng bạn còn thiếu khung).
        thu_tu = {"afk": ["afk"], "huyen-linh": ["huyen_linh"], "ca-hai": ["huyen_linh", "afk"]}[a.che_do]
        self.cd = {k: CheDo(k) for k in thu_tu}
        self.hien = thu_tu[0]                   # chế độ đang leo
        self.tien_trinh = None                  # số ải (Tiến Trình Màn Chơi Đỉnh Cao) đọc được gần nhất
        self.tran_tu = None                     # lúc thấy trận bắt đầu (time.monotonic)
        self.tran_che_do = None                 # chế độ của trận đang đánh; None nếu bot không tự bắt đầu trận này
        self.da_tinh = False                    # đã tính kết quả của màn THẮNG/BẠI đang hiện
        self.khong_ro_tu = None
        self.da_bao_khong_ro = False
        self.bat_dau = time.monotonic()
        self.tk = dict(tran=0, thang=0, thua=0, chep=0, tu_dong=0)
        self.da_tinh_chuoi = False              # đã tính bảng Chiến Đấu Tự Động Hoàn Tất đang hiện
        self.doc_lai_chuoi = 0                  # số lần đọc lại bảng kết quả chưa đọc được tiến trình
        self.trong_chuoi = False                # game đang (hoặc vừa) Tự Động Xử Lý, trận thua cuối chuỗi chưa tính
        self.xu_ly_tu = None                    # lúc thấy game bắt đầu Tự Động Xử Lý (đánh ngầm) trong chuỗi hiện tại
        self.thua_lien_tiep = 0
        self.thieu_ca_hai = 0                   # số lần liền Màn AFK không có nút nào quen thuộc
        self.vua_chep = False                   # vừa chép đội: lực chiến đội có thể chưa cập nhật
        self.luc_truoc = None                   # lực chiến đội đọc được ngay trước khi mở Thành Tích
        self.tran = None                        # thông tin trận đang đánh (để ghi tran.csv)
        self.dang_thu_thap = False              # mở Thành Tích chỉ để lưu tướng các bản ghi (--thu-thap-tuong)
        # So khung tướng của bản ghi với khung tướng của bạn (doc_tuong_cua_toi.py): bản ghi có tướng mà bản ghi có khung
        # còn của bạn không khung thì đội chép về yếu hơn hẳn (đo 13/10: đội có Saida thua 9/9 trận đầu).
        self.so_khung = None
        self.ngoai_phien = 0                    # leo hộ: số lần liền gặp màn của riêng bạn (đã ra khỏi phiên leo hộ)
        self.ai_ho = 0                          # leo hộ: số ải đã qua cho người nhờ
        # Leo hộ dùng tướng của người nhờ: khung tướng đọc từ tài khoản của bạn không dùng được.
        if a.thieu_khung != "thu" and not a.leo_ho:
            try:
                from doc_tuong_cua_toi import KET_QUA, SoKhung
                if KET_QUA.exists():
                    self.so_khung = SoKhung()
                    yeu = sorted(t for t, k in self.so_khung.cua_toi.items() if not k)
                    log.info("So khung tướng: tướng của bạn không khung: %s.", ", ".join(yeu) or "không có")
                else:
                    log.warning("Chưa có %s (chạy doc_tuong_cua_toi.py): không so khung tướng.", KET_QUA.name)
            except (OSError, ValueError, KeyError) as e:
                log.warning("Không nạp được dữ liệu so khung tướng (%s): không so khung tướng.", e)

    # ---------------------------------------------------------------- tiện ích

    def chup(self):
        img = self.adb.screenshot()
        return img, self.nd.nhan_dien(img)

    def bam(self, k: KetQua, nut, cho=CHO_SAU_BAM):
        if nut not in k.nut:
            # Màn hình đang chuyển (ví dụ màn BẠI vừa bấm ← xong: nút đã mờ đi nhưng chữ BẠI còn): chờ rồi chụp lại.
            log.debug("  không thấy nút %s - chờ", nut)
            time.sleep(CHO_KHONG_RO)
            return
        x, y = k.nut[nut]
        log.debug("  bấm %s (%d,%d)", nut, x, y)
        self.adb.tap(x, y)
        time.sleep(cho)

    def luu_anh(self, img, ten):
        DEBUG_DIR.mkdir(exist_ok=True)
        p = DEBUG_DIR / f"{time.strftime('%Y%m%d-%H%M%S')}-{ten}.png"
        cv2.imwrite(str(p), img)
        for cu in sorted(DEBUG_DIR.glob("*.png"))[:-MAX_DEBUG_IMAGES]:
            cu.unlink()
        log.info("  Đã lưu ảnh %s", p.relative_to(BASE))

    def thong_ke(self):
        phut = (time.monotonic() - self.bat_dau) / 60
        tu_dong = f", {self.tk['tu_dong']} ải nhờ Tự Động Xử Lý" if self.tk["tu_dong"] else ""
        if self.a.leo_ho:
            ai = ", ".join(f"{TEN_CHE_DO[c.ten]} {c.ai or '?'}" for c in self.cd.values())
            return (f"leo hộ {self.ai_ho} ải, {self.tk['tran']} trận, thắng {self.tk['thang']}, thua {self.tk['thua']}, "
                    f"chép đội {self.tk['chep']} lần, ải người nhờ: {ai}, {phut:.0f} phút")
        return (f"{self.tk['tran']} trận, thắng {self.tk['thang']}, thua {self.tk['thua']}, chép đội {self.tk['chep']} lần{tu_dong}, "
                f"ải {self.tien_trinh or '?'}, {phut:.0f} phút")

    def cap_nhat_tien_trinh(self, ai):
        if ai is None or ai == self.tien_trinh:
            return
        if self.tien_trinh is not None:
            log.info("Tiến trình: %s → %s", self.tien_trinh, ai)
        self.tien_trinh = ai
        if self.a.dung_o_ai and ai >= self.a.dung_o_ai:
            raise Dung(f"Đã tới ải {ai} (dừng ở ải {self.a.dung_o_ai} theo cài đặt).")

    def kiem_tra_dung(self):
        if self.a.gio_toi_da and time.monotonic() - self.bat_dau > self.a.gio_toi_da * 3600:
            raise Dung(f"Đã chạy đủ {self.a.gio_toi_da} giờ.")

    # ---------------------------------------------------------------- vòng chạy

    def chay(self):
        log.info("Bắt đầu %s %s. Mỗi đội thử tối đa %d trận, rồi chép đội khác từ Thành Tích.",
                 "leo hộ" if self.a.leo_ho else "leo", " + ".join(TEN_CHE_DO[c] for c in self.cd), self.a.thu_lai)
        while True:
            self.kiem_tra_dung()
            img, k = self.chup()
            if k.man_hinh != "khong_ro":
                self.khong_ro_tu = None
                self.da_bao_khong_ro = False
            if k.man_hinh not in ("thang", "bai", "dai_dien_thang"):
                self.da_tinh = False
            if k.man_hinh != "tu_dong_hoan_tat":
                self.da_tinh_chuoi = False
            # Chuỗi dừng mà không qua ải nào: game không hiện bảng kết quả lẫn màn BẠI, về thẳng màn đội hình (14/10).
            if self.trong_chuoi and k.man_hinh in ("doi_hinh", "man_afk"):
                self.thua_chuoi()
            log.debug("[%s] %s", self.hien, k)
            getattr(self, f"xu_ly_{k.man_hinh}")(img, k)

    # ---------------------------------------------------------------- xử lý từng màn hình

    def xu_ly_khoa(self, img, k):
        if not self.adb.screen_awake():
            log.info("Màn hình đang tắt - hãy bật màn hình. Thử lại sau %.0f giây.", CHO_MAN_TAT)
            time.sleep(CHO_MAN_TAT)
            return
        if not self.adb.game_booster_locked():
            self.xu_ly_khong_ro(img, k)         # màn tối nhưng không phải lớp khóa: có thể đang chuyển cảnh
            return
        log.info("Màn hình bị Game Booster khóa - mở khóa.")
        h, w = img.shape[:2]
        self.adb.tap(w // 2, h // 2)            # lớp khóa chặn mọi thao tác nên lần chạm này không tới game
        time.sleep(0.6)
        x, y = tim_o_khoa(self.adb.screenshot()) or (w // 2, int(h * 0.52))
        self.adb.swipe(x, y, x, y - h // 8, 400)
        time.sleep(1.0)
        if self.adb.game_booster_locked():
            log.info("  Kéo ổ khóa xong vẫn còn khóa, thử lại.")

    def xu_ly_nghi(self, img, k):
        log.info("Màn nghỉ của game - chạm để tiếp tục.")
        self.bam(k, "nghi_nhan_tiep_tuc")

    def xu_ly_bang_ban_goi(self, img, k):
        log.info("Bảng bán gói của game - bấm \"Nhấn để thoát\" (không mua gì).")
        self.luu_anh(img, "bang-ban-goi")
        self.bam(k, "nhan_de_thoat")

    def xu_ly_phan_thuong_afk(self, img, k):
        log.info("Nhận phần thưởng AFK.")
        self.bam(k, "thuong_nhan")

    def xu_ly_tu_dong_hoan_tat(self, img, k):
        """Bảng "Chiến Đấu Tự Động Hoàn Tất / Đã hoàn thành màn xN" khi chuỗi tự động dừng (thua, hoặc bạn tắt). Các ải
        thắng trong chuỗi không có màn THẮNG nên tính ở đây: đội mở đầu chuỗi thắng trận đầu nếu tiến trình tăng."""
        tt = self.so.tien_trinh_tu_dong(img)
        # Bảng vừa mở còn chạy hiệu ứng (14/10: có lần không đọc được số): chờ rồi đọc lại vài lần trước khi đóng.
        if tt is None and not self.da_tinh_chuoi and self.doc_lai_chuoi < DOC_LAI_CHUOI:
            self.doc_lai_chuoi += 1
            time.sleep(1.0)
            return
        self.doc_lai_chuoi = 0
        so_ai = tt[1] - tt[0] if tt else None
        log.info("Bảng Chiến Đấu Tự Động Hoàn Tất: %s. Đóng.",
                 f"tiến trình {tt[0]} → {tt[1]} ({so_ai} ải)" if tt else "không đọc được tiến trình")
        self.xu_ly_tu = None
        if not self.da_tinh_chuoi:
            self.da_tinh_chuoi = True
            cd = self.cd[self.hien]
            if so_ai:
                if self.tran:
                    self.tran["chuoi"] = so_ai
                self.ket_thuc_tran("thang")
                self.tk["thang"] += 1
                self.tk["tu_dong"] += so_ai
                self.thua_lien_tiep = 0
                self.sang_ai_moi(cd, tt[1])
                # Trận thua làm chuỗi dừng là trận của đội vừa thắng ở ải mới (game không hiện màn BẠI).
                self.tran = dict(che_do=self.hien, ai=tt[1], loai="mang sang", vi_tri=cd.vi_tri or "", doi=mo_ta(cd.doi),
                                 tran_thu=1, thieu_khung=",".join(cd.doi.thieu_khung or []) if cd.doi else "")
                self.tran_tu = time.monotonic()
                self.tran_che_do = self.hien
                self.trong_chuoi = True
            if self.trong_chuoi:
                self.thua_chuoi()
            log.info("  [%s]", self.thong_ke())
        self.bam_dong_trong(img)        # "Nhấn để đóng" cùng chỗ với bảng Thành Tích trống

    def thua_chuoi(self):
        """Trận thua làm chuỗi Tự Động Xử Lý dừng (game không hiện màn BẠI): tính như một trận BẠI."""
        self.trong_chuoi = False
        cd = self.cd[self.hien]
        self.ket_thuc_tran("thua")
        self.tk["thua"] += 1
        self.thua_lien_tiep += 1
        cd.thua += 1
        log.info("Tự Động Xử Lý dừng ở ải %s: %s thua %d/%d.", self.tien_trinh or "?", mo_ta(cd.doi), cd.thua,
                 self.so_tran_toi_da(cd))
        if cd.thua >= self.so_tran_toi_da(cd):
            cd.can_doi = True

    def xu_ly_xu_ly_xong(self, img, k):
        """Chuỗi đánh ngầm đã dừng: bấm nút "Tự Động Xử Lý Đã Hoàn Thành!" ở góc dưới trái bản đồ (chỗ nút Màn Chơi Đỉnh
        Cao) để mở bảng kết quả."""
        self.trong_chuoi = True
        log.info("Tự Động Xử Lý đã dừng - mở bảng kết quả.")
        h, w = img.shape[:2]
        s = w / 1600
        self.adb.tap(128 * s, h - (2560 - 2490) * s)
        time.sleep(3.0)

    def xu_ly_xu_ly_ngam(self, img, k):
        """Game đang Tự Động Xử Lý: đánh ngầm từng ải tới khi thua, không vẽ cảnh đánh. Không bấm gì (kể cả khi lớp khóa
        Game Booster bật: màn hình tối cho đỡ tốn pin), chỉ chụp lại thưa."""
        self.trong_chuoi = True
        if self.xu_ly_tu is None:
            self.xu_ly_tu = time.monotonic()
            log.info("Game đang Tự Động Xử Lý (đánh ngầm tới khi thua) - chờ.")
        if self.tran_tu is not None:
            self.tran_tu = time.monotonic()     # chuỗi dài bao lâu cũng không phải trận bị treo
        time.sleep(CHO_XU_LY)

    def ngoai_phien_leo_ho(self, img, ten):
        """Leo hộ mà gặp màn của riêng bạn (bản đồ, Màn AFK, đội hình của bạn): phiên leo hộ đã kết thúc (17/10: để màn
        THẮNG vài phút thì game tự về bản đồ) hoặc chưa mở. Gặp vài lần liền mới dừng, phòng lúc đang chuyển cảnh."""
        self.ngoai_phien += 1
        if self.ngoai_phien >= THIEU_NUT_TOI_DA:
            self.luu_anh(img, "ngoai-phien-leo-ho")
            raise Dung(f"Đang ở {ten} của bạn, không phải phiên leo hộ (phiên đã kết thúc hoặc chưa mở). Mở yêu cầu "
                       f"\"Yêu Cầu Đại Diện AFK Liên Hoàn\" (nút Đi trong Trò chuyện Bang Hội) rồi chạy lại.")
        time.sleep(CHO_KHONG_RO)

    def xu_ly_ban_do(self, img, k):
        if self.a.leo_ho:
            self.ngoai_phien_leo_ho(img, "bản đồ thế giới")
            return
        log.info("Đang ở bản đồ thế giới - mở Màn AFK.")
        self.bam(k, "ban_do_nut_man_afk", cho=3.0)

    def xu_ly_man_afk(self, img, k):
        if self.a.leo_ho:
            self.ngoai_phien_leo_ho(img, "Màn AFK")
            return
        self.cap_nhat_tien_trinh(self.so.ai_man_afk(img))
        # Mỗi giai đoạn, phần Chiến Đấu và phần Thách Đấu Huyền Linh có số ải giới hạn; hết ải phần nào thì Màn AFK chỉ
        # còn 1 nút ngang. Thiếu nút vài lần liền (không phải do đang chuyển cảnh) mới tính là hết.
        co_nut = [c for c in NUT_CHE_DO if nut_che_do(k, c)]
        if not co_nut:
            self.thieu_ca_hai += 1
            if self.thieu_ca_hai >= THIEU_NUT_TOI_DA:
                self.luu_anh(img, "man-afk-mot-nut")
                raise Dung("Màn AFK không còn nút Chiến Đấu / Thách Đấu Huyền Linh quen thuộc (có lẽ chỉ còn 1 nút ngang "
                           "vì một phần đã hết ải). Bot chưa có mẫu cho nút này nên không bấm; ảnh đã lưu trong debug/.")
            time.sleep(CHO_KHONG_RO)
            return
        self.thieu_ca_hai = 0
        for c in self.cd.values():
            if c.ten in co_nut:
                c.thieu_nut = 0
            elif not c.het:
                c.thieu_nut += 1
                if c.thieu_nut >= THIEU_NUT_TOI_DA:
                    c.het = True
                    log.info("Màn AFK không còn nút %s - phần này đã hết ải ở giai đoạn hiện tại.", TEN_CHE_DO[c.ten])
        self.doi_che_do_neu_can()
        nut = nut_che_do(k, self.hien)
        if nut is None:
            time.sleep(CHO_KHONG_RO)                # chờ xem nút có thật sự mất không
            return
        self.bam(k, nut, cho=2.5)

    def doi_che_do_neu_can(self):
        """Chế độ đang leo đã kẹt hoặc hết ải: chuyển sang chế độ còn leo được, hết cả thì dừng."""
        cd = self.cd[self.hien]
        if cd.ket or cd.het:
            con = [c for c in self.cd.values() if not c.ket and not c.het]
            if not con:
                ly_do = "; ".join(f"{TEN_CHE_DO[c.ten]}"
                                  + (f" ải {c.ai}" if self.a.leo_ho and c.ai else "")
                                  + f": {'đã hết ải' if c.het else 'đã thử hết các đội trong Thành Tích'}"
                                  for c in self.cd.values())
                o = "" if self.a.leo_ho else f" ở ải {self.tien_trinh or '?'}"
                raise Dung(f"Không {'leo hộ' if self.a.leo_ho else 'leo'} tiếp được{o} ({ly_do}).")
            self.hien = con[0].ten
            log.info("Chuyển sang %s.", TEN_CHE_DO[self.hien])

    def xu_ly_dai_dien_chon(self, img, k):
        """Leo hộ: bảng chọn ải của người nhờ (thẻ Huyền Linh và thẻ Màn AFK, mỗi thẻ ghi ải và đội hình địch). Hiện khi
        bấm Đi ở yêu cầu trong Trò chuyện Bang Hội, và sau mỗi lần bấm Tiếp Theo ở màn THẮNG."""
        if not self.a.leo_ho:
            raise Dung("Đang ở bảng chọn ải leo hộ (Đại Diện Tác Chiến): chạy lại với --leo-ho để leo hộ.")
        self.ngoai_phien = 0
        co_nut = [c for c in NUT_CHE_DO_HO if nut_che_do(k, c, NUT_CHE_DO_HO)]
        for c in self.cd.values():
            if c.ten in co_nut:
                c.thieu_nut = 0
            elif not c.het:
                c.thieu_nut += 1
                if c.thieu_nut >= THIEU_NUT_TOI_DA:
                    c.het = True
                    self.luu_anh(img, "leo-ho-thieu-nut")
                    log.info("Bảng chọn ải không còn nút %s - coi như người nhờ đã hết ải phần này.", TEN_CHE_DO[c.ten])
        self.doi_che_do_neu_can()
        nut = nut_che_do(k, self.hien, NUT_CHE_DO_HO)
        if nut is None:
            time.sleep(CHO_KHONG_RO)
            return
        self.bam(k, nut, cho=3.0)               # màn tải "Đang tham gia Đại Diện Tác Chiến" rồi tới màn đội hình

    def xu_ly_doi_hinh(self, img, k):
        cd = self.cd[self.hien]
        if k.dai_dien != self.a.leo_ho:
            if self.a.leo_ho:
                self.ngoai_phien_leo_ho(img, "màn đội hình")
                return
            raise Dung("Đang ở màn đội hình leo hộ (Đại Diện Tác Chiến): chạy lại với --leo-ho để leo hộ.")
        if self.a.leo_ho:
            self.ngoai_phien = 0
            if k.che_do and k.che_do != self.hien:
                # Nút ← của màn đội hình leo hộ chưa thử (có thể ra hẳn khỏi phiên): leo luôn chế độ đang mở.
                log.info("Đang ở màn đội hình leo hộ %s - leo chế độ này.", TEN_CHE_DO[k.che_do])
                self.hien = k.che_do
                cd = self.cd[self.hien]
            ai = self.so.ai_doi_hinh(img)
            if ai is not None and ai != cd.ai:
                if cd.ai is not None:
                    log.info("Leo hộ %s: ải %s → %s.", TEN_CHE_DO[self.hien], cd.ai, ai)
                cd.ai = ai
            self.tien_trinh = cd.ai
        if k.che_do and k.che_do != self.hien:
            log.info("Đang ở màn đội hình %s, cần %s - quay lại.", TEN_CHE_DO[k.che_do], TEN_CHE_DO[self.hien])
            self.bam(k, "nut_quay_lai", cho=2.5)
            return
        if cd.ket:
            if self.a.leo_ho:
                self.doi_che_do_neu_can()           # chưa rõ nút ← đi đâu: hết đội ở chế độ này thì dừng
                raise Dung(f"Leo hộ {TEN_CHE_DO[cd.ten]} ải {cd.ai or '?'}: đã thử hết các đội trong Thành Tích.")
            self.bam(k, "nut_quay_lai", cho=2.5)    # về Màn AFK để đổi chế độ hoặc dừng
            return
        if self.a.thu_thap_tuong and cd.can_thu_thap and self.tien_trinh is not None:
            log.info("Thu thập tướng: mở Thành Tích của %s ải %s.", TEN_CHE_DO[self.hien], self.tien_trinh)
            self.dang_thu_thap = True
            self.bam(k, "doi_hinh_thanh_tich", cho=3.0)
            return
        if cd.doi is None and not cd.can_doi and self.tt.doi_trong(img):
            log.info("Đội trống (chưa có tướng nào) - chép đội từ Thành Tích.")
            cd.can_doi = True
        if cd.can_doi or self.a.xem_thanh_tich:
            self.luc_truoc = self.tt.luc_doi(img)
            self.bam(k, "doi_hinh_thanh_tich", cho=3.0)
            return
        nut = ("dd_doi_hinh_chien_dau" if k.dai_dien else "doi_hinh_tu_dong" if self.a.tu_dong
               else "doi_hinh_chien_dau")
        luc = self.doc_luc_doi(img)
        ban_ghi = trieu(cd.doi.luc_chien) if cd.doi else None
        ty_le = luc / ban_ghi if luc and ban_ghi else None
        so_sanh = f" (đội bạn {luc:.1f}M" + (f" = {ty_le:.0%} bản ghi)" if ty_le else ")") if luc else ""
        if cd.moi_chep:
            cd.moi_chep = False
            if ty_le is not None:
                cd.ty_le.append((cd.doi, ty_le))
            # Đo 13/10 (trận đầu của đội chép): lực chiến đội bạn < 90% bản ghi thắng 1/13, 90-100% thắng 4/10,
            # >= 100% thắng 17/26. Chép không mất gì nên chép thử trước, đội yếu để sau.
            if (self.a.nguong_luc and cd.vong == 0 and not cd.danh_ngay and ty_le is not None
                    and ty_le < self.a.nguong_luc):
                log.info("Đội vừa chép%s thấp hơn %.0f%% - để sau, chép thử đội khác.", so_sanh,
                         self.a.nguong_luc * 100)
                cd.hoan.append((cd.doi, ty_le))
                cd.can_doi = True
                self.luc_truoc = luc
                self.bam(k, "doi_hinh_thanh_tich", cho=3.0)
                return
            cd.danh_ngay = False
        # Số trong ô đỏ của đường ải (và số sau trong "A → B" ở màn THẮNG) là ải đang phải đánh.
        log.info("%s %s ải %s với %s%s.", "Leo hộ" if self.a.leo_ho else "Đánh", TEN_CHE_DO[self.hien],
                 self.tien_trinh or "?", mo_ta(cd.doi), so_sanh)
        self.tran = dict(che_do=("ho_" if self.a.leo_ho else "") + self.hien, ai=self.tien_trinh or "", vi_tri=cd.vi_tri or "",
                         loai="có sẵn" if cd.doi is None else "mang sang" if cd.mang_sang else "chép",
                         doi=mo_ta(cd.doi), luc_ban_ghi=ban_ghi or "", luc_doi=f"{luc:.3f}" if luc else "",
                         ty_le=f"{ty_le:.3f}" if ty_le else "", tran_thu=cd.thua + 1,
                         thieu_khung=",".join(cd.doi.thieu_khung or []) if cd.doi else "")
        self.bam(k, nut, cho=2.0)
        self.tran_tu = time.monotonic()
        self.tran_che_do = self.hien
        cd.da_danh = True

    def doc_luc_doi(self, img):
        """Lực chiến đội (triệu) ở màn đội hình. Ngay sau khi chép đội, game cập nhật con số chậm một chút (đo 12/10: đọc
        ngay thì vẫn ra lực chiến của đội cũ), nên chờ tới khi nó khác số trước khi chép và đứng yên 2 lần liền."""
        luc = self.tt.luc_doi(img)
        if not self.vua_chep:
            return luc
        self.vua_chep = False
        truoc = self.luc_truoc
        for _ in range(DOI_LUC_TOI_DA):
            img2, k2 = self.chup()
            if k2.man_hinh != "doi_hinh":
                return luc
            moi = self.tt.luc_doi(img2)
            if moi is not None and moi == luc and moi != truoc:
                return moi
            luc = moi
            time.sleep(0.4)
        if luc is not None and luc == truoc:
            log.info("  Lực chiến đội không đổi sau khi chép (%.1fM): đội chép có thể trùng đội đang dùng.", luc)
        return luc

    def xu_ly_dang_danh(self, img, k):
        if self.a.tu_dong and k.tu_dong and "nut_tu_dong_xu_ly" in k.nut:
            # Chiến Đấu Tự Động đang chạy: chuyển sang đánh ngầm (game không vẽ cảnh đánh, đỡ tốn pin).
            log.info("Bấm Tự Động Xử Lý (game đánh ngầm các ải tiếp theo tới khi thua).")
            self.bam(k, "nut_tu_dong_xu_ly", cho=3.0)
            return
        if self.tran_tu is None:
            self.tran_tu = time.monotonic()
            self.tran_che_do = None
            log.info("Đang có trận đánh dở (không do bot bắt đầu) - chờ kết quả.")
        elif time.monotonic() - self.tran_tu > TRAN_TOI_DA:
            log.warning("Trận kéo dài hơn %d giây - có thể game bị treo.", TRAN_TOI_DA)
            self.luu_anh(img, "tran-qua-lau")
            self.tran_tu = time.monotonic()
        time.sleep(CHO_DANG_DANH)

    def so_tran_toi_da(self, cd: CheDo):
        """Số trận đội đang dùng được đánh trước khi chép đội khác. Đội mang sang từ ải trước được ít trận hơn:
        đo 12/10, ở ải 755-761 đội mang sang thua cả 3 trận, rồi bản ghi Thành Tích của chính ải đó thắng ngay."""
        return self.a.thu_lai_doi_cu if cd.mang_sang else self.a.thu_lai

    def ket_thuc_tran(self, ket_qua):
        giay = time.monotonic() - self.tran_tu if self.tran_tu else None
        self.tran_tu = None
        self.tran_che_do = None
        self.tk["tran"] += 1
        if self.tran:
            moi = not TRAN_CSV.exists()
            with TRAN_CSV.open("a", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, COT_CSV)
                if moi:
                    w.writeheader()
                w.writerow(dict(self.tran, thoi_gian=time.strftime("%Y-%m-%d %H:%M:%S"), ket_qua=ket_qua,
                                giay=f"{giay:.0f}" if giay else ""))
            self.tran = None
        return f" ({giay:.0f} giây)" if giay else ""

    def ket_qua_cu(self, ten):
        """Kết quả của trận bot không tự bắt đầu (còn lại từ lần chạy trước, hoặc trận đánh dở lúc khởi động): không
        gán cho chế độ nào; trả về True để người gọi bấm ← về Màn AFK rồi chọn chế độ của mình."""
        if self.tran_che_do is not None:
            return False
        if not self.da_tinh:
            self.da_tinh = True
            log.info("Màn %s của trận không do bot bắt đầu - không tính, về Màn AFK.", ten)
            self.tran_tu = None
        return True

    def xu_ly_thang(self, img, k):
        if self.ket_qua_cu("THẮNG"):
            self.bam(k, "nut_quay_lai", cho=2.5)
            return
        if not self.da_tinh:
            self.da_tinh = True
            thoi_gian = self.ket_thuc_tran("thang")
            self.tk["thang"] += 1
            self.thua_lien_tiep = 0
            tt = self.so.tien_trinh_thang(img)
            log.info("THẮNG%s! %s %s. [%s]", thoi_gian, TEN_CHE_DO[self.hien],
                     f"tiến trình {tt[0]} → {tt[1]}" if tt else "(không đọc được tiến trình)", self.thong_ke())
            # Chế độ vừa thắng sang ải mới: thử lại từ đầu, đội vừa thắng giữ nguyên để đánh tiếp. Chế độ kia vẫn ở ải
            # cũ (thắng Huyền Linh 515 xong, nút Chiến Đấu của Màn AFK vẫn là ải 1947M như trước) nên giữ nguyên.
            self.sang_ai_moi(self.cd[self.hien], tt[1] if tt else None)
            if self.a.mot_tran:
                raise Dung("Đã đánh xong 1 trận (--mot-tran).")
        self.bam(k, "thang_chien_dau", cho=2.5)     # đánh ải kế

    def xu_ly_dai_dien_thang(self, img, k):
        """Leo hộ thắng: màn THẮNG có dải "Đại Diện Tác Chiến" và nút Tiếp Theo (mở bảng chọn ải kế), không có tiến
        trình. Ải mới đọc ở tiêu đề màn đội hình kế tiếp."""
        if not self.a.leo_ho:
            raise Dung("Đang ở màn THẮNG của leo hộ (Đại Diện Tác Chiến): chạy lại với --leo-ho để leo hộ.")
        self.ngoai_phien = 0
        if not self.da_tinh and self.tran_che_do is not None:
            self.da_tinh = True
            thoi_gian = self.ket_thuc_tran("thang")
            self.tk["thang"] += 1
            self.thua_lien_tiep = 0
            self.ai_ho += 1
            cd = self.cd[self.hien]
            log.info("THẮNG%s! Leo hộ %s ải %s. [%s]", thoi_gian, TEN_CHE_DO[self.hien], cd.ai or "?", self.thong_ke())
            self.sang_ai_moi(cd, None)
            if cd.ai is not None:
                cd.ai += 1                          # đọc lại ở màn đội hình kế
            if self.a.mot_tran:
                raise Dung("Đã đánh xong 1 trận (--mot-tran).")
        elif not self.da_tinh:
            self.da_tinh = True
            log.info("Màn THẮNG leo hộ của trận không do bot bắt đầu - không tính, bấm Tiếp Theo.")
            self.tran_tu = None
        # Không bao giờ bấm ←: có thể ra khỏi phiên leo hộ.
        self.bam(k, "dd_tiep_theo", cho=3.0)

    def sang_ai_moi(self, cd: CheDo, ai):
        """Chế độ cd vừa thắng sang ải mới."""
        # Không tính đội đang dùng là đã thử ở ải mới: bản ghi của cùng người chơi ở ải mới có thể xếp vị trí khác
        # (đo 12/10: đội 274M thua 3 trận ở ải 757, chép lại bản ghi 274M của ải 757 thì thắng ngay).
        cd.da_thu.clear()
        cd.ket = False
        cd.can_doi = False
        cd.thua = 0
        cd.mang_sang = True
        cd.vi_tri = None
        cd.can_thu_thap = True
        cd.moi_chep = cd.danh_ngay = False
        cd.hoan.clear()
        cd.ty_le.clear()
        cd.vong = 0
        cd.ds_cu = None
        self.cap_nhat_tien_trinh(ai)

    def xu_ly_bai(self, img, k):
        if self.a.leo_ho:
            self.ngoai_phien = 0
            if self.tran_che_do is None:
                if not self.da_tinh:
                    self.da_tinh = True
                    log.info("Màn BẠI của trận không do bot bắt đầu - không tính, bấm Thử Lại.")
                    self.tran_tu = None
                self.bam(k, "bai_thu_lai", cho=2.5)
                return
        elif self.ket_qua_cu("BẠI"):
            self.bam(k, "nut_quay_lai", cho=2.5)
            return
        cd = self.cd[self.hien]
        self.trong_chuoi = False
        if not self.da_tinh:
            self.da_tinh = True
            thoi_gian = self.ket_thuc_tran("thua")
            self.tk["thua"] += 1
            self.thua_lien_tiep += 1
            cd.thua += 1
            log.info("BẠI%s: %s, %s thua %d/%d.", thoi_gian, TEN_CHE_DO[self.hien], mo_ta(cd.doi), cd.thua,
                     self.so_tran_toi_da(cd))
            if self.a.mot_tran:
                raise Dung("Đã đánh xong 1 trận (--mot-tran).")
            if self.a.thua_toi_da and self.thua_lien_tiep >= self.a.thua_toi_da:
                raise Dung(f"Thua {self.thua_lien_tiep} trận liên tiếp (giới hạn {self.a.thua_toi_da}).")
            if cd.thua >= self.so_tran_toi_da(cd):
                cd.can_doi = True
        if cd.can_doi and not self.a.leo_ho:
            self.bam(k, "nut_quay_lai", cho=2.5)    # về Màn AFK, vào lại màn đội hình rồi mở Thành Tích
        else:
            # Leo hộ: Thử Lại về màn đội hình của ải đó (ở đó mở Thành Tích nếu cần đổi đội); nút ← có thể ra khỏi phiên.
            self.bam(k, "bai_thu_lai", cho=2.5)

    def xu_ly_khong_ro(self, img, k):
        now = time.monotonic()
        if self.khong_ro_tu is None:
            self.khong_ro_tu = now
        elif now - self.khong_ro_tu > KHONG_RO_TOI_DA and not self.da_bao_khong_ro:
            self.da_bao_khong_ro = True
            app = self.adb.foreground_package()
            if app != GAME_PACKAGE:
                log.warning("Game không ở trên cùng màn hình (đang mở: %s). Hãy mở lại game ở Màn AFK.", app or "?")
            else:
                log.warning("Không nhận ra màn hình đã %d giây (hộp thoại lạ?). Hãy kiểm tra máy.", KHONG_RO_TOI_DA)
            self.luu_anh(img, "khong-ro")
        time.sleep(CHO_KHONG_RO if now - self.khong_ro_tu < KHONG_RO_TOI_DA else CHO_MAN_TAT)

    # ---------------------------------------------------------------- Thành Tích

    def xu_ly_thanh_tich(self, img, k):
        cd = self.cd[self.hien]
        if self.dang_thu_thap:
            self.thu_thap(img, k, cd)
            return
        if not (cd.can_doi or self.a.xem_thanh_tich):
            log.info("Bảng Thành Tích đang mở - đóng lại.")
            self.bam(k, "tt_nhan_de_dong")
            return
        dau = self.ve_doi_dau(img, k, True if self.a.loc else None)
        if dau is None:
            return
        d, _, k = dau
        # Chép nhanh: đội đứng đầu Thành Tích thắng ngay trận đầu ở 13/14 ải (đo 12/10/2026). Game tự xếp các bản ghi
        # theo khả năng thắng của tài khoản và đẩy đội đã thua xuống dưới, nên không cần đọc cả danh sách.
        if not self.a.xem_thanh_tich and self.dung_duoc(d, cd) and not d.thieu_khung:
            self.chep(k, d, cd, 0)
            return
        # Chưa đánh trận nào từ lần đọc trước (đang chép thử) thì thứ tự đội không đổi: dùng lại danh sách cũ, đi thẳng
        # từ đội đầu tới đội cần chép thay vì đọc lại cả 10 đội.
        if cd.ds_cu and not cd.da_danh and cung_doi(d, cd.ds_cu[0]) and not self.a.xem_thanh_tich:
            ds, dang_o = cd.ds_cu, 0
        else:
            ds, k = self.doc_tiep(d, k)
            if ds is None:
                return
            dang_o = len(ds) - 1
            cd.ds_cu, cd.da_danh = ds, False
            for i, x in enumerate(ds):
                da = any(cung_doi(x, y) for y in cd.da_thu)
                log.info("  Đội %2d: %s%s", i + 1, mo_ta(x), " (đã thử)" if da else "")
        if self.a.xem_thanh_tich:
            self.bam(k, "tt_nhan_de_dong")
            raise Dung("Đã xem Thành Tích (--xem-thanh-tich).")
        chon = self.chon_doi(ds, cd)
        if chon is None and cd.hoan:
            # Đã chép thử hết: đánh đội đã hoãn có tỉ lệ lực chiến cao nhất.
            j = max(range(len(cd.hoan)), key=lambda j: cd.hoan[j][1])
            doi_hoan, tl = cd.hoan.pop(j)
            chon = next((i for i, x in enumerate(ds) if cung_doi(x, doi_hoan)), None)
            if chon is None:
                log.info("  Đội đã chép thử %s không còn trong Thành Tích - bỏ qua.", mo_ta(doi_hoan))
                return
            log.info("Đã chép thử hết: đánh đội có lực chiến cao nhất còn lại (%.0f%% bản ghi).", tl * 100)
            cd.danh_ngay = True
        elif chon is None and cd.vong + 1 < self.a.so_vong:
            cd.vong += 1
            cd.da_thu.clear()
            log.info("Đã đánh hết các đội của %s ở ải này - vòng %d.", TEN_CHE_DO[self.hien], cd.vong + 1)
            chon = self.chon_doi(ds, cd)
        if chon is None:
            log.info("Đã thử hết các đội dùng được trong Thành Tích của %s ở ải này.", TEN_CHE_DO[self.hien])
            cd.ket = True
            cd.can_doi = False
            self.bam(k, "tt_nhan_de_dong")
            return
        # Đi từ đội đang đứng (cuối danh sách, hoặc đầu nếu dùng lại danh sách cũ) tới đội đã chọn. Game có lúc bỏ qua
        # một lần bấm mũi tên, nên sau mỗi đợt bấm thì đọc lại xem đang ở đội nào (nhận theo nội dung) rồi bấm bù.
        for _ in range(DI_TOI_TOI_DA):
            buoc = dang_o - chon
            for _ in range(abs(buoc)):
                self.bam(k, "tt_mui_ten_trai" if buoc > 0 else "tt_mui_ten_phai", cho=CHO_MUI_TEN)
            d, _, k = self.chup_doi()
            dang_o = next((j for j, x in enumerate(ds) if d is not None and cung_doi(d, x)), None)
            if dang_o is None or dang_o == chon:
                break
            log.info("  Đang ở đội %d, cần đội %d - bấm bù.", dang_o + 1, chon + 1)
        if d is None or dang_o != chon:
            log.info("  Không tới được đội %d vừa chọn - đọc lại danh sách.", chon + 1)
            cd.ds_cu = None
            return
        self.chep(k, d, cd, chon)

    def xu_ly_thanh_tich_trong(self, img, k):
        """Thành Tích không có bản ghi nào ("Không có bản ghi phù hợp"). Gặp 13/10 ở Màn AFK ải 808: ô lọc bật mà mọi
        bản ghi đều có tướng chưa sở hữu. Bảng trống khi bật lọc thì không có đội nào chép được."""
        cd = self.cd[self.hien]
        if self.dang_thu_thap:
            if o_loc_bat(img) and "tt_o_loc_chu" in k.nut:
                log.info("  Thành Tích trống khi bật lọc - tắt lọc để thu thập.")
                x, y = k.nut["tt_o_loc_chu"]
                s = img.shape[1] / 1600
                self.adb.tap(x - O_LOC_TRAI * s, y + O_LOC_DUOI * s)
                time.sleep(CHO_SAU_BAM)
                return
            log.info("Thu thập tướng: %s ải %s không có bản ghi nào.", TEN_CHE_DO[self.hien], self.tien_trinh)
            cd.can_thu_thap = False
            self.dang_thu_thap = False
        if self.a.xem_thanh_tich:
            self.bam_dong_trong(img)
            raise Dung("Thành Tích trống: không có đội nào chép được (bản ghi đều có tướng chưa sở hữu).")
        if cd.can_doi:
            log.info("Thành Tích của %s ở ải này không có đội nào chép được (bản ghi đều có tướng chưa sở hữu).",
                     TEN_CHE_DO[self.hien])
            cd.ket = True
            cd.can_doi = False
        self.bam_dong_trong(img)

    def bam_dong_trong(self, img):
        # Chữ "Nhấn để đóng" của bảng trống nhấp nháy mờ nên không dò bằng mẫu được: bấm thẳng vào chỗ của nó (bám đáy).
        h, w = img.shape[:2]
        self.adb.tap(w // 2, h - (2560 - 2418) * w / 1600)
        time.sleep(CHO_SAU_BAM)

    def chep(self, k, d, cd: CheDo, i):
        log.info("Chép đội %d: %s.", i + 1, mo_ta(d))
        self.bam(k, "tt_sao_chep", cho=2.0)
        cd.da_thu.append(d)
        cd.doi = d
        cd.vi_tri = i + 1
        cd.thua = 0
        cd.can_doi = False
        cd.mang_sang = False
        cd.moi_chep = True
        self.vua_chep = True
        self.tk["chep"] += 1

    def dung_duoc(self, d, cd: CheDo):
        """Đội chép được: chưa thử ở ải này, không phải Chiến Đấu Thủ Công (bot không tung chiêu tay được), không phải
        Cực Hạn nếu đã chọn bỏ qua."""
        return (not d.thu_cong and d.luc_chien is not None and not any(cung_doi(d, x) for x in cd.da_thu)
                and not (d.nhan == "cuc_han" and self.a.cuc_han == "bo"))

    def chup_doi(self):
        """Chụp lại tới khi đọc được đội trong Thành Tích và 2 lần đọc liên tiếp giống nhau (sau khi bấm mũi tên,
        thanh thẻ tên còn trượt một lúc sau khi lực chiến đã đứng yên). Trả về (đội hoặc None, ảnh, kết quả)."""
        truoc = None
        for lan in range(DOC_LAI_TOI_DA):
            img, k = self.chup()
            d = self.tt.doc(img) if k.man_hinh == "thanh_tich" else None
            if d is not None and d.luc_chien is not None and d.chu_ky is not None:
                if truoc is not None and cung_doi(d, truoc):
                    if self.so_khung is not None:
                        d.thieu_khung = self.so_khung.thieu(img)
                    return d, img, k
                truoc = d
            else:
                truoc = None
                log.debug("  chưa đọc được đội (lần %d): %s", lan + 1, k)
            time.sleep(0.3)
        return None, img, k

    def ve_doi_dau(self, img, k, loc):
        """Chờ bảng đứng yên, đưa ô lọc "chỉ đội đã sở hữu" về trạng thái `loc` (None: để nguyên), về đội đầu. Trả về
        (đội đầu, ảnh, kết quả nhận diện), hoặc None nếu có gì bất thường (vòng sau sẽ thử lại)."""
        # Bảng vừa mở còn đang trượt vào: chỉ đọc khi 2 ảnh liên tiếp có bảng ở cùng vị trí.
        moc = k.nut.get("tt_nam_dam")
        img, k = self.chup()
        if k.man_hinh != "thanh_tich" or moc is None or k.nut.get("tt_nam_dam") != moc:
            log.debug("  Bảng Thành Tích chưa đứng yên.")
            return None
        d = self.tt.doc(img)
        if d is None:
            return None
        if loc is not None and d.loc_bat is not None and d.loc_bat != loc and "tt_o_loc_chu" in k.nut:
            log.info("  %s lọc \"Chỉ hiển thị đội hình đã sở hữu\".", "Bật" if loc else "Tắt")
            x, y = k.nut["tt_o_loc_chu"]
            s = img.shape[1] / 1600
            self.adb.tap(x - O_LOC_TRAI * s, y + O_LOC_DUOI * s)
            time.sleep(CHO_SAU_BAM)
            return None
        for _ in range(SO_DOI_TOI_DA):
            if "tt_mui_ten_trai" not in k.nut:
                break
            self.bam(k, "tt_mui_ten_trai", cho=CHO_MUI_TEN)
            d, img, k = self.chup_doi()
            if d is None:
                return None
        else:
            return None
        if d.chu_ky is None or d.luc_chien is None:     # lần đọc đầu chưa chắc đã ổn định: đọc lại cho chắc
            d, img, k = self.chup_doi()
            if d is None:
                return None
        if self.so_khung is not None and d.thieu_khung is None:     # bảng mở sẵn ở đội đầu: chưa qua chup_doi
            d.thieu_khung = self.so_khung.thieu(img)
        return d, img, k

    def doc_tiep(self, d, k):
        """Đang ở đội đầu: đọc lần lượt tới đội cuối. Trả về (danh sách, kết quả nhận diện) với màn hình ở đội cuối,
        hoặc (None, k) nếu có gì bất thường."""
        ds = []
        for _ in range(SO_DOI_TOI_DA):
            ds.append(d)
            if "tt_mui_ten_phai" not in k.nut:
                return ds, k
            self.bam(k, "tt_mui_ten_phai", cho=CHO_MUI_TEN)
            d, _, k = self.chup_doi()
            if d is None:
                return None, k
        log.warning("  Thành Tích có hơn %d đội?", SO_DOI_TOI_DA)
        return None, k

    def thu_thap(self, img, k, cd: CheDo):
        """--thu-thap-tuong: tắt lọc, lướt từ đội đầu tới đội cuối và lưu dải tướng của từng bản ghi. Lướt hỏng giữa
        chừng thì bỏ cả lượt, vòng sau lướt lại từ đầu. Xong thì đóng bảng, hoặc để bảng mở nếu đang cần chép đội (lần
        chép sẽ bật lại lọc)."""
        dau = self.ve_doi_dau(img, k, False)
        if dau is None:
            return
        d, img, k = dau
        ban_ghi = []
        for _ in range(SO_DOI_TOI_DA):
            ban_ghi.append((d, self.tt.dai_tuong(img), img))
            if "tt_mui_ten_phai" not in k.nut:
                break
            for _ in range(DI_TOI_TOI_DA):          # game có lúc bỏ qua lần bấm mũi tên: còn ở đội cũ thì bấm lại
                self.bam(k, "tt_mui_ten_phai", cho=CHO_MUI_TEN)
                d, img, k = self.chup_doi()
                if d is None or not cung_doi(d, ban_ghi[-1][0]):
                    break
            if d is None or cung_doi(d, ban_ghi[-1][0]):
                log.info("  Thu thập tướng: không sang được đội %d - lướt lại.", len(ban_ghi) + 1)
                return
        else:
            log.warning("  Thành Tích có hơn %d đội?", SO_DOI_TOI_DA)
            return
        luot = time.strftime("%Y%m%d-%H%M%S") + f"-{self.hien}-{self.tien_trinh}"
        thu_muc = THU_THAP_DIR / luot
        thu_muc.mkdir(parents=True, exist_ok=True)
        moi = not THU_THAP_CSV.exists()
        with THU_THAP_CSV.open("a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, COT_THU_THAP)
            if moi:
                w.writeheader()
            for i, (x, dai, anh) in enumerate(ban_ghi, 1):
                ten = f"{luot}/{i:02d}.png"
                if dai is not None:
                    cv2.imwrite(str(THU_THAP_DIR / ten), dai)
                # Ảnh cả màn hình (nhỏ, JPEG) để xem lại khi cần, ví dụ vị trí tướng trên sơ đồ ô.
                nho = cv2.resize(anh, None, fx=800 / anh.shape[1], fy=800 / anh.shape[1], interpolation=cv2.INTER_AREA)
                cv2.imwrite(str(thu_muc / f"{i:02d}_man_hinh.jpg"), nho, [cv2.IMWRITE_JPEG_QUALITY, 80])
                w.writerow(dict(thoi_gian=time.strftime("%Y-%m-%d %H:%M:%S"), luot=luot, che_do=self.hien,
                                ai=self.tien_trinh, vi_tri=i, luc_chien=x.luc_chien or "", nhan=x.nhan or "",
                                ly_tuong=int(x.ly_tuong), thu_cong=int(x.thu_cong),
                                chu_ky=np.packbits(x.chu_ky).tobytes().hex() if x.chu_ky is not None else "",
                                anh=ten if dai is not None else ""))
        log.info("Thu thập tướng: đã lưu %d bản ghi của %s ải %s (%s).", len(ban_ghi), TEN_CHE_DO[self.hien],
                 self.tien_trinh, thu_muc.relative_to(BASE))
        cd.can_thu_thap = False
        self.dang_thu_thap = False
        if not cd.can_doi:
            self.bam(k, "tt_nhan_de_dong")

    def chon_doi(self, ds, cd: CheDo):
        """Chỉ số đội nên chép, None nếu hết đội dùng được: đội dùng được đầu tiên theo thứ tự của game (game xếp theo
        khả năng thắng của tài khoản; đội Lý Tưởng / Phù Hợp Với Tướng luôn đứng đầu, Cực Hạn thường ở cuối)."""
        ung = [i for i, d in enumerate(ds) if self.dung_duoc(d, cd)]
        if cd.vong > 0:
            # Vòng sau: đội có tỉ lệ lực chiến (đo khi chép ở vòng trước) cao trước; đội chưa đo giữ thứ tự của game.
            def tl(i):
                return max((t for x, t in cd.ty_le if cung_doi(x, ds[i])), default=0)
            ung.sort(key=lambda i: -tl(i))
        # Bản ghi thiếu khung (tướng của bạn không khung trong khi bản ghi có khung) để sau cùng, hoặc bỏ hẳn.
        tot = next((i for i in ung if not ds[i].thieu_khung), None)
        if tot is None and self.a.thieu_khung == "cuoi":
            tot = next(iter(ung), None)
        return tot


def nut_che_do(k: KetQua, che_do, bang=NUT_CHE_DO):
    """Tên mẫu nút vào chế độ đang thấy ở Màn AFK (hoặc bảng chọn ải leo hộ với bang=NUT_CHE_DO_HO), None nếu không có."""
    return next((n for n in bang[che_do] if n in k.nut), None)


def trieu(luc_chien):
    """ "287M" -> 287.0 (triệu). Bản ghi yếu ghi theo K (leo hộ tài khoản nhỏ, 17/10: "66826K") -> 66.826."""
    if not luc_chien or luc_chien[-1] not in "MK" or not luc_chien[:-1].isdigit():
        return None
    return float(luc_chien[:-1]) / (1000 if luc_chien[-1] == "K" else 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--che-do", choices=["afk", "huyen-linh", "ca-hai"], default="ca-hai",
                    help="chế độ leo (mặc định ca-hai: Huyền Linh trước, kẹt thì sang Màn AFK)")
    ap.add_argument("--thu-lai", type=int, default=1,
                    help="số trận mỗi đội trước khi chép đội khác (mặc định 1: đo 13/10, đội chép thắng 42%% ở trận đầu "
                         "nhưng chỉ 6-7%% ở trận 2-3)")
    ap.add_argument("--so-vong", type=int, default=2,
                    help="số vòng thử các đội trong Thành Tích ở một ải trước khi bỏ chế độ đó (mặc định 2)")
    ap.add_argument("--nguong-luc", type=float, default=0.95,
                    help="đội vừa chép có lực chiến đội bạn / bản ghi thấp hơn mức này thì chưa đánh, chép thử đội "
                         "khác; hết đội thì đánh theo tỉ lệ giảm dần (mặc định 0.95; 0 = tắt chép thử)")
    ap.add_argument("--thu-lai-doi-cu", type=int, default=1,
                    help="số trận của đội vừa thắng ải trước khi sang ải mới, trước khi chép đội của ải mới (mặc định 1)")
    ap.add_argument("--cuc-han", choices=["thu", "bo"], default="thu",
                    help="đội Cực Hạn (tỉ lệ thành công thấp): thử theo thứ tự của game hoặc bỏ qua (mặc định thu)")
    ap.add_argument("--thieu-khung", choices=["cuoi", "bo", "thu"], default="cuoi",
                    help="bản ghi có tướng mà bản ghi có khung còn của bạn không khung (theo doc_tuong_cua_toi.py): "
                         "cuoi = chỉ thử khi hết đội khác (mặc định), bo = không bao giờ chép, thu = không so khung")
    ap.add_argument("--khong-loc", dest="loc", action="store_false",
                    help="không bật lọc \"Chỉ hiển thị đội hình đã sở hữu\" trong Thành Tích")
    ap.add_argument("--tu-dong", action="store_true",
                    help="bắt đầu trận bằng Chiến Đấu Tự Động rồi bấm Tự Động Xử Lý: game tự đánh ngầm các ải tiếp theo "
                         "tới khi thua (không vẽ cảnh đánh, đỡ tốn pin); thua thì bot chép đội như thường")
    ap.add_argument("--dung-o-ai", type=int, help="dừng khi tiến trình tới ải này")
    ap.add_argument("--gio-toi-da", type=float, help="dừng sau bấy nhiêu giờ")
    ap.add_argument("--thua-toi-da", type=int,
                    help="dừng sau bấy nhiêu trận thua liên tiếp (mặc định: không giới hạn; bot vẫn tự dừng khi đã "
                         "thử hết các đội trong Thành Tích của mọi chế độ)")
    ap.add_argument("--mot-tran", action="store_true", help="đánh đúng 1 trận rồi dừng")
    ap.add_argument("--xem-thanh-tich", action="store_true", help="mở Thành Tích, in danh sách đội rồi dừng")
    ap.add_argument("--thu-thap-tuong", action="store_true",
                    help="mỗi ải mới của mỗi chế độ: tắt lọc, lưu ảnh tướng của cả 10 bản ghi vào thu_thap_tuong/ "
                         "(để thống kê bằng thong_ke_tuong.py)")
    ap.add_argument("--leo-ho", action="store_true",
                    help="leo hộ người khác (Đại Diện Tác Chiến): bấm Đi ở \"Yêu Cầu Đại Diện AFK Liên Hoàn\" trong "
                         "Trò chuyện Bang Hội rồi chạy; bot dùng tướng của người nhờ, chép đội từ Thành Tích như thường, "
                         "thắng thì bấm Tiếp Theo, dừng khi hết đội ở mọi chế độ hoặc phiên kết thúc")
    ap.add_argument("--serial", help="serial thiết bị (adb devices)")
    ap.add_argument("--adb", default=DEFAULT_ADB, help="đường dẫn adb")
    ap.add_argument("--debug", action="store_true", help="in chi tiết từng bước")
    a = ap.parse_args()
    if a.leo_ho and a.tu_dong:
        ap.error("--tu-dong không dùng được khi --leo-ho (màn đội hình leo hộ không có Chiến Đấu Tự Động)")

    # Màn hình: thông tin chính (chi tiết khi --debug). File log: luôn ghi chi tiết, xoay vòng 3 x 2MB.
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG if a.debug else logging.INFO)
    logfile = logging.handlers.RotatingFileHandler(BASE / "leo_ai.log", maxBytes=2_000_000, backupCount=2,
                                                   encoding="utf-8")
    logfile.setLevel(logging.DEBUG)
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(message)s", datefmt="%H:%M:%S",
                        handlers=[console, logfile])

    adb = Adb(a.adb, a.serial)
    if not adb.connected():
        sys.exit("Không thấy máy qua ADB. Kiểm tra 'adb devices' (nhiều máy thì thêm --serial).")
    bot = LeoAi(adb, a)

    # Giữ màn hình sáng khi cắm sạc trong lúc chạy, trả lại cài đặt cũ khi thoát.
    old_stay_on = adb.get_stay_on()
    log.debug("Cài đặt giữ màn hình sáng lúc đầu: %s", old_stay_on)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    adb.shell("svc power stayon true")
    if not adb.charging():
        log.warning("Máy không cắm sạc: màn hình vẫn có thể tự tắt. Nên cắm sạc khi chạy lâu.")
    try:
        while True:
            try:
                bot.chay()
            except AdbError as e:
                log.warning("Lỗi ADB: %s. Thử lại sau %.0f giây.", e, CHO_MAN_TAT)
                time.sleep(CHO_MAN_TAT)
    except Dung as e:
        log.info("DỪNG: %s", e)
    except KeyboardInterrupt:
        log.info("Dừng theo yêu cầu.")
    finally:
        log.info("Tổng kết: %s.", bot.thong_ke())
        try:
            adb.set_stay_on(old_stay_on if old_stay_on not in ("", "null") else 0)
        except AdbError as e:
            log.warning("Không trả lại được cài đặt giữ màn hình sáng: %s", e)


if __name__ == "__main__":
    main()
