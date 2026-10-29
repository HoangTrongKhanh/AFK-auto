package vn.afkauto.leoai

import android.os.BatteryManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import org.opencv.core.Core
import org.opencv.core.Mat
import org.opencv.imgcodecs.Imgcodecs
import vn.afkauto.leoai.vision.DocDanhSach
import vn.afkauto.leoai.vision.DocSoAi
import vn.afkauto.leoai.vision.DocThanhTich
import vn.afkauto.leoai.vision.DoiThanhTich
import vn.afkauto.leoai.vision.KHE_X
import vn.afkauto.leoai.vision.KetQua
import vn.afkauto.leoai.vision.REF_H
import vn.afkauto.leoai.vision.REF_W
import vn.afkauto.leoai.vision.SoKhung
import vn.afkauto.leoai.vision.ThuVienTuong
import vn.afkauto.leoai.vision.cungDoi
import vn.afkauto.leoai.vision.dacTrungVien
import vn.afkauto.leoai.vision.daiTuong
import vn.afkauto.leoai.vision.decodeImage
import vn.afkauto.leoai.vision.matTheDanhSach
import vn.afkauto.leoai.vision.timOKhoa
import vn.afkauto.leoai.vision.vungDanhSach
import java.io.File

// Chuyển từ leo_ai.py (bản máy tính đã chạy thật 12/10/2026: Màn AFK 754 → 765, Huyền Linh 765 → 769).
private const val CHO_SAU_BAM = 1500L        // chờ sau mỗi lần bấm để game kịp đổi màn hình
private const val CHO_MUI_TEN = 1200L        // chuyển đội trong Thành Tích (có hiệu ứng trượt)
private const val CHO_DANG_DANH = 3000L      // đang đánh: chụp lại sau bấy nhiêu ms
private const val CHO_KHONG_RO = 2000L       // màn hình chưa nhận ra (đang chuyển cảnh): chờ rồi chụp lại
private const val DOC_LAI_CHUOI = 4             // bảng kết quả Tự Động Xử Lý: đọc lại tối đa bấy nhiêu lần
private const val CHO_XU_LY = 20_000L         // đang Tự Động Xử Lý (game đánh ngầm): chụp lại sau bấy nhiêu ms
private const val CHO_MAN_TAT = 20_000L      // màn hình tắt / game không ở trên cùng: chờ lâu hơn
private const val TRAN_TOI_DA = 300_000L     // trận kéo dài hơn bấy nhiêu ms coi là bất thường (trận tối đa ~90 giây)
private const val KHONG_RO_TOI_DA = 60_000L  // ở màn không nhận ra bấy nhiêu ms thì lưu ảnh và báo
private const val SO_DOI_TOI_DA = 12         // Thành Tích có 10 đội; quá số này là có gì đó sai
private const val DOC_LAI_TOI_DA = 6         // sau khi bấm mũi tên: chụp tối đa bấy nhiêu lần tới khi đọc được đội đứng yên
private const val DI_TOI_TOI_DA = 3          // số đợt bấm bù khi game bỏ qua lần bấm mũi tên
private const val KHOA_CHO_TRUOC_KHI_CHAM = 2  // màn tối mà chưa thấy ổ khóa: chờ bấy nhiêu lần liền rồi mới chạm cho ổ khóa hiện
private const val LOW_BATTERY = 20
private const val PIN_KIEM_TRA = 300_000L
private const val O_LOC_TRAI = 387           // ô tích nằm bên trái dòng chữ lọc (97 so với 484 ở máy gốc)
private const val O_LOC_DUOI = 30            // bấm mép dưới ô tích: băng "18+" ở góc trên trái che nửa trên và chặn lần bấm
private const val THIEU_NUT_TOI_DA = 3       // Màn AFK thiếu nút của một phần bấy nhiêu lần liền thì coi phần đó đã hết ải
private const val DOI_LUC_TOI_DA = 8         // sau khi chép: đọc lực chiến đội tối đa bấy nhiêu lần chờ con số cập nhật
// Đọc danh sách tướng ở màn đội hình (doc_tuong_cua_toi.py): vuốt chậm ~nửa hàng thẻ ở khe giữa 2 cột (máy gốc).
private const val VUOT_TU = 2150
private const val VUOT_DEN = 2000
private const val VUOT_TOI_DA = 60
private const val TEP_TUONG = "tuong_cua_toi.json"
private const val THU_MUC_MAT = "tuong_cua_toi"
private const val UNG_VIEN_TOI_THIEU = 0.45      // thẻ ứng viên của một tướng: khớp mặt ít nhất bấy nhiêu
private const val COT_CSV = "thoi_gian,che_do,ai,loai,vi_tri,doi,luc_ban_ghi,luc_doi,ty_le,tran_thu,thieu_khung,ket_qua,chuoi,giay"

private val TEN_CHE_DO = mapOf("afk" to "Màn AFK", "huyen_linh" to "Thách Đấu Huyền Linh")
// Nút vào từng chế độ ở Màn AFK; hết ải một phần thì phần còn lại thành 1 nút ngang (mẫu khác).
private val NUT_CHE_DO = mapOf("afk" to listOf("man_afk_chien_dau", "man_afk_chien_dau_ngang"),
    "huyen_linh" to listOf("man_afk_huyen_linh"))

// Leo hộ (Đại Diện Tác Chiến): nút vào từng chế độ ở bảng chọn ải của người nhờ.
private val NUT_CHE_DO_HO = mapOf("afk" to listOf("dd_chon_chien_dau"), "huyen_linh" to listOf("dd_chon_huyen_linh"))

/** Tên mẫu nút vào chế độ đang thấy ở Màn AFK (hoặc bảng chọn ải leo hộ với bang = NUT_CHE_DO_HO), null nếu không có. */
private fun nutCheDo(k: KetQua, cheDo: String, bang: Map<String, List<String>> = NUT_CHE_DO) =
    bang.getValue(cheDo).firstOrNull { it in k.nut }

/** "287M" -> 287.0 (triệu). Bản ghi yếu ghi theo K (leo hộ tài khoản nhỏ, 17/10: "66826K") -> 66.826. */
private fun trieu(lucChien: String?): Double? {
    if (lucChien.isNullOrEmpty() || lucChien.last() !in "MK") return null
    val so = lucChien.dropLast(1).takeIf { it.isNotEmpty() && it.all(Char::isDigit) }?.toDouble() ?: return null
    return if (lucChien.last() == 'K') so / 1000 else so
}

/** Leo ải: mỗi vòng chụp màn hình, nhận ra đang ở màn nào rồi làm đúng một việc ở màn đó. */
class Leo(private val svc: BotService) {
    enum class CheDoChay { LEO, MOT_TRAN, XEM_THANH_TICH }

    /** Trạng thái leo của một chế độ ở ải hiện tại. */
    private class CheDo(val ten: String) {
        var doi: DoiThanhTich? = null               // đội đang dùng (null: đội có sẵn của người chơi)
        val daThu = mutableListOf<DoiThanhTich>()   // các đội đã chép ở ải này
        var thua = 0                                // số trận thua liên tiếp của đội đang dùng
        var canDoi = false                          // thua đủ, lần tới vào màn đội hình thì chép đội khác
        var ket = false                             // đã thử hết đội trong Thành Tích ở ải này
        var mangSang = false                        // đội đang dùng là đội vừa thắng ải trước
        var het = false                             // phần này đã hết ải trong giai đoạn (Màn AFK không còn nút của nó)
        var thieuNut = 0                            // số lần liền vào Màn AFK mà không thấy nút của phần này
        var viTri: Int? = null                      // vị trí trong Thành Tích của đội đang dùng lúc chép (1 = đầu)
        // Chép thử (cài đặt nguongLuc): đội vừa chép mà lực chiến đội bạn thấp hơn ngưỡng so với bản ghi thì chưa đánh,
        // chép thử đội khác; hết đội thì đánh các đội đã hoãn theo tỉ lệ lực chiến giảm dần.
        var moiChep = false                         // vừa chép, chưa vào màn đội hình để đọc lực chiến
        var danhNgay = false                        // đội vừa chép là đội đã hoãn (hoặc vòng sau): đánh luôn
        val hoan = mutableListOf<Pair<DoiThanhTich, Double>>()   // đã chép thử nhưng chưa đánh
        val tyLe = mutableListOf<Pair<DoiThanhTich, Double>>()   // mọi đội đã chép ở ải này
        var vong = 0                                // vòng thử đội trong Thành Tích ở ải này (0 = vòng đầu)
        var dsCu: List<DoiThanhTich>? = null        // danh sách Thành Tích đọc lần trước ở ải này
        var daDanh = true                           // đã đánh trận kể từ lần đọc dsCu (game có thể đã đổi thứ tự)
        var ai: Int? = null                         // leo hộ: ải của người nhờ ở chế độ này (đọc ở tiêu đề màn đội hình)
    }

