#!/usr/bin/env python3
"""Đọc khung (phẩm) các tướng của bạn trong Hội Trường Cộng Hưởng, để so với khung của tướng trong bản ghi
Thành Tích (thong_ke_tuong.py). Thẻ có khung là phẩm chuẩn, thẻ không khung là phẩm thấp so với bản ghi.

Mặc định mở Hội Trường từ nút trên bản đồ/Màn AFK, chụp và cuộn danh sách lớn tới cuối. Không lưu nếu mất màn hoặc chưa xác nhận hết cuộn.
--doi-hinh dùng lại bộ đọc đội hình cũ, có kiểm tra lực chiến để phát hiện kéo nhầm tướng.

Tướng được nhận ra bằng cách so ảnh mặt với các nhóm tướng đã đặt tên của dữ liệu Thành Tích. Thẻ của tướng đang trong
đội bị game phủ màu xanh và dấu tích nên khớp kém hơn: chỉ nhận khi hơn hẳn tướng đứng thứ 2.

    .venv/bin/python doc_tuong_cua_toi.py --serial R52N90Q08XR       # đọc trên máy rồi xuất trang so sánh
    .venv/bin/python doc_tuong_cua_toi.py --doi-hinh --anh samples/tab_s7_doi_hinh_man_afk.png   # thử trên ảnh có sẵn
    .venv/bin/python doc_tuong_cua_toi.py --khung                     # khung các tướng quan trọng (tự đọc / bạn đánh dấu)
    .venv/bin/python doc_tuong_cua_toi.py --khung Eryndor=1 Silven=1  # đánh dấu: 1 có khung, 0 không khung, -1 chưa có

Khung bạn đánh dấu (thu_thap_tuong/khung_tay.json) luôn được dùng thay cho kết quả tự đọc. Chỉ cần đánh dấu các tướng
quan trọng: tướng mà ít nhất 5% bản ghi dùng có khung (xem --khung).
"""
import argparse
import html
import json
import os
import shutil
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

import thong_ke_tuong as T
from adb import DEFAULT_ADB, Adb
from nhan_dien import REF_W, TPL_DIR, NhanDien
from thanh_tich import DocThanhTich

BASE = Path(__file__).resolve().parent
THU_MUC = BASE / "thu_thap_tuong"
KET_QUA = THU_MUC / "tuong_cua_toi.json"
ANH = THU_MUC / "tuong_cua_toi"
MAT_XAC_NHAN = THU_MUC / "mat_xac_nhan"
KHUNG_TAY = THU_MUC / "khung_tay.json"      # {tên: 1 có khung | 0 không khung | -1 chưa có tướng}, bạn tự đánh dấu
VIEN_THEM = THU_MUC / "vien_them.npz"       # đặc trưng viền của thẻ danh sách đã xác nhận (thêm vào bước xếp khung)
THU_VIEN = TPL_DIR / "tuong"   # ảnh mặt tướng bạn đã xác nhận (tên file = tên tướng): thêm vào thư viện

# Toạ độ máy gốc 1600x2560. Danh sách tướng nằm trên hàng nút Thành Tích / Chiến Đấu nên bám mép dưới.
DANH_SACH_Y = (1530, 2295)
KHE_X = 234                 # khe kem giữa cột thẻ 1 và 2: vuốt ở đây để không kéo trúng thẻ tướng
VUOT = (2150, 2000)         # vuốt chậm ~nửa hàng thẻ (hàng cách nhau 326px): hàng nào cũng có lúc hiện trọn (máy gốc)
VUOT_TOI_DA = 60
BUOC_COT, BUOC_HANG = 227, 326   # khoảng cách giữa 2 cột / 2 hàng thẻ (máy gốc, đo trên Tab S7)
KHE_HANG = 33               # khe kem giữa 2 hàng thẻ
CAO_THE = 290               # chiều cao một thẻ
XANH_TRONG_DOI = 0.3        # tỉ lệ điểm xanh lá phủ trên thẻ: tướng đang trong đội
NHAN_TUONG = 0.85           # thẻ thường: khớp mặt >= mức này mới tự nhận là tướng đó
GOI_Y = 0.6                 # thẻ thường khớp 0.6-0.85: chưa chắc, ghi tên đoán để bạn xác nhận (--xac-nhan)
NHAN_TRONG_DOI = (0.5, 0.12)  # thẻ đang trong đội: khớp >= 0.5 và hơn tướng thứ 2 ít nhất 0.12
# Chỉ so khung những tướng mà bản ghi thường dùng có khung. Đo 13/10 trên các đội bot đã chép (trận đầu): bản ghi có
# Saida có khung (Saida của bạn không khung, bản ghi có khung 100%) thắng 1/14; bản ghi có Mehira có khung (Mehira của bạn
# không khung, bản ghi chỉ có khung 26%) thắng 3/5, ngang các đội không thiếu khung (15/20).
KHUNG_CAN = 0.5
CUNG_THE = 0.85             # 2 thẻ (ở 2 lần chụp) khớp mặt >= mức này là cùng một thẻ
# Nút lọc tròn ở góc dưới phải danh sách đè lên thẻ (máy gốc, bám mép dưới; đo 14/10): bỏ thẻ chạm vùng này, thẻ đó sẽ
# hiện trọn ở lần chụp khác (vuốt nửa hàng mỗi lần).
NUT_LOC = (1410, 2080, 1585, 2255)
QUAN_TRONG = 0.05           # tướng quan trọng: ít nhất bấy nhiêu phần bản ghi dùng tướng này có khung


def doan(mask, do_dai=1):
    out, bd = [], None
    for i, c in enumerate(list(mask) + [False]):
        if c and bd is None:
            bd = i
        elif not c and bd is not None:
            if i - bd >= do_dai:
                out.append((bd, i))
            bd = None
    return out


