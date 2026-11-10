import unittest
from unittest.mock import patch
import cv2
import numpy as np
from nhan_dien import NhanDien
from hoi_truong import cat_the_hoi_truong, kiem_tra_do_phu
import test_doc_hoi_truong as flow


class TestAnhThat(unittest.TestCase):
    def test_thanh_noi_che_tieu_de_khong_lam_mat_hoi_truong(self):
        im=cv2.imread('tests/fixtures/hoi_truong_bi_che_tieu_de_48.png')
        out=NhanDien().nhan_dien(im)
        self.assertEqual(out.man_hinh,'hoi_truong')
        self.assertIn('ht_dau',out.nut)

    def test_che_do_khong_phai_hoi_truong(self):
        im=cv2.imread('samples/tab_s7_che_do_chien_dau.png')
        self.assertNotEqual(NhanDien().nhan_dien(im).man_hinh,'hoi_truong')

    def test_cuoi_danh_sach_du_21_the_khong_lay_hang_bi_che(self):
        im=cv2.imread('samples/tab_s7_hoi_truong_cuoi.png')
        self.assertEqual(NhanDien().nhan_dien(im).man_hinh,'hoi_truong')
        self.assertEqual(len(cat_the_hoi_truong(im)),21)

    def test_nhom_co_dinh_khong_tao_chong_lap_gia(self):
        rng=np.random.default_rng(0)
        def card():return rng.integers(0,255,(205,130,3),dtype=np.uint8),0
        sticky=[card() for _ in range(5)]
        with patch('cat_the_bo_sung.cat_day_du',side_effect=[sticky+[card()],sticky+[card()]]):
            out=kiem_tra_do_phu([None,None])
        self.assertTrue(out['noi_trang'][0]['can_kiem_tra'])


class TestXacMinhCuoi(unittest.TestCase):
    def test_cuon_nguoc_va_tro_lai_cuoi(self):
        runner=flow.TestChuoiCuon()
        images,adb=runner.run_sequence([10,30,50,50,50,30,50],verify=True)
        self.assertEqual(len(images),3)
        self.assertEqual(adb.swipe.call_count,6)

    def test_bi_ket_giua_danh_sach_khong_bao_het(self):
        with self.assertRaisesRegex(RuntimeError,'cuộn ngược không phản hồi'):
            flow.TestChuoiCuon().run_sequence([10,30,50,50,50,50],verify=True)
