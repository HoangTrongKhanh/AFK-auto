#!/usr/bin/env python3
"""Kiểm tra đọc số ải trên ảnh mẫu.

    .venv/bin/python test_so_ai.py
"""
import unittest

import cv2

from nhan_dien import SAMPLES
from so_ai import DocSoAi

AI_MAN_AFK = {
    "tab_s7_man_afk.png": 751,
    "tab_s7_man_afk_sau_khi_nhan_thuong.png": 751,
    "tab_s7_man_afk_sau_tran_thua.png": 751,
    "tab_s7_tooltip_giai_doan_2.png": 751,
    "tab_s7_man_afk_sau_khi_thang_752.png": 752,
    "tab_s7_man_afk_tu_dong_xu_ly.png": 427,
}

# Số ải ở tiêu đề màn đội hình (cả màn đội hình leo hộ)
AI_DOI_HINH = {
    "tab_s7_doi_hinh_man_afk.png": 238,
    "tab_s7_doi_hinh_huyen_linh.png": 515,
    "tab_s7_doi_hinh_acc2.png": 108,
    "tab_s7_dai_dien_doi_hinh.png": 45,
    "tab_s7_dai_dien_doi_hinh_hl.png": 178,
}


class TestSoAi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = DocSoAi()

    def anh(self, f):
        return cv2.imread(str(SAMPLES / f))

    def test_ai_man_afk(self):
        for f, ai in AI_MAN_AFK.items():
            with self.subTest(anh=f):
                self.assertEqual(self.d.ai_man_afk(self.anh(f)), ai)

    def test_tien_trinh_thang(self):
        self.assertEqual(self.d.tien_trinh_thang(self.anh("tab_s7_ket_qua_thang.png")), (751, 752))

    def test_tien_trinh_thang_bon_chu_so(self):
        """Màn thắng mới (25/10): số 1109 trước đây bị cắt mất chữ số đầu."""
        img = self.anh("tab_s7_ket_qua_thang_huyen_linh.png")
        for w in (1600, 1080, 800):
            with self.subTest(rong=w):
                nho = cv2.resize(img, (w, w * 8 // 5), interpolation=cv2.INTER_AREA)
                self.assertEqual(self.d.tien_trinh_thang(nho), (1109, 1110))

    def test_tien_trinh_tu_dong(self):
        self.assertEqual(self.d.tien_trinh_tu_dong(self.anh("tab_s7_tu_dong_hoan_tat.png")), (217, 245))
        self.assertEqual(self.d.tien_trinh_tu_dong(self.anh("tab_s7_xu_ly_hoan_tat.png")), (420, 445))
        self.assertIsNone(self.d.tien_trinh_tu_dong(self.anh("tab_s7_ket_qua_thang.png")))

    def test_ai_doi_hinh(self):
        for f, ai in AI_DOI_HINH.items():
            with self.subTest(anh=f):
                self.assertEqual(self.d.ai_doi_hinh(self.anh(f)), ai)
                nho = cv2.resize(self.anh(f), (1080, 1728), interpolation=cv2.INTER_AREA)
                self.assertEqual(self.d.ai_doi_hinh(nho), ai)
        self.assertIsNone(self.d.ai_doi_hinh(self.anh("tab_s7_man_afk.png")))

    def test_man_khac_tra_ve_none(self):
        for f in ("tab_s7_doi_hinh_man_afk.png", "tab_s7_ket_qua_bai_thu_lai.png", "tab_s7_man_afk_bi_game_booster_khoa.png"):
            with self.subTest(anh=f):
                self.assertIsNone(self.d.ai_man_afk(self.anh(f)))
                self.assertIsNone(self.d.tien_trinh_thang(self.anh(f)))

    def test_anh_thu_nho(self):
        nho = cv2.resize(self.anh("tab_s7_man_afk_sau_khi_thang_752.png"), (1200, 1920), interpolation=cv2.INTER_AREA)
        self.assertEqual(self.d.ai_man_afk(nho), 752)


if __name__ == "__main__":
    unittest.main(verbosity=1)
