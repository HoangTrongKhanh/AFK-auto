import json
from pathlib import Path
import tempfile
import unittest
import contextlib
import io
from unittest.mock import patch
import cv2
import numpy as np
from quan_ly_mau import KhoMau
from khung_can_python import dac_trung,hoc


class TestKhoMau(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.repo=KhoMau(self.root/'repo')
        self.quality=dict(day_du=True,bien_chuan=[0,0,130,205])
        self.ids=[];features=[];labels=[]
        for n in range(8):
            im=np.full((205,130,3),(20+n*9,110+n*5,190+n),np.uint8)
            label=int(n>=4)
            sid=self.repo.them(im,'frame',label,dict(session='train',label_source='user_confirmed',hero_id=n,group=f'hero:{n}'),quality=self.quality)
            self.repo.duyet(sid,'approved','Nhãn người dùng');self.ids.append(sid)
            features.append(dac_trung(im,self.quality));labels.append(label)
        self.model=self.root/'model.npz';hoc(features,labels,np.arange(8)).luu(self.model)

    def test_trung_anh_khong_tao_mau_moi_va_nhan_mau_thuan_bi_chan(self):
        r=self.repo.doc()[1]['records'][self.ids[0]];image=self.repo.anh(r)
        sid=self.repo.them(image,'frame',0,r['sources'][0],quality=self.quality)
        self.assertEqual(sid,self.ids[0]);self.assertEqual(len(self.repo.doc()[1]['records']),8)
        with self.assertRaises(ValueError):self.repo.them(image,'frame',1,r['sources'][0],quality=self.quality)

    def test_nhan_may_khong_duoc_tu_duyet(self):
        sid=self.repo.them(np.zeros((48,48,3),np.uint8),'face','Test',dict(session='auto',label_source='model_guess'))
        with self.assertRaises(ValueError):self.repo.duyet(sid,'approved','Muốn tự học')

    def test_khong_lay_mau_bi_loai_hoac_tap_kiem_tra(self):
        self.repo.duyet(self.ids[0],'rejected','Ảnh lỗi')
        with self.assertRaises(ValueError):self.repo.phat_hanh(self.model,self.ids)
        self.repo.duyet(self.ids[0],'approved','Đã kiểm tra lại')
        # Một ảnh giữ lại cùng nhóm tướng phải ngăn việc học nhóm đó.
        image=np.zeros((205,130,3),np.uint8)
        self.repo.them(image,'frame',0,dict(session='test',label_source='user_confirmed',group='hero:0'),role='test',quality=self.quality)
        with self.assertRaises(ValueError):self.repo.phat_hanh(self.model,self.ids)

    def test_phien_ban_bat_bien_va_khoi_phuc(self):
        a=self.repo.phat_hanh(self.model,self.ids,evidence={'round':1});self.repo.kich_hoat(a)
        b=self.repo.phat_hanh(self.model,self.ids,evidence={'round':2});self.repo.kich_hoat(b)
        self.assertNotEqual(a,b)
        self.assertEqual(self.repo.hien_tai()[1]['version'],b)
        self.assertEqual(self.repo.khoi_phuc(),a)
        self.assertEqual(self.repo.hien_tai()[1]['version'],a)
        with self.assertRaises(ValueError):self.repo.khoi_phuc()

    def test_ban_hong_khong_thay_the_ban_dang_chay(self):
        a=self.repo.phat_hanh(self.model,self.ids,evidence={'round':1});self.repo.kich_hoat(a)
        before=(self.repo.root/'current.json').read_bytes()
        b=self.repo.phat_hanh(self.model,self.ids,evidence={'round':2})
        (self.repo.root/'versions'/b/'model.npz').write_bytes(b'corrupted')
        with self.assertRaises(ValueError):self.repo.kich_hoat(b)
        self.assertEqual((self.repo.root/'current.json').read_bytes(),before)

    def test_khong_am_tham_fallback_khi_ban_active_bi_hong(self):
        version=self.repo.phat_hanh(self.model,self.ids);self.repo.kich_hoat(version)
        (self.repo.root/'versions'/version/'faces.npz').write_bytes(b'bad')
        with self.assertRaises(ValueError):self.repo.hien_tai()

    def test_loi_ghi_con_tro_giu_nguyen_ban_cu(self):
        a=self.repo.phat_hanh(self.model,self.ids,evidence={'round':1});self.repo.kich_hoat(a)
        b=self.repo.phat_hanh(self.model,self.ids,evidence={'round':2})
        before=(self.repo.root/'current.json').read_bytes()
        with patch('quan_ly_mau.os.replace',side_effect=OSError('disk error')):
            with self.assertRaises(OSError):self.repo.kich_hoat(b)
        self.assertEqual((self.repo.root/'current.json').read_bytes(),before)

    def test_duyet_du_lieu_cu_va_duong_dan_gia_bi_tu_choi(self):
        head,_=self.repo.doc();self.repo.duyet(self.ids[1],'rejected','Loại mẫu')
        with self.assertRaises(ValueError):self.repo.duyet(self.ids[0],'approved','Stale',expected_revision=head)
        with self.assertRaises(ValueError):self.repo.kich_hoat('../escape')

    def test_faces_chi_chua_mau_da_duyet(self):
        good=self.repo.them(np.full((48,48,3),30,np.uint8),'face','Approved',dict(session='faces',label_source='user_confirmed'))
        self.repo.duyet(good,'approved','Xác nhận tên')
        self.repo.them(np.full((48,48,3),80,np.uint8),'face','Pending',dict(session='faces',label_source='user_confirmed'))
        rejected=self.repo.them(np.full((48,48,3),150,np.uint8),'face','Rejected',dict(session='faces',label_source='user_confirmed'))
        self.repo.duyet(rejected,'rejected','Mẫu kém')
        version=self.repo.phat_hanh(self.model,self.ids)
        with np.load(self.repo.root/'versions'/version/'faces.npz',allow_pickle=False) as z:self.assertEqual(z['ten'].tolist(),['Approved'])

    def test_anh_goc_tap_doc_lap_khong_duoc_them_vao_hoc(self):
        self.repo.bao_ve_tap_kiem_tra('test-independent',[],['reserved-source'],'other-account')
        image=np.full((48,48,3),15,np.uint8)
        sid=self.repo.them(image,'face','HeldOut',dict(session='test',label_source='user_confirmed',source_sha256='reserved-source'))
        self.repo.duyet(sid,'approved','Nhãn đúng nhưng không phải dữ liệu học')
        with self.assertRaises(ValueError):self.repo.phat_hanh(self.model,self.ids)

    def test_khong_the_goi_anh_da_hoc_la_kiem_tra_doc_lap(self):
        pixel=self.repo.doc()[1]['records'][self.ids[0]]['pixel_sha256']
        with self.assertRaises(ValueError):self.repo.bao_ve_tap_kiem_tra('test-leaked',[pixel],[],'test')

    def test_hoc_tu_choi_nguon_test_truoc_khi_tao_model(self):
        self.repo.bao_ve_tap_kiem_tra('test-new-set',[],['test-source'],'other')
        image=np.full((205,130,3),90,np.uint8)
        sid=self.repo.them(image,'frame',0,dict(session='test',label_source='user_confirmed',source_sha256='test-source',hero_id=9,group='hero:9'),quality=self.quality)
        self.repo.duyet(sid,'approved','Nhãn đã xác nhận')
        output=self.root/'leaked.npz'
        with self.assertRaises(ValueError):self.repo.huan_luyen(output)
        self.assertFalse(output.exists())

    def test_bang_chung_cua_model_khac_bi_tu_choi(self):
        with self.assertRaises(ValueError):self.repo.phat_hanh(self.model,self.ids,evidence={'model_sha256':'wrong-model'})

    def test_quy_tac_co_phien_ban_va_khoi_phuc(self):
        a=self.repo.phat_hanh(self.model,self.ids);self.repo.kich_hoat(a)
        with self.assertRaisesRegex(ValueError,'quy tắc khác'):
            self.repo.phat_hanh(self.model,self.ids,evidence={'inference_policy':'v1'},inference_policy='v2')
        b=self.repo.phat_hanh(self.model,self.ids,evidence={'inference_policy':'v2'},inference_policy='v2')
        self.repo.kich_hoat(b)
        self.assertEqual(self.repo.hien_tai()[1]['inference_policy'],'v2')
        with patch('quan_ly_mau.policy_sha',return_value='changed'):
            with self.assertRaises(ValueError):self.repo.kiem_tra_ban(b)
        with patch('quan_ly_mau.inspect.getsource',return_value='changed decision code'):
            with self.assertRaises(ValueError):self.repo.kiem_tra_ban(b)
        self.assertEqual(self.repo.khoi_phuc(),a)

    def test_quy_tac_ten_va_dien_mao_duoc_giu_theo_phien_ban(self):
        a=self.repo.phat_hanh(self.model,self.ids,inference_policy='v2',name_policy='v1');self.repo.kich_hoat(a)
        with self.assertRaisesRegex(ValueError,'quy tắc tên khác'):
            self.repo.phat_hanh(self.model,self.ids,name_policy='v2',evidence={'name_policy':'v1'})
        for value,variant in [(20,'pham-thap'),(180,'pham-cao')]:
            sid=self.repo.them(np.full((48,48,3),value,np.uint8),'face','Silvina',
                dict(session='fresh',label_source='on_screen_name',appearance_id=variant))
            self.repo.duyet(sid,'approved','Đọc tên trực tiếp')
        b=self.repo.phat_hanh(self.model,self.ids,name_policy='v2');self.repo.kich_hoat(b)
        self.assertEqual(self.repo.hien_tai()[1]['name_policy'],'v2')
        self.assertEqual(self.repo.hien_tai()[1]['inference_policy'],'v2')
        with np.load(self.repo.root/'versions'/b/'faces.npz',allow_pickle=False) as z:
            self.assertEqual(z['ten'].tolist(),['Silvina','Silvina'])
        with patch('quan_ly_mau.name_policy_sha',return_value='modified'):
            with self.assertRaisesRegex(ValueError,'quy tắc tên'):self.repo.kiem_tra_ban(b)
        self.assertEqual(self.repo.khoi_phuc(),a)

    def test_hoc_tu_kho_chi_lay_nhom_da_duyet(self):
        out=self.root/'new-model.npz';result=self.repo.huan_luyen(out)
        self.assertEqual(set(result['training_ids']),set(self.ids))
        version=self.repo.phat_hanh(out,result['training_ids'],expected_revision=result['revision'])
        self.assertTrue((self.repo.root/'versions'/version/'model.npz').exists())

    def test_cli_phat_hanh_doc_sidecar_cua_buoc_hoc(self):
        from quan_ly_mau import main
        output=self.root/'candidate.npz';self.repo.huan_luyen(output)
        stdout=io.StringIO()
        with patch('sys.argv',['quan_ly_mau.py','--kho',str(self.repo.root),'publish','--model',str(output),'--training-ids',str(output.with_suffix('.training.json'))]),contextlib.redirect_stdout(stdout):
            main()
        self.repo.kiem_tra_ban(json.loads(stdout.getvalue()))

    def test_batch_loi_khong_luu_mot_phan(self):
        before=(self.repo.root/'HEAD.json').read_bytes()
        with self.assertRaises(ValueError):
            self.repo.duyet_nhieu([dict(id=self.ids[0],status='rejected',reason='Loại'),dict(id=self.ids[1],status='approved',reason='')])
        self.assertEqual((self.repo.root/'HEAD.json').read_bytes(),before)

    def test_batch_sua_nhan_khong_phu_thuoc_thu_tu(self):
        old=self.ids[0];r=self.repo.doc()[1]['records'][old]
        self.repo.duyet(old,'rejected','Nhãn cũ sai')
        new=self.repo.them(self.repo.anh(r),'frame',1,r['sources'][0],quality=self.quality)
        self.repo.duyet(new,'approved','Nhãn mới')
        self.repo.duyet_nhieu([dict(id=old,status='approved',reason='Khôi phục nhãn đúng'),dict(id=new,status='rejected',reason='Loại nhãn sửa nhầm')])
        self.assertEqual(self.repo.doc()[1]['records'][old]['status'],'approved')

    def test_mau_bi_loai_khong_quay_lai_tu_tep_ngoai(self):
        import doc_tuong_cua_toi as D
        image=np.full((48,48,3),30,np.uint8)
        sid=self.repo.them(image,'face','LocalApproved',dict(session='faces',label_source='user_confirmed'))
        self.repo.duyet(sid,'approved','Xác nhận tên')
        a=self.repo.phat_hanh(self.model,self.ids);self.repo.kich_hoat(a)
        bank=self.root/'extra.npz';np.savez(bank,mat=np.stack([image,image]),ten=np.array(['LocalApproved','NotApproved']))
        tv=D.ThuVien(bank,kho_mau=self.repo.root)
        self.assertIn('LocalApproved',set(tv.mat));self.assertNotIn('NotApproved',set(tv.mat))
        self.repo.duyet(sid,'rejected','Loại mẫu này')
        b=self.repo.phat_hanh(self.model,self.ids);self.repo.kich_hoat(b)
        with patch.object(D,'MAT_XAC_NHAN',self.root):
            cv2.imwrite(str(self.root/'LocalApproved~legacy.png'),image)
            tv=D.ThuVien(bank,kho_mau=self.repo.root)
        self.assertNotIn('LocalApproved',set(tv.mat))


if __name__=='__main__':unittest.main()
