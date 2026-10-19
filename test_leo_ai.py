#!/usr/bin/env python3
"""Kiểm tra logic chọn đội của leo_ai.py trên các đội đọc từ ảnh mẫu Thành Tích (không cần máy).

    .venv/bin/python test_leo_ai.py
"""
import argparse
import dataclasses
import unittest
from unittest import mock

import cv2

from leo_ai import THIEU_NUT_TOI_DA, CheDo, Dung, LeoAi, trieu
from nhan_dien import SAMPLES
from thanh_tich import cung_doi

THU_MUC = SAMPLES / "thanh_tich"


def bot(**kw):
    a = argparse.Namespace(che_do="ca-hai", thu_lai=3, thu_lai_doi_cu=1, so_vong=1, nguong_luc=0, cuc_han="thu",
                           loc=True, tu_dong=False, dung_o_ai=None, gio_toi_da=None, thua_toi_da=None, mot_tran=False,
                           xem_thanh_tich=False, thu_thap_tuong=False, thieu_khung="thu", leo_ho=False)
    for k, v in kw.items():
        setattr(a, k, v)
    return LeoAi(adb=None, a=a)


class TestChonDoi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        b = bot()
        cls.afk = [b.tt.doc(cv2.imread(str(THU_MUC / f"afk_751_{i:02d}.png"))) for i in range(1, 11)]
        cls.hl = [b.tt.doc(cv2.imread(str(THU_MUC / f"hl_515_{i:02d}.png"))) for i in range(1, 11)]

    def chon_het(self, b, ds, cd):
        """Chọn lần lượt tới khi hết đội; trả về danh sách chỉ số theo thứ tự đã chọn."""
        out = []
        while (i := b.chon_doi(ds, cd)) is not None:
            out.append(i)
            cd.da_thu.append(ds[i])
        return out

    def test_huyen_linh_uu_tien_ly_tuong_bo_thu_cong(self):
        # hl: 1 Lý Tưởng/Phù Hợp; 2,3,7,8,10 Thủ Công; 4,5,6 thường; 9 Cực Hạn
        self.assertEqual(self.chon_het(bot(), self.hl, CheDo("huyen_linh")), [0, 3, 4, 5, 8])

    def test_cuc_han_bo(self):
        self.assertEqual(self.chon_het(bot(cuc_han="bo"), self.hl, CheDo("huyen_linh")), [0, 3, 4, 5])
        self.assertNotIn(9, self.chon_het(bot(cuc_han="bo"), self.afk, CheDo("afk")))

    def test_man_afk_theo_thu_tu_cua_game(self):
        self.assertEqual(self.chon_het(bot(), self.afk, CheDo("afk")), list(range(10)))

    def test_doi_da_thu_nhan_theo_noi_dung_khi_thu_tu_doi(self):
        """Lần mở Thành Tích sau, thứ tự đội đổi (E18): đội đã thử vẫn bị bỏ qua dù đứng ở vị trí khác."""
        b, cd = bot(), CheDo("afk")
        cd.da_thu.append(self.afk[0])                      # đã thử WTF (đang ở vị trí 1)
        dao = [self.afk[1], self.afk[0]] + self.afk[2:]    # lần sau WTF ở vị trí 2
        self.assertEqual(b.chon_doi(dao, cd), 0)           # chọn CG•Linus, không chọn lại WTF
        self.assertTrue(cung_doi(dao[1], self.afk[0]))

    def test_thieu_khung(self):
        """Bản ghi có tướng mà bản ghi có khung còn của bạn không khung: để sau cùng (cuoi) hoặc bỏ hẳn (bo)."""
        ds = [dataclasses.replace(d, thieu_khung=["Saida"] if i in (1, 4) else []) for i, d in enumerate(self.afk)]
        self.assertEqual(self.chon_het(bot(thieu_khung="cuoi"), ds, CheDo("afk")), [0, 2, 3, 5, 6, 7, 8, 9, 1, 4])
        self.assertEqual(self.chon_het(bot(thieu_khung="bo"), ds, CheDo("afk")), [0, 2, 3, 5, 6, 7, 8, 9])

    def test_vong_sau_theo_ty_le(self):
        """Vòng 2: đội có tỉ lệ lực chiến đo được cao trước, đội chưa đo theo thứ tự của game."""
        b, cd = bot(), CheDo("afk")
        ds = self.afk
        cd.vong = 1
        cd.ty_le = [(ds[4], 1.05), (ds[2], 0.97), (ds[0], 0.80)]
        self.assertEqual(b.chon_doi(ds, cd), 4)
        cd.da_thu += [ds[4]]
        self.assertEqual(b.chon_doi(ds, cd), 2)
        cd.da_thu += [ds[2]]
        self.assertEqual(b.chon_doi(ds, cd), 0)
        cd.da_thu += [ds[0]]
        self.assertEqual(b.chon_doi(ds, cd), 1)

    def test_so_khung_tren_anh_mau(self):
        """Tài khoản thứ nhất (đọc 13/10, android/vision/src/test/resources/cua_toi.json): Saida không khung, bản ghi luôn
        dùng Saida có khung, nên mọi bản ghi mẫu có Saida bị đánh dấu thiếu khung."""
        import json
        from doc_tuong_cua_toi import SoKhung, ThuVien
        sk = SoKhung.__new__(SoKhung)
        sk.tv, sk.mat_cua_toi = ThuVien(), []
        sk.cua_toi = json.loads((SAMPLES.parent / "android/vision/src/test/resources/cua_toi.json").read_text())
        co_saida = {"afk_751_02", "afk_751_05", "afk_751_06", "hl_515_02", "hl_515_05"}
        for f in sorted(THU_MUC.glob("*.png")):
            thieu = sk.thieu(cv2.imread(str(f)))
            self.assertEqual(thieu, ["Saida"] if f.stem in co_saida else [], f.name)


