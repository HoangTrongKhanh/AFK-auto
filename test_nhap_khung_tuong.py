import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from collections import Counter
from types import SimpleNamespace

import cv2
import numpy as np
import doc_tuong_cua_toi as D
from nhap_khung_tuong import chuan_bi, doc_nhan, nhap_khung


class TestNhapKhung(unittest.TestCase):
    def test_zero_va_chua_ro_khong_bi_danh_dong(self):
        parsed = doc_nhan('11=1 # Bonnie\n89=? # Lumont\n95=0 # Indris')
        self.assertEqual(parsed[95], (0, 'Indris'))
        self.assertIsNone(parsed[89][0])
        self.assertEqual(parsed[11][0], 1)

    def test_tu_choi_trung_va_nhan_khong_hop_le(self):
        for text in ['11=1\n11=0', '11=-1', '11=2', '11=true', '11=', 'khong co nhan']:
            with self.subTest(text=text), self.assertRaises(ValueError):
                doc_nhan(text)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root/'source';self.source.mkdir()
        self.out = self.root/'result'
        self.manual = self.root/'khung_tay.json'
        self.manual.write_text(json.dumps({'Rolan': 1, 'Lumont': 1}))
        self.rows = []
        for n, (name, value) in enumerate([('Bonnie', None), ('Indris', 1), ('Lumont', None)], 1):
            cv2.imwrite(str(self.source/f'{n}.png'), np.full((205, 130, 3), n*50, np.uint8))
            self.rows.append(dict(anh=f'{n}.png', ten=name, khung=value, goi_y=None, trong_doi=False, diem=.99))
        self.raw = json.dumps(self.rows).encode()
        (self.source/'tuong_cua_toi.json').write_bytes(self.raw)
        self.digest = hashlib.sha256(self.raw).hexdigest()
        self.review = dict(sha256_json_goc=self.digest, chi_tiet=[dict(so_the=n, ten=r['ten'], sau=r['khung'], can_xac_nhan=True) for n,r in enumerate(self.rows,1)])
        self.review_path = self.root/'review.json';self.review_path.write_text(json.dumps(self.review))

    def test_tu_choi_so_ten_va_snapshot_lech(self):
        for text, digest in [('1=1 # Indris', self.digest), ('4=1', self.digest), ('1=1 # Bonnie', 'wrong')]:
            with self.subTest(text=text), self.assertRaises(ValueError):
                chuan_bi(self.rows, self.review, text, digest)

    def test_khong_nhan_the_ngoai_bang_can_xac_nhan(self):
        self.review['chi_tiet'][0]['can_xac_nhan'] = False
        with self.assertRaises(ValueError):
            chuan_bi(self.rows, self.review, '1=1', self.digest)

    def test_nhap_giu_bang_chung_va_uu_tien_nhan_nguoi_dung(self):
        with patch.object(D, 'ThuVien', return_value=SimpleNamespace(dem=Counter())):
            summary = nhap_khung(self.source, self.review_path, '1=1 # Bonnie\n2=0 # Indris\n3=? # Lumont', self.out, self.manual)
        result = json.loads((self.out/'tuong_cua_toi.json').read_text())
        self.assertEqual([r['khung'] for r in result], [1, 0, None])
        self.assertEqual([r['khung_tu_doc'] for r in result], [None, 1, None])
        self.assertEqual(result[1]['khung_nguoi_dung']['khung'], 0)
        self.assertEqual(summary['nhan_da_xac_nhan'], 2)
        self.assertEqual(json.loads(self.manual.read_text()), {'Rolan': 1, 'Bonnie': 1, 'Indris': 0})
        self.assertEqual((self.source/'tuong_cua_toi.json').read_bytes(), self.raw)
        self.assertIn('Bạn xác nhận', (self.out/'tuong_cua_toi.html').read_text())
        self.assertEqual(len(json.loads((self.out/'khung_da_xac_nhan.json').read_text())), 3)

    def test_anh_thieu_khong_ghi_bao_cao_hoac_nhan_tay(self):
        old = self.manual.read_bytes();(self.source/'3.png').unlink()
        with self.assertRaises(ValueError):
            nhap_khung(self.source, self.review_path, '1=1', self.out, self.manual)
        self.assertFalse(self.out.exists())
        self.assertEqual(self.manual.read_bytes(), old)


if __name__ == '__main__':
    unittest.main()
