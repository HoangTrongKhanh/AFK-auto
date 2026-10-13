package vn.afkauto.leoai.vision

import org.opencv.core.Core
import org.opencv.core.CvType
import org.opencv.core.Mat
import org.opencv.core.Scalar
import org.opencv.core.Size
import org.opencv.imgproc.Imgproc

// Chuyển từ so_ai.py: nhận dạng ký tự bằng mẫu cắt từ lực chiến trong Thành Tích, đọc số ải ở Màn AFK và
// "Tiến Trình Màn Chơi Đỉnh Cao A → B" ở màn THẮNG.
const val KY_TU_RONG = 24
const val KY_TU_CAO = 32
const val GIONG_KY_TU = 0.65
const val CACH_BIET = 0.05

private val MOC_MAN_AFK = 302 to 1243
private val DAI_DUONG_AI = Box(0, 1020, 1600, 1110)
private val MOC_THANG = 800 to 1655
private val SO_TRUOC = Box(690, 1715, 800, 1790)
private val SO_SAU = Box(910, 1715, 1035, 1790)

/** Ảnh nhị phân nhỏ (true = nét), lưu theo hàng. */
class Bin(val w: Int, val h: Int, val px: BooleanArray) {
    operator fun get(x: Int, y: Int) = px[y * w + x]

    fun crop(x0: Int, y0: Int, x1: Int, y1: Int) =
        Bin(x1 - x0, y1 - y0, BooleanArray((x1 - x0) * (y1 - y0)) { this[x0 + it % (x1 - x0), y0 + it / (x1 - x0)] })

    fun any() = px.any { it }

    fun count() = px.count { it }

    fun colSums() = IntArray(w) { x -> (0 until h).count { this[x, it] } }

    /** Ảnh CV_8U, nét = 255. */
    fun toMat(): Mat {
        val m = Mat(h, w, CvType.CV_8UC1)
        m.put(0, 0, ByteArray(px.size) { if (px[it]) 255.toByte() else 0 })
        return m
    }

    /** Cắt sát vùng có nét rồi đổi cỡ về rw x rh (INTER_AREA), giữ điểm > nguong. */
    fun chuanHoa(rw: Int, rh: Int, nguong: Int): Bin {
        var x0 = w; var y0 = h; var x1 = -1; var y1 = -1
        for (y in 0 until h) for (x in 0 until w) if (this[x, y]) {
            if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y
        }
        val m = crop(x0, y0, x1 + 1, y1 + 1).toMat()
        val r = Mat()
        Imgproc.resize(m, r, Size(rw.toDouble(), rh.toDouble()), 0.0, 0.0, Imgproc.INTER_AREA)
        m.release()
        val out = fromMat(r) { it > nguong }
        r.release()
        return out
    }

    companion object {
        /** Ảnh CV_8UC1 -> Bin theo điều kiện trên giá trị điểm ảnh. */
        fun fromMat(m: Mat, dk: (Int) -> Boolean): Bin {
            val c = if (m.isContinuous) m else m.clone()
            val buf = ByteArray(m.rows() * m.cols())
            c.get(0, 0, buf)
            if (c !== m) c.release()
            return Bin(m.cols(), m.rows(), BooleanArray(buf.size) { dk(buf[it].toInt() and 0xFF) })
        }

        fun xam(img: Mat, dk: (Int) -> Boolean): Bin {
            val g = Mat()
            Imgproc.cvtColor(img, g, Imgproc.COLOR_BGR2GRAY)
            val b = fromMat(g, dk)
            g.release()
            return b
        }

        /** Mặt nạ HSV như cv2.inRange (H 0-180). */
        fun hsv(img: Mat, lo: DoubleArray, hi: DoubleArray): Bin {
            val hsv = Mat()
            Imgproc.cvtColor(img, hsv, Imgproc.COLOR_BGR2HSV)
            val m = Mat()
            Core.inRange(hsv, Scalar(lo), Scalar(hi), m)
            hsv.release()
            val b = fromMat(m) { it != 0 }
            m.release()
            return b
        }
    }

    fun or(o: Bin) = Bin(w, h, BooleanArray(px.size) { px[it] || o.px[it] })

    fun mean() = if (px.isEmpty()) 0.0 else count().toDouble() / px.size
}

/** Thành phần liên thông (8 hướng): (x, y, rộng, cao, diện tích), không tính nền. */
fun thanhPhan(b: Bin): List<IntArray> {
    val m = b.toMat()
    val lab = Mat()
    val st = Mat()
    val ct = Mat()
    val n = Imgproc.connectedComponentsWithStats(m, lab, st, ct, 8, CvType.CV_32S)
    val out = (1 until n).map { i -> IntArray(5) { j -> st.get(i, j)[0].toInt() } }
    m.release(); lab.release(); st.release(); ct.release()
    return out
}

