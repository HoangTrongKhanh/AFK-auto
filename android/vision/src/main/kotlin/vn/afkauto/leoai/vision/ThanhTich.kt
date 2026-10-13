package vn.afkauto.leoai.vision

import org.opencv.core.Core
import org.opencv.core.Mat
import org.opencv.imgproc.Imgproc
import kotlin.math.max
import kotlin.math.min

// Chuyển từ thanh_tich.py: đọc đội đang chọn trong bảng Thành Tích. Thứ tự 10 đội đổi giữa các lần mở bảng, nên bot
// nhận ra đội theo nội dung (chữ ký tên + lực chiến) chứ không theo vị trí.
private val MOC = Box(285, 672, 365, 772)                  // biểu tượng nắm đấm (mẫu "tt_nam_dam")
private val VUNG_LUC_CHIEN = Box(368, 692, 560, 758)
private val VUNG_NHAN = Box(660, 680, 1320, 775)
private val DAI_THE = Box(100, 520, 1500, 545)
private const val TEN_Y0 = 418
private const val TEN_Y1 = 462
private const val THU_CONG_Y0 = 466
private const val THU_CONG_Y1 = 512
private const val LY_TUONG_Y0 = 365
private const val LY_TUONG_Y1 = 405
private const val RONG_THE = 490
private const val TEN_TU_MEP = 150
private val O_LOC = Box(55, 40, 140, 115)
private const val RONG_SO = 0.67
private const val RONG_M = 1.28
private const val RONG_K = 0.95                            // chữ K cuối của lực chiến đội ở màn đội hình
// Lực chiến đội của bạn ở góc trên trái màn đội hình, ví dụ "338,210K" (bám mép trên; dấu phẩy thấp nên tự bị loại).
private val VUNG_LUC_DOI = Box(105, 63, 320, 110)
const val CHU_KY_RONG = 128
const val CHU_KY_CAO = 24
const val GIONG_TEN = 0.85

class DoiThanhTich(
    val chuKy: Bin?,                // chữ ký ảnh tên người chơi (CHU_KY_RONG x CHU_KY_CAO)
    val lucChien: String?,          // ví dụ "287M"
    val nhan: String?,              // "chua_xep_hang" | "cuc_han" | "phu_hop" | null
    val lyTuong: Boolean,
    val thuCong: Boolean,
    val locBat: Boolean?,           // ô lọc "chỉ đội đã sở hữu" đang bật?
) {
    override fun toString(): String {
        val nhanVn = mapOf("chua_xep_hang" to "Chưa Xếp Hạng", "cuc_han" to "Cực Hạn", "phu_hop" to "Phù Hợp Với Tướng")[nhan]
        val them = listOfNotNull(nhanVn, "Lý Tưởng".takeIf { lyTuong }, "Thủ Công".takeIf { thuCong })
        return (listOf(lucChien ?: "?") + them).joinToString(" · ")
    }
}

private fun gianNo(b: Bin) = Bin(b.w, b.h, BooleanArray(b.px.size) { i ->
    val x = i % b.w
    val y = i / b.w
    var hit = false
    for (yy in max(0, y - 1)..min(b.h - 1, y + 1)) for (xx in max(0, x - 1)..min(b.w - 1, x + 1)) if (b[xx, yy]) hit = true
    hit
})

/** Mức giống nhau (0-1) của 2 chữ ký tên: phần nét của ảnh này nằm trong nét (nới 1px) của ảnh kia, lấy chiều thấp hơn. */
fun giongTen(a: Bin?, b: Bin?): Double {
    if (a == null || b == null) return 0.0
    val da = gianNo(a)
    val db = gianNo(b)
    var ab = 0; var ba = 0
    for (i in a.px.indices) {
        if (da.px[i] && b.px[i]) ab++
        if (db.px[i] && a.px[i]) ba++
    }
    return min(ab.toDouble() / max(1, b.count()), ba.toDouble() / max(1, a.count()))
}

/** Hai lần đọc là cùng một đội trong Thành Tích: cùng tên (chữ ký) và cùng lực chiến. */
fun cungDoi(x: DoiThanhTich, y: DoiThanhTich) = giongTen(x.chuKy, y.chuKy) >= GIONG_TEN && x.lucChien == y.lucChien

