#!/usr/bin/env python3
"""Thống kê tướng trong các bản ghi Thành Tích đã thu bằng `leo_ai.py --thu-thap-tuong`.

Bước 1 - gom nhóm: tách 5 thẻ tướng của mỗi bản ghi, gom các thẻ cùng một tướng thành nhóm (so ảnh mặt tướng, bỏ sao,
khung và cấp vì chúng đổi theo phẩm tướng của từng người), rồi xuất trang nhom.html: mỗi nhóm một ảnh để đặt tên.
    .venv/bin/python thong_ke_tuong.py gom

Bước 2 - đặt tên: điền tên tướng cho từng nhóm trong thu_thap_tuong/ten_tuong.json ({"1": "Tên", ...}). Các nhóm cùng
một tướng (ví dụ khác trang phục) thì đặt trùng tên là được gộp.

Bước 3 - thống kê: ghi thu_thap_tuong/tuong.csv (mỗi bản ghi một dòng, đủ 5 tướng) và trang thong_ke.html.
    .venv/bin/python thong_ke_tuong.py thong-ke
"""
import argparse
import base64
import csv
import html
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import cv2
import numpy as np

from nhan_dien import TPL_DIR

BASE = Path(__file__).resolve().parent
THU_MUC = BASE / "thu_thap_tuong"
BAN_GHI = THU_MUC / "ban_ghi.csv"
NHOM = THU_MUC / "nhom.json"
KHUNG = THU_MUC / "khung.json"
TEN = THU_MUC / "ten_tuong.json"

# Toạ độ trong ảnh dải tướng (thanh_tich.DAI_TUONG, 1100 x 205 theo máy gốc). Đo trên 20 ảnh mẫu: thẻ cách đều BUOC px,
# tâm thẻ cuối cách mép phải của phần không phải nền kem TAM_CUOI px (thẻ có cánh vương miện rộng hơn vài px).
BUOC = 130
TAM_CUOI = 61
SO_TUONG = 5
MAT_Y = (55, 140)           # phần mặt: dưới hàng sao, trên dòng "Cấp 600"
MAT_RONG = 44               # nửa bề rộng phần mặt (thẻ rộng ~116)
LE = 4                      # độ lệch cho phép khi so 2 mặt
CO_SO = (40, 40)            # kích thước chuẩn hoá phần mặt (sau khi cắt bớt LE mỗi bên)
# Khung thẻ (phẩm tướng): thẻ có khung luôn có hàng sao ở mép trên, thẻ không khung (phẩm thấp) thì không. Điểm khớp mẫu
# ngôi sao (2 mẫu: sao trên khung cam và sao trên khung mảnh màu nhạt) < SAO_KHONG thì chắc chắn không khung, >= SAO_CO
# thì chắc chắn có khung (kiểm tra bằng mắt trên 2100 thẻ); ở giữa thì so viền thẻ với các thẻ đã chắc chắn (k láng giềng).
SAO_KHONG, SAO_CO = 0.62, 0.75
MAU_SAO = ["sao_khung_cam.png", "sao_khung_mong.png"]
GIONG = 0.85                # 2 mặt khớp >= mức này coi là cùng tướng (thà tách thừa: đặt trùng tên là gộp lại được)


def nen_kem(dai):
    """Mặt nạ các điểm màu kem của nền bảng."""
    hsv = cv2.cvtColor(dai, cv2.COLOR_BGR2HSV)
    return (hsv[..., 1] < 60) & (hsv[..., 2] > 200)


