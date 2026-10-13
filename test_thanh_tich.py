#!/usr/bin/env python3
"""Kiểm tra đọc đội trong bảng Thành Tích trên các ảnh samples/thanh_tich/ (nhãn đúng ở samples/thanh_tich/nhan.txt).

    .venv/bin/python test_thanh_tich.py
"""
import unittest

import cv2

import thanh_tich as tt
from nhan_dien import SAMPLES

THU_MUC = SAMPLES / "thanh_tich"
# Ảnh khác có cùng người chơi với một ảnh trong nhan.txt (thẻ đang chọn ở vị trí khác): ảnh -> tên
CUNG_NGUOI = {
    SAMPLES / "tab_s7_thanh_tich_doi_1.png": "CG.Linus",               # thẻ bên trái (lần mở đầu tiên)
    SAMPLES / "tab_s7_thanh_tich_huyen_linh_doi_chon.png": "HebiZ",
}


def doc_nhan():
    out = []
    for line in (THU_MUC / "nhan.txt").read_text(encoding="utf-8").splitlines():
        f = line.split("#")[0].split()
        if f:
            out.append(dict(file=f[0], luc_chien=f[1], nhan=None if f[2] == "-" else f[2],
                            ly_tuong=f[3] == "1", thu_cong=f[4] == "1", ten=f[5]))
    return out


class TestThanhTich(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = tt.DocThanhTich()
        cls.nhan = doc_nhan()
        cls.ket = {n["file"]: cls.doc.doc(cv2.imread(str(THU_MUC / n["file"]))) for n in cls.nhan}

    def test_doc_tung_doi(self):
        for n in self.nhan:
            with self.subTest(anh=n["file"]):
                k = self.ket[n["file"]]
                self.assertIsNotNone(k)
                self.assertEqual(k.luc_chien, n["luc_chien"])
                self.assertEqual(k.nhan, n["nhan"])
                self.assertEqual(k.ly_tuong, n["ly_tuong"])
                self.assertEqual(k.thu_cong, n["thu_cong"])
                self.assertFalse(k.loc_bat)

    def test_nhan_ra_doi_theo_ten(self):
        """Cùng người chơi thì cùng chữ ký (kể cả ở vị trí thẻ khác), khác người thì khác."""
        ket = [(n["ten"], self.ket[n["file"]]) for n in self.nhan]
        for p, ten in CUNG_NGUOI.items():
            ket.append((ten, self.doc.doc(cv2.imread(str(p)))))
        for i, (ten_a, a) in enumerate(ket):
            for ten_b, b in ket[i + 1:]:
                s = tt.giong_ten(a.chu_ky, b.chu_ky)
                if ten_a == ten_b:
                    self.assertGreaterEqual(s, tt.GIONG_TEN, f"{ten_a}: {s:.2f}")
                else:
                    self.assertLess(s, tt.GIONG_TEN - 0.15, f"{ten_a} / {ten_b}: {s:.2f}")

    def test_may_rong_1080(self):
        """Máy rộng 1080 (như A54): đọc đúng mọi trường, chữ ký tên vẫn phân biệt được giữa các ảnh cùng máy."""
        def doc(p):
            return self.doc.doc(cv2.resize(cv2.imread(str(p)), (1080, 1728), interpolation=cv2.INTER_AREA))
        ket = []
        for n in self.nhan:
            k = doc(THU_MUC / n["file"])
            with self.subTest(anh=n["file"]):
                self.assertEqual((k.luc_chien, k.nhan, k.ly_tuong, k.thu_cong),
                                 (n["luc_chien"], n["nhan"], n["ly_tuong"], n["thu_cong"]))
            ket.append((n["ten"], k))
        ket += [(ten, doc(p)) for p, ten in CUNG_NGUOI.items()]
        for i, (ten_a, a) in enumerate(ket):
            for ten_b, b in ket[i + 1:]:
                self.assertEqual(tt.cung_doi(a, b) or tt.giong_ten(a.chu_ky, b.chu_ky) >= tt.GIONG_TEN,
                                 ten_a == ten_b, f"{ten_a} / {ten_b}")

    def test_luc_chien_doi(self):
        """Lực chiến đội của bạn ở màn đội hình ("338,210K"), cả ở các độ phân giải thấp hơn."""
        mong = {"tab_s7_doi_hinh_man_afk.png": 338.21, "tab_s7_doi_hinh_da_sao_chep.png": 257.943,
                "tab_s7_doi_hinh_huyen_linh.png": 276.957}
        for f, v in mong.items():
            img = cv2.imread(str(SAMPLES / f))
            for w in (1600, 1200, 1080, 800):
                with self.subTest(anh=f, rong=w):
                    nho = cv2.resize(img, (w, w * 8 // 5), interpolation=cv2.INTER_AREA)
                    self.assertAlmostEqual(self.doc.luc_doi(nho), v)
        self.assertIsNone(self.doc.luc_doi(cv2.imread(str(SAMPLES / "tab_s7_man_afk.png"))))

    def test_o_loc_bat(self):
        k = self.doc.doc(cv2.imread(str(SAMPLES / "tab_s7_thanh_tich_loc_da_so_huu.png")))
        self.assertTrue(k.loc_bat)

    def test_khong_phai_thanh_tich(self):
        self.assertIsNone(self.doc.doc(cv2.imread(str(SAMPLES / "tab_s7_man_afk.png"))))
        self.assertIsNone(self.doc.doc(cv2.imread(str(SAMPLES / "tab_s7_doi_hinh_man_afk.png"))))


if __name__ == "__main__":
    unittest.main(verbosity=1)
