from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch
from kiem_chung_doc_lap import parse_labels,seal_check,score,check_freeze
from quan_ly_mau import canonical,ghi_json,sha


class TestKiemChungDocLap(unittest.TestCase):
    def test_nhan_can_dung_bo_kiem_tra_va_khong_trung(self):
        self.assertEqual(parse_labels('BO_KIEM_TRA=test-example\n1=0\n2=?','test-example',{1,2}),{1:0,2:None})
        for text in ['1=0','BO_KIEM_TRA=old\n1=0','BO_KIEM_TRA=test-example\n1=1\n1=0','BO_KIEM_TRA=test-example\n3=1']:
            with self.subTest(text=text),self.assertRaises(ValueError):parse_labels(text,'test-example',{1,2})

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        ghi_json(self.root/'dataset.json',dict(items=[{'id':n} for n in range(1,5)],limits='classification only'))
        ghi_json(self.root/'predictions_sealed.json',[dict(id=n,khung=k) for n,k in enumerate([1,0,None,1],1)])
        ghi_json(self.root/'protocol.json',dict(model_sha256='test-model'))
        files={p.name:sha(p.read_bytes()) for p in self.root.iterdir()}
        self.token='test-'+sha(canonical(files))[:16]
        ghi_json(self.root/'seal.json',dict(dataset_id=self.token,files=files))

    def test_nhan_mot_phan_va_chua_ro_khong_bi_tinh_thanh_khong(self):
        with patch('kiem_chung_doc_lap.check_freeze',return_value={'model_sha256':'test-model'}):
            a=score(self.root,f'BO_KIEM_TRA={self.token}\n1=1\n2=0\n3=0')
            self.assertEqual((a['dung'],a['sai'],a['chua_ro']),(2,0,1));self.assertFalse(a['complete'])
            b=score(self.root,f'BO_KIEM_TRA={self.token}\n4=?')
            self.assertEqual(b['nhan_nguoi_dung_chua_ro'],1);self.assertEqual(b['so_nhan_ro'],3)
            self.assertEqual(b['so_tra_loi'],4);self.assertFalse(b['complete'])
            self.assertTrue((self.root/'labels_history'/f"{a['reference_labels_sha256']}.json").exists())
            self.assertTrue((self.root/'labels_history'/f"{b['reference_labels_sha256']}.json").exists())

    def test_nhan_sai_duoc_thong_ke_khong_dung_lua_chon_tay(self):
        with patch('kiem_chung_doc_lap.check_freeze',return_value={'model_sha256':'test-model'}):
            r=score(self.root,f'BO_KIEM_TRA={self.token}\n1=0\n2=1\n3=0\n4=1')
            self.assertEqual((r['dung'],r['sai'],r['chua_ro']),(1,2,1))
            self.assertEqual((r['false_positive'],r['false_negative']),(1,1));self.assertTrue(r['complete'])

    def test_doi_du_doan_sau_khi_gan_nhan_bi_phat_hien(self):
        (self.root/'predictions_sealed.json').write_text('[]')
        with self.assertRaises(ValueError):seal_check(self.root)

    def test_cham_lai_cung_nhan_khong_tao_revision_gia(self):
        with patch('kiem_chung_doc_lap.check_freeze',return_value={'model_sha256':'test-model'}):
            text=f'BO_KIEM_TRA={self.token}\n1=1'
            a=score(self.root,text);b=score(self.root,text)
            self.assertEqual(a['reference_labels_sha256'],b['reference_labels_sha256'])

    def test_cham_du_doan_cu_khong_can_dung_ma_doc_hien_tai(self):
        (self.root/'model.npz').write_bytes(b'frozen')
        ghi_json(self.root/'protocol.json',dict(model_sha256=sha(b'frozen'),
            function_sha256={'danh_gia_khung':'old-code'},dependencies={}))
        self.assertEqual(check_freeze(self.root,runtime=False)['model_sha256'],sha(b'frozen'))
        with self.assertRaisesRegex(ValueError,'Logic đã đổi'):check_freeze(self.root)
        (self.root/'model.npz').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'Mô hình đã đổi'):check_freeze(self.root,runtime=False)


if __name__=='__main__':unittest.main()
