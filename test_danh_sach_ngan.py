import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
import unittest
import cv2
import numpy as np
from hoi_truong import kiem_tra_danh_sach_ngan,chup_hoi_truong


class TestDanhSachNgan(unittest.TestCase):
    def setUp(self):
        rng=np.random.default_rng(19)
        self.cards=[]
        for i in range(3):
            card=rng.integers(0,255,(205,130,3),dtype=np.uint8)
            self.cards.append((card,100+i*308,dict(day_du=True),card))

    def check(self,count=3,top=True,cards=None):
        with patch('hoi_truong.cat_the_hoi_truong',return_value=self.cards if cards is None else cards):
            return kiem_tra_danh_sach_ngan(None,count,top)

    def test_dung_yen_thieu_nguon_hoac_chua_thay_dau_khong_duoc_bao_du(self):
        self.assertFalse(self.check(count=None)['hop_le'])
        self.assertFalse(self.check(top=False)['hop_le'])
        self.assertFalse(self.check(count=48)['hop_le'])
        self.assertFalse(self.check(count=0,cards=[])['hop_le'])

    def test_du_nguon_nhung_the_loi_hoac_dem_trung_khong_duoc_bao_du(self):
        bad=list(self.cards);c=bad[1];bad[1]=(c[0],c[1],dict(day_du=False),c[3])
        self.assertFalse(self.check(cards=bad)['hop_le'])
        self.assertFalse(self.check(cards=[self.cards[0]]*3)['hop_le'])

    def test_du_anh_du_bien_va_so_luong_khop_nguon(self):
        self.assertTrue(self.check()['hop_le'])

    def run_flow(self,values,count=3,top=True,change_after_back=False):
        imgs=[np.full((256,160,3),v,np.uint8) for v in values]
        a,nd=Mock(),Mock();a.game_booster_locked.return_value=False;a.screenshot.side_effect=imgs
        nd.nhan_dien.return_value=SimpleNamespace(man_hinh='hoi_truong',nut={'ht_dau':(0,0)} if top else {})
        calls=[0]
        def cut(im,**kwargs):
            if kwargs.get('kem_chat_luong'):
                calls[0]+=1
                if change_after_back and calls[0]>=3:
                    altered=list(self.cards);c=np.random.default_rng(57).integers(0,255,(205,130,3),dtype=np.uint8)
                    altered[0]=(c,100,dict(day_du=True),c);return altered
                return self.cards
            return [(c[0],c[1]) for c in self.cards]
        proof={}
        with patch('time.sleep'),patch('hoi_truong.cat_the_hoi_truong',side_effect=cut):
            images=chup_hoi_truong(a,nd,so_tuong_du_kien=count,bang_chung_phien=proof,toi_da=5)
        return images,a,proof

    def test_xac_minh_danh_sach_ngan_bang_cuon_hai_chieu(self):
        images,a,proof=self.run_flow([10,10,10,10])
        self.assertEqual(len(images),1);self.assertEqual(a.swipe.call_count,3)
        self.assertEqual(proof['cach_xac_minh'],'so_luong_nguon_va_hai_chieu_dung_yen')
        self.assertTrue(proof['da_xac_minh'])

    def test_danh_sach_dai_bi_ket_khong_duoc_nham_la_ngan(self):
        with self.assertRaisesRegex(RuntimeError,'không phản hồi'):self.run_flow([10,10,10],count=48)
        with self.assertRaisesRegex(RuntimeError,'không phản hồi'):self.run_flow([10,10,10],count=None)
        with self.assertRaisesRegex(RuntimeError,'không phản hồi'):self.run_flow([10,10,10],top=False)

    def test_con_dich_chuyen_khi_thu_nguoc_khong_xac_nhan_ngan(self):
        with self.assertRaisesRegex(RuntimeError,'còn dịch chuyển'):self.run_flow([10,10,10,30])

    def test_so_luong_giu_nguyen_nhung_mat_the_doi_khong_xac_nhan(self):
        with self.assertRaisesRegex(RuntimeError,'còn dịch chuyển'):
            self.run_flow([10,10,10,10],change_after_back=True)

    def test_anh_that_thieu_nguon_khong_tu_bao_nam_tuong_la_da_du(self):
        im=cv2.imread('samples/tab_s7_hoi_truong_tren_cung.png')
        self.assertFalse(kiem_tra_danh_sach_ngan(im,None,True)['hop_le'])
        self.assertFalse(kiem_tra_danh_sach_ngan(im,48,True)['hop_le'])

if __name__=='__main__':unittest.main()
