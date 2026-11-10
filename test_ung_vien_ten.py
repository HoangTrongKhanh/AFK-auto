"""Gợi ý nhiều tỷ lệ giúp xác nhận; không tự biến điểm thử thành tên đã nhận."""
import json
from collections import Counter
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import cv2
import doc_tuong_cua_toi as D
from hoi_truong import cat_the_hoi_truong


class TestUngVienTen(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Cố định nền thư viện gốc, không phụ thuộc các mẫu cá nhân mới được xác nhận.
        with tempfile.TemporaryDirectory() as tmp, patch.object(D, 'MAT_XAC_NHAN', Path(tmp)):
            cls.tv = D.ThuVien(kho_mau=False)
        im = cv2.imread('samples/tab_s7_hoi_truong_dau.png')
        cls.card = cat_the_hoi_truong(im, can_bien=False)[5][0]  # mặt Eironn trong lưới 6 cột

    def test_goi_y_da_ty_le_luu_ca_diem_goc(self):
        m = D.mat(self.card)
        base = dict((t, d) for d, t in self.tv.diem(m))
        uv = self.tv.goi_y_da_ty_le(m)
        self.assertEqual(len(uv), 3)
        self.assertEqual(uv[0]['ten'], 'Eironn')
        self.assertGreater(uv[0]['diem'], base['Eironn'] + .05)
        self.assertEqual(uv[0]['diem_goc'], base['Eironn'])
        self.assertIn(uv[0]['ty_le'], [.9, .95, 1., 1.05, 1.1])
        self.assertEqual(len(set(x['ten'] for x in uv)), len(uv))

    def test_diem_thu_rat_cao_khong_tu_gan_ten(self):
        tv = Mock()
        tv.diem.return_value = [(.7, 'A'), (.3, 'B')]
        tv.danh_gia_khung.return_value = dict(khung=1)
        tv.goi_y_da_ty_le.return_value = [dict(ten='B', diem=.99, diem_goc=.3, ty_le=1.1)]
        with patch('hoi_truong.cat_the_hoi_truong', return_value=[(self.card, 0)]):
            ds = D.doc([None], tv, hoi_truong=True, goi_y_da_ty_le=True)
        self.assertIsNone(ds[0]['ten'])
        self.assertEqual(ds[0]['goi_y'], 'A')
        self.assertEqual(ds[0]['ung_vien_ten'][0]['ten'], 'B')

    def test_khong_tinh_goi_y_lai_cho_ten_da_nhan(self):
        tv = Mock()
        tv.diem.return_value = [(.99, 'A'), (.3, 'B')]
        tv.danh_gia_khung.return_value = dict(khung=1)
        with patch('hoi_truong.cat_the_hoi_truong', return_value=[(self.card, 0)]):
            ds = D.doc([None], tv, hoi_truong=True, goi_y_da_ty_le=True)
        self.assertEqual(ds[0]['ten'], 'A')
        tv.goi_y_da_ty_le.assert_not_called()

    def test_ca_the_diem_thap_cung_co_anh_ung_vien_va_so_the_on_dinh(self):
        tv = Mock()
        tv.diem.return_value = [(.4, 'A'), (.2, 'B')]
        tv.danh_gia_khung.return_value = dict(khung=1)
        tv.mat = {'A': [D.mat(self.card)], 'B': [D.mat(self.card)]}
        tv.dem, tv.ty_le_khung = Counter(), Counter()
        with patch('hoi_truong.cat_the_hoi_truong', return_value=[(self.card, 0)]):
            ds = D.doc([None], tv, hoi_truong=True)
        self.assertIsNone(ds[0]['goi_y'])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.multiple(D, THU_MUC=root, ANH=root/'tuong_cua_toi', KET_QUA=root/'tuong_cua_toi.json'):
                D.xuat(ds, tv)
            out = json.loads((root/'tuong_cua_toi.json').read_text())
            self.assertEqual([v['ten'] for v in out[0]['ung_vien_ten']], ['A', 'B'])
            report = (root/'tuong_cua_toi.html').read_text()
            self.assertIn('Thẻ 1: chưa xác định tên', report)
            self.assertIn('A · 0.400', report)
            self.assertIn('B · 0.200', report)
            self.assertGreaterEqual(report.count('data:image/'), 4)


if __name__ == '__main__':
    unittest.main()
