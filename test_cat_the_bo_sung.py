import unittest
import cv2,numpy as np
from hoi_truong import cat_the_hoi_truong
from cat_the_bo_sung import cat_day_du

class TestMotTheTocTrang(unittest.TestCase):
    def setUp(self):self.im=cv2.imread('tests/fixtures/hoi_truong_mot_the_toc_trang.png')

    def test_tim_du_the_don_le_khi_chu_cap_va_toc_trang_lam_mat_hang(self):
        self.assertEqual(len(cat_the_hoi_truong(self.im)),5)
        cards=cat_day_du(self.im,kem_chat_luong=True)
        self.assertEqual(len(cards),6)
        q=cards[-1][2];self.assertTrue(q['day_du']);self.assertTrue(q['vung_sao_day_du']);self.assertTrue(q['vien_day_du'])
        self.assertEqual(q['bo_cat'],'single_column_v1');self.assertGreater(min(q['ho_tro_vien']),.2)
        self.assertEqual(cards[-1][0].shape,(205,130,3))

    def test_anh_thu_nho_mat_moc_khong_tu_sinh_the(self):
        small=cv2.resize(self.im,(800,1280),interpolation=cv2.INTER_AREA)
        self.assertEqual(len(cat_day_du(small)),len(cat_the_hoi_truong(small)))

    def test_cho_trong_khong_tao_the_ao(self):
        im=self.im.copy();bg=im[1200,450];im[1030:1340,150:375]=bg
        self.assertEqual(len(cat_day_du(im)),5)

    def test_the_bi_cat_mat_phan_duoi_khong_bao_du_bien(self):
        im=self.im.copy();im[1210:1340,150:375]=im[1200,450]
        self.assertEqual(len(cat_day_du(im)),5)

    def test_cac_anh_cu_khong_bi_them_the_ao(self):
        for name in ['tren_cung','dau','cuon','cuoi']:
            with self.subTest(name=name):
                im=cv2.imread('samples/tab_s7_hoi_truong_'+name+'.png')
                original=cat_the_hoi_truong(im,kem_chat_luong=True);new=cat_day_du(im,kem_chat_luong=True)
                self.assertEqual(len(original),len(new))
                for a,b in zip(original,new):np.testing.assert_array_equal(a[0],b[0])

if __name__=='__main__':unittest.main()