def tach_the(dai):
    """Danh sách (ảnh mặt, ảnh cả thẻ) của 5 thẻ tướng, trái sang phải; None nếu không tìm được."""
    if dai is None or dai.size == 0:
        return None
    co_the = nen_kem(dai)[40:170].mean(axis=0) <= 0.85
    xs = np.nonzero(co_the)[0]
    if len(xs) == 0:
        return None
    cuoi = xs.max() + 1 - TAM_CUOI
    out = []
    for i in range(SO_TUONG - 1, -1, -1):
        c = cuoi - i * BUOC
        if c - MAT_RONG < 0 or co_the[c - 40:c + 40].mean() < 0.9:
            return None
        out.append((dai[MAT_Y[0]:MAT_Y[1], c - MAT_RONG:c + MAT_RONG], dai[:, max(0, c - BUOC // 2):c + BUOC // 2]))
    return out


def diem_sao(the, mau_sao):
    """Điểm khớp cao nhất của mẫu ngôi sao trong phần trên thẻ."""
    g = cv2.cvtColor(the[5:70], cv2.COLOR_BGR2GRAY)
    return max(float(cv2.matchTemplate(g, m, cv2.TM_CCOEFF_NORMED).max()) for m in mau_sao)


def dac_trung_vien(the):
    """Đặc trưng viền thẻ (độ bão hoà và độ sáng của mép trên, mép trái, mép phải), bỏ phần mặt tướng ở giữa."""
    hsv = cv2.cvtColor(the, cv2.COLOR_BGR2HSV).astype(np.float32)
    phan = []
    for kenh in (1, 2):
        x = hsv[..., kenh]
        phan += [cv2.resize(x[5:60], (26, 11)).ravel(), cv2.resize(x[40:195, 0:14], (4, 20)).ravel(),
                 cv2.resize(x[40:195, -14:], (4, 20)).ravel()]
    f = np.concatenate(phan)
    return (f - f.mean()) / (f.std() + 1e-6)


def phan_loai_khung(thes):
    """1 = thẻ có khung, 0 = không khung, cho từng thẻ. Thẻ ở vùng lẫn theo điểm sao được xếp theo 7 thẻ chắc chắn có viền
    giống nhất (kiểm tra chéo trên tập chắc chắn: 0/300 sai; vùng lẫn sai khoảng 2%, chủ yếu thẻ khung mảnh 3 sao)."""
    mau_sao = [cv2.imread(str(TPL_DIR / t), cv2.IMREAD_GRAYSCALE) for t in MAU_SAO]
    diem = np.array([diem_sao(t, mau_sao) for t in thes])
    nhan = np.where(diem < SAO_KHONG, 0, np.where(diem >= SAO_CO, 1, -1))
    chac = np.nonzero(nhan >= 0)[0]
    lan = np.nonzero(nhan < 0)[0]
    if len(lan) and len(chac):
        F = np.array([dac_trung_vien(t) for t in thes])
        for i in lan:
            gan = chac[np.argsort(((F[chac] - F[i]) ** 2).sum(axis=1))[:7]]
            nhan[i] = int(nhan[gan].mean() >= 0.5)
    return nhan


def giong(a, b):
    """Mức khớp (0-1) của 2 ảnh mặt: phần giữa của ảnh này trượt trong ảnh kia (lệch tối đa LE px), lấy chiều thấp hơn."""
    def mot_chieu(x, y):
        return float(cv2.matchTemplate(x, y[LE:-LE, LE:-LE], cv2.TM_CCOEFF_NORMED).max())
    return min(mot_chieu(a, b), mot_chieu(b, a))


def gom(mats, cu=None):
    """Gom ảnh mặt thành nhóm: mỗi ảnh vào nhóm có thành viên khớp nhất (>= GIONG), không có thì lập nhóm mới.
    `cu`: chỉ số nhóm đã gán từ lần gom trước (None = ảnh mới) để giữ nguyên số nhóm và tên đã đặt; chỉ ảnh mới được
    gom. Trả về list chỉ số nhóm theo thứ tự ảnh."""
    cu = cu or [None] * len(mats)
    so_nhom = max((c for c in cu if c is not None), default=-1) + 1
    thanh_vien = [[] for _ in range(so_nhom)]
    for m, c in zip(mats, cu):
        if c is not None and len(thanh_vien[c]) < 8:
            thanh_vien[c].append(m)
    nhom = []
    for m, c in zip(mats, cu):
        if c is not None:
            nhom.append(c)
            continue
        tot, diem = None, GIONG
        for j, tv in enumerate(thanh_vien):
            if not tv:
                continue
            s = max(giong(m, x) for x in tv[:8])
            if s >= diem:
                tot, diem = j, s
        if tot is None:
            thanh_vien.append([m])
            tot = len(thanh_vien) - 1
        elif len(thanh_vien[tot]) < 8:
            thanh_vien[tot].append(m)
        nhom.append(tot)
    return nhom


def doc_ban_ghi():
    if not BAN_GHI.exists():
        sys.exit(f"Chưa có {BAN_GHI.relative_to(THU_MUC.parent)}: chạy leo_ai.py --thu-thap-tuong trước.")
    with BAN_GHI.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def anh_html(img, cao=64):
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return f'<img src="data:image/jpeg;base64,{base64.b64encode(buf).decode()}" height="{cao}">'


TRANG = """<!doctype html><html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{tieu_de}</title><style>
:root{{--nen:#faf7f0;--chu:#2b2620;--phu:#6d655a;--vien:#e2dacb;--the:#fff}}
@media (prefers-color-scheme:dark){{:root{{--nen:#1c1a17;--chu:#eee8dc;--phu:#a89f91;--vien:#3a352e;--the:#26231f}}}}
body{{margin:0;padding:16px;background:var(--nen);color:var(--chu);font:15px/1.45 system-ui,sans-serif}}
h1{{font-size:20px;margin:0 0 4px}} h2{{font-size:16px;margin:24px 0 8px}} p{{color:var(--phu);margin:4px 0 12px}}
.luoi{{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px}}
.o{{background:var(--the);border:1px solid var(--vien);border-radius:10px;padding:8px}}
.o b{{font-size:18px}} img{{border-radius:6px;margin:2px}}
table{{border-collapse:collapse;width:100%;max-width:900px}} td,th{{border-bottom:1px solid var(--vien);padding:6px 8px;
text-align:left;vertical-align:middle}} th{{color:var(--phu);font-weight:600}} td.so{{text-align:right;font-variant-numeric:tabular-nums}}
.thanh{{height:10px;background:#c9853a;border-radius:5px}} .bang{{overflow-x:auto}}
input,textarea{{width:100%;box-sizing:border-box;margin-top:6px;padding:6px 8px;font:inherit;color:var(--chu);
background:var(--nen);border:1px solid var(--vien);border-radius:6px}} button{{font:inherit;padding:8px 14px;
border-radius:8px;border:1px solid var(--vien);background:#c9853a;color:#fff;cursor:pointer}}
</style></head><body>{than}</body></html>"""


def lenh_gom(_a):
    rows = doc_ban_ghi()
    mats, thes, nguon, loi = [], [], [], 0
    for r in rows:
        dai = cv2.imread(str(THU_MUC / r["anh"])) if r["anh"] else None
        the = tach_the(dai)
        if the is None:
            loi += 1
            print(f"  Không tách được thẻ tướng: {r['anh'] or r['luot'] + ' #' + r['vi_tri']}")
            continue
        for i, (m, t) in enumerate(the):
            thes.append(t)
            mats.append(cv2.resize(m, (CO_SO[0] + 2 * LE, CO_SO[1] + 2 * LE), interpolation=cv2.INTER_AREA))
            nguon.append((r["luot"], r["vi_tri"], i))
    # Giữ số nhóm của lần gom trước (tên đã đặt theo số nhóm), chỉ gom các thẻ mới thu thêm.
    cu = json.loads(NHOM.read_text(encoding="utf-8")) if NHOM.exists() else {}
    khoa = [f"{l}|{v}|{i}" for l, v, i in nguon]
    nhom = gom(mats, [cu[k] - 1 if k in cu else None for k in khoa])
    moi = sum(k not in cu for k in khoa)
    khung = phan_loai_khung(thes)
    KHUNG.write_text(json.dumps({k: int(x) for k, x in zip(khoa, khung)}, indent=0), encoding="utf-8")
    print(f"  Khung thẻ: {int(khung.sum())} có khung, {int((khung == 0).sum())} không khung.")
    print(f"  {len(khoa) - moi} thẻ giữ nhóm cũ, {moi} thẻ mới.")
    NHOM.write_text(json.dumps({f"{l}|{v}|{i}": n + 1 for (l, v, i), n in zip(nguon, nhom)}, indent=0),
                    encoding="utf-8")
    dem = Counter(nhom)
    ten = json.loads(TEN.read_text(encoding="utf-8")) if TEN.exists() else {}
    for j in range(max(dem) + 1):
        ten.setdefault(str(j + 1), "")
    TEN.write_text(json.dumps(ten, ensure_ascii=False, indent=1), encoding="utf-8")
    dau = {j: next(i for i, x in enumerate(nhom) if x == j) for j in dem}
    co_ten = [j for j in dem if ten.get(str(j + 1))]
    o = []
    # Nhóm chưa có tên lên đầu, kèm gợi ý tướng đã đặt tên giống nhất (thường là cùng tướng khác trang phục / phẩm).
    for j, n in sorted(dem.items(), key=lambda x: (bool(ten.get(str(x[0] + 1))), -x[1])):
        cac = [i for i, x in enumerate(nhom) if x == j]
        goi_y = "Tên tướng"
        if not ten.get(str(j + 1)) and co_ten:
            s, k = max((giong(mats[cac[0]], mats[dau[k]]), k) for k in co_ten)
            if s >= 0.6:
                goi_y = f"Giống {ten[str(k + 1)]}?"
        # Thẻ đầu to để dễ nhận ra tướng, thêm vài mặt rải đều trong nhóm để kiểm tra nhóm không lẫn tướng khác.
        rai = [cac[k * len(cac) // 6] for k in range(1, 6)] if len(cac) > 6 else cac[1:]
        o.append(f'<div class="o"><b>{j + 1}</b> · {n} thẻ<br>{anh_html(thes[cac[0]], 150)}<br>'
                 + "".join(anh_html(mats[i], 40) for i in rai)
                 + f'<input data-n="{j + 1}" value="{html.escape(ten.get(str(j + 1), ""))}" placeholder="{html.escape(goi_y)}">'
                 + "</div>")
    than = (f"<h1>Đặt tên tướng</h1><p>{len(rows)} bản ghi, {len(mats)} thẻ tướng, {len(dem)} nhóm"
            f"{f', {loi} bản ghi không tách được' if loi else ''}. Gõ tên tướng vào ô dưới mỗi nhóm. Một tướng có thể bị "
            f"tách thành 2-3 nhóm (khác trang phục, có khăn...): đặt trùng tên là được gộp. Nếu thấy một nhóm lẫn tướng "
            f"khác nhau thì ghi chú vào tên. Xong bấm nút dưới cùng rồi dán kết quả cho Claude.</p>"
            f'<div class="luoi">{"".join(o)}</div>'
            '<p><button id="chep">Sao chép danh sách tên</button> <span id="bao"></span></p>'
            '<textarea id="kq" rows="6" readonly></textarea>'
            """<script>
const o = [...document.querySelectorAll('input[data-n]')];
try { const l = JSON.parse(localStorage.getItem('ten_tuong') || '{}');
      o.forEach(e => { if (!e.value && l[e.dataset.n]) e.value = l[e.dataset.n]; }); } catch (e) {}
function kq() { const t = {}; o.forEach(e => t[e.dataset.n] = e.value.trim());
  try { localStorage.setItem('ten_tuong', JSON.stringify(t)); } catch (e) {}
  return JSON.stringify(t, null, 1); }
o.forEach(e => e.addEventListener('input', kq));
document.getElementById('chep').onclick = async () => {
  const s = kq(), k = document.getElementById('kq'); k.value = s;
  try { await navigator.clipboard.writeText(s); document.getElementById('bao').textContent = 'Đã sao chép.'; }
  catch (e) { k.select(); document.getElementById('bao').textContent = 'Hãy tự sao chép ô bên dưới.'; } };
</script>""")
    (THU_MUC / "nhom.html").write_text(TRANG.format(tieu_de="Nhóm tướng", than=than), encoding="utf-8")
    print(f"{len(rows)} bản ghi, {len(mats)} thẻ, {len(dem)} nhóm. Xem {(THU_MUC / 'nhom.html').relative_to(THU_MUC.parent)}, "
          f"đặt tên trong {TEN.relative_to(THU_MUC.parent)}.")


def lenh_thong_ke(_a):
    rows = doc_ban_ghi()
    if not NHOM.exists():
        sys.exit("Chưa gom nhóm: chạy 'thong_ke_tuong.py gom' trước.")
    nhom = json.loads(NHOM.read_text(encoding="utf-8"))
    ten = json.loads(TEN.read_text(encoding="utf-8")) if TEN.exists() else {}

    def ten_nhom(n):
        return ten.get(str(n)) or f"Nhóm {n}"

    khung = json.loads(KHUNG.read_text(encoding="utf-8")) if KHUNG.exists() else {}
    doi = []
    for r in rows:
        ds = [nhom.get(f"{r['luot']}|{r['vi_tri']}|{i}") for i in range(SO_TUONG)]
        if None in ds:
            continue
        doi.append(dict(r, tuong=[ten_nhom(n) for n in ds],
                        khung=[khung.get(f"{r['luot']}|{r['vi_tri']}|{i}", "") for i in range(SO_TUONG)]))
    with (THU_MUC / "tuong.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["che_do", "ai", "luot", "vi_tri", "luc_chien", "nhan", "ly_tuong", "thu_cong"]
                   + [f"tuong_{i + 1}" for i in range(SO_TUONG)] + [f"khung_{i + 1}" for i in range(SO_TUONG)])
        for d in doi:
            w.writerow([d["che_do"], d["ai"], d["luot"], d["vi_tri"], d["luc_chien"], d["nhan"], d["ly_tuong"],
                        d["thu_cong"]] + d["tuong"] + d["khung"])

    # Một bảng chung cho cả 2 chế độ (Huyền Linh có nhiều lượt hơn nên chiếm phần lớn số bản ghi), kèm cột tỉ lệ riêng
    # từng chế độ để so sánh.
    CHE_DO = (("afk", "Màn AFK"), ("huyen_linh", "Huyền Linh"))
    theo = {c: [d for d in doi if d["che_do"] == c] for c, _ in CHE_DO}
    dem = Counter(t for d in doi for t in set(d["tuong"]))
    dem_cd = {c: Counter(t for d in ds for t in set(d["tuong"])) for c, ds in theo.items()}
    dau = Counter(t for d in doi if d["vi_tri"] == "1" for t in set(d["tuong"]))
    so_dau = sum(1 for d in doi if d["vi_tri"] == "1")
    # Đội bot chép được: không Chiến Đấu Thủ Công, không Cực Hạn (tỉ lệ thành công thấp).
    chep = [d for d in doi if d["thu_cong"] == "0" and d["nhan"] != "cuc_han"]
    dem_chep = Counter(t for d in chep for t in set(d["tuong"]))
    # Khung thẻ (phẩm) của từng tướng trong bản ghi: thẻ có khung là phẩm chuẩn, không khung là phẩm thấp.
    co_khung, co_khung_dau = Counter(), Counter()
    for d in doi:
        for t, k in zip(d["tuong"], d["khung"]):
            if k == 1:
                co_khung[t] += 1
                co_khung_dau[t] += d["vi_tri"] == "1"

    def ty_le(n, tong):
        return f"{n / tong:.0%}" if tong else "-"

    dong = []
    for t, n in dem.most_common():
        dong.append(f"<tr><td>{html.escape(t)}</td><td class='so'>{n}</td><td class='so'>{ty_le(n, len(doi))}</td>"
                    f"<td style='width:22%'><div class='thanh' style='width:{n / len(doi) * 100:.0f}%'></div></td>"
                    + "".join(f"<td class='so'>{ty_le(dem_cd[c][t], len(theo[c]))}</td>" for c, _ in CHE_DO)
                    + f"<td class='so'>{dau[t]}/{so_dau}</td><td class='so'>{ty_le(dem_chep[t], len(chep))}</td>"
                    f"<td class='so'>{ty_le(co_khung[t], n)}</td>"
                    f"<td class='so'>{ty_le(co_khung_dau[t], dau[t])}</td></tr>")
    bo = Counter(tuple(sorted(d["tuong"])) for d in doi)
    bo_cd = {c: Counter(tuple(sorted(d["tuong"])) for d in ds) for c, ds in theo.items()}
    dong_bo = "".join(f"<tr><td>{html.escape(', '.join(x))}</td><td class='so'>{n}</td>"
                      + "".join(f"<td class='so'>{bo_cd[c][x]}</td>" for c, _ in CHE_DO) + "</tr>"
                      for x, n in bo.most_common(15))
    mo_ta = []
    for c, ten_cd in CHE_DO:
        ds = theo[c]
        if ds:
            ais = sorted({int(d["ai"]) for d in ds if d["ai"]})
            mo_ta.append(f"{ten_cd} {len(ds)} bản ghi trong {len({d['luot'] for d in ds})} lượt, ải "
                         f"{ais[0] if ais else '?'}–{ais[-1] if ais else '?'}")
    the_cd = "".join(f"<th>{ten_cd}</th>" for _, ten_cd in CHE_DO)
    than = (f"<h1>Thống kê tướng trong Thành Tích</h1><p>{len(doi)} bản ghi của cả 2 chế độ ({'; '.join(mo_ta)}). "
            f"Ô lọc tắt khi thu thập nên gồm cả đội có tướng chưa sở hữu, đội Chiến Đấu Thủ Công và Cực Hạn. Mỗi tướng "
            f"chỉ đếm 1 lần trong một bản ghi. Đội chép được: không Thủ Công, không Cực Hạn. "
            f"Có khung: tỉ lệ lần tướng xuất hiện với thẻ có khung (phẩm chuẩn); thẻ không khung là phẩm thấp.</p>"
            f"<div class='bang'><table><tr><th>Tướng</th><th>Số bản ghi</th><th>Tỉ lệ</th><th></th>{the_cd}"
            f"<th>Ở bản ghi đầu</th><th>Trong {len(chep)} đội chép được</th><th>Có khung</th>"
            f"<th>Có khung (bản ghi đầu)</th></tr>{''.join(dong)}</table></div>"
            f"<h2>Đội hình hay gặp nhất</h2><div class='bang'><table><tr><th>5 tướng</th><th>Số bản ghi</th>{the_cd}"
            f"</tr>{dong_bo}</table></div>")
    (THU_MUC / "thong_ke.html").write_text(TRANG.format(tieu_de="Thống kê tướng", than=than), encoding="utf-8")
    print(f"Đã ghi {(THU_MUC / 'tuong.csv').relative_to(THU_MUC.parent)} và {(THU_MUC / 'thong_ke.html').relative_to(THU_MUC.parent)}.")


def main():
    global THU_MUC, BAN_GHI, NHOM, TEN, KHUNG
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="lenh", required=True)
    sub.add_parser("gom", help="tách thẻ tướng, gom nhóm, xuất nhom.html").set_defaults(f=lenh_gom)
    sub.add_parser("thong-ke", help="ghi tuong.csv và thong_ke.html").set_defaults(f=lenh_thong_ke)
    ap.add_argument("--thu-muc", type=Path, default=THU_MUC, help="thư mục dữ liệu (mặc định thu_thap_tuong/)")
    a = ap.parse_args()
    THU_MUC = a.thu_muc.resolve()
    BAN_GHI, NHOM, TEN = THU_MUC / "ban_ghi.csv", THU_MUC / "nhom.json", THU_MUC / "ten_tuong.json"
    KHUNG = THU_MUC / "khung.json"
    a.f(a)


if __name__ == "__main__":
    main()
