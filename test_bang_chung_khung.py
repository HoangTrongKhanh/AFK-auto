"""Quy tắc mới giữ trạng thái chưa rõ khi các bằng chứng mâu thuẫn."""
import unittest
from unittest.mock import patch
from bang_chung_khung import quyet_dinh_v2

class TestBangChungKhung(unittest.TestCase):
    def decide(self,evidence,star,learned):
        with patch('bang_chung_khung.bang_chung',return_value=evidence):
            return quyet_dinh_v2(None,None,star,learned)['khung']

    def test_giong_sao_tren_toc_khong_du_de_ket_luan_co_khung(self):
        plain=dict(nen_canh=.05,vang_canh=.05,vang_goc=.05,dien_tich_sao_xanh=0)
        self.assertEqual(self.decide(plain,dict(diem=.81,sao_tin_cay=True),dict(khung=None)),0)
        self.assertIsNone(self.decide(plain,dict(diem=.81,sao_tin_cay=True),dict(khung=1)))

    def test_sao_xanh_va_mau_khong_khung_mau_thuan_giu_chua_ro(self):
        blue=dict(nen_canh=.5,vang_canh=.3,vang_goc=.3,dien_tich_sao_xanh=40)
        star=dict(diem=.8,sao_tin_cay=True)
        self.assertIsNone(self.decide(blue,star,dict(khung=0)))
        self.assertEqual(self.decide(blue,star,dict(khung=None)),1)

    def test_vien_trang_tri_khong_du_de_ket_luan_neu_khong_co_sao(self):
        ornate=dict(nen_canh=.5,vang_canh=.3,vang_goc=.3,dien_tich_sao_xanh=0)
        self.assertIsNone(self.decide(ornate,dict(diem=.6,sao_tin_cay=False),None))

if __name__=='__main__':unittest.main()