class ChuSo(private val mau: List<Pair<Char, BooleanArray>>) {
    /** Ký tự giống nhất với ảnh m (đã chuẩn hoá), '?' nếu không đủ giống hoặc không hơn hẳn ký tự thứ hai. */
    fun docKyTu(m: Bin, chiSo: Boolean = false): Char {
        val tot = LinkedHashMap<Char, Double>()
        for ((c, t) in mau) {
            if (chiSo && !c.isDigit()) continue
            var same = 0
            for (i in t.indices) if (t[i] == m.px[i]) same++
            val s = same.toDouble() / t.size
            if (s > (tot[c] ?: 0.0)) tot[c] = s
        }
        val xep = tot.entries.sortedByDescending { it.value }
        if (xep.isEmpty() || xep[0].value < GIONG_KY_TU || (xep.size > 1 && xep[0].value - xep[1].value < CACH_BIET)) return '?'
        return xep[0].key
    }

    /** Dãy chữ số không dính nhau trong ảnh nhị phân -> số, null nếu không đọc được. */
    fun docSo(b: Bin): Int? {
        val hops = thanhPhan(b).filter { b.h * 0.5 <= it[3] && it[3] <= b.h * 0.9 && it[4] >= 15 }.sortedBy { it[0] }
        val s = hops.joinToString("") { (x, y, w, hh) ->
            docKyTu(b.crop(x, y, x + w, y + hh).chuanHoa(KY_TU_RONG, KY_TU_CAO, 127), chiSo = true).toString()
        }
        return if (s.isNotEmpty() && '?' !in s) s.toInt() else null
    }
}

private operator fun IntArray.component5() = this[4]

/** Ảnh quy về rộng REF_W (như cv2.resize ... if k != 1 else img). Trả về chính img nếu không cần đổi cỡ. */
internal fun veGoc(img: Mat): Mat {
    val k = REF_W.toDouble() / img.cols()
    return if (k != 1.0) scale(img, k) else img
}

class DocSoAi(private val nd: NhanDien) {
    private val chuSo = ChuSo(nd.bo.chuSo)

    /** (ảnh quy về rộng 1600, dx, dy) hoặc null nếu không thấy mẫu mốc. */
    private fun <T> voiMoc(img: Mat, mau: String, moc: Pair<Int, Int>, block: (Mat, Double, Double) -> T?): T? {
        val (small, _) = nd.thuNho(img)
        val k = nd.tim(small, mau)
        small.release()
        if (k.diem < 0.8) return null
        val ref = veGoc(img)
        try {
            return block(ref, k.x * 2.0 - moc.first, k.y * 2.0 - moc.second)
        } finally {
            if (ref !== img) ref.release()
        }
    }

    /** Số ải hiện tại ở Màn AFK (chữ trắng trong ô đỏ), null nếu không đọc được. */
    fun aiManAfk(img: Mat): Int? = voiMoc(img, "man_afk_tieu_de", MOC_MAN_AFK) { ref, dx, dy ->
        val b = DAI_DUONG_AI
        val dai = ref.cat(b.x0 + dx, b.y0 + dy, b.x1 + dx, b.y1 + dy)
        val doMask = Bin.hsv(dai, doubleArrayOf(0.0, 100.0, 150.0), doubleArrayOf(10.0, 255.0, 255.0))
            .or(Bin.hsv(dai, doubleArrayOf(170.0, 100.0, 150.0), doubleArrayOf(180.0, 255.0, 255.0)))
        val tp = thanhPhan(doMask)
        val kq = if (tp.isEmpty()) null else {
            val (x, y, w, h) = tp.maxBy { it[4] }
            val o = dai.submat(y, y + h, x, x + w)
            val trang = Bin.hsv(o, doubleArrayOf(0.0, 0.0, 215.0), doubleArrayOf(180.0, 70.0, 255.0))
            o.release()
            chuSo.docSo(trang)
        }
        dai.release()
        kq
    }

    /** (ải trước, ải sau) trong "Tiến Trình Màn Chơi Đỉnh Cao A → B" ở màn THẮNG; null nếu không đọc được. */
    fun tienTrinhThang(img: Mat): Pair<Int, Int>? = voiMoc(img, "thang_da_tang", MOC_THANG) { ref, dx, dy ->
        val a = ref.cat(SO_TRUOC.x0 + dx, SO_TRUOC.y0 + dy, SO_TRUOC.x1 + dx, SO_TRUOC.y1 + dy)
        val b = ref.cat(SO_SAU.x0 + dx, SO_SAU.y0 + dy, SO_SAU.x1 + dx, SO_SAU.y1 + dy)
        val truoc = chuSo.docSo(Bin.xam(a) { it > 200 })
        val sau = chuSo.docSo(Bin.hsv(b, doubleArrayOf(35.0, 80.0, 200.0), doubleArrayOf(85.0, 255.0, 255.0)))
        a.release()
        b.release()
        if (truoc != null && sau != null) truoc to sau else null
    }
}
