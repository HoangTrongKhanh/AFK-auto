"""Kiểm tra Hội Trường trên ảnh đã chụp thật và hai kiểu nút người dùng cung cấp."""
from pathlib import Path
import unittest
from unittest.mock import Mock
import cv2
import numpy as np
from nhan_dien import NhanDien, SAMPLES, TPL_DIR
from hoi_truong import cat_the_hoi_truong, chup_hoi_truong
import doc_tuong_cua_toi as D

class TestHoiTruong(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nd=NhanDien();cls.tv=D.ThuVien()
    def test_man_dau_va_cuon(self):
        for n in ['tren_cung','dau','cuon']:
            im=cv2.imread(str(SAMPLES/f'tab_s7_hoi_truong_{n}.png'))
            self.assertEqual(self.nd.nhan_dien(im).man_hinh,'hoi_truong')
    def test_nut_ban_do_va_afk(self):
        for n,key in [('tab_s7_hoi_truong_nut','ht_nut_menu'),('tab_s7_man_afk','ht_nut_afk')]:
            im=cv2.imread(str(SAMPLES/f'{n}.png'));sm,_=self.nd._thu_nho(im)
            score,pt=self.nd.tim(sm,key);self.assertGreater(score,.9);self.assertIsNotNone(pt)
    def test_hai_kieu_nut_nguoi_dung(self):
        tpl=cv2.imread(str(TPL_DIR/'ht_nut_menu.png'))
        for name in ['nut_tron','nut_khong_tron']:
            im=cv2.imread(str(Path(__file__).parent/'tests/fixtures/hoi_truong'/f'{name}.png'))
            im=cv2.resize(im,None,fx=2.8,fy=2.8)
            score=cv2.minMaxLoc(cv2.matchTemplate(im,tpl,cv2.TM_CCOEFF_NORMED))[1]
            self.assertGreater(score,.9,name)
    def test_the_lon_doc_tuong_quan_trong(self):
        im=cv2.imread(str(SAMPLES/'tab_s7_hoi_truong_dau.png'))
        ds=D.doc([im],self.tv,hoi_truong=True)
        byname={d['ten']:d for d in ds if d['ten']}
        for ten in ['Rolan','Mehira','Eryndor']:
            self.assertIn(ten,byname)
            # Ảnh có sao nhưng nút nâng cấp che góc có thể bị giữ chưa rõ; không được đọc thành 0.
            self.assertIn(byname[ten]['khung'],(1,None))
        self.assertTrue(all(not d['trong_doi'] for d in ds))
    def test_anh_trung_khong_them_the(self):
        im=cv2.imread(str(SAMPLES/'tab_s7_hoi_truong_dau.png'))
        self.assertEqual(len(D.doc([im],self.tv,hoi_truong=True)),len(D.doc([im,im],self.tv,hoi_truong=True)))
    def test_bo_nen_trang(self):
        self.assertEqual(cat_the_hoi_truong(np.full((2560,1600,3),240,np.uint8)),[])
    def test_man_la_khong_bam(self):
        adb=Mock();adb.screenshot.return_value=np.full((2560,1600,3),240,np.uint8);adb.game_booster_locked.return_value=False
        with self.assertRaises(RuntimeError):chup_hoi_truong(adb,self.nd)
        adb.tap.assert_not_called();adb.swipe.assert_not_called()

if __name__=='__main__':unittest.main()
