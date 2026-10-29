#!/usr/bin/env python3
"""Kiểm tra nhận diện màn hình trên mọi ảnh mẫu có trong samples/nhan.txt.

    .venv/bin/python test_nhan_dien.py          # chạy test
    .venv/bin/python test_nhan_dien.py --bien   # thêm bảng biên an toàn của từng mẫu (điểm khớp đúng / nhầm)
"""
import sys
import unittest

import cv2

from nhan_dien import MAN_HINH, MAU, SAMPLES, NhanDien


def doc_nhan():
    """[(file, man_hinh, them)] từ samples/nhan.txt; them là che_do ("afk"/"huyen_linh") hoặc "tu_dong"."""
    out = []
    for line in (SAMPLES / "nhan.txt").read_text(encoding="utf-8").splitlines():
        line = line.split("#")[0].split()
        if line:
            out.append((line[0], line[1], line[2] if len(line) > 2 else None))
    return out


class TestNhanDien(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nd = NhanDien()

    def test_moi_anh_mau(self):
        for f, man, them in doc_nhan():
            with self.subTest(anh=f):
                img = cv2.imread(str(SAMPLES / f))
                self.assertIsNotNone(img, f"không đọc được {f}")
                ket = self.nd.nhan_dien(img)
                self.assertEqual(ket.man_hinh, man, str(ket))
                if them in ("afk", "huyen_linh"):
                    self.assertEqual(ket.che_do, them, str(ket))
                if them == "tu_dong":
                    self.assertTrue(ket.tu_dong, str(ket))

    def test_moi_mau_deu_duoc_dung(self):
        dung = {t for _, can in MAN_HINH for t in can}
        from nhan_dien import NUT_THEM
        dung |= {t for ds in NUT_THEM.values() for t in ds}
        self.assertEqual(set(MAU) - dung, set())

    def test_nut_di_tiep_man_thang(self):
        """Đo 25/10: nút Huyền Linh thay Chiến Đấu; phải nhận đúng nút để vào ải kế, cả khi thu nhỏ."""
        for ten, nut in (("tab_s7_ket_qua_thang.png", "thang_chien_dau"),
                         ("tab_s7_ket_qua_thang_huyen_linh.png", "thang_huyen_linh")):
            img = cv2.imread(str(SAMPLES / ten))
            for w in (1600, 1080, 800):
                with self.subTest(anh=ten, rong=w):
                    nho = cv2.resize(img, (w, w * 8 // 5), interpolation=cv2.INTER_AREA)
                    k = self.nd.nhan_dien(nho)
                    self.assertEqual(k.man_hinh, "thang")
                    self.assertIn(nut, k.nut)
                    x, y = k.nut[nut]
                    self.assertTrue(680 * w / 1600 < x < 1575 * w / 1600)
                    self.assertTrue(2320 * w / 1600 < y < 2520 * w / 1600)

    def test_anh_thu_nho_van_nhan_ra(self):
        """Cùng tỉ lệ khung hình nhưng độ phân giải thấp hơn (máy 800x1280): vẫn nhận ra như cũ."""
        for f, man, _ in doc_nhan()[:12]:
            with self.subTest(anh=f):
                img = cv2.imread(str(SAMPLES / f))
                nho = cv2.resize(img, (800, 1280), interpolation=cv2.INTER_AREA)
                self.assertEqual(self.nd.nhan_dien(nho).man_hinh, man)


def bao_cao_bien():
    """Với mỗi mẫu: điểm thấp nhất trên các ảnh đáng lẽ phải thấy nó, và điểm cao nhất trên các ảnh không được thấy."""
    nd = NhanDien()
    can_cua = {}
    for man, can in MAN_HINH:
        for t in can:
            can_cua.setdefault(t, set()).add(man)
    diem = {}
    for f, man, _ in doc_nhan():
        img = cv2.imread(str(SAMPLES / f))
        diem[f] = (man, nd.tat_ca_diem(img))
    print(f"{'mẫu':24s} {'đúng thấp nhất':>15s} {'nhầm cao nhất':>15s}  ảnh nhầm")
    for t in MAU:
        mans = can_cua.get(t)
        if not mans:
            continue
        dung = [d[t] for man, d in diem.values() if man in mans]
        nham = [(d[t], f) for f, (man, d) in diem.items() if man not in mans and man not in ("khoa",)]
        lo, (hi, f_hi) = min(dung, default=float("nan")), max(nham)
        print(f"{t:24s} {lo:15.2f} {hi:15.2f}  {f_hi}")


if __name__ == "__main__":
    if "--bien" in sys.argv:
        sys.argv.remove("--bien")
        bao_cao_bien()
    unittest.main(verbosity=1)
