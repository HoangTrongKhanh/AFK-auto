import unittest
from types import SimpleNamespace
from ten_dien_mao import danh_gia_ten
from doc_tuong_cua_toi import gan_ten

class TestTenDienMao(unittest.TestCase):
    def tv(self,scores):return SimpleNamespace(quy_tac_ten='v2',diem=lambda m:scores)

    def test_diem_yeu_khong_day_ten_sai_thanh_goi_y_don(self):
        card=dict(mat=None,trong_doi=False)
        gan_ten([card],self.tv([(.70,'Isabella'),(.38,'Silvina')]),hon_nhi=.04)
        self.assertIsNone(card['ten']);self.assertIsNone(card['goi_y'])
        self.assertEqual(card['ten_chi_tiet']['ly_do'],'can_mau_dien_mao_da_xac_nhan')
        self.assertEqual(len(card['ung_vien_ten']),2)

    def test_mau_dien_mao_khop_chac_van_nhan_dung(self):
        card=dict(mat=None,trong_doi=False)
        gan_ten([card],self.tv([(.97,'Silvina'),(.70,'Isabella')]),hon_nhi=.04)
        self.assertEqual(card['ten'],'Silvina');self.assertEqual(card['ten_chi_tiet']['trang_thai'],'da_nhan')

    def test_dien_mao_hai_tuong_gan_nhau_khong_tu_gan(self):
        card=dict(mat=None,trong_doi=False)
        gan_ten([card],self.tv([(.97,'Silvina'),(.95,'Isabella')]),hon_nhi=.04)
        self.assertIsNone(card['ten']);self.assertEqual(card['ten_chi_tiet']['ly_do'],'hai_ten_qua_gan_nhau')

    def test_khong_nhan_ten_thu_hai_khi_ten_dau_da_dung(self):
        cards=[dict(mat=None,trong_doi=False) for _ in range(2)]
        gan_ten(cards,self.tv([(.97,'Silvina'),(.8,'Isabella')]),hon_nhi=.04)
        self.assertEqual(sum(x['ten']=='Silvina' for x in cards),1)
        unknown=next(x for x in cards if x['ten'] is None)
        self.assertEqual(unknown['ten_chi_tiet']['ly_do'],'ten_da_gan_cho_the_khac')

if __name__=='__main__':unittest.main()
