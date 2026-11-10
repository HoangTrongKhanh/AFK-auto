"""Hồi quy từ ảnh máy thật: viền đại diện động và chữ đóng nhấp nháy."""
import unittest
import cv2
from nhan_dien import NhanDien, SAMPLES
from thanh_tich import DocThanhTich, cung_doi, giong_ten

class TestThanhTichDong(unittest.TestCase):
    def test_cung_doi_khi_di_hai_chieu_va_thu_nho(self):
        nd = NhanDien()
        doc = DocThanhTich(nd)
        for width in (1600, 1080, 800):
            ds = {}
            for name in ('tt-dau', 'tt-phai-3', 'tt-trai-3', 'tt-phai-4', 'tt-trai-4'):
                img = cv2.imread(str(SAMPLES / 'thanh_tich_dong' / f'{name}.png'))
                img = cv2.resize(img, (width, width * 8 // 5), interpolation=cv2.INTER_AREA)
                k = nd.nhan_dien(img)
                self.assertEqual(k.man_hinh, 'thanh_tich', (name, width))
                self.assertIn('tt_nam_dam', k.nut)
                ds[name] = doc.doc(img)
            for i, luc in ((3, '13073M'), (4, '14022M')):
                a, b = ds[f'tt-phai-{i}'], ds[f'tt-trai-{i}']
                self.assertEqual(a.luc_chien, luc)
                self.assertTrue(cung_doi(a, b), (width, i, giong_ten(a.chu_ky, b.chu_ky)))
            self.assertFalse(cung_doi(ds['tt-phai-3'], ds['tt-phai-4']))
            self.assertFalse(ds['tt-phai-3'].thu_cong)
            self.assertTrue(ds['tt-phai-4'].thu_cong)

if __name__ == '__main__':
    unittest.main()
