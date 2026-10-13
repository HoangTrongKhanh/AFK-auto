#!/usr/bin/env python3
"""Đọc khung (phẩm) các tướng của bạn ở danh sách tướng trong màn đội hình, để so với khung của tướng trong bản ghi
Thành Tích (thong_ke_tuong.py). Thẻ có khung là phẩm chuẩn, thẻ không khung là phẩm thấp so với bản ghi.

Bot mở màn đội hình (bấm Chiến Đấu ở Màn AFK, chưa đánh), chụp danh sách tướng, vuốt xuống tới hết danh sách. Vuốt ở khe
giữa 2 cột thẻ để không kéo nhầm tướng vào đội, và so lực chiến đội trước / sau mỗi lần vuốt: đổi là dừng ngay.

Tướng được nhận ra bằng cách so ảnh mặt với các nhóm tướng đã đặt tên của dữ liệu Thành Tích. Thẻ của tướng đang trong
đội bị game phủ màu xanh và dấu tích nên khớp kém hơn: chỉ nhận khi hơn hẳn tướng đứng thứ 2.

    .venv/bin/python doc_tuong_cua_toi.py --serial R52N90Q08XR       # đọc trên máy rồi xuất trang so sánh
    .venv/bin/python doc_tuong_cua_toi.py --anh samples/tab_s7_doi_hinh_man_afk.png   # thử trên ảnh có sẵn
"""
import argparse
import html
import json
import sys
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
    out = []
    for ha, hb in hang:
        for ca, cb in cot:
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

    def __init__(self):
        js = json.loads((THU_VIEN / "tuong.json").read_text(encoding="utf-8"))
        o = T.CO_SO[0] + 2 * T.LE
        self.mat, self.dem, self.ty_le_khung = {}, Counter(), Counter()
        for tn, x in js["tuong"].items():
            tam = cv2.imread(str(THU_VIEN / f"{tn}.png"))
            self.mat[tn] = [tam[:, i * o:(i + 1) * o] for i in range(x["so_mat"])]
            self.dem[tn] = x["so_lan"]
            self.ty_le_khung[tn] = x["co_khung"] * x["so_lan"]
        # Mặt đã xác nhận lấy từ chính danh sách của bạn (--xac-nhan): lần sau khớp gần như tuyệt đối.
        for f in sorted(MAT_XAC_NHAN.glob("*.png")) if MAT_XAC_NHAN.exists() else []:
            self.mat.setdefault(f.stem.split("~")[0], []).insert(0, cv2.imread(str(f)))
        v = js["vien"]
        self.vien = np.fromfile(THU_VIEN / "vien.bin", dtype="<f4").reshape(v["so"], v["chieu"])
        self.nhan_khung = np.fromfile(THU_VIEN / "vien_nhan.bin", dtype=np.uint8).astype(int)
        self.mau_sao = [cv2.imread(str(TPL_DIR / t), cv2.IMREAD_GRAYSCALE) for t in T.MAU_SAO]

    def khung(self, the):
        d = T.diem_sao(the, self.mau_sao)
        if d < T.SAO_KHONG:
            return 0
        if d >= T.SAO_CO:
            return 1
        gan = np.argsort(((self.vien - T.dac_trung_vien(the)) ** 2).sum(axis=1))[:7]
        return int(self.nhan_khung[gan].mean() >= 0.5)

    def diem(self, m):
        """Điểm khớp cao nhất với từng tướng, giảm dần: list (điểm, tên)."""
        return sorted(((max(T.giong(m, x) for x in v), t) for t, v in self.mat.items()), reverse=True)


