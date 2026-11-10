import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import cv2
import numpy as np
from nhap_ten_tuong import doc_ten, nhap_ten


class TestNhapTen(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.bank=self.root/'bank'
        raw=b'[{"ten":null}]'
        (self.root/'snapshot.json').write_bytes(raw)
        self.version=hashlib.sha256(raw).hexdigest()[:16]
        (self.root/'danh_sach.json').write_text(json.dumps(dict(phien=self.version,can_bo_sung=[dict(so_the=6,anh='6.png'),dict(so_the=7,anh='7.png')])))
        img=np.random.default_rng(0).integers(0,255,(205,130,3),dtype=np.uint8)
        cv2.imwrite(str(self.root/'6.png'),img);cv2.imwrite(str(self.root/'7.png'),img)

    def test_giu_ten_nhieu_tu_va_bo_qua_chua_ro(self):
        self.assertEqual(doc_ten('6=Lili May\n7=?'),{6:'Lili May',7:None})

    def test_trung_ma_bao_loi(self):
        with self.assertRaises(ValueError):doc_ten('6=A\n6=B')

    def test_ma_la_khong_ghi_mau(self):
        with self.assertRaises(ValueError):nhap_ten(self.root,'6=A\n8=B',self.bank)
        self.assertFalse(self.bank.exists())

    def test_anh_loi_khong_nhap_mot_phan(self):
        (self.root/'7.png').unlink()
        with self.assertRaises(ValueError):nhap_ten(self.root,'6=A\n7=B',self.bank)
        self.assertFalse(self.bank.exists())

    def test_snapshot_doi_khong_ghi_mau(self):
        (self.root/'snapshot.json').write_text('[]')
        with self.assertRaises(ValueError):nhap_ten(self.root,'6=A',self.bank)
        self.assertFalse(self.bank.exists())

    def test_nhap_va_sua_ten_khong_de_nhan_cu(self):
        out=nhap_ten(self.root,'6=A\n7=?',self.bank)
        self.assertEqual(out['con_thieu'],[7])
        nhap_ten(self.root,'6=Lili May',self.bank)
        self.assertEqual(len(list(self.bank.glob('*.png'))),1)
        self.assertTrue(next(self.bank.glob('*.png')).name.startswith('Lili May~'))
        saved=json.loads((self.root/'ten_da_xac_nhan.json').read_text())
        self.assertEqual(saved[0]['ten'],'Lili May')
        self.assertEqual(saved[0]['nguon_nhan'],'nguoi_dung_xac_nhan_ten')
        self.assertEqual(cv2.imread(str(next(self.bank.glob('*.png')))).shape,(48,48,3))
