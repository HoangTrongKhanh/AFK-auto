"""Bảo toàn phiên khung tướng khi đọc rỗng hoặc lỗi ghi giữa chừng."""
import json
from pathlib import Path
import tempfile
import unittest
from collections import Counter
from types import SimpleNamespace
from unittest.mock import patch

import cv2
import numpy as np
import doc_tuong_cua_toi as D


class TestLuuKhung(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for key, value in {'THU_MUC': self.root, 'ANH': self.root / 'tuong_cua_toi',
                           'KET_QUA': self.root / 'tuong_cua_toi.json', 'BASE': self.root}.items():
            mock = patch.object(D, key, value)
            mock.start()
            self.addCleanup(mock.stop)
        D.ANH.mkdir()
        self.old_image = D.ANH / '01.png'
        self.old_image.write_bytes(b'old-image')
        self.old_json = '[{"anh":"tuong_cua_toi/01.png","khung":1}]'
        D.KET_QUA.write_text(self.old_json)
        self.card = dict(the=np.full((205, 130, 3), 80, np.uint8), ten='Rolan',
                         goi_y=None, khung=1, trong_doi=False, diem=.99)

    def assert_old(self):
        self.assertEqual(D.KET_QUA.read_text(), self.old_json)
        self.assertEqual(self.old_image.read_bytes(), b'old-image')
        self.assertEqual(list(D.ANH.glob('phien-*')), [])

    def test_rong_khong_ghi_json_anh_html(self):
        report = self.root / 'tuong_cua_toi.html'
        report.write_text('old-report')
        with self.assertRaises(ValueError):
            D.xuat([], None)
        self.assert_old()
        self.assertEqual(report.read_text(), 'old-report')

    def test_loi_anh_thu_hai_khong_mat_phien_cu(self):
        write = cv2.imwrite
        calls = 0
        def fail_second(path, img):
            nonlocal calls
            calls += 1
            return write(path, img) if calls == 1 else False
        with patch.object(D.cv2, 'imwrite', side_effect=fail_second):
            with self.assertRaises(OSError):
                D.luu_ket_qua([self.card, self.card])
        self.assert_old()

    def test_loi_thay_json_khong_mat_phien_cu(self):
        with patch.object(D.os, 'replace', side_effect=OSError('disk error')):
            with self.assertRaises(OSError):
                D.luu_ket_qua([self.card])
        self.assert_old()
        self.assertEqual(list(self.root.glob('.khung-*')), [])

    def test_thanh_cong_json_chi_toi_anh_da_ghi(self):
        D.luu_ket_qua([self.card])
        rows = json.loads(D.KET_QUA.read_text())
        image = self.root / rows[0]['anh']
        self.assertNotEqual(image, self.old_image)
        np.testing.assert_array_equal(cv2.imread(str(image)), self.card['the'])
        self.assertEqual(rows[0]['ten'], 'Rolan')
        self.assertEqual(self.old_image.read_bytes(), b'old-image')
        # Phiên tiếp theo dùng đường dẫn khác, không sửa ảnh phiên trước.
        D.luu_ket_qua([self.card])
        self.assertNotEqual(json.loads(D.KET_QUA.read_text())[0]['anh'], rows[0]['anh'])
        self.assertTrue(image.exists())

    def test_xac_nhan_ten_chi_hoc_vien_khi_co_khung_tay(self):
        cv2.imwrite(str(self.old_image), self.card['the'])
        D.KET_QUA.write_text(json.dumps([dict(anh='tuong_cua_toi/01.png', khung=1, trong_doi=False)]))
        vien = self.root / 'vien_them.npz'
        for tay, expected in [({}, False), ({'Rolan': -1}, False), ({'Rolan': 0}, True)]:
            with self.subTest(tay=tay), \
                 patch.object(D, 'MAT_XAC_NHAN', self.root / 'mat_xac_nhan'), \
                 patch.object(D, 'VIEN_THEM', vien), \
                 patch.object(D, 'doc_khung_tay', return_value=tay), \
                 patch.object(D, 'ThuVien'), patch.object(D, 'gan_ten'), patch.object(D, 'xuat'), \
                 patch('sys.argv', ['doc_tuong_cua_toi.py', '--xac-nhan', '1=Rolan']):
                D.main()
                self.assertEqual(vien.exists(), expected)
                if expected:
                    with np.load(vien) as z:
                        self.assertEqual(z['nhan'].tolist(), [0])

    def test_xac_nhan_bao_cao_xuat_rieng(self):
        cv2.imwrite(str(self.old_image), self.card['the'])
        D.KET_QUA.write_text(json.dumps([dict(anh='tuong_cua_toi/01.png', khung=1, trong_doi=False)]))
        with patch.object(D, 'MAT_XAC_NHAN', self.root / 'mat_xac_nhan'), \
             patch.object(D, 'VIEN_THEM', self.root / 'vien_them.npz'), \
             patch.object(D, 'doc_khung_tay', return_value={}), \
             patch.object(D, 'ThuVien'), patch.object(D, 'gan_ten'), patch.object(D, 'xuat') as export, \
             patch('sys.argv', ['doc_tuong_cua_toi.py', '--thu-muc-ra', str(self.root), '--xac-nhan', '1=Rolan']):
            D.main()
            export.assert_called_once()
            self.assertTrue(list((self.root / 'mat_xac_nhan').glob('Rolan~*.png')))
            self.assertFalse((self.root / 'vien_them.npz').exists())

    def test_xac_nhan_ten_giu_nhan_khung_va_nguon_nguoi_dung(self):
        cv2.imwrite(str(self.old_image),self.card['the'])
        D.KET_QUA.write_text(json.dumps([dict(anh='tuong_cua_toi/01.png',ten='Old',khung=0,
            khung_tu_doc=1,khung_nguoi_dung={'khung':0,'nguon_nhan':'user'},trong_doi=False)]))
        with patch.object(D,'MAT_XAC_NHAN',self.root/'mat_xac_nhan'), \
             patch.object(D,'VIEN_THEM',self.root/'vien_them.npz'), \
             patch.object(D,'doc_khung_tay',return_value={}), \
             patch.object(D,'ThuVien',return_value=SimpleNamespace(dem=Counter())), \
             patch.object(D,'gan_ten',side_effect=lambda rows,tv:rows), \
             patch('sys.argv',['doc_tuong_cua_toi.py','--xac-nhan','1=NewName']):
            D.main()
        row=json.loads(D.KET_QUA.read_text())[0]
        self.assertEqual(row['ten'],'NewName');self.assertEqual(row['khung'],0)
        self.assertEqual(row['khung_tu_doc'],1);self.assertEqual(row['khung_nguoi_dung']['khung'],0)
        self.assertEqual(row['ten_nguoi_dung']['ten'],'NewName')

    def test_hai_dien_mao_cung_ten_khong_ghi_de_mau_cu(self):
        with patch.object(D,'MAT_XAC_NHAN',self.root/'mat_xac_nhan'), \
             patch.object(D,'VIEN_THEM',self.root/'vien_them.npz'), \
             patch.object(D,'doc_khung_tay',return_value={}), \
             patch.object(D,'ThuVien',return_value=SimpleNamespace(dem=Counter())), \
             patch.object(D,'gan_ten',side_effect=lambda rows,tv:rows):
            for seed,variant in [(1,'pham-thap'),(2,'pham-cao')]:
                card=np.random.default_rng(seed).integers(0,255,(205,130,3),dtype=np.uint8)
                cv2.imwrite(str(self.old_image),card)
                D.KET_QUA.write_text(json.dumps([dict(anh='tuong_cua_toi/01.png',khung=0,trong_doi=False)]))
                with patch('sys.argv',['doc_tuong_cua_toi.py','--xac-nhan','1=Rolan','--dien-mao',variant]):D.main()
        self.assertEqual(len(list((self.root/'mat_xac_nhan').glob('Rolan~*.png'))),2)
        self.assertEqual(json.loads(D.KET_QUA.read_text())[0]['ten_nguoi_dung']['dien_mao'],'pham-cao')


if __name__ == '__main__':
    unittest.main()