/** Tách ký tự lực chiến ("287M"): chữ kem sáng trên nền nâu; ký tự dính nhau được cắt theo bề rộng dự kiến. */
fun tachLucChien(vung: Mat, rongCuoi: Double = RONG_M): List<Bin> {
    val bin = Bin.xam(vung) { it > 185 }
    val hops = thanhPhan(bin).filter { it[3] >= bin.h * 0.45 && it[4] >= 20 }.sortedBy { it[0] }
    val out = ArrayList<Bin>()
    for ((i, s) in hops.withIndex()) {
        val (x, y, w, hh) = s
        // Lấy trọn chiều cao các cột của ký tự: ở độ phân giải thấp nét chữ có thể đứt thành mẩu rời (đuôi số 9).
        val mien = bin.crop(x, 0, x + w, bin.h)
        val cuoi = i == hops.size - 1
        val rongM = if (cuoi) min(w.toDouble(), rongCuoi * hh) else 0.0    // lực chiến luôn kết thúc bằng chữ M hoặc K
        val soChuSo = if (rongM > 0) max(0, pyRound((w - rongM) / (RONG_SO * hh))) else max(1, pyRound(w / (RONG_SO * hh)))
        val bien = ArrayList<Int>()
        if (rongM > 0 || soChuSo > 1) {
            val cot = mien.colSums()
            val buoc = (w - rongM) / max(1, soChuSo)
            for (j in 1 until soChuSo + (if (rongM > 0) 1 else 0)) {
                val duKien = (j * buoc).toInt()
                val lo = max(1, duKien - (buoc * 0.3).toInt())
                val hi = min(w - 1, duKien + (buoc * 0.3).toInt())
                var best = lo
                for (c in lo until hi) if (cot[c] < cot[best]) best = c
                bien.add(best)
            }
        }
        val cacBien = listOf(0) + bien + listOf(w)
        for ((c0, c1) in cacBien.zipWithNext()) {
            val p = mien.crop(c0, 0, c1, mien.h)
            if (p.any()) out.add(p.chuanHoa(KY_TU_RONG, KY_TU_CAO, 127))
        }
    }
    return out
}

class DocThanhTich(private val nd: NhanDien) {
    private val chuSo = ChuSo(nd.bo.chuSo)

    private fun khop(vung: Mat, tpl: Mat): Double {
        if (vung.rows() < tpl.rows() || vung.cols() < tpl.cols()) return 0.0
        val r = Mat()
        Imgproc.matchTemplate(vung, tpl, r, Imgproc.TM_CCOEFF_NORMED)
        val v = Core.minMaxLoc(r).maxVal
        r.release()
        return v
    }

    /** Lực chiến đội của bạn ở màn đội hình, tính bằng triệu ("257,943K" -> 257.943); null nếu không đọc được. */
    fun lucDoi(img: Mat): Double? {
        val ref = veGoc(img)
        try {
            val v = ref.cat(VUNG_LUC_DOI.x0.toDouble(), VUNG_LUC_DOI.y0.toDouble(), VUNG_LUC_DOI.x1.toDouble(), VUNG_LUC_DOI.y1.toDouble())
            val s = tachLucChien(v, RONG_K).joinToString("") { chuSo.docKyTu(it).toString() }
            v.release()
            if (s.length < 2 || !s.dropLast(1).all { it.isDigit() } || s.last() !in "KM") return null
            val so = s.dropLast(1).toLong()
            return if (s.last() == 'K') so / 1000.0 else so.toDouble()
        } finally {
            if (ref !== img) ref.release()
        }
    }

