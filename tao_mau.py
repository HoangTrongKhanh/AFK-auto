#!/usr/bin/env python3
"""Cắt các mẫu nhận diện vào templates/vi/ từ ảnh mẫu trong samples/:
  - mẫu màn hình và nút theo bảng MAU ở nhan_dien.py,
  - mẫu chữ "Chiến Đấu Thủ Công", "Chưa Xếp Hạng" và mẫu ký tự lực chiến cho thanh_tich.py.

Chạy lại sau khi sửa toạ độ hoặc thêm ảnh mẫu:
    .venv/bin/python tao_mau.py
"""
import json
import shutil

import cv2

from nhan_dien import MAN_HINH, MAU, NUT_THEM, SAMPLES, TPL_DIR

# Mẫu phụ cho thanh_tich.py: tên -> (ảnh mẫu, hộp x0 y0 x1 y1 theo máy gốc)
MAU_THANH_TICH = {
    "tt_thu_cong": ("thanh_tich/hl_515_02", (700, 470, 990, 508)),        # dưới tên đội đang chọn (thẻ giữa)
    "tt_chua_xep_hang": ("thanh_tich/afk_751_01", (830, 692, 1225, 755)),
}
MAU_KY_TU_MOI_LOAI = 3      # giữ tối đa bấy nhiêu mẫu cho mỗi ký tự lực chiến
# Lực chiến đội của bạn ở màn đội hình (bỏ dấu phẩy), để có mẫu chữ K: ảnh mẫu -> giá trị
LUC_DOI = {
    "tab_s7_doi_hinh_man_afk": "338210K",
    "tab_s7_doi_hinh_da_sao_chep": "257943K",
    "tab_s7_doi_hinh_huyen_linh": "276957K",
}


def cat(nguon, hop):
    img = cv2.imread(str(SAMPLES / f"{nguon}.png"))
    if img is None:
        raise SystemExit(f"thiếu ảnh mẫu samples/{nguon}.png")
    x0, y0, x1, y1 = hop
    return img[y0:y1, x0:x1]


def main():
    TPL_DIR.mkdir(parents=True, exist_ok=True)
    for ten, m in MAU.items():
        cv2.imwrite(str(TPL_DIR / f"{ten}.png"), cat(m.nguon, m.hop))
    for ten, (nguon, hop) in MAU_THANH_TICH.items():
        cv2.imwrite(str(TPL_DIR / f"{ten}.png"), cat(nguon, hop))
    # Bảng mẫu cho bản Android (đọc trong vision/BoMau.kt) để toạ độ chỉ khai báo một chỗ là nhan_dien.py.
    bang = {
        "mau": {ten: {"hop": list(m.hop), "neo": m.neo, "le": m.le, "nguong": m.nguong} for ten, m in MAU.items()},
        "man_hinh": [{"ten": man, "can": can} for man, can in MAN_HINH],
        "nut_them": NUT_THEM,
    }
    (TPL_DIR / "mau.json").write_text(json.dumps(bang, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Đã tạo {len(MAU) + len(MAU_THANH_TICH)} mẫu và mau.json trong {TPL_DIR}")

    # Ký tự lực chiến: tách từ các ảnh Thành Tích đã biết lực chiến (samples/thanh_tich/nhan.txt).
    import thanh_tich as tt
    from nhan_dien import NhanDien
    nd = NhanDien()
    out = TPL_DIR / "luc_chien"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir()
    dem = {}
    for line in (SAMPLES / "thanh_tich" / "nhan.txt").read_text(encoding="utf-8").splitlines():
        f = line.split("#")[0].split()
        if not f:
            continue
        img = cv2.imread(str(SAMPLES / "thanh_tich" / f[0]))
        diem, vt = nd.tim(nd._thu_nho(img)[0], "tt_nam_dam")
        if diem < 0.8:
            raise SystemExit(f"{f[0]}: không thấy biểu tượng nắm đấm")
        k = tt.REF_W / img.shape[1]
        ref = cv2.resize(img, None, fx=k, fy=k) if k != 1 else img
        dx = vt[0] * 2 - (tt.MOC[0] + tt.MOC[2]) / 2
        dy = vt[1] * 2 - (tt.MOC[1] + tt.MOC[3]) / 2
        x0, y0, x1, y1 = tt.VUNG_LUC_CHIEN
        kts = tt.tach_luc_chien(tt._cat(ref, (x0 + dx, y0 + dy, x1 + dx, y1 + dy)))
        if len(kts) != len(f[1]):
            raise SystemExit(f"{f[0]}: tách được {len(kts)} ký tự, nhãn là {f[1]}")
        for c, m in zip(f[1], kts):
            n = dem.get(c, 0)
            if n < MAU_KY_TU_MOI_LOAI:
                cv2.imwrite(str(out / f"{c}_{n}.png"), m.astype("uint8") * 255)
                dem[c] = n + 1
    for nguon, nhan in LUC_DOI.items():
        img = cv2.imread(str(SAMPLES / f"{nguon}.png"))
        kts = tt.tach_luc_chien(tt._cat(img, tt.VUNG_LUC_DOI), tt.RONG_K)
        if len(kts) != len(nhan):
            raise SystemExit(f"{nguon}: tách được {len(kts)} ký tự lực chiến đội, nhãn là {nhan}")
        # Nét chữ ở màn đội hình hơi khác Thành Tích (số 9 lẫn với 0 ở máy rộng 1080) nên lưu mẫu riêng, đếm riêng.
        for c, m in zip(nhan, kts):
            n = dem.get("d" + c, 0)
            if n < MAU_KY_TU_MOI_LOAI:
                cv2.imwrite(str(out / f"{c}_d{n}.png"), m.astype("uint8") * 255)
                dem["d" + c] = n + 1
    print(f"Đã tạo mẫu ký tự lực chiến: {''.join(sorted({c[-1] for c in dem}))}")


if __name__ == "__main__":
    main()
