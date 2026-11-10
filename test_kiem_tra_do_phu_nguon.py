import unittest
from kiem_tra_do_phu_nguon import doi_chieu

class TestDoPhuNguon(unittest.TestCase):
    def test_cung_so_luong_nhung_gom_trung_khong_duoc_bao_du(self):
        out=doi_chieu([dict(id=1,owned=True,confirmed_group=1),dict(id=2,owned=True,confirmed_group=1)],{1,2})
        self.assertFalse(out['thu_du_trong_phien']);self.assertEqual(out['nhom_chua_co_nguon'],[2])

    def test_anh_chua_doi_chieu_khong_duoc_tu_coi_la_dung(self):
        out=doi_chieu([dict(id=1,owned=True)],{1})
        self.assertFalse(out['thu_du_trong_phien']);self.assertEqual(out['chua_doi_chieu'],[1])

    def test_bo_o_chua_so_huu_va_chi_xac_nhan_khi_mot_mot(self):
        records=[dict(id=1,owned=True,confirmed_group=2),dict(id=2,owned=False),dict(id=3,owned=True,confirmed_group=1)]
        self.assertTrue(doi_chieu(records,{1,2})['thu_du_trong_phien'])
        records.append(dict(id=4,owned=True,confirmed_group=9))
        self.assertFalse(doi_chieu(records,{1,2})['thu_du_trong_phien'])

if __name__=='__main__':unittest.main()
