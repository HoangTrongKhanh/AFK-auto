package vn.afkauto.leoai

import android.os.BatteryManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import org.opencv.core.Mat
import vn.afkauto.leoai.vision.DocSoAi
import vn.afkauto.leoai.vision.DocThanhTich
import vn.afkauto.leoai.vision.DoiThanhTich
import vn.afkauto.leoai.vision.KetQua
import vn.afkauto.leoai.vision.REF_W
import vn.afkauto.leoai.vision.cungDoi
import vn.afkauto.leoai.vision.timOKhoa

// Chuyển từ leo_ai.py (bản máy tính đã chạy thật 12/10/2026: Màn AFK 754 → 765, Huyền Linh 765 → 769).
private const val CHO_SAU_BAM = 1500L        // chờ sau mỗi lần bấm để game kịp đổi màn hình
private const val CHO_MUI_TEN = 1200L        // chuyển đội trong Thành Tích (có hiệu ứng trượt)
private const val CHO_DANG_DANH = 3000L      // đang đánh: chụp lại sau bấy nhiêu ms
private const val CHO_KHONG_RO = 2000L       // màn hình chưa nhận ra (đang chuyển cảnh): chờ rồi chụp lại
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
private const val THIEU_NUT_TOI_DA = 3       // Màn AFK thiếu nút của một phần bấy nhiêu lần liền thì coi phần đó đã hết ải
private const val DOI_LUC_TOI_DA = 8         // sau khi chép: đọc lực chiến đội tối đa bấy nhiêu lần chờ con số cập nhật
private const val COT_CSV = "thoi_gian,che_do,ai,loai,vi_tri,doi,luc_ban_ghi,luc_doi,ty_le,tran_thu,ket_qua,giay"

