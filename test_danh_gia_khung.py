"""Không ép ảnh kém chất lượng/viền nhập nhằng thành thiếu khung."""
import json
import io
from contextlib import redirect_stdout
import tempfile
from collections import Counter
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

import cv2
import numpy as np
import doc_tuong_cua_toi as D
from hoi_truong import cat_the_hoi_truong


class TestDanhGiaKhung(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tv = D.ThuVien()
        cls.cards = cat_the_hoi_truong(cv2.imread('samples/tab_s7_hoi_truong_cuon.png'), can_bien=False)

    def test_anh_rong_va_sai_kho_khong_thanh_khong_khung(self):
        for im in [None, np.zeros((10, 10, 3), np.uint8), np.full((205, 130, 3), 240, np.uint8)]:
            with self.subTest(shape=None if im is None else im.shape):
                self.assertIsNone(self.tv.danh_gia_khung(im)['khung'])

    def test_ba_the_co_sao_tung_bi_doc_thanh_khong_khung(self):
        # Đối chiếu bằng mắt trên ảnh cuộn: cả ba thẻ đều có hàng sao.
        for i in [9, 13, 14]:
            with self.subTest(index=i):
                card = self.cards[i][0]
                self.assertEqual(self.tv.khung(card), 0)
                self.assertIsNone(self.tv.danh_gia_khung(card)['khung'])

    def test_sao_ro_va_vien_dong_thuan_van_nhan_khung(self):
        for i in [0, 1, 2, 3]:
            self.assertEqual(self.tv.danh_gia_khung(self.cards[i][0])['khung'], 1)

    def test_the_khong_sao_vien_nhat_tri_khong_bi_tu_choi(self):
        # Thẻ đầu bản ghi AFK 751-03 có viền thường, không có hàng sao.
        img = cv2.imread('samples/thanh_tich/afk_751_03.png')
        cards = D.T.tach_the(D.DocThanhTich_dai(img))
        negatives = [c for _, c in cards if self.tv.khung(c) == 0]
        self.assertTrue(negatives)
        self.assertTrue(any(self.tv.danh_gia_khung(c)['khung'] == 0 for c in negatives))

    def test_quan_sat_chua_ro_khong_bo_phieu_khong_khung(self):
        self.assert_observations([None, 1, None], 1)

    def test_quan_sat_chac_mau_thuan_can_xac_nhan(self):
        self.assert_observations([0, 0, 1], None)

    def test_tat_ca_quan_sat_chua_ro_van_la_chua_ro(self):
        self.assert_observations([None, None], None)

    def test_khong_khung_chac_va_quan_sat_chua_ro(self):
        self.assert_observations([None, 0, None], 0)

    def assert_observations(self, labels, expected):
        card = self.cards[0][0]
        tv = Mock()
        tv.danh_gia_khung.side_effect = [dict(khung=k) for k in labels]
        tv.diem.return_value = [(.95, 'A'), (.5, 'B')]
        with patch('hoi_truong.cat_the_hoi_truong', return_value=[(card, 0)]):
            ds = D.doc([None] * len(labels), tv, hoi_truong=True)
        self.assertEqual(len(ds), 1)
        self.assertEqual(ds[0]['khung'], expected)

    def test_ban_ghi_chua_ro_khong_danh_dau_thieu_khung(self):
        sk = D.SoKhung.__new__(D.SoKhung)
        sk.tv = Mock()
        sk.tv.danh_gia_khung.return_value = dict(khung=None)
        sk.khung_cua_toi = Mock(return_value=('A', 0))
        with patch.object(D, 'DocThanhTich_dai'), patch.object(D.T, 'tach_the', return_value=[(None, None)]):
            self.assertEqual(sk.thieu(None), [])
        sk.khung_cua_toi.assert_not_called()

    def test_json_null_html_va_bo_so_khung(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            card = self.cards[0][0]
            rows = [dict(khung=None, ten='A', goi_y=None, diem=.99, the=card, trong_doi=False,
                         khung_chi_tiet=[dict(khung=None, ly_do='vien_chua_dong_thuan')])]
            tv = Mock(dem=Counter(A=1), ty_le_khung=Counter(A=1))
            with patch.multiple(D, THU_MUC=root, ANH=root/'tuong_cua_toi', KET_QUA=root/'tuong_cua_toi.json', BASE=root), \
                 patch.object(D, 'doc_khung_tay', return_value={}):
                D.xuat(rows, tv)
                saved = json.loads(D.KET_QUA.read_text())
                self.assertIsNone(saved[0]['khung'])
                self.assertEqual(saved[0]['khung_chi_tiet'], rows[0]['khung_chi_tiet'])
                report = (root/'tuong_cua_toi.html').read_text()
                self.assertIn('chưa xác định khung', report)
                self.assertNotIn('>Không khung<', report)
                sk = D.SoKhung(Mock())
                self.assertEqual(sk.cua_toi, {})
                self.assertEqual(sk.mat_cua_toi, [])
                library = Mock()
                library.quan_trong.return_value = [('A', .5)]
                output = io.StringIO()
                with patch.object(D, 'ThuVien', return_value=library), redirect_stdout(output):
                    D.khung_tay([])
                self.assertIn('chưa rõ khung', output.getvalue())
                with patch.object(D, 'doc_khung_tay', return_value={'A': 0}):
                    self.assertEqual(D.SoKhung(Mock()).cua_toi, {'A': 0})


if __name__ == '__main__':
    unittest.main()
