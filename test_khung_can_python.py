import json
from pathlib import Path
import tempfile
import unittest
import cv2
import numpy as np
from khung_can_python import MauKhungCan, dac_trung
from hoi_truong import cat_the_hoi_truong
import doc_tuong_cua_toi as D

FIXTURE=Path(__file__).resolve().parent/'tests/fixtures/khung_can'


class TestKhungCanPython(unittest.TestCase):
    def test_toc_trang_khong_thanh_sao_nhung_sao_that_van_nhan(self):
        model=D.ThuVien(mau_khung_can=FIXTURE/'mau29.npz')
        for n,label in [(95,0),(11,1),(86,0),(88,0)]:
            with self.subTest(so_the=n):
                image=cv2.imread(str(FIXTURE/f'{n}.png'))
                quality=json.loads((FIXTURE/f'{n}.json').read_text())
                self.assertEqual(model.danh_gia_khung(image,quality)['khung'],label)

    def test_khong_hoc_phan_mat_trung_tam(self):
        image=np.full((205,130,3),(80,140,220),np.uint8)
        quality=dict(day_du=True,bien_chuan=[0,0,130,205])
        other=image.copy();other[85:160,40:85]=(220,10,50)
        np.testing.assert_array_equal(dac_trung(image,quality),dac_trung(other,quality))

    def test_anh_mat_bien_van_phai_chua_ro_du_da_co_mau(self):
        model=D.ThuVien(mau_khung_can=FIXTURE/'mau29.npz')
        image=cv2.imread(str(FIXTURE/'11.png'));quality=json.loads((FIXTURE/'11.json').read_text())
        quality['day_du']=False
        self.assertIsNone(model.danh_gia_khung(image,quality)['khung'])

    def test_hai_lop_khong_tach_biet_khong_ep_nhan(self):
        image=cv2.imread(str(FIXTURE/'11.png'));quality=json.loads((FIXTURE/'11.json').read_text());f=dac_trung(image,quality)
        bank=MauKhungCan(np.tile(f,(8,1)),[0]*4+[1]*4,np.arange(8),[.1,.1])
        self.assertIsNone(bank.du_doan(image,quality)['khung'])

    def test_mau_xa_va_file_sai_phien_ban_bi_tu_choi(self):
        image=cv2.imread(str(FIXTURE/'11.png'));quality=json.loads((FIXTURE/'11.json').read_text())
        bank=MauKhungCan(np.ones((8,70))*10,[0]*4+[1]*4,np.arange(8),[.01,.01])
        self.assertEqual(bank.du_doan(image,quality)['ly_do'],'ngoai_mien_mau_can')
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'bad.npz';np.savez(path,phien_ban=999)
            with self.assertRaises(ValueError):MauKhungCan.nap(path)

    def test_hang_cuoi_khong_can_chu_cap_khop_mau(self):
        image=cv2.imread('samples/tab_s7_hoi_truong_cuoi_828.png')
        items=cat_the_hoi_truong(image,kem_chat_luong=True)
        self.assertEqual(len(items),18)  # 5 cố định + 6 + 6 + 1; trước sửa chỉ thấy 5.
        self.assertTrue(items[-1][2]['day_du'])


if __name__=='__main__':unittest.main()