class AdbGia:
    """Ghi lại các lần bấm thay vì gửi tới máy."""
    def __init__(self):
        self.bam = []

    def tap(self, x, y):
        self.bam.append((x, y))


class TestChepThu(unittest.TestCase):
    def setUp(self):
        self.img = cv2.imread(str(SAMPLES / "tab_s7_doi_hinh_man_afk.png"))     # đội bạn 338.21M
        self.b = bot(nguong_luc=0.95, so_vong=2)
        self.b.adb = AdbGia()
        self.b.hien = "afk"
        self.k = self.b.nd.nhan_dien(self.img)
        self.ban_ghi = self.b.tt.doc(cv2.imread(str(THU_MUC / "afk_751_01.png")))
        cho = mock.patch("leo_ai.time.sleep")        # không chờ thật sau mỗi lần bấm
        cho.start()
        self.addCleanup(cho.stop)

    def vao_doi_hinh(self, luc_chien, danh_ngay=False):
        cd = self.b.cd["afk"]
        cd.doi = dataclasses.replace(self.ban_ghi, luc_chien=luc_chien)
        cd.moi_chep, cd.danh_ngay = True, danh_ngay
        self.b.adb.bam.clear()
        self.b.xu_ly_doi_hinh(self.img, self.k)
        return cd

    def test_doi_yeu_de_sau(self):
        cd = self.vao_doi_hinh("400M")                 # 338/400 = 85% < 95%: chưa đánh, chép thử đội khác
        self.assertEqual(len(cd.hoan), 1)
        self.assertTrue(cd.can_doi)
        self.assertEqual(self.b.adb.bam, [self.k.nut["doi_hinh_thanh_tich"]])
        self.assertIsNone(self.b.tran)

    def test_doi_du_manh_danh_ngay(self):
        cd = self.vao_doi_hinh("340M")                 # 338/340 = 99%
        self.assertEqual(cd.hoan, [])
        self.assertEqual(self.b.adb.bam, [self.k.nut["doi_hinh_chien_dau"]])
        self.assertAlmostEqual(cd.ty_le[0][1], 338.21 / 340, places=3)

    def test_doi_hoan_thi_danh_luon(self):
        cd = self.vao_doi_hinh("400M", danh_ngay=True)
        self.assertEqual(cd.hoan, [])
        self.assertEqual(self.b.adb.bam, [self.k.nut["doi_hinh_chien_dau"]])


class TestTuDong(unittest.TestCase):
    def test_bang_hoan_tat_tinh_cac_ai_da_qua(self):
        """Bảng Chiến Đấu Tự Động Hoàn Tất 217 → 245: tính 28 ải, sang ải 245 với đội đang dùng, rồi đóng bảng."""
        b = bot(tu_dong=True)
        b.adb = AdbGia()
        b.hien = "afk"
        cd = b.cd["afk"]
        cd.thua, cd.da_thu = 0, ["đội cũ"]
        img = cv2.imread(str(SAMPLES / "tab_s7_tu_dong_hoan_tat.png"))
        with mock.patch("leo_ai.time.sleep"), mock.patch("leo_ai.TRAN_CSV", SAMPLES.parent / "debug" / "tran_test.csv"):
            b.xu_ly_tu_dong_hoan_tat(img, b.nd.nhan_dien(img))
            b.xu_ly_tu_dong_hoan_tat(img, b.nd.nhan_dien(img))        # bảng còn hiện: không tính lại
        self.assertEqual(b.tk["tu_dong"], 28)
        self.assertEqual(b.tien_trinh, 245)
        self.assertTrue(cd.mang_sang)
        self.assertEqual(cd.da_thu, [])
        self.assertEqual(b.tk["thua"], 1)             # trận thua làm chuỗi dừng (không có màn BẠI)
        self.assertEqual(cd.thua, 1)
        self.assertTrue(cd.can_doi)                    # đội mang sang chỉ được 1 trận: chép đội khác
        self.assertEqual(len(b.adb.bam), 2)


