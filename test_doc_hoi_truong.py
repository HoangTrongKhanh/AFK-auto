"""Độ phủ ảnh thật, lựa chọn quan sát và các trạng thái cuộn Hội Trường."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import cv2
import numpy as np
import doc_tuong_cua_toi as D
from hoi_truong import cat_the_hoi_truong, chup_hoi_truong


class TestCatVaNhanTen(unittest.TestCase):
    def test_nam_the_dau_ke_ca_toc_trang(self):
        im = cv2.imread('samples/tab_s7_hoi_truong_tren_cung.png')
        self.assertEqual(len(cat_the_hoi_truong(im, kem_chat_luong=True)), 5)

    def test_the_toc_trang_o_hai_trang(self):
        for name, expected in [('dau', 10), ('cuon', 17)]:
            with self.subTest(name=name):
                im = cv2.imread(f'samples/tab_s7_hoi_truong_{name}.png')
                self.assertEqual(len(cat_the_hoi_truong(im, kem_chat_luong=True)), expected)

    def test_doi_chieu_anh_thu_nho_cung_ty_le_man_hinh(self):
        for name, expected in [('tren_cung', 5), ('dau', 10), ('cuon', 17)]:
            im = cv2.imread(f'samples/tab_s7_hoi_truong_{name}.png')
            for width in [800, 1080]:
                with self.subTest(name=name, width=width):
                    small = cv2.resize(im, (width, round(im.shape[0] * width / im.shape[1])),
                                       interpolation=cv2.INTER_AREA)
                    self.assertEqual(len(cat_the_hoi_truong(small, kem_chat_luong=True)), expected)

    def test_ten_nhap_nhang_chi_goi_y(self):
        tv = Mock()
        tv.diem.return_value = [(.91, 'A'), (.90, 'B')]
        card = dict(mat=None, trong_doi=False)
        D.gan_ten([card], tv, hon_nhi=.04)
        self.assertIsNone(card['ten'])
        self.assertEqual(card['goi_y'], 'A')

    def test_khong_gan_ten_hang_hai_khi_ten_dau_da_dung(self):
        tv = Mock()
        tv.diem.side_effect = [[(.99, 'A'), (.86, 'B')], [(.94, 'A'), (.88, 'B')]]
        cards = [dict(mat=None, trong_doi=False) for _ in range(2)]
        D.gan_ten(cards, tv, hon_nhi=.04)
        self.assertEqual([x['ten'] for x in cards], ['A', None])

    def test_mat_va_anh_duoc_thay_cung_nhau_khi_lan_sau_net_hon(self):
        im = cv2.imread('samples/tab_s7_hoi_truong_dau.png')
        sharp = cat_the_hoi_truong(im, can_bien=False)[0][0]
        blur = cv2.GaussianBlur(sharp, (5, 5), .9)
        tv = Mock()
        # Cố ý cho lần mờ có điểm sao "chắc" hơn để tách tiêu chí chọn ảnh mặt.
        tv.danh_gia_khung.side_effect = [dict(khung=1), dict(khung=1)]
        tv.diem.return_value = [(.95, 'A'), (.5, 'B')]
        with patch('hoi_truong.cat_the_hoi_truong', side_effect=[[(blur, 0)], [(sharp, 0)]]):
            ds = D.doc([im, im], tv, hoi_truong=True)
        self.assertEqual(len(ds), 1)
        np.testing.assert_array_equal(ds[0]['mat'], D.mat(sharp))
        np.testing.assert_array_equal(ds[0]['the'], sharp)


class TestChuoiCuon(unittest.TestCase):
    def run_sequence(self, values, *, lost=None, limit=8, verify=False):
        imgs = [np.full((256, 160, 3), v, np.uint8) for v in values]
        adb, nd = Mock(), Mock()
        adb.game_booster_locked.return_value = False
        adb.screenshot.side_effect = imgs
        def detect(img):
            value = int(img[0, 0, 0])
            return SimpleNamespace(man_hinh='khong_ro' if value == lost else 'hoi_truong',
                                   nut={'ht_dau': (0, 0)} if value == 10 else {})
        nd.nhan_dien.side_effect = detect
        with patch('time.sleep'), patch('hoi_truong.cat_the_hoi_truong', return_value=[(imgs[0], 0)]), \
             patch('cat_the_bo_sung.cat_day_du',return_value=[(imgs[0],0)]):
            return chup_hoi_truong(adb, nd, toi_da=limit, xac_minh_cuoi=verify), adb

    def test_luu_ca_trang_cuoi_khong_lap_anh_dung_yen(self):
        images, adb = self.run_sequence([10, 30, 50, 50, 50])
        self.assertEqual([int(i[0, 0, 0]) for i in images], [10, 30, 50])
        self.assertEqual(adb.swipe.call_count, 4)

    def test_mat_man_khong_tra_ve_phien_doc_do(self):
        with self.assertRaisesRegex(RuntimeError, 'rời Hội Trường'):
            self.run_sequence([10, 30, 90], lost=90)

    def test_cuon_khong_phan_hoi_bao_loi(self):
        with self.assertRaisesRegex(RuntimeError, 'không phản hồi'):
            self.run_sequence([10, 10, 10])

    def test_cham_gioi_han_khong_tra_ve_phien_doc_do(self):
        with self.assertRaisesRegex(RuntimeError, '2 lần cuộn'):
            self.run_sequence([10, 30, 50], limit=2)

    def test_ve_dau_truoc_khi_thu_the(self):
        images, adb = self.run_sequence([30, 10, 30, 50, 50, 50])
        self.assertEqual([int(i[0, 0, 0]) for i in images], [10, 30, 50])
        # Lần đầu vuốt xuống để về đầu, các lần sau vuốt lên để đọc.
        first, second = [c.args for c in adb.swipe.call_args_list[:2]]
        self.assertLess(first[1], first[3])
        self.assertGreater(second[1], second[3])


if __name__ == '__main__':
    unittest.main()
