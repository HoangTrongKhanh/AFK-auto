#!/usr/bin/env python3
"""Ghi kết quả nhận diện của bản Python (nhan_dien.py, thanh_tich.py, so_ai.py) trên mọi ảnh trong samples/ ra
src/test/resources/ket_qua_python.tsv, để kiểm thử bản Kotlin cho ra kết quả giống hệt.

Chạy lại mỗi khi sửa thuật toán bên Python hoặc thêm ảnh mẫu:
    ../../.venv/bin/python tao_ket_qua_python.py
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

import cv2  # noqa: E402

from leo_ai import tim_o_khoa  # noqa: E402
from nhan_dien import NhanDien  # noqa: E402
from so_ai import DocSoAi  # noqa: E402
from thanh_tich import DocThanhTich  # noqa: E402
import doc_tuong_cua_toi as D  # noqa: E402
import thong_ke_tuong as T  # noqa: E402

OUT = HERE / "src/test/resources/ket_qua_python.tsv"
CUA_TOI = HERE / "src/test/resources/cua_toi.json"     # khung tướng của bạn (tên -> 1/0) dùng cho phép so khung


def main():
    nd = NhanDien()
    tt = DocThanhTich(nd)
    so = DocSoAi(nd)
    rows = []
    for path in sorted((ROOT / "samples").rglob("*.png")):
        rel = path.relative_to(ROOT).as_posix()
        img = cv2.imread(str(path))
        k = nd.nhan_dien(img)
        nut = ";".join(f"{t}:{x},{y}" for t, (x, y) in sorted(k.nut.items()))
        rows.append(["man", rel, k.man_hinh, k.che_do or "-", "1" if k.tu_dong else "0", f"{k.do_sang:.2f}", nut,
                     "1" if k.dai_dien else "0"])
        diem = nd.tat_ca_diem(img)
        rows.append(["diem", rel] + [f"{t}:{s:.4f}" for t, s in sorted(diem.items())])
        d = tt.doc(img)
        if d is None:
            rows.append(["doi", rel, "none"])
        else:
            ky = "-" if d.chu_ky is None else "".join("1" if b else "0" for b in d.chu_ky.flatten())
            rows.append(["doi", rel, d.luc_chien or "-", d.nhan or "-", str(int(d.ly_tuong)), str(int(d.thu_cong)),
                         "-" if d.loc_bat is None else str(int(d.loc_bat)), ky])
        ai = so.ai_man_afk(img)
        thang = so.tien_trinh_thang(img)
        td = so.tien_trinh_tu_dong(img)
        dh = so.ai_doi_hinh(img)
        rows.append(["so", rel, "-" if ai is None else str(ai), "-" if thang is None else f"{thang[0]},{thang[1]}",
                     "-" if td is None else f"{td[0]},{td[1]}", "-" if dh is None else str(dh)])
        ld = tt.luc_doi(img)
        rows.append(["luc_doi", rel, "-" if ld is None else f"{ld:.3f}", "1" if tt.doi_trong(img) else "0"])
        khoa = tim_o_khoa(img)
        rows.append(["khoa", rel, "none" if khoa is None else f"{khoa[0]},{khoa[1]}"])
    # Thẻ tướng trong Thành Tích: khung và tướng giống nhất của từng thẻ; tướng thiếu khung theo cua_toi.json.
    tv = D.ThuVien()
    cua_toi = json.loads(CUA_TOI.read_text(encoding="utf-8"))
    sk = D.SoKhung.__new__(D.SoKhung)
    sk.tv, sk.cua_toi, sk.mat_cua_toi = tv, cua_toi, []
    for path in sorted((ROOT / "samples").rglob("*.png")):
        rel = path.relative_to(ROOT).as_posix()
        img = cv2.imread(str(path))
        dai = tt.dai_tuong(img)
        the = T.tach_the(dai) if dai is not None else None
        if the is None:
            continue
        o = []
        for m, c in the:
            m = cv2.resize(m, (T.CO_SO[0] + 2 * T.LE, T.CO_SO[1] + 2 * T.LE), interpolation=cv2.INTER_AREA)
            d, ten = tv.diem(m)[0]
            o.append(f"{ten}:{d:.4f}:{tv.khung(c)}")
        rows.append(["the", rel] + o)
        rows.append(["thieu", rel, ";".join(sk.thieu(img))])
    # Danh sách tướng ở màn đội hình (ảnh mẫu): khung, đang trong đội, tên.
    for path in sorted((ROOT / "samples").glob("tab_s7_doi_hinh_*.png")):
        rel = path.relative_to(ROOT).as_posix()
        tuong = D.doc([cv2.imread(str(path))], tv)
        rows.append(["ds", rel] + [f"{x['ten'] or '-'}:{x['khung']}:{int(x['trong_doi'])}" for x in tuong])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("".join("\t".join(r) + "\n" for r in rows), encoding="utf-8")
    print(f"Đã ghi {len(rows)} dòng vào {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