def gan_ten(tuong, tv):
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
    cap = sorted(((d, i, t) for i, x in enumerate(tuong) if not x["trong_doi"] for d, t in x["ds_diem"] if d >= GOI_Y),
                 reverse=True)
    for d, i, t in cap:
        x = tuong[i]
        if x["ten"] or t in da:
            continue
        if d >= NHAN_TUONG:
            x["ten"] = t
            da.add(t)
        elif x["goi_y"] is None:
            x["goi_y"], x["diem"] = t, round(d, 2)
    for x in tuong:
        if x["ten"]:
            x["goi_y"] = None
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
            if x.get("ten"):
                self.cua_toi[x["ten"]] = max(self.cua_toi.get(x["ten"], 0), x["khung"])
            if not x["trong_doi"]:
                self.mat_cua_toi.append((mat(cv2.imread(str(THU_MUC / x["anh"]))), x["khung"]))

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
            if not self.tv.khung(t):
                continue
            m = cv2.resize(m, (T.CO_SO[0] + 2 * T.LE, T.CO_SO[1] + 2 * T.LE), interpolation=cv2.INTER_AREA)
            ten, k = self.khung_cua_toi(m)
            if ten and self.tv.dem[ten] and self.tv.ty_le_khung[ten] / self.tv.dem[ten] < KHUNG_CAN:
                continue                # tướng này bản ghi thường dùng không khung: thiếu khung không sao
            if k == 0:
                out.append(ten or "?")
        return out


_doc_dai = None


def DocThanhTich_dai(img):
    """Dải thẻ tướng của đội đang hiện trong Thành Tích (thanh_tich.DocThanhTich.dai_tuong)."""
    global _doc_dai
    if _doc_dai is None:
        _doc_dai = DocThanhTich()
    return _doc_dai.dai_tuong(img)


def doc(anh_list, tv):
    """Đọc các ảnh chụp danh sách (theo thứ tự vuốt), bỏ thẻ trùng giữa các lần chụp."""
    tuong, cot = [], None
    for img in anh_list:
        ds, c = cat_the(img, cot)
        cot = cot or c
        for the, _ in ds:
            m = mat(the)
            if any(T.giong(m, x["mat"]) >= CUNG_THE for x in tuong):
                continue
            tuong.append(dict(khung=tv.khung(the), trong_doi=trong_doi(the), the=the, mat=m))
    return gan_ten(tuong, tv)


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


