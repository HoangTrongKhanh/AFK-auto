#!/usr/bin/env python3
"""Tạo thư viện tướng templates/vi/tuong/ từ dữ liệu Thành Tích đã thu (thu_thap_tuong/, xem thong_ke_tuong.py), để
bot (bản PC và app Android) so khung tướng khi chọn đội mà không cần dữ liệu gốc:

  - <Tên>.png: tối đa SO_MAT ảnh mặt tướng (48x48) xếp ngang, để nhận ra tướng trên thẻ (bản ghi và danh sách của bạn).
    Mặt đã xác nhận trong thu_thap_tuong/mat_xac_nhan/ đứng đầu.
  - tuong.json: {"tuong": {tên: {"so_mat", "so_lan", "co_khung"}}, "vien": {"so", "chieu"}}. co_khung = tỉ lệ số lần tướng
    xuất hiện với thẻ có khung trong bản ghi (tướng bản ghi thường dùng không khung thì thiếu khung không sao).
  - vien.bin: đặc trưng viền (float32, little-endian) của các thẻ đã biết khung, mỗi thẻ "chieu" số; vien_nhan.bin: nhãn
    (1 byte, 1 = có khung). Dùng để xếp thẻ có điểm khớp sao lưng chừng (k láng giềng gần nhất).

Chạy lại sau khi thu thêm dữ liệu hoặc đặt tên thêm tướng:
    .venv/bin/python tao_thu_vien_tuong.py
"""
import csv
import json
import random
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

import thong_ke_tuong as T
from nhan_dien import TPL_DIR

BASE = Path(__file__).resolve().parent
DU_LIEU = BASE / "thu_thap_tuong"
RA = TPL_DIR / "tuong"
SO_MAT = 12
VIEN_MOI_LOAI = 300         # số thẻ mẫu mỗi loại (có khung / không khung) cho bước xếp theo viền


def main():
    nhom = json.loads((DU_LIEU / "nhom.json").read_text(encoding="utf-8"))
    ten = json.loads((DU_LIEU / "ten_tuong.json").read_text(encoding="utf-8"))
    khung = json.loads((DU_LIEU / "khung.json").read_text(encoding="utf-8"))
    with (DU_LIEU / "ban_ghi.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    mat, so_lan, co_khung = {}, Counter(), Counter()
    vien = {0: [], 1: []}
    for r in rows:
        the = T.tach_the(cv2.imread(str(DU_LIEU / r["anh"]))) if r["anh"] else None
        for i, (m, t) in enumerate(the or []):
            khoa = f"{r['luot']}|{r['vi_tri']}|{i}"
            k = khung.get(khoa)
            if k is not None:
                vien[k].append(T.dac_trung_vien(t))
            tn = ten.get(str(nhom.get(khoa)))
            if not tn:
                continue
            so_lan[tn] += 1
            co_khung[tn] += k or 0
            if len(mat.setdefault(tn, [])) < SO_MAT:
                mat[tn].append(cv2.resize(m, (T.CO_SO[0] + 2 * T.LE, T.CO_SO[1] + 2 * T.LE),
                                          interpolation=cv2.INTER_AREA))
    xac_nhan = DU_LIEU / "mat_xac_nhan"
    for f in sorted(xac_nhan.glob("*.png")) if xac_nhan.exists() else []:
        tn = f.stem.split("~")[0]
        mat.setdefault(tn, []).insert(0, cv2.imread(str(f)))

    RA.mkdir(parents=True, exist_ok=True)
    for f in RA.glob("*"):
        f.unlink()
    tuong = {}
    for tn, ds in sorted(mat.items()):
        ds = ds[:SO_MAT]
        cv2.imwrite(str(RA / f"{tn}.png"), np.hstack(ds))
        tuong[tn] = dict(so_mat=len(ds), so_lan=so_lan[tn], co_khung=round(co_khung[tn] / max(1, so_lan[tn]), 3))
    random.seed(0)
    chon = [(f, 0) for f in random.sample(vien[0], min(VIEN_MOI_LOAI, len(vien[0])))] + \
           [(f, 1) for f in random.sample(vien[1], min(VIEN_MOI_LOAI, len(vien[1])))]
    np.array([f for f, _ in chon], dtype="<f4").tofile(RA / "vien.bin")
    np.array([n for _, n in chon], dtype=np.uint8).tofile(RA / "vien_nhan.bin")
    (RA / "tuong.json").write_text(json.dumps(dict(tuong=tuong, vien=dict(so=len(chon), chieu=len(chon[0][0]))),
                                              ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Đã ghi {len(tuong)} tướng và {len(chon)} thẻ mẫu viền vào {RA.relative_to(BASE)}.")


if __name__ == "__main__":
    main()