def cat_the(img, cot=None):
    """Các thẻ thấy trọn trong danh sách: (list (ảnh thẻ theo khổ thẻ bản ghi 130x205, tâm y theo máy gốc), các cột).
    `cot`: vị trí các cột thẻ đo được ở ảnh trước (cuối danh sách có ô trống nên đo lại sẽ thiếu cột)."""
    k0 = REF_W / img.shape[1]
    ref = cv2.resize(img, None, fx=k0, fy=k0, interpolation=cv2.INTER_AREA) if k0 != 1 else img
    h = ref.shape[0]
    y0, y1 = h - (2560 - DANH_SACH_Y[0]), h - (2560 - DANH_SACH_Y[1])
    vung = ref[y0:y1]
    kem = T.nen_kem(vung)
    if cot is None:
        cot = [(a, b) for a, b in doan(kem.mean(axis=0) <= 0.6) if b - a > 150]
    if len(cot) < 3:
        return [], None
    buoc = float(np.median(np.diff([a for a, _ in cot])))
    k = T.BUOC / buoc
    # Hàng: lưới đều, cách nhau BUOC_HANG (theo tỉ lệ với khoảng cách cột). Tìm độ lệch của lưới sao cho các khe kem
    # ngang (khe giữa 2 hàng thẻ, kem suốt chiều ngang) trùng nhiều nhất; đo trên cả chiều ngang chứ không trên một cột
    # vì thẻ tướng tóc trắng có nhiều điểm giống màu kem.
    p = buoc * BUOC_HANG / BUOC_COT
    g = kem.mean(axis=1)
    khe = int(round(KHE_HANG * buoc / BUOC_COT))

    def diem_lech(o):
        return np.mean([g[int(o + j * p):int(o + j * p) + khe].mean() for j in range(-1, int(len(g) / p) + 1)
                        if 0 <= int(o + j * p) and int(o + j * p) + khe <= len(g)])
    o = max(range(int(p)), key=diem_lech)
    cao = int(round(CAO_THE * buoc / BUOC_COT))
    hang = []
    for j in range(-1, int(len(g) / p) + 1):
        tren = int(o + j * p) + khe
        if tren >= 0 and tren + cao <= len(g):
            hang.append((tren, tren + cao))
    nho = cv2.resize(vung, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
    nho = cv2.copyMakeBorder(nho, 40, 40, 80, 80, cv2.BORDER_REPLICATE)
    xam = cv2.cvtColor(vung, cv2.COLOR_BGR2GRAY)
    lx0, ly0, lx1, ly1 = NUT_LOC[0], h - (2560 - NUT_LOC[1]) - y0, NUT_LOC[2], h - (2560 - NUT_LOC[3]) - y0
    out = []
    for ha, hb in hang:
        for ca, cb in cot:
            if ca < lx1 and cb > lx0 and ha < ly1 and hb > ly0:     # bị nút lọc che
                continue
            # Ô trống (cuối danh sách) hoặc ô chụp lúc còn trôi: phần lớn là nền kem / gần như một màu.
            # Ô trống: gần như toàn màu kem. Thẻ tướng lông trắng (Faramor) có nhiều điểm giống màu kem nên ngưỡng kem thấp.
            if (~kem[ha:hb, ca:cb]).mean() < 0.35 or xam[ha:hb, ca:cb].std() < 15:   # thẻ phủ xanh ~26
                continue
            cx, ty = int((ca + cb) / 2 * k) + 80, int(ha * k) + 40
            the = nho[ty - 15:ty + 190, cx - 65:cx + 65]
            if the.shape[:2] == (205, 130):
                out.append((the, y0 + (ha + hb) / 2))
    return out, cot


def mat(the):
    m = the[T.MAT_Y[0]:T.MAT_Y[1], 65 - T.MAT_RONG:65 + T.MAT_RONG]
    return cv2.resize(m, (T.CO_SO[0] + 2 * T.LE, T.CO_SO[1] + 2 * T.LE), interpolation=cv2.INTER_AREA)


def trong_doi(the):
    hsv = cv2.cvtColor(the, cv2.COLOR_BGR2HSV)
    return float(((hsv[..., 0] >= 35) & (hsv[..., 0] <= 85) & (hsv[..., 1] > 60)).mean()) >= XANH_TRONG_DOI


class ThuVien:
    """Thư viện tướng templates/vi/tuong/ (tao_thu_vien_tuong.py): mặt các tướng đã đặt tên, tỉ lệ có khung của từng
    tướng trong bản ghi, thẻ mẫu viền đã biết khung. App Android dùng cùng thư viện này."""

    def __init__(self, thu_vien_mat=None, *, mau_khung_can=None, kho_mau=None, quy_tac_khung=None):
        from quan_ly_mau import KhoMau, MAC_DINH as KHO_MAC_DINH, pixel_sha
        release = None if kho_mau is False else KhoMau(kho_mau if kho_mau is not None else KHO_MAC_DINH).hien_tai()
        self.phien_ban_mau = release[1]['version'] if release else None
        self.quy_tac_ten = release[1].get('name_policy','v1') if release else 'v1'
        self.quy_tac_khung = quy_tac_khung or (release[1].get('inference_policy','v1') if release else 'v1')
        if self.quy_tac_khung not in ('v1','v2'):raise ValueError('Sai phiên bản quy tắc khung')
        js = json.loads((THU_VIEN / "tuong.json").read_text(encoding="utf-8"))
        o = T.CO_SO[0] + 2 * T.LE
        self.mat, self.dem, self.ty_le_khung = {}, Counter(), Counter()
        for tn, x in js["tuong"].items():
            tam = cv2.imread(str(THU_VIEN / f"{tn}.png"))
            self.mat[tn] = [tam[:, i * o:(i + 1) * o] for i in range(x["so_mat"])]
            self.dem[tn] = x["so_lan"]
            self.ty_le_khung[tn] = x["co_khung"] * x["so_lan"]
        self.so_ban_ghi = js.get("so_ban_ghi") or max(1, sum(self.dem.values()) // 5)
        approved_pairs = None
        if release:
            released_data = json.loads((release[0]/'dataset.json').read_text())['records'].values()
            denied = {(r['label'],r['pixel_sha256']) for r in released_data if r['kind']=='face' and r['status']=='rejected'}
            self.mat = {name:[m for m in faces if (name,pixel_sha(m)) not in denied] for name,faces in self.mat.items()}
            self.mat = {name:faces for name,faces in self.mat.items() if faces}
            approved_pairs = {(r['label'],r['pixel_sha256']) for r in released_data
                              if r['kind']=='face' and r['status']=='approved' and r['role']=='train'}
        # Mặt đã xác nhận lấy từ chính danh sách của bạn (--xac-nhan): lần sau khớp gần như tuyệt đối.
        if release:
            # Chỉ dùng bộ cá nhân thuộc bản phát hành đã duyệt; mẫu bị loại không
            # tự quay lại từ thư mục mặt cũ. Thư viện nền đóng gói vẫn dùng chung.
            with np.load(release[0]/'faces.npz', allow_pickle=False) as z:
                for name, face in zip(z['ten'], z['mat']):
                    self.mat.setdefault(str(name), []).insert(0, face.copy())
        else:
            for f in sorted(MAT_XAC_NHAN.glob("*.png")) if MAT_XAC_NHAN.exists() else []:
                self.mat.setdefault(f.stem.split("~")[0], []).insert(0, cv2.imread(str(f)))
        if thu_vien_mat is not None:
            with np.load(thu_vien_mat, allow_pickle=False) as z:
                faces, names = z["mat"], z["ten"]
                if (faces.dtype != np.uint8 or faces.shape[1:] != (48, 48, 3)
                        or names.ndim != 1 or names.dtype.kind not in 'US' or len(faces) != len(names)):
                    raise ValueError("Thư viện mặt bổ sung không đúng định dạng")
                for name, face in zip(names, faces):
                    if approved_pairs is not None and (str(name),pixel_sha(face)) not in approved_pairs:
                        continue
                    samples = self.mat.setdefault(str(name), [])
                    if not any(np.array_equal(face, old) for old in samples):
                        samples.append(face.copy())
        v = js["vien"]
        self.vien = np.fromfile(THU_VIEN / "vien.bin", dtype="<f4").reshape(v["so"], v["chieu"])
        self.nhan_khung = np.fromfile(THU_VIEN / "vien_nhan.bin", dtype=np.uint8).astype(int)
        self.mau_sao = [cv2.imread(str(TPL_DIR / t), cv2.IMREAD_GRAYSCALE) for t in T.MAU_SAO]
        from khung_can_python import MAC_DINH, MauKhungCan
        path = Path(mau_khung_can) if mau_khung_can is not None else release[0]/'model.npz' if release else MAC_DINH
        self.mau_khung_can = MauKhungCan.nap(path) if path.exists() else None
        if VIEN_THEM.exists() and not release:    # Chế độ quản lý không nạp thêm mẫu viền ngoài phiên bản.
            z = np.load(VIEN_THEM)
            self.vien = np.vstack([self.vien, z["vien"]])
            self.nhan_khung = np.concatenate([self.nhan_khung, z["nhan"].astype(int)])

    def quan_trong(self):
        """[(tên, phần bản ghi dùng tướng này có khung)] của các tướng quan trọng, giảm dần."""
        ds = [(t, self.ty_le_khung[t] / self.so_ban_ghi) for t in self.dem
              if self.dem[t] and self.ty_le_khung[t] / self.dem[t] >= KHUNG_CAN]   # Mehira: bản ghi ít dùng có khung
        return sorted(((t, p) for t, p in ds if p >= QUAN_TRONG), key=lambda x: -x[1])

    def khung(self, the):
        return self.khung_tin(the)[0]

    def khung_tin(self, the):
        """(khung, độ tin): độ tin là khoảng cách của điểm sao tới giữa 2 ngưỡng (càng xa càng chắc)."""
        d = T.diem_sao(the, self.mau_sao)
        tin = abs(d - (T.SAO_KHONG + T.SAO_CO) / 2)
        if d < T.SAO_KHONG:
            return 0, tin
        if d >= T.SAO_CO:
            return 1, tin
        gan = np.argsort(((self.vien - T.dac_trung_vien(the)) ** 2).sum(axis=1))[:7]
        return int(self.nhan_khung[gan].mean() >= 0.5), tin

    def diem(self, m):
        """Điểm khớp cao nhất với từng tướng, giảm dần: list (điểm, tên)."""
        return sorted(((max(T.giong(m, x) for x in v), t) for t, v in self.mat.items()), reverse=True)

    def goi_y_da_ty_le(self, m):
        """Xếp ứng viên để người dùng đối chiếu; không tự nâng điểm dùng để gán tên."""
        best = {}
        base = dict((t, d) for d, t in self.diem(m))
        h, w = m.shape[:2]
        for scale in (.9, .95, 1.0, 1.05, 1.1):
            if scale == 1.0:
                scores = [(d, t) for t, d in base.items()]
            else:
                matrix = cv2.getRotationMatrix2D(((w - 1) / 2, (h - 1) / 2), 0, scale)
                z = cv2.warpAffine(m, matrix, (w, h), flags=cv2.INTER_LINEAR,
                                   borderMode=cv2.BORDER_REFLECT_101)
                scores = self.diem(z)
            for d, t in scores:
                # Khi điểm bằng nhau, ưu tiên ảnh gốc để tránh gợi ý một biến đổi không cần thiết.
                old = best.get(t)
                if old is None or d > old[0] or (d == old[0] and scale == 1):
                    best[t] = (d, scale)
        return [dict(ten=t, diem=float(d), diem_goc=float(base[t]), ty_le=float(scale))
                for t, (d, scale) in sorted(best.items(), key=lambda x: (-x[1][0], x[0]))[:3]]

    def danh_gia_khung(self, the, chat_luong_cat=None):
        """Kết quả bảo thủ cho Python: None là chưa rõ; điểm khớp/phiếu không phải xác suất."""
        out = dict(khung=None, diem_sao=None, phieu_co=0, so_mau=0, khoang_cach=None,
                   ly_do="anh_khong_hop_le")
        if chat_luong_cat is not None:
            out['cat_the'] = chat_luong_cat
            if (not chat_luong_cat.get('day_du') or not chat_luong_cat.get('vung_sao_day_du',True)
                    or not chat_luong_cat.get('vien_day_du',True)):
                out['ly_do'] = 'bien_bi_cat_hoac_chua_xac_minh'
                return out
        if the is None or the.shape != (205, 130, 3) or the.dtype != np.uint8:
            return out
        gray = cv2.cvtColor(the, cv2.COLOR_BGR2GRAY)
        if gray.std() < 15 or gray[55:140, 21:109].std() < 12:
            out["ly_do"] = "anh_it_chi_tiet"
            return out
        if chat_luong_cat is not None:
            # Căn biên thay đổi kích thước ngôi sao so với mẫu cũ. Chỉ thay tỷ lệ mẫu,
            # giữ nguyên ảnh thẻ đã căn và vùng tìm sao để không làm xê dịch viền.
            from can_khung_tuong import diem_sao_da_ty_le
            star = diem_sao_da_ty_le(the,self.mau_sao)
            d = star['diem']
            out.update(sao_ty_le=star['ty_le'],co_hang_sao=star['co_hang_sao'])
        else:
            d = float(T.diem_sao(the, self.mau_sao))
        out["diem_sao"] = d
        if not np.isfinite(d):
            out["diem_sao"] = None
            return out
        if (chat_luong_cat is not None and chat_luong_cat.get('bien_chuan')
                and getattr(self,'quy_tac_khung','v1')=='v2'):
            from bang_chung_khung import quyet_dinh_v2
            learned=self.mau_khung_can.du_doan(the,chat_luong_cat) if self.mau_khung_can else None
            out['mau_khung_can']=learned
            out.update(quyet_dinh_v2(the,chat_luong_cat,star,learned))
            return out
        if (chat_luong_cat is not None and chat_luong_cat.get('bien_chuan')
                and getattr(self, 'mau_khung_can', None) is not None):
            learned = self.mau_khung_can.du_doan(the, chat_luong_cat)
            out['mau_khung_can'] = learned
            if learned['khung'] is not None:
                if (learned['khung'] == 0 and d >= T.SAO_CO
                        and learned['ty_le_mau_sao_xanh'] >= .005):
                    out['ly_do'] = 'mau_can_sao_mau_thuan'
                    return out
                # Viền/màu được học từ nhãn đã xác nhận, không tra tên hoặc
                # lựa chọn tay. Giữ điểm sao cũ để thấy cả trường hợp nhận nhầm tóc.
                out.update(khung=learned['khung'], ly_do=learned['ly_do'])
                return out
        if d >= T.SAO_CO and (chat_luong_cat is None or star['sao_tin_cay']):
            out.update(khung=1, ly_do="sao_ro")
            return out
        if len(self.vien) < 7:
            out["ly_do"] = "thieu_mau_vien"
            return out
        kc = ((self.vien - T.dac_trung_vien(the)) ** 2).mean(axis=1)
        gan = np.argsort(kc)[:7]
        co = int(self.nhan_khung[gan].sum())
        out.update(phieu_co=co, so_mau=7, khoang_cach=float(kc[gan[0]]))
        if co <= 1 and (chat_luong_cat is None or d < T.SAO_KHONG):
            out.update(khung=0, ly_do="vien_dong_thuan_khong_khung")
        elif chat_luong_cat is None and d >= T.SAO_KHONG and co >= 6:
            out.update(khung=1, ly_do="vien_dong_thuan_co_khung")
        else:
            out["ly_do"] = "sao_vien_mau_thuan" if d < T.SAO_KHONG and co >= 6 else "vien_chua_dong_thuan"
        return out


def gan_ten(tuong, tv, hon_nhi=0.0):
    """Gán tên tướng cho các thẻ, mỗi tướng một thẻ. Thẻ đang trong đội trước (chắc chắn là tướng trong bản ghi, khớp kém
    vì lớp phủ xanh nên xét theo độ hơn tướng thứ 2), rồi thẻ thường theo điểm giảm dần. Thẻ thường khớp chưa đủ chắc thì
    ghi tên đoán vào "goi_y"."""
    for x in tuong:
        x["ds_diem"] = tv.diem(x["mat"])
        x["ten"], x["goi_y"], x["diem"] = None, None, round(x["ds_diem"][0][0], 2)
    da = set()
    trong = sorted((x for x in tuong if x["trong_doi"]), key=lambda x: -x["ds_diem"][0][0])
    for x in trong:
        (d1, t1), (d2, _) = x["ds_diem"][0], x["ds_diem"][1]
        if d1 >= NHAN_TRONG_DOI[0] and d1 - d2 >= NHAN_TRONG_DOI[1] and t1 not in da:
            x["ten"] = t1
            da.add(t1)
    cap = sorted(((d, i, t) for i, x in enumerate(tuong) if not x["trong_doi"]
                  for d, t in (x["ds_diem"][:1] if hon_nhi else x["ds_diem"]) if d >= GOI_Y),
                 reverse=True)
    for d, i, t in cap:
        x = tuong[i]
        if x["ten"] or t in da:
            continue
        d2 = x["ds_diem"][1][0] if len(x["ds_diem"]) > 1 else 0.0
        if d >= NHAN_TUONG and (not hon_nhi or d - d2 >= hon_nhi):
            x["ten"] = t
            da.add(t)
        elif x["goi_y"] is None:
            x["goi_y"], x["diem"] = t, round(d, 2)
    for x in tuong:
        if x["ten"]:
            x["goi_y"] = None
        if getattr(tv,'quy_tac_ten','v1')=='v2':
            from ten_dien_mao import danh_gia_ten
            x['ten_chi_tiet']=danh_gia_ten(x['ds_diem'],x['ten'],trong_doi=x['trong_doi'],hon_nhi=hon_nhi or .04)
            # Giữ danh sách ứng viên tham khảo, không đẩy một tên yếu thành gợi ý đơn.
            if not x['ten'] and x['ds_diem'][0][0]<NHAN_TUONG:x['goi_y']=None
        x["ung_vien_ten"] = [dict(ten=t, diem=float(d), diem_goc=float(d), ty_le=1.0)
                             for d, t in x["ds_diem"][:3]]
    return tuong


class SoKhung:
    """So khung tướng trong một bản ghi Thành Tích với khung tướng của bạn (tuong_cua_toi.json). Dùng khi chọn đội để
    chép (leo_ai.py): bản ghi có tướng mà bản ghi dùng thẻ có khung còn của bạn không khung thì đội chép về yếu hơn hẳn."""

    def __init__(self, tv: "ThuVien | None" = None):
        self.tv = tv or ThuVien()
        ds = json.loads(KET_QUA.read_text(encoding="utf-8"))
        self.cua_toi = {}           # tên tướng -> khung (1/0)
        self.mat_cua_toi = []       # (ảnh mặt, khung) của thẻ không bị phủ xanh: so trực tiếp khi chưa biết tên tướng
        for x in ds:
            # Thẻ tướng đang trong đội bị game phủ xanh: khung đọc không tin được (14/10: Eryndor có khung đọc thành không).
            if x.get("ten") and not x["trong_doi"] and x["khung"] in (0, 1):
                self.cua_toi[x["ten"]] = max(self.cua_toi.get(x["ten"], 0), x["khung"])
            if not x["trong_doi"] and x["khung"] in (0, 1):
                face = cv2.imread(str(THU_MUC / x["mat"])) if x.get('mat') else mat(cv2.imread(str(THU_MUC / x["anh"])))
                self.mat_cua_toi.append((face, x["khung"]))
        for ten, k in doc_khung_tay().items():     # bạn đánh dấu: luôn thay kết quả tự đọc
            self.cua_toi[ten] = 1 if k == 1 else 0

    def khung_cua_toi(self, m):
        """(tên hoặc None, khung của bạn hoặc None nếu không thấy tướng này trong danh sách của bạn)."""
        d, ten = self.tv.diem(m)[0]
        if d >= NHAN_TUONG and ten in self.cua_toi:
            return ten, self.cua_toi[ten]
        tot = max(((T.giong(m, x), k) for x, k in self.mat_cua_toi), default=(0, None))
        if tot[0] >= NHAN_TUONG:
            return (ten if d >= NHAN_TUONG else None), tot[1]
        return (ten if d >= NHAN_TUONG else None), None

    def thieu(self, img):
        """Tên các tướng (hoặc "?") của đội đang hiện trong Thành Tích mà bản ghi có khung còn của bạn không khung.
        None nếu không tách được thẻ tướng."""
        the = T.tach_the(DocThanhTich_dai(img))
        if the is None:
            return None
        out = []
        for m, t in the:
            if self.tv.danh_gia_khung(t)["khung"] != 1:
                continue
            m = cv2.resize(m, (T.CO_SO[0] + 2 * T.LE, T.CO_SO[1] + 2 * T.LE), interpolation=cv2.INTER_AREA)
            ten, k = self.khung_cua_toi(m)
            if ten and self.tv.dem[ten] and self.tv.ty_le_khung[ten] / self.tv.dem[ten] < KHUNG_CAN:
                continue                # tướng này bản ghi thường dùng không khung: thiếu khung không sao
            if k == 0:
                out.append(ten or "?")
        return out


_doc_dai = None


def doc_khung_tay():
    return json.loads(KHUNG_TAY.read_text(encoding="utf-8")) if KHUNG_TAY.exists() else {}


def khung_tay(gan):
    """--khung: in khung các tướng quan trọng; gan = ["Eryndor=1", ...] thì lưu trước."""
    tay = doc_khung_tay()
    for g in gan:
        ten, v = g.split("=", 1)
        tay[ten] = int(v)
    if gan:
        KHUNG_TAY.write_text(json.dumps(tay, ensure_ascii=False, indent=1), encoding="utf-8")
    tu_doc = {}
    if KET_QUA.exists():
        for x in json.loads(KET_QUA.read_text(encoding="utf-8")):
            if x.get("ten") and not x["trong_doi"]:
                if x["khung"] in (0, 1):
                    tu_doc[x["ten"]] = max(tu_doc.get(x["ten"]) or 0, x["khung"])
                else:
                    tu_doc.setdefault(x["ten"], None)
    chu = {1: "có khung", 0: "KHÔNG khung", -1: "chưa có", None: "chưa rõ khung"}
    print("Tướng quan trọng (phần bản ghi dùng có khung) · tự đọc · bạn đánh dấu:")
    for ten, p in ThuVien().quan_trong():
        print(f"  {ten:10s} {p:4.0%}  {(chu[tu_doc[ten]] if ten in tu_doc else 'không thấy'):11s}  {chu[tay[ten]] if ten in tay else '-' }")


def DocThanhTich_dai(img):
    """Dải thẻ tướng của đội đang hiện trong Thành Tích (thanh_tich.DocThanhTich.dai_tuong)."""
    global _doc_dai
    if _doc_dai is None:
        _doc_dai = DocThanhTich()
    return _doc_dai.dai_tuong(img)


def doc(anh_list, tv, hoi_truong=False, goi_y_da_ty_le=False):
    """Gộp thẻ qua nhiều ảnh. Hội Trường giữ mặt/thẻ nét nhất, khung chưa rõ nếu quan sát chắc mâu thuẫn.
    Bộ đọc đội hình cũ vẫn lấy đa số khung và chọn thẻ theo điểm sao."""
    tuong, cot = [], None
    for img in anh_list:
        if hoi_truong:
            from hoi_truong import cat_the_hoi_truong
            if getattr(tv,'quy_tac_ten','v1')=='v2':
                from cat_the_bo_sung import cat_day_du as cat_the_hoi_truong
            ds, c = cat_the_hoi_truong(img, kem_chat_luong=True), None
        else:
            ds, c = cat_the(img, cot)
        cot = cot or c
        for item in ds:
            the = item[0]
            quality = item[2] if len(item)>2 else None
            # Danh tính bám ảnh tham chiếu đã được xác nhận; ảnh căn biên dùng riêng để đọc khung.
            m = mat(item[3] if len(item)>3 else the)
            dg = tv.danh_gia_khung(the, chat_luong_cat=quality) if hoi_truong else None
            k, tin = (dg["khung"], 0.0) if hoi_truong else tv.khung_tin(the)
            gan = max(((T.giong(m, x["mat"]), i) for i, x in enumerate(tuong)), default=(-1, -1))
            cu = tuong[gan[1]] if gan[0] >= CUNG_THE else None
            net = float(cv2.Laplacian(cv2.cvtColor(m, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var())
            if cu is None:
                tuong.append(dict(khung=k, trong_doi=False if hoi_truong else trong_doi(the), the=the, mat=m,
                                  do_net=net, lan=[(k, tin)], khung_chi_tiet=[dg] if dg else [],
                                  cat_day_du=bool(quality and quality.get('day_du')),chat_luong_cat=quality))
                continue
            cu["lan"].append((k, tin))
            old_valid = cu.get('cat_day_du',False)
            new_valid = bool(quality and quality.get('day_du'))
            if (hoi_truong and ((new_valid and not old_valid) or (new_valid == old_valid and net > cu["do_net"]))) or (not hoi_truong and tin > max(t for _, t in cu["lan"][:-1])):
                cu["the"] = the
                if hoi_truong:
                    cu["mat"], cu["do_net"] = m, net
                    cu['cat_day_du'] = new_valid
                    cu['chat_luong_cat'] = quality
            if hoi_truong:
                cu["khung_chi_tiet"].append(dg)
                da_biet = {kk for kk, _ in cu["lan"] if kk is not None}
                cu["khung"] = next(iter(da_biet)) if len(da_biet) == 1 else None
            else:
                co = sum(kk for kk, _ in cu["lan"])
                khong = len(cu["lan"]) - co
                cu["khung"] = 1 if co > khong else 0 if khong > co else max(cu["lan"], key=lambda x: x[1])[0]
    gan_ten(tuong, tv, hon_nhi=0.04 if hoi_truong else 0.0)
    if goi_y_da_ty_le:
        for x in tuong:
            if x["ten"] is None:
                x["ung_vien_ten"] = tv.goi_y_da_ty_le(x["mat"])
    return tuong


def chup_danh_sach(adb, nd, tt):
    """Mở màn đội hình nếu đang ở Màn AFK, rồi chụp và vuốt tới hết danh sách tướng. Trả về list ảnh."""
    img = adb.screenshot()
    k = nd.nhan_dien(img)
    if k.man_hinh == "man_afk" and "man_afk_chien_dau" in k.nut:
        print("Mở màn đội hình (chưa đánh).")
        adb.tap(*k.nut["man_afk_chien_dau"])
        for _ in range(8):                      # chuyển cảnh có lúc lâu hơn vài giây
            time.sleep(1.5)
            img = adb.screenshot()
            k = nd.nhan_dien(img)
            if k.man_hinh == "doi_hinh":
                break
    if k.man_hinh != "doi_hinh":
        sys.exit(f"Cần mở màn đội hình (hoặc Màn AFK) trước; đang ở: {k.man_hinh}.")
    luc = tt.luc_doi(img)
    print(f"Lực chiến đội lúc đầu: {luc}M")
    s = img.shape[1] / REF_W
    h = img.shape[0]
    x = KHE_X * s
    ya, yb = h - (2560 - VUOT[0]) * s, h - (2560 - VUOT[1]) * s

    def vung_ds(im):
        # Chỉ so vùng danh sách: chiến trường phía trên luôn có hiệu ứng chuyển động.
        return cv2.resize(im[int(h - (2560 - DANH_SACH_Y[0]) * s):int(h - (2560 - DANH_SACH_Y[1]) * s)], (160, 76))

    def kiem_tra(im, lan):
        moi = tt.luc_doi(im)
        if nd.nhan_dien(im).man_hinh != "doi_hinh" or (luc is not None and moi is not None and moi != luc):
            sys.exit(f"Dừng: sau lần vuốt {lan} màn hình / lực chiến đội đã đổi ({luc} -> {moi}). Kiểm tra lại đội.")

    # Về đầu danh sách: vuốt ngược tới khi danh sách đứng yên.
    cu = vung_ds(img)
    for i in range(VUOT_TOI_DA):
        adb.swipe(x, yb, x, ya, 250)
        time.sleep(1.2)
        img = adb.screenshot()
        kiem_tra(img, f"về đầu {i + 1}")
        moi = vung_ds(img)
        if cv2.absdiff(moi, cu).mean() < 2.0:
            break
        cu = moi
    anh = [img]
    for i in range(VUOT_TOI_DA):
        adb.swipe(x, ya, x, yb, 1000)
        time.sleep(1.6)                         # chờ danh sách trôi hết rồi mới chụp
        img = adb.screenshot()
        kiem_tra(img, i + 1)
        moi = vung_ds(img)
        if cv2.absdiff(moi, cu).mean() < 2.0:   # hết danh sách
            break
        anh.append(img)
        cu = moi
    print(f"Đã chụp {len(anh)} ảnh danh sách.")
    return anh


def chu_khung(k):
    return {1: "có khung", 0: "không khung", None: "chưa xác định khung"}[k]


def giai_thich_khung(x):
    """Thông tin kiểm tra được, không gọi điểm khớp hay tỷ lệ phiếu là xác suất."""
    if x.get("khung_nguoi_dung") is not None:
        text = f"Bạn xác nhận: {chu_khung(x['khung'])}."
        if "khung_tu_doc" in x:
            text += f" Trước xác nhận máy đọc: {chu_khung(x['khung_tu_doc'])}."
        return text
    ds = x.get("khung_chi_tiet", [])
    if not ds:
        return ""
    known = {d["khung"] for d in ds if d["khung"] is not None}
    parts = []
    if len(known) > 1:
        parts.append("Các lần đọc khung mâu thuẫn; cần xác nhận.")
    for d in ds:
        diem = d.get("diem_sao")
        if diem is None:
            parts.append("Chưa xác minh đủ biên/sao; không kết luận khung." if d.get('cat_the') else "Ảnh không đủ chi tiết hoặc không hợp lệ.")
            continue
        text = f"Điểm khớp sao {diem:.3f}"
        if d.get("so_mau"):
            text += f"; {d['phieu_co']}/{d['so_mau']} mẫu viền nghiêng về có khung"
        parts.append(text + ".")
    return " ".join(dict.fromkeys(parts))


def luu_ket_qua(tuong):
    """Ghi ảnh phiên mới trước, thay JSON nguyên tử sau; lỗi thì giữ nguyên phiên cũ."""
    if not tuong:
        raise ValueError("Chưa đọc được thẻ nào. Giữ nguyên dữ liệu khung tướng cũ.")
    ANH.mkdir(parents=True, exist_ok=True)
    phien = Path(tempfile.mkdtemp(prefix="phien-", dir=ANH))
    tam = None
    try:
        ds = []
        for i, x in enumerate(tuong, 1):
            f = phien / f"{i:02d}.png"
            if not cv2.imwrite(str(f), x["the"]):
                raise OSError(f"Không ghi được ảnh thẻ {i}; giữ dữ liệu cũ.")
            face_path = None
            if x.get('mat') is not None:
                face_file=phien/f'{i:02d}_mat.png'
                if not cv2.imwrite(str(face_file),x['mat']):
                    raise OSError(f'Không ghi được mặt thẻ {i}; giữ dữ liệu cũ.')
                face_path=face_file.resolve().relative_to(THU_MUC.resolve()).as_posix()
            ds.append(dict(anh=f.resolve().relative_to(THU_MUC.resolve()).as_posix(), mat=face_path,
                           ten=x["ten"], goi_y=x["goi_y"],
                           ten_chi_tiet=x.get('ten_chi_tiet'),
                           khung=x["khung"], trong_doi=x["trong_doi"], diem=x["diem"],
                           khung_chi_tiet=x.get("khung_chi_tiet", []),
                           ung_vien_ten=x.get("ung_vien_ten", []),
                           ten_nguoi_dung=x.get("ten_nguoi_dung"),chat_luong_cat=x.get('chat_luong_cat'),
                           **({"khung_nguoi_dung": x["khung_nguoi_dung"],
                               "khung_tu_doc": x.get("khung_tu_doc")} if x.get("khung_nguoi_dung") is not None else {})))
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=KET_QUA.parent,
                                         prefix=".khung-", delete=False) as out:
            tam = Path(out.name)
            json.dump(ds, out, ensure_ascii=False, indent=1)
            out.flush()
            os.fsync(out.fileno())
        os.replace(tam, KET_QUA)
    except BaseException:
        shutil.rmtree(phien)
        raise
    finally:
        if tam is not None:
            tam.unlink(missing_ok=True)


def xuat(tuong, tv):
    if not tuong:
        raise ValueError("Chưa đọc được thẻ nào. Giữ nguyên dữ liệu khung tướng cũ.")

    cua_toi = {}
    for x in tuong:
        if x["ten"] and x["khung"] in (0, 1):
            cua_toi[x["ten"]] = max(cua_toi.get(x["ten"], 0), x["khung"])
    dong = []
    for t, n in tv.dem.most_common():
        kb = tv.ty_le_khung[t] / n
        if t in cua_toi:
            ct = "Có khung" if cua_toi[t] else "Không khung"
            thieu = not cua_toi[t] and kb >= 0.8
        else:
            ct = "Chưa xác định khung" if any(x["ten"] == t for x in tuong) else "Không thấy"
            thieu = False
        dong.append(f"<tr{' class=thieu' if thieu else ''}><td>{html.escape(t)}</td><td class='so'>{n}</td>"
                    f"<td class='so'>{kb:.0%}</td><td>{ct}</td><td>{'Thiếu khung' if thieu else ''}</td></tr>")
    la = [x for x in tuong if not x["ten"]]
    cho = [(i, x) for i, x in enumerate(tuong, 1) if not x["ten"]]
    o_cho = ""
    for i, x in cho:
        from ten_dien_mao import giai_thich_ten
        name_note=giai_thich_ten(x.get('ten_chi_tiet'))
        refs = []
        for uv in x.get("ung_vien_ten", []):
            name = uv["ten"]
            samples = getattr(tv, "mat", {}).get(name, [])
            # Chọn mẫu gần ảnh cần xác nhận nhất, thay vì luôn dùng ảnh đầu thư viện.
            query = x["mat"]
            if uv["ty_le"] != 1:
                h, w = query.shape[:2]
                matrix = cv2.getRotationMatrix2D(((w - 1) / 2, (h - 1) / 2), 0, uv["ty_le"])
                query = cv2.warpAffine(query, matrix, (w, h), flags=cv2.INTER_LINEAR,
                                       borderMode=cv2.BORDER_REFLECT_101)
            sample = max(samples, key=lambda m: T.giong(query, m)) if samples else None
            pic = T.anh_html(sample, 64) if sample is not None else ""
            refs.append(f'<div>{pic}<br>{html.escape(name)} · {uv["diem"]:.3f}'
                        f'<br><small>gốc {uv["diem_goc"]:.3f}; tỷ lệ {uv["ty_le"]:g}</small></div>')
        o_cho += (f'<div class="o">{T.anh_html(x["the"], 120)}<br><b>Thẻ {i}: chưa xác định tên</b>'
                  + (f'<p>{html.escape(name_note)}</p>' if name_note else '')
                  + '<div style="display:flex;gap:8px;flex-wrap:wrap">' + ''.join(refs) + '</div></div>')
    o = "".join(f'<div class="o">{T.anh_html(x["the"], 120)}<br>{html.escape(x["ten"] or "?")} · '
                f'{chu_khung(x["khung"])}{" · trong đội" if x["trong_doi"] else ""}'
                f'{"<br><small>Tên đã được bạn xác nhận</small>" if x.get("ten_nguoi_dung") else ""}'
                f'<br><small>{html.escape(giai_thich_khung(x))}</small></div>'
                for x in tuong)
    chua_ro = sum(x["khung"] is None for x in tuong)
    than = (f"<h1>Khung tướng của bạn</h1><p>Đọc {len(tuong)} thẻ trong danh sách tướng, nhận ra "
            f"{len(tuong) - len(la)} tướng có trong dữ liệu Thành Tích. \"Thiếu khung\": tướng của bạn không khung trong khi "
            f"bản ghi có khung ít nhất 80% số lần.</p>"
            f"<p>{chua_ro} thẻ chưa xác định khung: không dùng để kết luận thiếu khung. "
            f"Điểm khớp sao và số phiếu mẫu viền bên dưới không phải xác suất đúng.</p>"
            f"<p>{sum(bool(x.get('ten_nguoi_dung')) for x in tuong)} tên được bạn xác nhận trực tiếp.</p>"
            f"<p>{sum(x.get('khung_nguoi_dung') is not None for x in tuong)} khung được bạn xác nhận trực tiếp.</p>"
            f"<div class='bang'><table><tr><th>Tướng</th><th>Số lần trong bản ghi</th><th>Bản ghi có khung</th>"
            f"<th>Của bạn</th><th></th></tr>{''.join(dong)}</table></div>"
            + (f"<h2>Cần xác nhận</h2><p>Ứng viên và ảnh thư viện bên cạnh chỉ để tham khảo; tướng có thể chưa có trong thư viện. "
               f"Điểm khớp không phải xác suất đúng. Xác nhận tên bằng --xac-nhan SO=TEN, ví dụ --xac-nhan 28=Damian. "
               f"Nếu xuất riêng, dùng thêm --thu-muc-ra trỏ tới thư mục của báo cáo này. "
               f"Xác nhận tên không đồng nghĩa xác nhận khung.</p><div class='luoi'>{o_cho}</div>" if cho else "")
            + f"<h2>Các thẻ đã đọc</h2><p>Kiểm tra tên và khung từng thẻ; \"?\" là tướng chưa có trong dữ liệu Thành Tích.</p>"
            f"<div class='luoi'>{o}</div>")
    trang = T.TRANG.replace("</style>", "tr.thieu td{{background:rgba(200,60,40,.15)}}</style>")
    noi_dung = trang.format(tieu_de="Khung tướng của bạn", than=than)
    luu_ket_qua(tuong)
    (THU_MUC / "tuong_cua_toi.html").write_text(noi_dung, encoding="utf-8")
    print(f"Đã ghi {KET_QUA} và {THU_MUC / 'tuong_cua_toi.html'}.")
    for t in sorted(cua_toi):
        print(f"  {t:10s} {'có khung' if cua_toi[t] else 'KHÔNG khung'}")


def main():
    global THU_MUC, ANH, KET_QUA
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--doi-hinh", action="store_true", help="Dùng bộ đọc đội hình cũ thay Hội Trường")
    ap.add_argument("--goi-y-da-ty-le", action="store_true",
                    help="Thử nhiều tỷ lệ ảnh mặt để xếp 3 ứng viên tham khảo; không tự gán tên theo điểm thử")
    ap.add_argument("--thu-muc-ra", type=Path,
                    help="Thư mục ảnh/JSON/HTML riêng khi thử nghiệm hoặc đọc lại để --xac-nhan")
    ap.add_argument("--thu-vien-mat", type=Path,
                    help="Nạp mẫu mặt bổ sung từ bo_sung_mau_tuong.py (chỉ Python)")
    ap.add_argument("--serial", help="serial thiết bị (adb devices)")
    ap.add_argument('--so-tuong-du-kien',type=int,
                    help='Số tướng duy nhất đã đối chiếu trong danh sách hiện tại, kể cả nhóm cố định; xác minh danh sách ngắn')
    ap.add_argument("--adb", default=DEFAULT_ADB)
    ap.add_argument("--anh", nargs="+", help="đọc từ ảnh chụp có sẵn thay vì chụp trên máy")
    ap.add_argument("--xac-nhan", nargs="+", metavar="SO=TEN",
                    help="xác nhận thẻ số SO (trong trang tuong_cua_toi.html) là tướng TEN, rồi gán tên lại không cần máy")
    ap.add_argument('--dien-mao',help='Mã diện mạo cho mẫu tên xác nhận, ví dụ pham-thap; giữ các diện mạo đã có')
    ap.add_argument("--khung", nargs="*", metavar="TEN=1|0|-1",
                    help="in khung các tướng quan trọng; kèm TEN=GIÁ_TRỊ thì đánh dấu (1 có khung, 0 không, -1 chưa có)")
    a = ap.parse_args()
    if a.dien_mao and (not a.xac_nhan or not a.dien_mao.strip() or any(c in a.dien_mao for c in '/\\\x00')):
        ap.error('--dien-mao cần dùng cùng --xac-nhan và mã diện mạo hợp lệ')
    if a.thu_muc_ra is not None:
        if a.khung is not None:
            ap.error("--khung dùng dữ liệu tài khoản, không dùng cùng --thu-muc-ra")
        THU_MUC = a.thu_muc_ra.resolve()
        ANH, KET_QUA = THU_MUC / "tuong_cua_toi", THU_MUC / "tuong_cua_toi.json"
    if a.khung is not None:
        khung_tay(a.khung)
        return
    if a.xac_nhan:
        ds = json.loads(KET_QUA.read_text(encoding="utf-8"))
        from quan_ly_mau import KhoMau, sha, pixel_sha
        repo = KhoMau(BASE/'thu_thap_tuong'/'kho_mau')
        managed = (MAT_XAC_NHAN.resolve()==(BASE/'thu_thap_tuong'/'mat_xac_nhan').resolve() and repo.hien_tai() is not None)
        assignments=[]
        for xn in a.xac_nhan:
            so,ten=xn.split('=',1);so=int(so);ten=ten.strip()
            if not 1<=so<=len(ds) or not ten or any(c in ten for c in '/\\~\x00'):
                raise ValueError('Số thẻ/tên xác nhận không hợp lệ')
            if so in {n for n,_ in assignments}:raise ValueError('Số thẻ xác nhận bị trùng')
            assignments.append((so,ten))
        MAT_XAC_NHAN.mkdir(parents=True, exist_ok=True)
        tay = doc_khung_tay()
        vien, nhan = ([], []) if managed or not VIEN_THEM.exists() else map(list, (np.load(VIEN_THEM)[k] for k in ("vien", "nhan")))
        for so,ten in assignments:
            source_path=THU_MUC/ds[so-1]['anh']
            the = cv2.imread(str(source_path))
            face = cv2.imread(str(THU_MUC/ds[so-1]['mat'])) if ds[so-1].get('mat') else mat(the)
            if managed:
                sid=repo.them(face,'face',ten,dict(session='cli_'+sha(KET_QUA.read_bytes())[:16],label_source='user_confirmed',
                    source_sha256=sha(source_path.read_bytes()),hero_id=so,group='face:'+ten,
                    appearance_id=a.dien_mao or 'chua_phan_loai'))
                print(f'Mẫu {sid} đã vào hàng chờ duyệt; cần phát hành/kích hoạt bản mới để bộ đọc dùng mẫu này.')
            cv2.imwrite(str(MAT_XAC_NHAN / f"{ten}~{pixel_sha(face)[:16]}.png"), face)
            if not managed and not ds[so - 1]["trong_doi"] and tay.get(ten) in (0, 1):
                # Xác nhận tên không đồng nghĩa đã xác nhận khung.
                k = tay[ten]
                vien.append(T.dac_trung_vien(the).astype("<f4"))
                nhan.append(1 if k == 1 else 0)
            print(f"Đã lưu mặt thẻ {so} là {ten}.")
        if vien:
            np.savez(VIEN_THEM, vien=np.array(vien, dtype="<f4"), nhan=np.array(nhan, dtype=np.uint8))
        tv = ThuVien(a.thu_vien_mat)
        tuong = []
        for x in ds:
            the = cv2.imread(str(THU_MUC / x["anh"]))
            face = cv2.imread(str(THU_MUC/x['mat'])) if x.get('mat') else mat(the)
            tuong.append(dict(khung=x["khung"], trong_doi=x["trong_doi"], the=the, mat=face,
                              diem=x.get('diem',0),ten_nguoi_dung=x.get('ten_nguoi_dung'),
                              khung_nguoi_dung=x.get('khung_nguoi_dung'),khung_tu_doc=x.get('khung_tu_doc'),
                              khung_chi_tiet=x.get("khung_chi_tiet", []),chat_luong_cat=x.get('chat_luong_cat')))
        resolved=gan_ten(tuong,tv)
        for so,ten in assignments:
            resolved[so-1].update(ten=ten,goi_y=None,
                ten_nguoi_dung=dict(so_the=so,ten=ten,nguon_nhan='nguoi_dung_xac_nhan_ten',dien_mao=a.dien_mao),
                ten_chi_tiet=dict(trang_thai='nguoi_dung_xac_nhan',ly_do='ten_duoc_xac_nhan_truc_tiep',dien_mao=a.dien_mao))
        xuat(resolved, tv)
        return
    tv = ThuVien(a.thu_vien_mat)
    if a.anh:
        anh = [cv2.imread(p) for p in a.anh]
    else:
        adb = Adb(a.adb, a.serial)
        if not adb.connected():
            sys.exit("Không thấy máy qua ADB.")
        nd = NhanDien()
        if a.doi_hinh:
            anh = chup_danh_sach(adb, nd, DocThanhTich(nd))
        else:
            from hoi_truong import chup_hoi_truong
            proof={}
            anh = chup_hoi_truong(adb, nd,so_tuong_du_kien=a.so_tuong_du_kien,bang_chung_phien=proof)
            from quan_ly_mau import ghi_json
            ghi_json(THU_MUC/'xac_minh_phien.json',proof)
    cards=doc(anh,tv,hoi_truong=not a.doi_hinh,goi_y_da_ty_le=a.goi_y_da_ty_le)
    if a.so_tuong_du_kien is not None and len(cards)!=a.so_tuong_du_kien:
        raise RuntimeError(f'Sau gộp có {len(cards)} thẻ, khác {a.so_tuong_du_kien} tướng nguồn; giữ dữ liệu cũ')
    xuat(cards,tv)


if __name__ == "__main__":
    main()