    private val nd get() = svc.nd
    private val tt by lazy { DocThanhTich(svc.nd) }
    private val so by lazy { DocSoAi(svc.nd) }
    private val thuVien by lazy { ThuVienTuong.load { name -> svc.assets.open(name).use { it.readBytes() } } }
    private var soKhung: SoKhung? = null
    private var daThuDocTuong = false               // đã tự đọc danh sách tướng trong lần chạy này
    private val prefs get() = svc.prefs

    private var cheDoChay = CheDoChay.LEO
    private var cd = mapOf<String, CheDo>()
    private var hien = "afk"
    private var tienTrinh: Int? = null
    private var tranTu: Long? = null
    private var tranCheDo: String? = null
    private var daTinh = false
    private var khongRoTu: Long? = null
    private var daBaoKhongRo = false
    private var khoaLan = 0
    private var batDau = 0L
    private var tran = 0
    private var thang = 0
    private var thuaTong = 0
    private var chep = 0
    private var pinLuc = 0L
    private var pinDaBao = false
    private var thieuCaHai = 0                      // số lần liền Màn AFK không có nút nào quen thuộc
    private var vuaChep = false                     // vừa chép đội: lực chiến đội có thể chưa cập nhật
    private var lucTruoc: Double? = null            // lực chiến đội đọc được ngay trước khi mở Thành Tích
    private var tranInfo: List<String>? = null      // thông tin trận đang đánh (để ghi tran.csv), trừ 4 cột cuối
    private var tuDongAi = 0                        // số ải qua được nhờ Tự Động Xử Lý
    private var xuLyTu: Long? = null                // lúc thấy game bắt đầu Tự Động Xử Lý trong chuỗi hiện tại
    private var daTinhChuoi = false                 // đã tính bảng Chiến Đấu Tự Động Hoàn Tất đang hiện
    private var docLaiChuoi = 0                     // số lần đọc lại bảng kết quả chưa đọc được tiến trình
    private var trongChuoi = false                  // game đang (hoặc vừa) Tự Động Xử Lý, trận thua cuối chuỗi chưa tính
    private var leoHo = false                       // leo hộ người khác (Đại Diện Tác Chiến), đọc từ cài đặt lúc bắt đầu
    private var ngoaiPhien = 0                      // leo hộ: số lần liền gặp màn của riêng bạn (đã ra khỏi phiên)
    private var aiHo = 0                            // leo hộ: số ải đã qua cho người nhờ

    private fun now() = svc.uptime()

    private suspend fun <T> cpu(block: () -> T): T = withContext(Dispatchers.Default) { block() }

    private suspend fun chup(): Pair<Mat, KetQua> {
        val img = svc.screenshot()
        return img to cpu { nd.nhanDien(img) }
    }

    private suspend fun bam(k: KetQua, nut: String, cho: Long = CHO_SAU_BAM) {
        // Màn hình đang chuyển (ví dụ màn BẠI vừa bấm ← xong: nút đã mờ đi nhưng chữ BẠI còn): chờ rồi chụp lại.
        val (x, y) = k.nut[nut] ?: run { delay(CHO_KHONG_RO); return }
        svc.tap(x, y)
        delay(cho)
    }

    private fun tenCheDo(c: String?) = TEN_CHE_DO[c] ?: "?"

    private fun moTa(d: DoiThanhTich?) = d?.toString() ?: "đội có sẵn"

    private fun thongKe() = (if (leoHo) "leo hộ $aiHo ải, " else "") +
        "$tran trận, thắng $thang, thua $thuaTong, chép đội $chep lần" +
        (if (tuDongAi > 0) ", $tuDongAi ải nhờ Tự Động Xử Lý" else "") +
        (if (leoHo) ", ải người nhờ: " + cd.values.joinToString { "${tenCheDo(it.ten)} ${it.ai ?: "?"}" }
        else ", ải ${tienTrinh ?: "?"}") + ", ${(now() - batDau) / 60_000} phút"

    private fun trangThai(viec: String) =
        BotStatus.set((if (leoHo) "Leo hộ · " else "") + "Ải ${tienTrinh ?: "?"} · $viec · ${prefs.todayText()}")

    // ---------------------------------------------------------------- vòng chạy

    suspend fun chay(cach: CheDoChay) {
        cheDoChay = cach
        val thuTu = when (prefs.cheDo) {
            "afk" -> listOf("afk")
            "huyen_linh" -> listOf("huyen_linh")
            else -> listOf("huyen_linh", "afk")      // Huyền Linh trước: ít bản ghi cần tướng bạn còn thiếu khung
        }
        cd = thuTu.associateWith { CheDo(it) }
        hien = thuTu.first()
        leoHo = prefs.leoHo
        ngoaiPhien = 0
        aiHo = 0
        tienTrinh = if (leoHo) null else prefs.lastStage.takeIf { it > 0 }
        tranTu = null
        tranCheDo = null
        daTinh = false
        khongRoTu = null
        batDau = now()
        tran = 0; thang = 0; thuaTong = 0; chep = 0; tuDongAi = 0
        xuLyTu = null
        AppLog.i("Bắt đầu ${if (leoHo) "leo hộ" else "leo"} ${thuTu.joinToString(" + ") { tenCheDo(it) }}. Mỗi đội thử ${prefs.thuLai} trận " +
            "(đội mang sang ải mới ${prefs.thuLaiDoiCu} trận), rồi chép đội khác từ Thành Tích.")
        daThuDocTuong = false
        // Leo hộ dùng tướng của người nhờ: khung tướng đọc từ tài khoản của bạn không dùng được.
        soKhung = if (prefs.thieuKhung == "thu" || leoHo) null else napSoKhung()
        if (!dangSac().second) AppLog.i("Máy không cắm sạc: nên cắm sạc khi để bot chạy lâu.")
        try {
            while (true) {
                kiemTraDung()
                kiemTraPin()
                val (img, k) = try {
                    chup()
                } catch (e: ScreenshotFailed) {
                    AppLog.i("Không chụp được màn hình (mã ${e.code}) - thử lại sau ${CHO_MAN_TAT / 1000} giây.")
                    delay(CHO_MAN_TAT)
                    continue
                }
                try {
                    if (k.manHinh != "khong_ro") {
                        khongRoTu = null
                        if (daBaoKhongRo) Notifier.cancel(svc, Notifier.ID_WAITING)
                        daBaoKhongRo = false
                    }
                    if (k.manHinh != "khoa") khoaLan = 0
                    if (k.manHinh !in listOf("thang", "bai", "dai_dien_thang")) daTinh = false
                    if (k.manHinh != "tu_dong_hoan_tat") daTinhChuoi = false
                    // Chuỗi dừng mà không qua ải nào: game không hiện bảng kết quả lẫn màn BẠI, về thẳng màn đội hình.
                    if (trongChuoi && (k.manHinh == "doi_hinh" || k.manHinh == "man_afk")) thuaChuoi()
                    when (k.manHinh) {
                        "khoa" -> xuLyKhoa(img)
                        "nghi" -> { AppLog.i("Màn nghỉ của game - chạm để tiếp tục."); bam(k, "nghi_nhan_tiep_tuc") }
                        "bang_ban_goi" -> {
                            // Bảng bán gói (Kim cương) khi đạt mốc ải: chỉ bấm "Nhấn để thoát", không bao giờ bấm nút mua.
                            AppLog.i("Bảng bán gói của game - bấm \"Nhấn để thoát\" (không mua gì).")
                            bam(k, "nhan_de_thoat")
                        }
                        "phan_thuong_afk" -> { AppLog.i("Nhận phần thưởng AFK."); bam(k, "thuong_nhan") }
                        "ban_do" -> if (leoHo) ngoaiPhienLeoHo(img, "bản đồ thế giới") else {
                            AppLog.i("Đang ở bản đồ thế giới - mở Màn AFK.")
                            bam(k, "ban_do_nut_man_afk", 3000)
                        }
                        "dai_dien_chon" -> xuLyDaiDienChon(img, k)
                        "dai_dien_thang" -> xuLyDaiDienThang(k)
                        "huyen_linh_chon" -> {
                            // Bảng thông tin ải mới (25/10): bấm Chiến Đấu để tiếp tục khi bảng đang mở.
                            if (leoHo) ngoaiPhienLeoHo(img, "bảng chọn ải Huyền Linh")
                            else if (hien != "huyen_linh") bam(k, "nut_quay_lai", 2500)
                            else {
                                AppLog.i("Bảng chọn ải Huyền Linh - bấm Chiến Đấu để tiếp tục.")
                                bam(k, "hl_chon_chien_dau", 2500)
                            }
                        }
                        "man_afk" -> xuLyManAfk(img, k)
                        "doi_hinh" -> xuLyDoiHinh(img, k)
                        "thanh_tich" -> xuLyThanhTich(k)
                        "thanh_tich_trong" -> xuLyThanhTichTrong(img)
                        "tu_dong_hoan_tat" -> xuLyTuDongHoanTat(img)
                        "xu_ly_ngam" -> xuLyNgam()
                        "xu_ly_xong" -> {
                            trongChuoi = true
                            // Chuỗi đánh ngầm đã dừng: bấm nút "Tự Động Xử Lý Đã Hoàn Thành!" ở góc dưới trái bản đồ (chỗ
                            // nút Màn Chơi Đỉnh Cao) để mở bảng kết quả.
                            AppLog.i("Tự Động Xử Lý đã dừng - mở bảng kết quả.")
                            val w = img.cols()
                            svc.tap(128 * w / REF_W, img.rows() - (REF_H - 2490) * w / REF_W)
                            delay(3000)
                        }
                        "dang_danh" -> xuLyDangDanh(img, k)
                        "thang" -> xuLyThang(img, k)
                        "bai" -> xuLyBai(k)
                        else -> xuLyKhongRo(img)
                    }
                } finally {
                    img.release()
                }
            }
        } finally {
            Notifier.cancel(svc, Notifier.ID_WAITING)
            AppLog.i("Tổng kết: ${thongKe()}.")
        }
    }