def xuat(tuong, tv):
    ANH.mkdir(parents=True, exist_ok=True)
    for f in ANH.glob("*.png"):
        f.unlink()
    ds = []
    for i, x in enumerate(tuong, 1):
        cv2.imwrite(str(ANH / f"{i:02d}.png"), x["the"])
        ds.append(dict(anh=f"tuong_cua_toi/{i:02d}.png", ten=x["ten"], goi_y=x["goi_y"], khung=x["khung"],
                       trong_doi=x["trong_doi"], diem=x["diem"]))
    KET_QUA.write_text(json.dumps(ds, ensure_ascii=False, indent=1), encoding="utf-8")

    cua_toi = {}
    for x in tuong:
        if x["ten"]:
            cua_toi[x["ten"]] = max(cua_toi.get(x["ten"], 0), x["khung"])
    dong = []
    for t, n in tv.dem.most_common():
        kb = tv.ty_le_khung[t] / n
        if t in cua_toi:
            ct = "Có khung" if cua_toi[t] else "Không khung"
            thieu = not cua_toi[t] and kb >= 0.8
        else:
            ct, thieu = "Không thấy", False
        dong.append(f"<tr{' class=thieu' if thieu else ''}><td>{html.escape(t)}</td><td class='so'>{n}</td>"
                    f"<td class='so'>{kb:.0%}</td><td>{ct}</td><td>{'Thiếu khung' if thieu else ''}</td></tr>")
    la = [x for x in tuong if not x["ten"]]
    cho = [(i, x) for i, x in enumerate(tuong, 1) if x["goi_y"]]
    o_cho = "".join(f'<div class="o">{T.anh_html(x["the"], 120)}<br>Thẻ {i}: giống {html.escape(x["goi_y"])} '
                    f'({x["diem"]})?</div>' for i, x in cho)
    o = "".join(f'<div class="o">{T.anh_html(x["the"], 120)}<br>{html.escape(x["ten"] or "?")} · '
                f'{"có khung" if x["khung"] else "không khung"}{" · trong đội" if x["trong_doi"] else ""}</div>'
                for x in tuong)
    than = (f"<h1>Khung tướng của bạn</h1><p>Đọc {len(tuong)} thẻ trong danh sách tướng, nhận ra "
            f"{len(tuong) - len(la)} tướng có trong dữ liệu Thành Tích. \"Thiếu khung\": tướng của bạn không khung trong khi "
            f"bản ghi có khung ít nhất 80% số lần.</p>"
            f"<div class='bang'><table><tr><th>Tướng</th><th>Số lần trong bản ghi</th><th>Bản ghi có khung</th>"
            f"<th>Của bạn</th><th></th></tr>{''.join(dong)}</table></div>"
            + (f"<h2>Cần xác nhận</h2><p>Các thẻ này hơi giống một tướng trong bản ghi nhưng chưa đủ chắc. Nếu đúng, "
               f"báo lại số thẻ và tên (ví dụ \"thẻ 28 là Damian\").</p><div class='luoi'>{o_cho}</div>" if cho else "")
            + f"<h2>Các thẻ đã đọc</h2><p>Kiểm tra tên và khung từng thẻ; \"?\" là tướng chưa có trong dữ liệu Thành Tích.</p>"
            f"<div class='luoi'>{o}</div>")
    trang = T.TRANG.replace("</style>", "tr.thieu td{{background:rgba(200,60,40,.15)}}</style>")
    (THU_MUC / "tuong_cua_toi.html").write_text(trang.format(tieu_de="Khung tướng của bạn", than=than),
                                                encoding="utf-8")
    print(f"Đã ghi {KET_QUA.relative_to(BASE)} và thu_thap_tuong/tuong_cua_toi.html.")
    for t in sorted(cua_toi):
        print(f"  {t:10s} {'có khung' if cua_toi[t] else 'KHÔNG khung'}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--serial", help="serial thiết bị (adb devices)")
    ap.add_argument("--adb", default=DEFAULT_ADB)
    ap.add_argument("--anh", nargs="+", help="đọc từ ảnh chụp có sẵn thay vì chụp trên máy")
    ap.add_argument("--xac-nhan", nargs="+", metavar="SO=TEN",
                    help="xác nhận thẻ số SO (trong trang tuong_cua_toi.html) là tướng TEN, rồi gán tên lại không cần máy")
    a = ap.parse_args()
    if a.xac_nhan:
        ds = json.loads(KET_QUA.read_text(encoding="utf-8"))
        MAT_XAC_NHAN.mkdir(parents=True, exist_ok=True)
        for xn in a.xac_nhan:
            so, ten = xn.split("=", 1)
            the = cv2.imread(str(THU_MUC / ds[int(so) - 1]["anh"]))
            cv2.imwrite(str(MAT_XAC_NHAN / f"{ten}~{int(time.time())}.png"), mat(the))
            print(f"Đã lưu mặt thẻ {so} là {ten}.")
        tv = ThuVien()
        tuong = []
        for x in ds:
            the = cv2.imread(str(THU_MUC / x["anh"]))
            tuong.append(dict(khung=x["khung"], trong_doi=x["trong_doi"], the=the, mat=mat(the)))
        xuat(gan_ten(tuong, tv), tv)
        return
    tv = ThuVien()
    if a.anh:
        anh = [cv2.imread(p) for p in a.anh]
    else:
        adb = Adb(a.adb, a.serial)
        if not adb.connected():
            sys.exit("Không thấy máy qua ADB.")
        nd = NhanDien()
        anh = chup_danh_sach(adb, nd, DocThanhTich(nd))
    xuat(doc(anh, tv), tv)


if __name__ == "__main__":
    main()