    /** Đọc đội đang chọn; null nếu không thấy bảng Thành Tích (không thấy biểu tượng nắm đấm). */
    fun doc(img: Mat): DoiThanhTich? {
        val (small, _) = nd.thuNho(img)
        val moc = nd.tim(small, "tt_nam_dam")
        small.release()
        if (moc.diem < 0.8) return null
        val ref = veGoc(img)
        try {
            val dx = moc.x * 2 - (MOC.x0 + MOC.x1) / 2.0
            val dy = moc.y * 2 - (MOC.y0 + MOC.y1) / 2.0
            fun cat(b: Box) = ref.cat(b.x0 + dx, b.y0 + dy, b.x1 + dx, b.y1 + dy)

            val vlc = cat(VUNG_LUC_CHIEN)
            val so = tachLucChien(vlc).joinToString("") { chuSo.docKyTu(it).toString() }
            vlc.release()
            val luc = so.takeIf { it.isNotEmpty() && '?' !in it }

            // Nhãn: theo màu nền (đỏ = Cực Hạn, xanh = Phù Hợp Với Tướng), hoặc mẫu chữ "Chưa Xếp Hạng".
            val vn = cat(VUNG_NHAN)
            val doMau = Bin.hsv(vn, doubleArrayOf(0.0, 120.0, 150.0), doubleArrayOf(8.0, 255.0, 255.0))
                .or(Bin.hsv(vn, doubleArrayOf(172.0, 120.0, 150.0), doubleArrayOf(180.0, 255.0, 255.0))).mean()
            val xanh = Bin.hsv(vn, doubleArrayOf(98.0, 70.0, 110.0), doubleArrayOf(118.0, 255.0, 255.0)).mean()
            val nhan = when {
                doMau > 0.25 -> "cuc_han"
                xanh > 0.25 -> "phu_hop"
                khop(vn, nd.bo.chuaXepHang) >= 0.8 -> "chua_xep_hang"
                else -> null
            }
            vn.release()

            // Thẻ đang chọn: đoạn màu cam dài nhất; ảnh đại diện ở đầu thẻ không cam nên chỉ tin mép phải.
            val dai = cat(DAI_THE)
            val cam = Bin.hsv(dai, doubleArrayOf(10.0, 140.0, 200.0), doubleArrayOf(24.0, 255.0, 255.0))
            dai.release()
            val cot = cam.colSums()
            var doan: Pair<Int, Int>? = null
            var bd = -1
            for (x in 0..cam.w) {
                val c = x < cam.w && cot[x].toDouble() / cam.h > 0.5
                if (c && bd < 0) bd = x
                else if (!c && bd >= 0) {
                    if (doan == null || x - bd > doan.second - doan.first) doan = bd to x
                    bd = -1
                }
            }
            var chuKy: Bin? = null
            var thuCong = false
            var lyTuong = false
            if (doan != null && doan.second - doan.first > 200) {
                val tx1 = doan.second + DAI_THE.x0 + dx
                val tx0 = tx1 - RONG_THE
                val ot = ref.cat(tx0 + TEN_TU_MEP, TEN_Y0 + dy, tx1 - 10, TEN_Y1 + dy)
                var o = Mat()
                Imgproc.cvtColor(ot, o, Imgproc.COLOR_BGR2GRAY)
                ot.release()
                // Bỏ phần ảnh đại diện còn lấn vào: bắt đầu từ cột đầu tiên thuộc ô tên màu trắng.
                val trang = Bin.fromMat(o) { it > 200 }
                val tc = trang.colSums()
                val dau = (0 until trang.w).firstOrNull { tc[it].toDouble() / trang.h > 0.5 }
                if (dau != null) {
                    val o2 = o.submat(0, o.rows(), dau, o.cols()).clone()
                    o.release()
                    o = o2
                }
                val chu = Bin.fromMat(o) { it < 140 }
                o.release()
                if (chu.count() > 20) chuKy = chu.chuanHoa(CHU_KY_RONG, CHU_KY_CAO, 100)
                val vtc = ref.cat(tx0 + 100, THU_CONG_Y0 + dy, tx1, THU_CONG_Y1 + dy)
                thuCong = khop(vtc, nd.bo.thuCong) >= 0.7
                vtc.release()
                val vlt = ref.cat(tx0 + 100, LY_TUONG_Y0 + dy, tx1, LY_TUONG_Y1 + dy)
                lyTuong = Bin.hsv(vlt, doubleArrayOf(98.0, 60.0, 100.0), doubleArrayOf(118.0, 255.0, 255.0)).mean() > 0.15
                vlt.release()
            }

            // Ô lọc (bám mép trên, không dời theo bảng): đang bật thì có dấu tích xanh lá.
            val vo = ref.cat(O_LOC.x0.toDouble(), O_LOC.y0.toDouble(), O_LOC.x1.toDouble(), O_LOC.y1.toDouble())
            val loc = if (vo.empty()) null else
                Bin.hsv(vo, doubleArrayOf(35.0, 80.0, 80.0), doubleArrayOf(85.0, 255.0, 255.0)).mean() > 0.2
            vo.release()
            return DoiThanhTich(chuKy, luc, nhan, lyTuong, thuCong, loc)
        } finally {
            if (ref !== img) ref.release()
        }
    }
}
