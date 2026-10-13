#!/usr/bin/env python3
"""Ghi kết quả nhận diện của bản Python (nhan_dien.py, thanh_tich.py, so_ai.py) trên mọi ảnh trong samples/ ra
src/test/resources/ket_qua_python.tsv, để kiểm thử bản Kotlin cho ra kết quả giống hệt.

Chạy lại mỗi khi sửa thuật toán bên Python hoặc thêm ảnh mẫu:
    ../../.venv/bin/python tao_ket_qua_python.py
"""
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

OUT = HERE / "src/test/resources/ket_qua_python.tsv"


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
        rows.append(["man", rel, k.man_hinh, k.che_do or "-", "1" if k.tu_dong else "0", f"{k.do_sang:.2f}", nut])
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
        rows.append(["so", rel, "-" if ai is None else str(ai), "-" if thang is None else f"{thang[0]},{thang[1]}"])
        ld = tt.luc_doi(img)
        rows.append(["luc_doi", rel, "-" if ld is None else f"{ld:.3f}"])
        khoa = tim_o_khoa(img)
        rows.append(["khoa", rel, "none" if khoa is None else f"{khoa[0]},{khoa[1]}"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("".join("\t".join(r) + "\n" for r in rows), encoding="utf-8")
    print(f"Đã ghi {len(rows)} dòng vào {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