private val TEN_CHE_DO = mapOf("afk" to "Màn AFK", "huyen_linh" to "Thách Đấu Huyền Linh")
private val NUT_CHE_DO = mapOf("afk" to "man_afk_chien_dau", "huyen_linh" to "man_afk_huyen_linh")

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
    }

    private val nd get() = svc.nd
    private val tt by lazy { DocThanhTich(svc.nd) }
    private val so by lazy { DocSoAi(svc.nd) }
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
    private var tranInfo: List<String>? = null      // thông tin trận đang đánh (để ghi tran.csv), trừ 3 cột cuối

    private fun now() = svc.uptime()

    private suspend fun <T> cpu(block: () -> T): T = withContext(Dispatchers.Default) { block() }

    private suspend fun chup(): Pair<Mat, KetQua> {
        val img = svc.screenshot()
        return img to cpu { nd.nhanDien(img) }
    }

    private suspend fun bam(k: KetQua, nut: String, cho: Long = CHO_SAU_BAM) {
        val (x, y) = k.nut.getValue(nut)
        svc.tap(x, y)
        delay(cho)
    }

    private fun tenCheDo(c: String?) = TEN_CHE_DO[c] ?: "?"

    private fun moTa(d: DoiThanhTich?) = d?.toString() ?: "đội có sẵn"

    private fun thongKe() = "$tran trận, thắng $thang, thua $thuaTong, chép đội $chep lần, ải ${tienTrinh ?: "?"}, " +
        "${(now() - batDau) / 60_000} phút"

    private fun trangThai(viec: String) =
        BotStatus.set("Ải ${tienTrinh ?: "?"} · $viec · ${prefs.todayText()}")

    // ---------------------------------------------------------------- vòng chạy

    suspend fun chay(cach: CheDoChay) {
        cheDoChay = cach
        val thuTu = when (prefs.cheDo) {
            "afk" -> listOf("afk")
            "huyen_linh" -> listOf("huyen_linh")
            else -> listOf("afk", "huyen_linh")
        }
        cd = thuTu.associateWith { CheDo(it) }
        hien = thuTu.first()
        tienTrinh = prefs.lastStage.takeIf { it > 0 }
        tranTu = null
        tranCheDo = null
        daTinh = false
        khongRoTu = null
        batDau = now()
        tran = 0; thang = 0; thuaTong = 0; chep = 0
        AppLog.i("Bắt đầu leo ${thuTu.joinToString(" + ") { tenCheDo(it) }}. Mỗi đội thử ${prefs.thuLai} trận " +
            "(đội mang sang ải mới ${prefs.thuLaiDoiCu} trận), rồi chép đội khác từ Thành Tích.")
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
                    if (k.manHinh != "thang" && k.manHinh != "bai") daTinh = false
                    when (k.manHinh) {
                        "khoa" -> xuLyKhoa(img)
                        "nghi" -> { AppLog.i("Màn nghỉ của game - chạm để tiếp tục."); bam(k, "nghi_nhan_tiep_tuc") }
                        "phan_thuong_afk" -> { AppLog.i("Nhận phần thưởng AFK."); bam(k, "thuong_nhan") }
                        "ban_do" -> { AppLog.i("Đang ở bản đồ thế giới - mở Màn AFK."); bam(k, "ban_do_nut_man_afk", 3000) }
                        "man_afk" -> xuLyManAfk(img, k)
                        "doi_hinh" -> xuLyDoiHinh(img, k)
                        "thanh_tich" -> xuLyThanhTich(k)
                        "dang_danh" -> xuLyDangDanh(img)
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

    /** (mức pin %, đang sạc). */
    private fun dangSac(): Pair<Int, Boolean> {
        val bm = svc.getSystemService(BatteryManager::class.java)
        return bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY) to bm.isCharging
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

    private suspend fun xuLyManAfk(img: Mat, k: KetQua) {
        capNhatTienTrinh(cpu { so.aiManAfk(img) })
        // Mỗi giai đoạn, phần Chiến Đấu và phần Thách Đấu Huyền Linh có số ải giới hạn; hết ải phần nào thì Màn AFK chỉ
        // còn 1 nút ngang. Thiếu nút vài lần liền (không phải do đang chuyển cảnh) mới tính là hết.
        val coNut = NUT_CHE_DO.filterValues { it in k.nut }.keys
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
        val c = cd.getValue(hien)
        if (c.ket || c.het) {
            val con = cd.values.filter { !it.ket && !it.het }
            if (con.isEmpty()) throw StopBot("Không leo tiếp được ở ải ${tienTrinh ?: "?"} (" + cd.values.joinToString("; ") {
                "${tenCheDo(it.ten)}: " + if (it.het) "đã hết ải" else "đã thử hết các đội trong Thành Tích"
            } + ").")
            hien = con.first().ten
            AppLog.i("Chuyển sang ${tenCheDo(hien)}.")
        }
        val nut = NUT_CHE_DO.getValue(hien)
        if (nut !in k.nut) {
            delay(CHO_KHONG_RO)                     // chờ xem nút có thật sự mất không
            return
        }
        bam(k, nut, 2500)
    }

    private suspend fun xuLyDoiHinh(img: Mat, k: KetQua) {
        val c = cd.getValue(hien)
        if (k.cheDo != null && k.cheDo != hien) {
            AppLog.i("Đang ở màn đội hình ${tenCheDo(k.cheDo)}, cần ${tenCheDo(hien)} - quay lại.")
            bam(k, "nut_quay_lai", 2500)
            return
        }
        if (c.ket) {
            bam(k, "nut_quay_lai", 2500)            // về Màn AFK để đổi chế độ hoặc dừng
            return
        }
        if (c.canDoi || cheDoChay == CheDoChay.XEM_THANH_TICH) {
            trangThai("${tenCheDo(hien)} · mở Thành Tích")
            lucTruoc = cpu { tt.lucDoi(img) }
            bam(k, "doi_hinh_thanh_tich", 3000)
            return
        }
        val luc = docLucDoi(img)
        val banGhi = c.doi?.lucChien?.takeIf { it.endsWith("M") }?.dropLast(1)?.toDoubleOrNull()
        val tyLe = if (luc != null && banGhi != null) luc / banGhi else null
        val soSanh = luc?.let { " (đội bạn ${"%.1f".format(it)}M" + (tyLe?.let { t -> " = ${"%.0f".format(t * 100)}% bản ghi)" } ?: ")") } ?: ""
        // Số trong ô đỏ của đường ải (và số sau trong "A → B" ở màn THẮNG) là ải đang phải đánh.
        AppLog.i("Đánh ${tenCheDo(hien)} ải ${tienTrinh ?: "?"} với ${moTa(c.doi)}$soSanh.")
        trangThai("${tenCheDo(hien)} · đánh (${moTa(c.doi)})")
        tranInfo = listOf(hien, (tienTrinh ?: "").toString(),
            if (c.doi == null) "có sẵn" else if (c.mangSang) "mang sang" else "chép", (c.viTri ?: "").toString(),
            moTa(c.doi).replace(",", " "), banGhi?.toString() ?: "", luc?.let { "%.3f".format(it) } ?: "",
            tyLe?.let { "%.3f".format(it) } ?: "", (c.thua + 1).toString())
        bam(k, "doi_hinh_chien_dau", 2000)
        tranTu = now()
        tranCheDo = hien
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
    private fun ghiTran(ketQua: String, giay: Long?) {
        val info = tranInfo ?: return
        tranInfo = null
        runCatching {
            val f = java.io.File(svc.getExternalFilesDir(null), "tran.csv")
            if (!f.exists()) f.writeText(COT_CSV + "\n")
            val tg = java.time.LocalDateTime.now().format(java.time.format.DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"))
            f.appendText((listOf(tg) + info + listOf(ketQua, giay?.toString() ?: "")).joinToString(",") + "\n")
        }
    }

    private suspend fun xuLyDangDanh(img: Mat) {
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

    private fun ketThucTran(win: Boolean): String {
        val giay = tranTu?.let { (now() - it) / 1000 }
        tranTu = null
        tranCheDo = null
        tran++
        prefs.addBattle(win)
        ghiTran(if (win) "thang" else "thua", giay)
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
        if (ketQuaCu("THẮNG")) {
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
            // Chế độ vừa thắng sang ải mới: thử lại từ đầu, đội vừa thắng giữ nguyên để đánh tiếp. Không tính đội đang
            // dùng là đã thử: bản ghi của cùng người chơi ở ải mới có thể xếp vị trí khác. Chế độ kia vẫn ở ải cũ.
            val c = cd.getValue(hien)
            c.daThu.clear()
            c.ket = false
            c.canDoi = false
            c.thua = 0
            c.mangSang = true
            c.viTri = null
            tien?.let { capNhatTienTrinh(it.second) }
            if (cheDoChay == CheDoChay.MOT_TRAN) throw StopBot("Đã đánh xong 1 trận: THẮNG.")
        }
        bam(k, "thang_chien_dau", 2500)             // đánh ải kế
    }

    private suspend fun xuLyBai(k: KetQua) {
        if (ketQuaCu("BẠI")) {
            bam(k, "nut_quay_lai", 2500)
            return
        }
        val c = cd.getValue(hien)
        if (!daTinh) {
            daTinh = true
            val thoiGian = ketThucTran(false)
            thuaTong++
            c.thua++
            AppLog.i("BẠI$thoiGian: ${tenCheDo(hien)}, ${moTa(c.doi)} thua ${c.thua}/${soTranToiDa(c)}.")
            if (cheDoChay == CheDoChay.MOT_TRAN) throw StopBot("Đã đánh xong 1 trận: BẠI.")
            if (c.thua >= soTranToiDa(c)) c.canDoi = true
        }
        if (c.canDoi) bam(k, "nut_quay_lai", 2500)  // về Màn AFK, vào lại màn đội hình rồi mở Thành Tích
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
        if (cheDoChay != CheDoChay.XEM_THANH_TICH && dungDuoc(dau, c)) {
            chep(kDau, dau, c, 0)
            return
        }
        val (ds, k) = docTiep(dau, kDau) ?: return
        for ((i, d) in ds.withIndex()) {
            val da = c.daThu.any { cungDoi(d, it) }
            AppLog.i("  Đội ${i + 1}: ${moTa(d)}${if (da) " (đã thử)" else ""}")
        }
        if (cheDoChay == CheDoChay.XEM_THANH_TICH) {
            bam(k, "tt_nhan_de_dong")
            throw StopBot("Đã đọc xong Thành Tích (${ds.size} đội).")
        }
        val chon = ds.indices.firstOrNull { dungDuoc(ds[it], c) }
        if (chon == null) {
            AppLog.i("Đã thử hết các đội dùng được trong Thành Tích của ${tenCheDo(hien)} ở ải này.")
            c.ket = true
            c.canDoi = false
            bam(k, "tt_nhan_de_dong")
            return
        }
        // Đang ở đội cuối danh sách: lùi về đội đã chọn. Game có lúc bỏ qua một lần bấm mũi tên, nên sau mỗi đợt bấm
        // thì đọc lại xem đang ở đội nào (nhận theo nội dung) rồi bấm bù cho tới đúng đội.
        var dangO: Int? = ds.size - 1
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
            return
        }
        chep(kq, d, c, chon)
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
            img.release()
            if (d?.lucChien != null && d.chuKy != null) {
                if (truoc != null && cungDoi(d, truoc!!)) return d to kk
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
        img.release()
        if (d == null) return null
        var k = k1
        if (d.locBat == false && "tt_o_loc_chu" in k.nut) {
            AppLog.i("  Bật lọc \"Chỉ hiển thị đội hình đã sở hữu\".")
            val (x, y) = k.nut.getValue("tt_o_loc_chu")
            svc.tap(x - (O_LOC_TRAI * svc.screenWidth() / REF_W), y)
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