class TestMotNut(unittest.TestCase):
    def test_huyen_linh_het_ai_thi_sang_chien_dau(self):
        """Huyền Linh đã hết ải (15/10, ải 930): Màn AFK chỉ còn 1 nút Chiến Đấu ngang. Chế độ Cả hai bỏ Huyền Linh và bấm
        nút ngang để leo Màn AFK."""
        b = bot()
        b.adb = AdbGia()
        img = cv2.imread(str(SAMPLES / "tab_s7_man_afk_mot_nut.png"))
        k = b.nd.nhan_dien(img)
        self.assertEqual(b.hien, "huyen_linh")
        with mock.patch("leo_ai.time.sleep"):
            for _ in range(THIEU_NUT_TOI_DA):
                b.xu_ly_man_afk(img, k)
        self.assertTrue(b.cd["huyen_linh"].het)
        self.assertEqual(b.hien, "afk")
        self.assertEqual(b.adb.bam, [k.nut["man_afk_chien_dau_ngang"]])


class TestLeoHo(unittest.TestCase):
    """Leo hộ (Đại Diện Tác Chiến, 17/10): bảng chọn ải → đội hình (tướng của người nhờ) → THẮNG → Tiếp Theo."""
    def setUp(self):
        self.b = bot(leo_ho=True, nguong_luc=0.95)
        self.b.adb = AdbGia()
        cho = mock.patch("leo_ai.time.sleep")
        cho.start()
        self.addCleanup(cho.stop)
        csv = mock.patch("leo_ai.TRAN_CSV", SAMPLES.parent / "debug" / "tran_test.csv")
        csv.start()
        self.addCleanup(csv.stop)

    def man(self, ten):
        img = cv2.imread(str(SAMPLES / f"{ten}.png"))
        return img, self.b.nd.nhan_dien(img)

    def test_chon_huyen_linh_truoc(self):
        img, k = self.man("tab_s7_dai_dien_chon_ai")
        self.b.xu_ly_dai_dien_chon(img, k)
        self.assertEqual(self.b.adb.bam, [k.nut["dd_chon_huyen_linh"]])

    def test_doi_trong_thi_mo_thanh_tich(self):
        img, k = self.man("tab_s7_dai_dien_doi_hinh_hl_trong")
        self.b.xu_ly_doi_hinh(img, k)
        self.assertEqual(self.b.cd["huyen_linh"].ai, 178)
        self.assertEqual(self.b.adb.bam, [k.nut["doi_hinh_thanh_tich"]])

    def test_danh_bang_nut_chien_dau_ngang_roi_tiep_theo(self):
        img, k = self.man("tab_s7_dai_dien_doi_hinh")      # Màn AFK ải 45 của người nhờ, đội có sẵn
        self.b.xu_ly_doi_hinh(img, k)
        self.assertEqual(self.b.hien, "afk")                # đang mở chế độ nào thì leo chế độ đó
        self.assertEqual(self.b.adb.bam, [k.nut["dd_doi_hinh_chien_dau"]])
        self.assertEqual(self.b.tran["che_do"], "ho_afk")
        img, k = self.man("tab_s7_dai_dien_thang")
        self.b.xu_ly_dai_dien_thang(img, k)
        self.b.xu_ly_dai_dien_thang(img, k)                 # màn THẮNG còn hiện: không tính lại
        self.assertEqual(self.b.ai_ho, 1)
        self.assertEqual(self.b.cd["afk"].ai, 46)
        self.assertEqual(self.b.adb.bam[1:], [k.nut["dd_tiep_theo"]] * 2)

    def test_ra_khoi_phien_thi_dung(self):
        img, k = self.man("tab_s7_man_afk")
        with self.assertRaises(Dung):
            for _ in range(THIEU_NUT_TOI_DA):
                self.b.xu_ly_man_afk(img, k)
        self.assertEqual(self.b.adb.bam, [])

    def test_khong_leo_ho_ma_gap_man_leo_ho_thi_dung(self):
        b = bot()
        img, k = self.man("tab_s7_dai_dien_doi_hinh")
        with self.assertRaises(Dung):
            b.xu_ly_doi_hinh(img, k)

    def test_luc_chien_theo_k(self):
        self.assertEqual(trieu("287M"), 287.0)
        self.assertAlmostEqual(trieu("66826K"), 66.826)
        self.assertIsNone(trieu("?5M"))


class TestSoTran(unittest.TestCase):
    def test_doi_mang_sang_it_tran_hon(self):
        b = bot()
        cd = CheDo("afk")
        self.assertEqual(b.so_tran_toi_da(cd), 3)          # đội có sẵn lúc bắt đầu / đội vừa chép
        cd.mang_sang = True
        self.assertEqual(b.so_tran_toi_da(cd), 1)          # đội vừa thắng ải trước


if __name__ == "__main__":
    unittest.main(verbosity=1)
