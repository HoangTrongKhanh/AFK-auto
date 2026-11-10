import csv
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import cv2
import numpy as np
import doc_tuong_cua_toi as D
from bo_sung_mau_tuong import chon_mau, tao_bo_sung


class TestBoSungMau(unittest.TestCase):
    def test_mau_trung_khong_lap(self):
        face = np.random.default_rng(0).integers(0, 255, (48,48,3), dtype=np.uint8)
        out = chon_mau([('a',face),('b',face.copy())], 6)
        self.assertEqual(len(out), 1)

    def test_chon_da_dang_on_dinh_va_gioi_han(self):
        rng = np.random.default_rng(0)
        rows = [(str(i), rng.integers(0, 255, (48,48,3), dtype=np.uint8)) for i in range(8)]
        a, b = chon_mau(rows, 3), chon_mau(list(reversed(rows)), 3)
        self.assertEqual([k for k,m in a], [k for k,m in b])
        self.assertEqual(len(a), 3)

    def test_chi_dung_nhom_da_dat_ten_va_luu_nguon(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'nhom.json').write_text(json.dumps({'s|1|0':1, 's|1|1':2}))
            (root/'ten_tuong.json').write_text(json.dumps({'1':'A'}))
            with (root/'ban_ghi.csv').open('w') as f:
                writer=csv.DictWriter(f,fieldnames=['luot','vi_tri','anh']);writer.writeheader()
                writer.writerow(dict(luot='s',vi_tri='1',anh='a.png'))
            cv2.imwrite(str(root/'a.png'),np.zeros((20,20,3),np.uint8))
            face=np.random.default_rng(0).integers(0,255,(48,48,3),dtype=np.uint8)
            with patch('bo_sung_mau_tuong.T.tach_the',return_value=[(face,face)]*5):
                info=tao_bo_sung(root,root/'bank.npz')
            self.assertEqual(info['so_mat'],1)
            with np.load(root/'bank.npz',allow_pickle=False) as z:
                self.assertEqual(z['ten'].tolist(),['A'])
                self.assertEqual(z['khoa'].tolist(),['s|1|0'])
            tv=D.ThuVien(root/'bank.npz',kho_mau=False)  # Bộ giả lập riêng, không dùng bản phát hành cá nhân.
            self.assertIn('A',tv.mat)
            self.assertEqual(len(tv.mat['A']),1)

    def test_thu_vien_sai_kho_bao_loi(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'bad.npz';np.savez(p,mat=np.zeros((1,10,10,3),np.uint8),ten=np.array(['A']))
            with self.assertRaises(ValueError):D.ThuVien(p)


class TestMauTrucTiep(unittest.TestCase):
    def test_bon_ten_doc_tu_chi_tiet_khong_can_du_doan_nhom(self):
        folder=Path('tests/fixtures/tuong_da_xac_nhan')
        labels=json.loads((folder/'nhan.json').read_text())
        with tempfile.TemporaryDirectory() as tmp:
            bank=Path(tmp)/'bank.npz'
            faces=[cv2.imread(str(folder/o['mat'])) for o in labels.values()]
            np.savez_compressed(bank,mat=np.stack(faces),ten=np.array(list(labels)))
            with patch.object(D,'MAT_XAC_NHAN',Path(tmp)/'empty'):
                tv=D.ThuVien(bank)
            for name,o in labels.items():
                self.assertTrue((folder/o['bang_chung']).exists())
                d,actual=tv.diem(cv2.imread(str(folder/o['mat'])))[0]
                self.assertEqual(actual,name)
                self.assertGreater(d,.99)