    private fun kiemTraDung() {
        val gio = prefs.gioToiDa
        if (cheDoChay == CheDoChay.LEO && gio > 0 && now() - batDau > gio * 3_600_000L) throw StopBot("Đã chạy đủ $gio giờ.")
    }

    private fun capNhatTienTrinh(ai: Int?) {
        if (ai == null || ai == tienTrinh) return
        if (tienTrinh != null) AppLog.i("Tiến trình: $tienTrinh → $ai")
        tienTrinh = ai
        prefs.lastStage = ai
        val dung = prefs.dungOAi
        if (cheDoChay == CheDoChay.LEO && dung > 0 && ai >= dung) throw StopBot("Đã tới ải $ai (dừng ở ải $dung theo cài đặt).")
    }

    /** (mức pin %, đang cắm sạc). Xét "đang cắm nguồn" thay vì BatteryManager.isCharging: đo 14/10 trên Tab S7 cắm củ sạc
     *  mà game chạy nặng, pin không lên nên isCharging = false dù máy vẫn đang cắm. */
    private fun dangSac(): Pair<Int, Boolean> {
        val bm = svc.getSystemService(BatteryManager::class.java)
        val tt = svc.registerReceiver(null, android.content.IntentFilter(android.content.Intent.ACTION_BATTERY_CHANGED))
        val cam = (tt?.getIntExtra(BatteryManager.EXTRA_PLUGGED, 0) ?: 0) != 0
        return bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY) to (cam || bm.isCharging)
    }

    private fun kiemTraPin() {
        if (now() - pinLuc < PIN_KIEM_TRA) return
        pinLuc = now()
        val (muc, sac) = dangSac()
        if (!sac && muc in 0..LOW_BATTERY) {
            if (!pinDaBao) {
                AppLog.i("Pin còn $muc% và không sạc.")
                Notifier.show(svc, Notifier.ID_BATTERY, "Pin yếu ($muc%)", "Hãy cắm sạc để bot chạy tiếp; hết pin máy sẽ tắt và bot dừng.")
                pinDaBao = true
            }
        } else if (sac || muc > LOW_BATTERY + 5) {
            if (pinDaBao) Notifier.cancel(svc, Notifier.ID_BATTERY)
            pinDaBao = false
        }
    }

    // ---------------------------------------------------------------- xử lý từng màn hình

    /** Màn hình tối: lớp khóa Game Booster (chạm cho ổ khóa hiện rồi kéo lên), màn hình tắt, hoặc đang chuyển cảnh. */
    private suspend fun xuLyKhoa(img: Mat) {
        if (!svc.screenOn()) {
            AppLog.i("Màn hình đang tắt - hãy bật màn hình. Thử lại sau ${CHO_MAN_TAT / 1000} giây.")
            trangThai("chờ bật màn hình")
            delay(CHO_MAN_TAT)
            return
        }
        var oKhoa = cpu { timOKhoa(img) }
        val w = img.cols()
        val h = img.rows()
        if (oKhoa == null) {
            // Có thể chỉ là màn chuyển cảnh tối: chờ vài lần rồi mới chạm (lớp khóa chặn chạm nên chạm không tới game).
            if (++khoaLan < KHOA_CHO_TRUOC_KHI_CHAM) {
                delay(CHO_KHONG_RO)
                return
            }
            AppLog.i("Màn hình bị che tối (Game Booster khóa?) - mở khóa.")
            svc.tap(w / 2, h / 2)
            delay(600)
            val lai = svc.screenshot()
            oKhoa = cpu { timOKhoa(lai) }
            lai.release()
        } else {
            AppLog.i("Màn hình bị Game Booster khóa - mở khóa.")
        }
        val (x, y) = oKhoa ?: (w / 2 to (h * 0.52).toInt())
        svc.swipe(x, y, x, y - h / 8, 400)
        delay(1000)
        khoaLan = 0
    }

    /** Leo hộ mà gặp màn của riêng bạn (bản đồ, Màn AFK, đội hình của bạn): phiên leo hộ đã kết thúc (17/10: để màn
     *  THẮNG vài phút thì game tự về bản đồ) hoặc chưa mở. Gặp vài lần liền mới dừng, phòng lúc đang chuyển cảnh. */
    private suspend fun ngoaiPhienLeoHo(img: Mat, ten: String) {
        if (++ngoaiPhien >= THIEU_NUT_TOI_DA) {
            svc.saveImage(img, "ngoai-phien-leo-ho", force = true)
            throw StopBot("Đang ở $ten của bạn, không phải phiên leo hộ (phiên đã kết thúc hoặc chưa mở). Bấm Đi ở " +
                "\"Yêu Cầu Đại Diện AFK Liên Hoàn\" trong Trò chuyện Bang Hội rồi chạy lại.")
        }
        delay(CHO_KHONG_RO)
    }

    /** Chế độ đang leo đã kẹt hoặc hết ải: chuyển sang chế độ còn leo được, hết cả thì dừng. */
    private fun doiCheDoNeuCan() {
        val c = cd.getValue(hien)
        if (!c.ket && !c.het) return
        val con = cd.values.filter { !it.ket && !it.het }
        if (con.isEmpty()) {
            val lyDo = cd.values.joinToString("; ") {
                tenCheDo(it.ten) + (if (leoHo && it.ai != null) " ải ${it.ai}" else "") + ": " +
                    if (it.het) "đã hết ải" else "đã thử hết các đội trong Thành Tích"
            }
            throw StopBot(if (leoHo) "Không leo hộ tiếp được ($lyDo)." else "Không leo tiếp được ở ải ${tienTrinh ?: "?"} ($lyDo).")
        }
        hien = con.first().ten
        AppLog.i("Chuyển sang ${tenCheDo(hien)}.")
    }

    /** Leo hộ: bảng chọn ải của người nhờ (thẻ Huyền Linh và thẻ Màn AFK). Hiện khi bấm Đi ở yêu cầu trong Trò chuyện
     *  Bang Hội, và sau mỗi lần bấm Tiếp Theo ở màn THẮNG. */
    private suspend fun xuLyDaiDienChon(img: Mat, k: KetQua) {
        if (!leoHo) throw StopBot("Đang ở bảng chọn ải leo hộ (Đại Diện Tác Chiến): bật \"Leo hộ người khác\" rồi chạy lại.")
        ngoaiPhien = 0
        val coNut = NUT_CHE_DO_HO.keys.filter { nutCheDo(k, it, NUT_CHE_DO_HO) != null }
        for (c in cd.values) {
            if (c.ten in coNut) c.thieuNut = 0
            else if (!c.het && ++c.thieuNut >= THIEU_NUT_TOI_DA) {
                c.het = true
                svc.saveImage(img, "leo-ho-thieu-nut", force = true)
                AppLog.i("Bảng chọn ải không còn nút ${tenCheDo(c.ten)} - coi như người nhờ đã hết ải phần này.")
            }
        }
        doiCheDoNeuCan()
        val nut = nutCheDo(k, hien, NUT_CHE_DO_HO)
        if (nut == null) {
            delay(CHO_KHONG_RO)
            return
        }
        trangThai("${tenCheDo(hien)} · vào ải")
        bam(k, nut, 3000)                       // màn tải "Đang tham gia Đại Diện Tác Chiến" rồi tới màn đội hình
    }

    /** Leo hộ thắng: màn THẮNG có dải "Đại Diện Tác Chiến" và nút Tiếp Theo (mở bảng chọn ải kế), không có tiến trình. */
    private suspend fun xuLyDaiDienThang(k: KetQua) {
        if (!leoHo) throw StopBot("Đang ở màn THẮNG của leo hộ (Đại Diện Tác Chiến): bật \"Leo hộ người khác\" rồi chạy lại.")
        ngoaiPhien = 0
        if (!daTinh && tranCheDo != null) {
            daTinh = true
            val thoiGian = ketThucTran(true)
            thang++
            aiHo++
            val c = cd.getValue(hien)
            AppLog.i("THẮNG$thoiGian! Leo hộ ${tenCheDo(hien)} ải ${c.ai ?: "?"}. [${thongKe()}]")
            sangAiMoi(c, null)
            c.ai = c.ai?.plus(1)                    // đọc lại ở màn đội hình kế
            if (cheDoChay == CheDoChay.MOT_TRAN) throw StopBot("Đã đánh xong 1 trận: THẮNG.")
        } else if (!daTinh) {
            daTinh = true
            AppLog.i("Màn THẮNG leo hộ của trận không do bot bắt đầu - không tính, bấm Tiếp Theo.")
            tranTu = null
        }
        bam(k, "dd_tiep_theo", 3000)            // không bao giờ bấm ←: có thể ra khỏi phiên leo hộ
    }

    private suspend fun xuLyManAfk(img: Mat, k: KetQua) {
        if (leoHo) return ngoaiPhienLeoHo(img, "Màn AFK")
        capNhatTienTrinh(cpu { so.aiManAfk(img) })
        // Mỗi giai đoạn, phần Chiến Đấu và phần Thách Đấu Huyền Linh có số ải giới hạn; hết ải phần nào thì Màn AFK chỉ
        // còn 1 nút ngang. Thiếu nút vài lần liền (không phải do đang chuyển cảnh) mới tính là hết.
        val coNut = NUT_CHE_DO.keys.filter { nutCheDo(k, it) != null }
        if (coNut.isEmpty()) {
            if (++thieuCaHai >= THIEU_NUT_TOI_DA) {
                svc.saveImage(img, "man-afk-mot-nut", force = true)
                throw StopBot("Màn AFK không còn nút Chiến Đấu / Thách Đấu Huyền Linh quen thuộc (có lẽ chỉ còn 1 nút ngang " +
                    "vì một phần đã hết ải). Bot chưa có mẫu cho nút này nên không bấm; ảnh đã lưu trong thư mục debug.")
            }
            delay(CHO_KHONG_RO)
            return
        }
        thieuCaHai = 0
        for (c in cd.values) {
            if (c.ten in coNut) c.thieuNut = 0
            else if (!c.het && ++c.thieuNut >= THIEU_NUT_TOI_DA) {
                c.het = true
                AppLog.i("Màn AFK không còn nút ${tenCheDo(c.ten)} - phần này đã hết ải ở giai đoạn hiện tại.")
            }
        }
        doiCheDoNeuCan()
        val nut = nutCheDo(k, hien)
        if (nut == null) {
            delay(CHO_KHONG_RO)                     // chờ xem nút có thật sự mất không
            return
        }
        bam(k, nut, 2500)
    }

    private suspend fun xuLyDoiHinh(img: Mat, k: KetQua) {
        var c = cd.getValue(hien)
        if (k.daiDien != leoHo) {
            if (leoHo) return ngoaiPhienLeoHo(img, "màn đội hình")
            throw StopBot("Đang ở màn đội hình leo hộ (Đại Diện Tác Chiến): bật \"Leo hộ người khác\" rồi chạy lại.")
        }
        if (leoHo) {
            ngoaiPhien = 0
            val mo = k.cheDo
            if (mo != null && mo != hien && mo in cd) {
                // Nút ← của màn đội hình leo hộ chưa thử (có thể ra hẳn khỏi phiên): leo luôn chế độ đang mở.
                AppLog.i("Đang ở màn đội hình leo hộ ${tenCheDo(mo)} - leo chế độ này.")
                hien = mo
                c = cd.getValue(hien)
            }
            val ai = cpu { so.aiDoiHinh(img) }
            if (ai != null && ai != c.ai) {
                if (c.ai != null) AppLog.i("Leo hộ ${tenCheDo(hien)}: ải ${c.ai} → $ai.")
                c.ai = ai
            }
            tienTrinh = c.ai
        }
        if (k.cheDo != null && k.cheDo != hien) {
            AppLog.i("Đang ở màn đội hình ${tenCheDo(k.cheDo)}, cần ${tenCheDo(hien)} - quay lại.")
            bam(k, "nut_quay_lai", 2500)
            return
        }
        if (c.ket) {
            if (leoHo) {
                doiCheDoNeuCan()                    // chưa rõ nút ← đi đâu: hết đội ở chế độ này thì dừng
                throw StopBot("Leo hộ ${tenCheDo(c.ten)} ải ${c.ai ?: "?"}: đã thử hết các đội trong Thành Tích.")
            }
            bam(k, "nut_quay_lai", 2500)            // về Màn AFK để đổi chế độ hoặc dừng
            return
        }
        // Chưa đọc khung tướng của bạn: đọc một lần ở màn đội hình (1-2 phút, không đánh) để so khung khi chọn đội.
        if (cheDoChay == CheDoChay.LEO && prefs.thieuKhung != "thu" && soKhung == null && !daThuDocTuong && !leoHo) {
            daThuDocTuong = true
            AppLog.i("Chưa có khung tướng của bạn - đọc danh sách tướng trước (một lần).")
            docDanhSachTuong()
            soKhung = napSoKhung()
            return
        }
        if (c.doi == null && !c.canDoi && cpu { tt.doiTrong(img) }) {
            AppLog.i("Đội trống (chưa có tướng nào) - chép đội từ Thành Tích.")
            c.canDoi = true
        }
        if (c.canDoi || cheDoChay == CheDoChay.XEM_THANH_TICH) {
            trangThai("${tenCheDo(hien)} · mở Thành Tích")
            lucTruoc = cpu { tt.lucDoi(img) }
            bam(k, "doi_hinh_thanh_tich", 3000)
            return
        }
        val luc = docLucDoi(img)
        val banGhi = trieu(c.doi?.lucChien)
        val tyLe = if (luc != null && banGhi != null) luc / banGhi else null
        val soSanh = luc?.let { " (đội bạn ${"%.1f".format(it)}M" + (tyLe?.let { t -> " = ${"%.0f".format(t * 100)}% bản ghi)" } ?: ")") } ?: ""
        if (c.moiChep) {
            c.moiChep = false
            c.doi?.let { d -> tyLe?.let { c.tyLe.add(d to it) } }
            // Đo 13/10 (trận đầu của đội chép): lực chiến đội bạn < 90% bản ghi thắng 1/13, 90-100% thắng 4/10, >= 100%
            // thắng 17/26. Chép không mất gì nên chép thử trước, đội yếu để sau.
            val nguong = prefs.nguongLuc / 100.0
            if (nguong > 0 && c.vong == 0 && !c.danhNgay && tyLe != null && tyLe < nguong) {
                AppLog.i("Đội vừa chép$soSanh thấp hơn ${prefs.nguongLuc}% - để sau, chép thử đội khác.")
                c.hoan.add(c.doi!! to tyLe)
                c.canDoi = true
                lucTruoc = luc
                bam(k, "doi_hinh_thanh_tich", 3000)
                return
            }
            c.danhNgay = false
        }
        // Số trong ô đỏ của đường ải (và số sau trong "A → B" ở màn THẮNG) là ải đang phải đánh.
        AppLog.i("${if (leoHo) "Leo hộ" else "Đánh"} ${tenCheDo(hien)} ải ${tienTrinh ?: "?"} với ${moTa(c.doi)}$soSanh.")
        trangThai("${tenCheDo(hien)} · đánh (${moTa(c.doi)})")
        tranInfo = listOf((if (leoHo) "ho_" else "") + hien, (tienTrinh ?: "").toString(),
            if (c.doi == null) "có sẵn" else if (c.mangSang) "mang sang" else "chép", (c.viTri ?: "").toString(),
            moTa(c.doi).replace(",", " "), banGhi?.toString() ?: "", luc?.let { "%.3f".format(java.util.Locale.ROOT, it) } ?: "",
            tyLe?.let { "%.3f".format(java.util.Locale.ROOT, it) } ?: "", (c.thua + 1).toString(), c.doi?.thieuKhung.orEmpty().joinToString(";"))
        bam(k, if (k.daiDien) "dd_doi_hinh_chien_dau" else if (prefs.tuDong) "doi_hinh_tu_dong" else "doi_hinh_chien_dau", 2000)
        tranTu = now()
        tranCheDo = hien
        c.daDanh = true
    }

    /** Lực chiến đội (triệu) ở màn đội hình. Ngay sau khi chép đội, game cập nhật con số chậm một chút (đo 12/10: đọc
     *  ngay thì vẫn ra lực chiến của đội cũ), nên chờ tới khi nó khác số trước khi chép và đứng yên 2 lần liền. */
    private suspend fun docLucDoi(img: Mat): Double? {
        var luc = cpu { tt.lucDoi(img) }
        if (!vuaChep) return luc
        vuaChep = false
        val truoc = lucTruoc
        repeat(DOI_LUC_TOI_DA) {
            val (img2, k2) = chup()
            val moi = if (k2.manHinh == "doi_hinh") cpu { tt.lucDoi(img2) } else null
            img2.release()
            if (k2.manHinh != "doi_hinh") return luc
            if (moi != null && moi == luc && moi != truoc) return moi
            luc = moi
            delay(400)
        }
        if (luc != null && luc == truoc) AppLog.i("  Lực chiến đội không đổi sau khi chép (${"%.1f".format(luc)}M): đội chép có thể trùng đội đang dùng.")
        return luc
    }

    /** Ghi một dòng vào tran.csv (thư mục files của app) để phân tích chênh lệch lực chiến và tỉ lệ thắng. */
    private fun ghiTran(ketQua: String, giay: Long?, chuoi: Int? = null) {
        val info = tranInfo ?: return
        tranInfo = null
        runCatching {
            val f = java.io.File(svc.getExternalFilesDir(null), "tran.csv")
            if (!f.exists()) f.writeText(COT_CSV + "\n")
            val tg = java.time.LocalDateTime.now().format(java.time.format.DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"))
            f.appendText((listOf(tg) + info + listOf(ketQua, chuoi?.toString() ?: "", giay?.toString() ?: "")).joinToString(",") + "\n")
        }
    }

    private suspend fun xuLyDangDanh(img: Mat, k: KetQua) {
        if (prefs.tuDong && k.tuDong && "nut_tu_dong_xu_ly" in k.nut) {
            // Chiến Đấu Tự Động đang chạy: chuyển sang đánh ngầm (game không vẽ cảnh đánh, đỡ tốn pin).
            AppLog.i("Bấm Tự Động Xử Lý (game đánh ngầm các ải tiếp theo tới khi thua).")
            bam(k, "nut_tu_dong_xu_ly", 3000)
            return
        }
        val t = tranTu
        if (t == null) {
            tranTu = now()
            tranCheDo = null
            AppLog.i("Đang có trận đánh dở (không do bot bắt đầu) - chờ kết quả.")
        } else if (now() - t > TRAN_TOI_DA) {
            AppLog.i("Trận kéo dài hơn ${TRAN_TOI_DA / 1000} giây - có thể game bị treo.")
            svc.saveImage(img, "tran-qua-lau", force = true)
            tranTu = now()
        }
        delay(CHO_DANG_DANH)
    }

    private fun soTranToiDa(c: CheDo) = if (c.mangSang) prefs.thuLaiDoiCu else prefs.thuLai

    private fun ketThucTran(win: Boolean, chuoi: Int? = null): String {
        val giay = tranTu?.let { (now() - it) / 1000 }
        tranTu = null
        tranCheDo = null
        tran++
        prefs.addBattle(win)
        ghiTran(if (win) "thang" else "thua", giay, chuoi)
        return giay?.let { " ($it giây)" } ?: ""
    }

    /** Kết quả của trận bot không tự bắt đầu: không gán cho chế độ nào; true để người gọi bấm ← về Màn AFK. */
    private fun ketQuaCu(ten: String): Boolean {
        if (tranCheDo != null) return false
        if (!daTinh) {
            daTinh = true
            AppLog.i("Màn $ten của trận không do bot bắt đầu - không tính, về Màn AFK.")
            tranTu = null
        }
        return true
    }

    private suspend fun xuLyThang(img: Mat, k: KetQua) {
        if (!daTinh && ketQuaCu("THẮNG")) {
            bam(k, "nut_quay_lai", 2500)
            return
        }
        if (!daTinh) {
            daTinh = true
            val thoiGian = ketThucTran(true)
            thang++
            val tien = cpu { so.tienTrinhThang(img) }
            AppLog.i("THẮNG$thoiGian! ${tenCheDo(hien)} " +
                (tien?.let { "tiến trình ${it.first} → ${it.second}" } ?: "(không đọc được tiến trình)") + ". [${thongKe()}]")
            sangAiMoi(cd.getValue(hien), tien?.second)
            if (cheDoChay == CheDoChay.MOT_TRAN) throw StopBot("Đã đánh xong 1 trận: THẮNG.")
        }
        // Đo 25/10: Huyền Linh có nút riêng ở màn THẮNG; màn cũ vẫn dùng Chiến Đấu.
        // Màn thắng còn hiện sau lần bấm thì bấm lại, không coi kết quả vừa tính là trận cũ rồi quay lui.
        bam(k, if ("thang_huyen_linh" in k.nut) "thang_huyen_linh" else "thang_chien_dau", 2500)
    }

    /** Chế độ c vừa thắng sang ải mới: thử lại từ đầu, đội vừa thắng giữ nguyên để đánh tiếp. Không tính đội đang dùng
     *  là đã thử: bản ghi của cùng người chơi ở ải mới có thể xếp vị trí khác. Chế độ kia vẫn ở ải cũ. */
    private fun sangAiMoi(c: CheDo, ai: Int?) {
        c.daThu.clear()
        c.ket = false
        c.canDoi = false
        c.thua = 0
        c.mangSang = true
        c.viTri = null
        c.moiChep = false; c.danhNgay = false
        c.hoan.clear(); c.tyLe.clear()
        c.vong = 0
        c.dsCu = null
        ai?.let { capNhatTienTrinh(it) }
    }

    /** Bảng "Chiến Đấu Tự Động Hoàn Tất / Đã hoàn thành màn xN" khi chuỗi tự động dừng (thua, hoặc bạn tắt). Các ải thắng
     *  trong chuỗi không có màn THẮNG nên tính ở đây: đội mở đầu chuỗi thắng trận đầu nếu tiến trình tăng. */
    private suspend fun xuLyTuDongHoanTat(img: Mat) {
        val tt = cpu { so.tienTrinhTuDong(img) }
        // Bảng vừa mở còn chạy hiệu ứng (14/10: có lần không đọc được số): chờ rồi đọc lại vài lần trước khi đóng.
        if (tt == null && !daTinhChuoi && docLaiChuoi < DOC_LAI_CHUOI) {
            docLaiChuoi++
            delay(1000)
            return
        }
        docLaiChuoi = 0
        if (tt == null && !daTinhChuoi) svc.saveImage(img, "tu-dong-khong-doc-duoc", force = true)
        val soAi = tt?.let { it.second - it.first }
        AppLog.i("Bảng Chiến Đấu Tự Động Hoàn Tất: " +
            (tt?.let { "tiến trình ${it.first} → ${it.second} ($soAi ải)" } ?: "không đọc được tiến trình") + ". Đóng.")
        xuLyTu = null
        if (!daTinhChuoi) {
            daTinhChuoi = true
            val c = cd.getValue(hien)
            if (tt != null && soAi != null && soAi > 0) {
                ketThucTran(true, soAi)
                thang++
                tuDongAi += soAi
                sangAiMoi(c, tt.second)
                // Trận thua làm chuỗi dừng là trận của đội vừa thắng ở ải mới (game không hiện màn BẠI).
                tranInfo = listOf(hien, tt.second.toString(), "mang sang", (c.viTri ?: "").toString(),
                    moTa(c.doi).replace(",", " "), "", "", "", "1", c.doi?.thieuKhung.orEmpty().joinToString(";"))
                tranTu = now()
                tranCheDo = hien
                trongChuoi = true
            }
            if (trongChuoi) thuaChuoi()
            AppLog.i("  [${thongKe()}]")
        }
        bamDongTrong(img)       // "Nhấn để đóng" cùng chỗ với bảng Thành Tích trống
    }

    /** Trận thua làm chuỗi Tự Động Xử Lý dừng (game không hiện màn BẠI): tính như một trận BẠI. */
    private fun thuaChuoi() {
        trongChuoi = false
        val c = cd.getValue(hien)
        ketThucTran(false)
        thuaTong++
        c.thua++
        AppLog.i("Tự Động Xử Lý dừng ở ải ${tienTrinh ?: "?"}: ${moTa(c.doi)} thua ${c.thua}/${soTranToiDa(c)}.")
        if (c.thua >= soTranToiDa(c)) c.canDoi = true
    }

    /** Game đang Tự Động Xử Lý: đánh ngầm từng ải tới khi thua, không vẽ cảnh đánh. Không bấm gì (kể cả khi lớp khóa
     *  Game Booster bật: màn hình tối cho đỡ tốn pin), chỉ chụp lại thưa. */
    private suspend fun xuLyNgam() {
        trongChuoi = true
        if (xuLyTu == null) {
            xuLyTu = now()
            AppLog.i("Game đang Tự Động Xử Lý (đánh ngầm tới khi thua) - chờ.")
            trangThai("${tenCheDo(hien)} · Tự Động Xử Lý")
        }
        if (tranTu != null) tranTu = now()      // chuỗi dài bao lâu cũng không phải trận bị treo
        delay(CHO_XU_LY)
    }

    private suspend fun xuLyBai(k: KetQua) {
        if (leoHo) {
            ngoaiPhien = 0
            if (tranCheDo == null) {
                if (!daTinh) {
                    daTinh = true
                    AppLog.i("Màn BẠI của trận không do bot bắt đầu - không tính, bấm Thử Lại.")
                    tranTu = null
                }
                bam(k, "bai_thu_lai", 2500)
                return
            }
        } else if (ketQuaCu("BẠI")) {
            bam(k, "nut_quay_lai", 2500)
            return
        }
        val c = cd.getValue(hien)
        trongChuoi = false
        if (!daTinh) {
            daTinh = true
            val thoiGian = ketThucTran(false)
            thuaTong++
            c.thua++
            AppLog.i("BẠI$thoiGian: ${tenCheDo(hien)}, ${moTa(c.doi)} thua ${c.thua}/${soTranToiDa(c)}.")
            if (cheDoChay == CheDoChay.MOT_TRAN) throw StopBot("Đã đánh xong 1 trận: BẠI.")
            if (c.thua >= soTranToiDa(c)) c.canDoi = true
        }
        // Leo hộ: Thử Lại về màn đội hình của ải đó (ở đó mở Thành Tích nếu cần đổi đội); nút ← có thể ra khỏi phiên.
        if (c.canDoi && !leoHo) bam(k, "nut_quay_lai", 2500)  // về Màn AFK, vào lại màn đội hình rồi mở Thành Tích
        else bam(k, "bai_thu_lai", 2500)
    }

    private suspend fun xuLyKhongRo(img: Mat) {
        val t = now()
        val tu = khongRoTu ?: t.also { khongRoTu = it }
        if (t - tu > KHONG_RO_TOI_DA && !daBaoKhongRo) {
            daBaoKhongRo = true
            val app = svc.foregroundPackage
            val lyDo = if (app.isNotEmpty() && app != GAME_PACKAGE)
                "Game không ở trên cùng màn hình (đang mở: $app). Hãy mở lại game ở Màn AFK."
            else "Không nhận ra màn hình đã ${KHONG_RO_TOI_DA / 1000} giây (hộp thoại lạ?). Hãy kiểm tra máy."
            AppLog.i(lyDo)
            svc.saveImage(img, "khong-ro", force = true)
            Notifier.show(svc, Notifier.ID_WAITING, "AFK Auto đang chờ bạn", "$lyDo Bot sẽ tự chạy tiếp khi ổn lại.")
            trangThai("chờ: không nhận ra màn hình")
        }
        delay(if (t - tu < KHONG_RO_TOI_DA) CHO_KHONG_RO else CHO_MAN_TAT)
    }

    // ---------------------------------------------------------------- Thành Tích

    private suspend fun xuLyThanhTich(k0: KetQua) {
        val c = cd.getValue(hien)
        if (!(c.canDoi || cheDoChay == CheDoChay.XEM_THANH_TICH)) {
            AppLog.i("Bảng Thành Tích đang mở - đóng lại.")
            bam(k0, "tt_nhan_de_dong")
            return
        }
        val (dau, kDau) = veDoiDau(k0) ?: return
        // Chép nhanh: đội đứng đầu Thành Tích thắng ngay trận đầu ở 13/14 ải (đo 12/10/2026). Game tự xếp các bản ghi
        // theo khả năng thắng của tài khoản và đẩy đội đã thua xuống dưới, nên không cần đọc cả danh sách.
        if (cheDoChay != CheDoChay.XEM_THANH_TICH && dungDuoc(dau, c) && dau.thieuKhung.isNullOrEmpty()) {
            chep(kDau, dau, c, 0)
            return
        }
        // Chưa đánh trận nào từ lần đọc trước (đang chép thử) thì thứ tự đội không đổi: dùng lại danh sách cũ, đi thẳng
        // từ đội đầu tới đội cần chép thay vì đọc lại cả 10 đội.
        val cu = c.dsCu
        val ds: List<DoiThanhTich>
        var k: KetQua
        var dangO: Int?
        if (cu != null && !c.daDanh && cheDoChay != CheDoChay.XEM_THANH_TICH && cungDoi(dau, cu[0])) {
            ds = cu; k = kDau; dangO = 0
        } else {
            val r = docTiep(dau, kDau) ?: return
            ds = r.first; k = r.second; dangO = ds.size - 1
            c.dsCu = ds
            c.daDanh = false
            for ((i, d) in ds.withIndex()) {
                val da = c.daThu.any { cungDoi(d, it) }
                AppLog.i("  Đội ${i + 1}: ${moTa(d)}${if (da) " (đã thử)" else ""}")
            }
        }
        if (cheDoChay == CheDoChay.XEM_THANH_TICH) {
            bam(k, "tt_nhan_de_dong")
            throw StopBot("Đã đọc xong Thành Tích (${ds.size} đội).")
        }
        var chon = chonDoi(ds, c)
        if (chon == null && c.hoan.isNotEmpty()) {
            // Đã chép thử hết: đánh đội đã hoãn có tỉ lệ lực chiến cao nhất.
            val j = c.hoan.indices.maxByOrNull { c.hoan[it].second }!!
            val (doiHoan, tl) = c.hoan.removeAt(j)
            chon = ds.indices.firstOrNull { cungDoi(ds[it], doiHoan) }
            if (chon == null) {
                AppLog.i("  Đội đã chép thử ${moTa(doiHoan)} không còn trong Thành Tích - bỏ qua.")
                return
            }
            AppLog.i("Đã chép thử hết: đánh đội có lực chiến cao nhất còn lại (${"%.0f".format(tl * 100)}% bản ghi).")
            c.danhNgay = true
        } else if (chon == null && c.vong + 1 < prefs.soVong) {
            c.vong++
            c.daThu.clear()
            AppLog.i("Đã đánh hết các đội của ${tenCheDo(hien)} ở ải này - vòng ${c.vong + 1}.")
            chon = chonDoi(ds, c)
        }
        if (chon == null) {
            AppLog.i("Đã thử hết các đội dùng được trong Thành Tích của ${tenCheDo(hien)} ở ải này.")
            c.ket = true
            c.canDoi = false
            bam(k, "tt_nhan_de_dong")
            return
        }
        // Đi từ đội đang đứng (cuối danh sách, hoặc đầu nếu dùng lại danh sách cũ) tới đội đã chọn. Game có lúc bỏ qua
        // một lần bấm mũi tên, nên sau mỗi đợt bấm thì đọc lại xem đang ở đội nào (nhận theo nội dung) rồi bấm bù.
        var kq = k
        var d: DoiThanhTich? = null
        for (lan in 0 until DI_TOI_TOI_DA) {
            val buoc = (dangO ?: break) - chon
            repeat(kotlin.math.abs(buoc)) { bam(kq, if (buoc > 0) "tt_mui_ten_trai" else "tt_mui_ten_phai", CHO_MUI_TEN) }
            val r = chupDoi()
            d = r.first
            kq = r.second
            dangO = if (d == null) null else ds.indices.firstOrNull { cungDoi(d, ds[it]) }
            if (dangO == null || dangO == chon) break
            AppLog.i("  Đang ở đội ${dangO + 1}, cần đội ${chon + 1} - bấm bù.")
        }
        if (d == null || dangO != chon) {
            AppLog.i("  Không tới được đội ${chon + 1} vừa chọn - đọc lại danh sách.")
            c.dsCu = null
            return
        }
        chep(kq, d, c, chon)
    }

    /** Đội nên chép: đội dùng được đầu tiên theo thứ tự của game (vòng sau: tỉ lệ lực chiến đo được cao trước), bản ghi
     *  thiếu khung để sau cùng hoặc bỏ hẳn. null nếu hết đội dùng được. */
    private fun chonDoi(ds: List<DoiThanhTich>, c: CheDo): Int? {
        var ung = ds.indices.filter { dungDuoc(ds[it], c) }
        if (c.vong > 0) {
            fun tl(i: Int) = c.tyLe.filter { cungDoi(it.first, ds[i]) }.maxOfOrNull { it.second } ?: 0.0
            ung = ung.sortedByDescending { tl(it) }
        }
        return ung.firstOrNull { ds[it].thieuKhung.isNullOrEmpty() }
            ?: if (prefs.thieuKhung == "cuoi") ung.firstOrNull() else null
    }

    /** Thành Tích không có bản ghi nào ("Không có bản ghi phù hợp"). Gặp 13/10 ở Màn AFK ải 808: ô lọc bật mà mọi bản ghi
     *  đều có tướng chưa sở hữu, nên không có đội nào chép được. */
    private suspend fun xuLyThanhTichTrong(img: Mat) {
        val c = cd.getValue(hien)
        if (cheDoChay == CheDoChay.XEM_THANH_TICH) {
            bamDongTrong(img)
            throw StopBot("Thành Tích trống: không có đội nào chép được (bản ghi đều có tướng chưa sở hữu).")
        }
        if (c.canDoi) {
            AppLog.i("Thành Tích của ${tenCheDo(hien)} ở ải này không có đội nào chép được (bản ghi đều có tướng chưa sở hữu).")
            c.ket = true
            c.canDoi = false
        }
        bamDongTrong(img)
    }

    /** Chữ "Nhấn để đóng" của bảng Thành Tích trống và bảng Chiến Đấu Tự Động Hoàn Tất nhấp nháy mờ nên không dò bằng
     *  mẫu được: bấm thẳng vào chỗ của nó (bám đáy). */
    private suspend fun bamDongTrong(img: Mat) {
        val w = img.cols()
        svc.tap(w / 2, img.rows() - (REF_H - 2418) * w / REF_W)
        delay(CHO_SAU_BAM)
    }

    private suspend fun chep(k: KetQua, d: DoiThanhTich, c: CheDo, i: Int) {
        AppLog.i("Chép đội ${i + 1}: ${moTa(d)}.")
        bam(k, "tt_sao_chep", 2000)
        c.daThu.add(d)
        c.doi = d
        c.viTri = i + 1
        c.thua = 0
        c.canDoi = false
        c.mangSang = false
        c.moiChep = true
        vuaChep = true
        chep++
    }

    /** Đội chép được: chưa thử ở ải này, không phải Chiến Đấu Thủ Công (bot không tung chiêu tay được), không phải
     *  Cực Hạn nếu đã chọn bỏ qua. */
    private fun dungDuoc(d: DoiThanhTich, c: CheDo) =
        !d.thuCong && d.lucChien != null && c.daThu.none { cungDoi(d, it) } && !(d.nhan == "cuc_han" && prefs.boCucHan)

    /** Chụp lại tới khi đọc được đội và 2 lần đọc liên tiếp giống nhau (thanh thẻ tên còn trượt một lúc sau khi bấm
     *  mũi tên). Trả về (đội hoặc null, kết quả nhận diện mới nhất). */
    private suspend fun chupDoi(): Pair<DoiThanhTich?, KetQua> {
        var truoc: DoiThanhTich? = null
        var k: KetQua? = null
        repeat(DOC_LAI_TOI_DA) {
            val (img, kk) = chup()
            k = kk
            val d = if (kk.manHinh == "thanh_tich") cpu { tt.doc(img) } else null
            if (d?.lucChien != null && d.chuKy != null && truoc != null && cungDoi(d, truoc!!)) {
                soKhung?.let { sk -> d.thieuKhung = cpu { daiTuong(nd, img)?.let { dai -> sk.thieu(dai).also { dai.release() } } } }
                img.release()
                return d to kk
            }
            img.release()
            if (d?.lucChien != null && d.chuKy != null) {
                truoc = d
            } else {
                truoc = null
            }
            delay(300)
        }
        return null to k!!
    }

    /** Chờ bảng đứng yên, bật lọc "chỉ đội đã sở hữu", về đội đầu. Trả về (đội đầu, kết quả nhận diện), hoặc null nếu
     *  có gì bất thường (vòng sau sẽ thử lại). */
    private suspend fun veDoiDau(k0: KetQua): Pair<DoiThanhTich, KetQua>? {
        // Bảng vừa mở còn đang trượt vào: chỉ đọc khi 2 ảnh liên tiếp có bảng ở cùng vị trí.
        val moc = k0.nut["tt_nam_dam"] ?: return null
        val (img, k1) = chup()
        if (k1.manHinh != "thanh_tich" || k1.nut["tt_nam_dam"] != moc) {
            img.release()
            return null
        }
        var d = cpu { tt.doc(img) }
        // Bảng mở sẵn ở đội đầu thì đội này không qua chupDoi: so khung ngay trên ảnh này.
        if (d != null && "tt_mui_ten_trai" !in k1.nut && d.chuKy != null && d.lucChien != null) {
            soKhung?.let { sk -> d.thieuKhung = cpu { daiTuong(nd, img)?.let { dai -> sk.thieu(dai).also { dai.release() } } } }
        }
        img.release()
        if (d == null) return null
        var k = k1
        if (d.locBat == false && "tt_o_loc_chu" in k.nut) {
            AppLog.i("  Bật lọc \"Chỉ hiển thị đội hình đã sở hữu\".")
            val (x, y) = k.nut.getValue("tt_o_loc_chu")
            svc.tap(x - (O_LOC_TRAI * svc.screenWidth() / REF_W), y + (O_LOC_DUOI * svc.screenWidth() / REF_W))
            delay(CHO_SAU_BAM)
            return null
        }
        var dau = false
        for (lan in 0 until SO_DOI_TOI_DA) {
            if ("tt_mui_ten_trai" !in k.nut) {
                dau = true
                break
            }
            bam(k, "tt_mui_ten_trai", CHO_MUI_TEN)
            val r = chupDoi()
            d = r.first ?: return null
            k = r.second
        }
        if (!dau) return null
        if (d!!.chuKy == null || d.lucChien == null) {   // lần đọc đầu chưa chắc đã ổn định: đọc lại cho chắc
            val r = chupDoi()
            d = r.first ?: return null
            k = r.second
        }
        return d to k
    }

    /** Đang ở đội đầu: đọc lần lượt tới đội cuối. Trả về (danh sách, kết quả nhận diện) với màn hình ở đội cuối, hoặc
     *  null nếu có gì bất thường. */
    private suspend fun docTiep(dau: DoiThanhTich, k0: KetQua): Pair<List<DoiThanhTich>, KetQua>? {
        val ds = mutableListOf<DoiThanhTich>()
        var d = dau
        var k = k0
        repeat(SO_DOI_TOI_DA) {
            ds.add(d)
            if ("tt_mui_ten_phai" !in k.nut) return ds to k
            bam(k, "tt_mui_ten_phai", CHO_MUI_TEN)
            val r = chupDoi()
            d = r.first ?: return null
            k = r.second
        }
        AppLog.i("  Thành Tích có hơn $SO_DOI_TOI_DA đội?")
        return null
    }

    // ---------------------------------------------------------------- khung tướng của bạn

    /** Khung tướng của bạn đã đọc (files/tuong_cua_toi.json + ảnh mặt); null nếu chưa có. */
    private fun napSoKhung(): SoKhung? {
        apDungXacNhan()
        val f = File(svc.filesDir, TEP_TUONG)
        val tay = KhungTuong.docTay(svc.filesDir)
        if (!f.exists() && tay.isEmpty()) {
            AppLog.i("Chưa có khung tướng của bạn: bot sẽ đọc danh sách tướng ở màn đội hình.")
            return null
        }
        return runCatching {
            val arr = if (f.exists()) JSONArray(f.readText()) else JSONArray()
            val cuaToi = mutableMapOf<String, Int>()
            val mat = mutableListOf<Pair<Mat, Int>>()
            for (i in 0 until arr.length()) {
                val o = arr.getJSONObject(i)
                val k = o.getInt("khung")
                // Thẻ tướng đang trong đội bị game phủ xanh: khung đọc không tin được, bỏ qua (không coi là thiếu khung).
                if (o.has("ten") && !o.optBoolean("trong_doi")) o.getString("ten").let { cuaToi[it] = maxOf(cuaToi[it] ?: 0, k) }
                if (o.has("mat")) mat.add(decodeImage(File(svc.filesDir, o.getString("mat")).readBytes()) to k)
            }
            // Khung bạn đánh dấu luôn thay kết quả tự đọc (chưa có tướng: coi như không khung, game cũng ẩn bản ghi đó).
            for ((t, k) in tay) cuaToi[t] = if (k == KhungTuong.CO) 1 else 0
            val yeu = cuaToi.filterValues { it == 0 }.keys.sorted()
            AppLog.i("So khung tướng: tướng của bạn không khung: ${yeu.joinToString(", ").ifEmpty { "không có" }}" +
                (if (tay.isNotEmpty()) " (bạn đánh dấu ${tay.size} tướng)." else "."))
            SoKhung(thuVien, cuaToi, mat)
        }.getOrElse {
            AppLog.i("Không đọc được $TEP_TUONG (${it.message}): không so khung tướng.")
            null
        }
    }

    /** Bài thử / đọc lại sau khi nâng phẩm tướng: đọc khung tướng của bạn ở danh sách tướng của màn đội hình. */
    private val daApDung = mutableSetOf<String>()

    /** Thẻ bạn đã xác nhận ở màn hình app (đúng là tướng X, khung K): thêm mặt thẻ vào thư viện và viền thẻ vào bước xếp
     *  khung, để lần đọc danh sách sau nhận đúng ngay. Mỗi tệp chỉ thêm một lần (theo thời gian sửa tệp). */
    private fun apDungXacNhan() {
        for ((ten, xn) in KhungTuong.docXacNhan(svc.filesDir)) {
            val f = File(svc.filesDir, xn.anh)
            val khoa = "$ten|${f.lastModified()}|${xn.khung}"
            if (!f.exists() || khoa in daApDung) continue
            runCatching {
                val anh = decodeImage(f.readBytes())
                thuVien.themMat(ten, matTheDanhSach(anh))
                if (xn.khung == KhungTuong.CO || xn.khung == KhungTuong.KHONG) thuVien.themVien(dacTrungVien(anh), xn.khung)
                anh.release()
                daApDung.add(khoa)
            }.onFailure { AppLog.i("Không dùng được thẻ xác nhận của $ten: ${it.message}") }
        }
    }

    /** Lưu thẻ ứng viên của từng tướng quan trọng (tối đa 3 thẻ giống nhất, thẻ đã gán tên đứng đầu) để bạn xác nhận ở
     *  màn hình app. */
    private fun luuUngVien(ds: List<vn.afkauto.leoai.vision.TuongCuaToi>) {
        val thuMuc = File(svc.filesDir, KhungTuong.THU_MUC_UNG_VIEN).apply { deleteRecursively(); mkdirs() }
        val diem = ds.map { thuVien.diem(it.mat).associate { (d, t) -> t to d } }
        val out = mutableMapOf<String, List<KhungTuong.UngVien>>()
        for (q in KhungTuong.quanTrong(svc)) {
            val chon = ds.indices.filter { (diem[it][q.ten] ?: 0.0) >= UNG_VIEN_TOI_THIEU }
                .sortedWith(compareBy<Int> { ds[it].trongDoi }.thenByDescending { ds[it].ten == q.ten }.thenByDescending { diem[it][q.ten] })
                .take(3)
            out[q.ten] = chon.mapIndexed { j, i ->
                val ten = "${KhungTuong.THU_MUC_UNG_VIEN}/${q.ten}_$j.png"
                Imgcodecs.imwrite(File(thuMuc.parentFile, ten).path, ds[i].anh)
                KhungTuong.UngVien(ten, ds[i].khung, diem[i][q.ten] ?: 0.0, ds[i].trongDoi)
            }
        }
        KhungTuong.ghiUngVien(svc.filesDir, out)
    }

    suspend fun docTuong(): Boolean {
        val ok = docDanhSachTuong()
        if (ok) soKhung = napSoKhung()
        return ok
    }

    /** Mở màn đội hình (nếu đang ở Màn AFK, chưa đánh), về đầu danh sách tướng rồi vuốt dần xuống tới hết, đọc khung và nhận
     *  tướng của từng thẻ, lưu vào files/tuong_cua_toi.json. Vuốt ở khe giữa 2 cột thẻ để không kéo nhầm tướng vào đội, và
     *  so lực chiến đội sau mỗi lần vuốt: đổi là dừng ngay. Trả về true nếu đọc xong. */
    private suspend fun docDanhSachTuong(): Boolean {
        trangThai("đọc khung tướng")
        cpu { apDungXacNhan() }
        var (img, k) = chup()
        val nutAfk = nutCheDo(k, "afk")
        if (k.manHinh == "man_afk" && nutAfk != null) {
            AppLog.i("Mở màn đội hình (chưa đánh).")
            img.release()
            bam(k, nutAfk, 1500)
            for (lan in 0 until 8) {
                val r = chup(); img = r.first; k = r.second
                if (k.manHinh == "doi_hinh") break
                img.release()
                delay(1500)
            }
        }
        if (k.manHinh != "doi_hinh") {
            img.release()
            AppLog.i("Đọc khung tướng: cần mở màn đội hình (hoặc Màn AFK) trước.")
            return false
        }
        val luc = cpu { tt.lucDoi(img) }
        val w = img.cols()
        val h = img.rows()
        val s = w.toDouble() / REF_W
        val x = (KHE_X * s).toInt()
        val ya = h - ((REF_H - VUOT_TU) * s).toInt()
        val yb = h - ((REF_H - VUOT_DEN) * s).toInt()
        suspend fun kiemTra(im: Mat, kk: KetQua, lan: String) {
            val moi = if (kk.manHinh == "doi_hinh") cpu { tt.lucDoi(im) } else null
            if (kk.manHinh != "doi_hinh" || (luc != null && moi != null && moi != luc)) {
                im.release()
                throw StopBot("Đọc khung tướng: sau lần vuốt $lan màn hình / lực chiến đội đã đổi ($luc -> $moi). Kiểm tra lại đội.")
            }
        }
        fun khac(a: Mat, b: Mat): Double {
            val d = Mat()
            Core.absdiff(a, b, d)
            val m = Core.mean(d)
            d.release()
            return (m.`val`[0] + m.`val`[1] + m.`val`[2]) / 3
        }
        // Về đầu danh sách: vuốt ngược tới khi danh sách đứng yên.
        var cu = cpu { vungDanhSach(img) }
        img.release()
        for (lan in 1..VUOT_TOI_DA) {
            svc.swipe(x, yb, x, ya, 250)
            delay(1200)
            val (im, kk) = chup()
            kiemTra(im, kk, "về đầu $lan")
            val moi = cpu { vungDanhSach(im) }
            im.release()
            val dung = khac(moi, cu) < 2.0
            cu.release()
            cu = moi
            if (dung) break
        }
        val doc = DocDanhSach(thuVien)
        run {
            val (im, _) = chup()
            cpu { doc.them(im) }
            im.release()
        }
        for (lan in 1..VUOT_TOI_DA) {
            svc.swipe(x, ya, x, yb, 1000)
            delay(1600)                             // chờ danh sách trôi hết rồi mới chụp
            val (im, kk) = chup()
            kiemTra(im, kk, "$lan")
            val moi = cpu { vungDanhSach(im) }
            val het = khac(moi, cu) < 2.0           // hết danh sách: ảnh không đổi
            cu.release()
            cu = moi
            if (!het) cpu { doc.them(im) }
            im.release()
            if (het) break
        }
        cu.release()
        val ds = cpu { doc.xong() }
        val thuMuc = File(svc.filesDir, THU_MUC_MAT).apply { deleteRecursively(); mkdirs() }
        val arr = JSONArray()
        ds.forEachIndexed { i, t ->
            val o = JSONObject().put("khung", t.khung).put("trong_doi", t.trongDoi)
            t.ten?.let { o.put("ten", it) }
            t.goiY?.let { o.put("goi_y", it) }
            if (!t.trongDoi) {
                val ten = "$THU_MUC_MAT/%03d.png".format(i + 1)
                Imgcodecs.imwrite(File(svc.filesDir, ten).path, t.mat)
                o.put("mat", ten)
            }
            arr.put(o)
        }
        File(svc.filesDir, TEP_TUONG).writeText(arr.toString(1))
        runCatching { luuUngVien(ds) }.onFailure { AppLog.i("Không lưu được thẻ ứng viên: ${it.message}") }
        val cuaToi = ds.filter { !it.trongDoi }.mapNotNull { t -> t.ten?.let { it to t.khung } }
            .groupBy({ it.first }, { it.second }).mapValues { it.value.max() }
        val trongDoi = ds.filter { it.trongDoi && it.ten != null && it.ten !in cuaToi }.mapNotNull { it.ten }.sorted()
        val thieu = cuaToi.filter { (t, kh) -> kh == 0 && (thuVien.coKhung[t] ?: 0.0) >= 0.8 }.keys.sorted()
        AppLog.i("Đọc khung tướng: ${ds.size} thẻ, nhận ra ${cuaToi.size} tướng có trong thư viện. Không khung: " +
            cuaToi.filterValues { it == 0 }.keys.sorted().joinToString(", ").ifEmpty { "không có" } + ".")
        if (thieu.isNotEmpty()) AppLog.i("  Thiếu khung so với bản ghi (bản ghi thường có khung): ${thieu.joinToString(", ")}.")
        if (trongDoi.isNotEmpty()) AppLog.i("  Đang trong đội (thẻ phủ xanh, chưa đọc được khung - đánh dấu ở màn hình app): ${trongDoi.joinToString(", ")}.")
        ds.filter { it.goiY != null }.forEach { AppLog.i("  Chưa chắc: một thẻ giống ${it.goiY} (${"%.2f".format(it.diem)}).") }
        ds.forEach { it.anh.release(); it.mat.release() }
        return true
    }

    // ---------------------------------------------------------------- bài thử

    /** Nhận diện màn hình hiện tại và ghi kết quả vào nhật ký (kèm lưu ảnh). */
    suspend fun nhanDienThu() {
        val t0 = now()
        val (img, k) = chup()
        AppLog.i("Màn hình ${img.cols()}x${img.rows()}: $k (${now() - t0} ms)")
        when (k.manHinh) {
            "man_afk" -> AppLog.i("  Ải: ${cpu { so.aiManAfk(img) } ?: "không đọc được"}")
            "thang" -> AppLog.i("  Tiến trình: ${cpu { so.tienTrinhThang(img) } ?: "không đọc được"}")
            "thanh_tich" -> AppLog.i("  Đội đang hiện: ${cpu { tt.doc(img) } ?: "không đọc được"}")
        }
        svc.saveImage(img, "nhan-dien-${k.manHinh}", force = true)
        img.release()
    }
}
