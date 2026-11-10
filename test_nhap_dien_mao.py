import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np,cv2
from nhap_dien_mao import nhap
from quan_ly_mau import KhoMau,sha

class TestNhapDienMao(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.p=Path(self.tmp.name);self.repo=KhoMau(self.p/'repo')
        rng=np.random.default_rng(10);self.cards=[rng.integers(0,255,(205,130,3),dtype=np.uint8) for _ in range(2)]
        cv2.imwrite(str(self.p/'nguon.png'),self.cards[0]);cv2.imwrite(str(self.p/'ten.png'),self.cards[1])
        self.items=[dict(ten='Silvina',ten_doc_tren_man='Silvina',dien_mao='pham-thap',source_image='nguon.png',source_position=1,
            source_sha256=sha((self.p/'nguon.png').read_bytes()),evidence='ten.png',evidence_sha256=sha((self.p/'ten.png').read_bytes()))]
        self.manifest=self.p/'manifest.json'

    def run_import(self):
        self.manifest.write_text(json.dumps(dict(session='development-new',items=self.items)))
        cards=[(c,0,dict(day_du=True),c) for c in self.cards]
        with patch('nhap_dien_mao.cat_the_hoi_truong',return_value=cards):return nhap(self.manifest,self.repo)

    def test_giu_nhieu_dien_mao_va_khong_tu_duyet(self):
        a=self.run_import();self.repo.duyet(a['sample_ids'][0],'approved','Tên hiển thị trực tiếp')
        self.items[0].update(dien_mao='pham-cao',source_position=2)
        b=self.run_import();_,d=self.repo.doc();self.assertEqual(len(d['records']),2)
        self.assertEqual(d['records'][b['sample_ids'][0]]['status'],'pending')
        self.assertEqual(d['records'][a['sample_ids'][0]]['status'],'approved')

    def test_anh_kiem_tra_khong_duoc_them_vao_mau_dien_mao(self):
        self.repo.bao_ve_tap_kiem_tra('test-protected',[],[self.items[0]['source_sha256']],'heldout')
        with self.assertRaisesRegex(ValueError,'bộ kiểm tra'):self.run_import()
        self.assertEqual(len(self.repo.doc()[1]['records']),0)

    def test_anh_doi_sau_xac_nhan_khong_nhap(self):
        cv2.imwrite(str(self.p/'nguon.png'),self.cards[1])
        with self.assertRaisesRegex(ValueError,'đã đổi'):self.run_import()
        self.assertEqual(len(self.repo.doc()[1]['records']),0)

    def test_nhan_khong_khop_hoac_vi_tri_ngoai_anh_khong_nhap_mot_phan(self):
        self.items.append(dict(self.items[0],source_position=7))
        with self.assertRaises(ValueError):self.run_import()
        self.assertEqual(len(self.repo.doc()[1]['records']),0)
        self.items=self.items[:1];self.items[0]['ten_doc_tren_man']='Isabella'
        with self.assertRaises(ValueError):self.run_import()

    def test_cung_anh_hai_ten_khong_tao_mau_mot_phan(self):
        self.items.append(dict(self.items[0],ten='Isabella',ten_doc_tren_man='Isabella'))
        with self.assertRaisesRegex(ValueError,'hai tên'):self.run_import()
        self.assertEqual(len(self.repo.doc()[1]['records']),0)

    def test_ten_hien_thi_dai_giu_ten_rut_gon_da_xac_nhan(self):
        for display,name in [('Smokey & Meerky','Smokey'),('Elijah & Lailah','SS')]:
            with self.subTest(display=display):
                self.items[0].update(ten=name,ten_doc_tren_man=display)
                # Mỗi tên dùng một ảnh riêng, giữ kiểm tra xung đột tên của cùng ảnh.
                self.items[0]['source_position']=1 if name=='Smokey' else 2
                result=self.run_import();r=self.repo.doc()[1]['records'][result['sample_ids'][0]]
                self.assertEqual(r['label'],name);self.assertEqual(r['sources'][0]['displayed_name'],display)

if __name__=='__main__':unittest.main()
