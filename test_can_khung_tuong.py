import unittest
import cv2
import numpy as np
from can_khung_tuong import can_khung
from hoi_truong import cat_the_hoi_truong
import doc_tuong_cua_toi as D


class TestCanKhung(unittest.TestCase):
    def test_bien_di_chuyen_duoc_can_lai(self):
        for dx,dy in [(0,0),(12,7),(-9,-5)]:
            im=np.full((1200,800,3),(225,235,245),np.uint8)
            x,y=145+dx,500+dy
            cv2.rectangle(im,(x,y),(x+210,y+285),(20,130,220),-1)
            # Tạo mặt có cấu trúc để không phải vùng trống.
            cv2.circle(im,(x+100,y+120),45,(90,60,40),-1)
            card,q=can_khung(im,250,500,1,300,1000)
            self.assertTrue(q['day_du'],q)
            self.assertEqual(q['bien'],[x,y,x+211,y+286])
            a,b,c,d=q['bien_chuan']
            self.assertLessEqual(abs((a+c)/2-65),.5)
            self.assertLessEqual(abs((b+d)/2-102.5),.5)
            self.assertEqual(card.shape,(205,130,3))

    def test_bien_cham_vung_bi_che_khong_doc_khung(self):
        im=np.full((1200,800,3),(225,235,245),np.uint8)
        cv2.rectangle(im,(145,500),(355,785),(20,130,220),-1)
        card,q=can_khung(im,250,500,1,510,1000)
        self.assertIsNone(card)
        self.assertFalse(q['day_du'])
        result=D.ThuVien().danh_gia_khung(np.zeros((205,130,3),np.uint8),chat_luong_cat=q)
        self.assertIsNone(result['khung'])
        self.assertIn('bien',result['ly_do'])

    def test_khong_lay_the_hang_ke_tiep(self):
        im=cv2.imread('samples/tab_s7_hoi_truong_cuon.png')
        items=cat_the_hoi_truong(im,kem_chat_luong=True)
        checked=0
        for card,y,q,old in items:
            if not q['day_du']:continue
            a,b,c,d=q['bien_chuan']
            self.assertGreater(a,0);self.assertLess(c,130)
            self.assertGreater(b,0);self.assertLess(d,205)
            # Ngoài biên object phải là nền đồng nhất, không phải ngôi sao hàng dưới.
            self.assertEqual(float(card[d:].std(axis=(0,1)).max()),0)
            checked+=1
        self.assertGreater(checked,0)

    def test_giu_du_ung_vien_khi_chua_xac_minh_bien(self):
        im=cv2.imread('samples/tab_s7_hoi_truong_tren_cung.png')
        rows=cat_the_hoi_truong(im,kem_chat_luong=True)
        self.assertEqual(len(rows),5)
        for card,y,q,old in rows:
            self.assertEqual(old.shape,(205,130,3))
            if not q['day_du']:
                self.assertIsNone(D.ThuVien().danh_gia_khung(card,chat_luong_cat=q)['khung'])

    def test_hoa_tiet_toc_khong_thanh_hang_sao(self):
        # Hàng cuối thật: Nara và Gerda có tóc/mũ tạo cực đại khớp sao đơn lẻ.
        im=cv2.imread('samples/tab_s7_hoi_truong_cuoi.png')
        rows=cat_the_hoi_truong(im,kem_chat_luong=True)
        model=D.ThuVien()
        for index in [11,13]:
            card,y,q,old=rows[index]
            self.assertTrue(q['day_du'])
            self.assertNotEqual(model.danh_gia_khung(card,chat_luong_cat=q)['khung'],1)

    def test_sao_ro_van_duoc_doc_sau_can_bien(self):
        im=cv2.imread('samples/tab_s7_hoi_truong_cuoi.png')
        card,y,q,old=cat_the_hoi_truong(im,kem_chat_luong=True)[0]
        self.assertTrue(q['day_du'])
        self.assertEqual(D.ThuVien().danh_gia_khung(card,chat_luong_cat=q)['khung'],1)
