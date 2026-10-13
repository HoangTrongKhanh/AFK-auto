package vn.afkauto.leoai.vision

import org.json.JSONObject
import org.opencv.core.Core
import org.opencv.core.Mat
import org.opencv.core.MatOfByte
import org.opencv.core.Size
import org.opencv.imgcodecs.Imgcodecs
import org.opencv.imgproc.Imgproc
import kotlin.math.max
import kotlin.math.min

// Chuyển từ nhan_dien.py, giữ nguyên thuật toán và ngưỡng. Ảnh dùng thứ tự kênh BGR như cv2 trong Python.
// Toạ độ đo trên máy gốc 1600x2560 (Tab S7). Bảng mẫu (vùng, mốc neo, ngưỡng, thứ tự màn hình) đọc từ
// templates/vi/mau.json do tao_mau.py xuất ra, để toạ độ chỉ khai báo một chỗ là nhan_dien.py.
const val REF_W = 1600
const val REF_H = 2560
const val WORK_W = 800                      // tìm mẫu trên ảnh thu nhỏ về rộng bấy nhiêu (= 1/2 máy gốc)
const val WORK = WORK_W.toDouble() / REF_W
// Lớp khóa Game Booster làm tối cả màn hình: độ sáng trung bình 35-42 khi bị khóa, màn bình thường >= 84.
const val LOCKED_BRIGHTNESS = 60.0

data class Box(val x0: Int, val y0: Int, val x1: Int, val y1: Int) {
    val width get() = x1 - x0
    val height get() = y1 - y0

    fun intersects(o: Box) = x0 < o.x1 && o.x0 < x1 && y0 < o.y1 && o.y0 < y1
}

/** Làm tròn như round() của Python (nửa về số chẵn) để kết quả trùng với bản Python. */
internal fun pyRound(v: Double) = Math.rint(v).toInt()

fun decodeImage(bytes: ByteArray, flags: Int = Imgcodecs.IMREAD_COLOR): Mat {
    val buf = MatOfByte(*bytes)
    val img = Imgcodecs.imdecode(buf, flags)
    buf.release()
    require(!img.empty()) { "không giải mã được ảnh" }
    return img
}

/** Đổi cỡ theo hệ số như cv2.resize(img, None, fx=k, fy=k). */
internal fun scale(img: Mat, k: Double, interp: Int = Imgproc.INTER_AREA): Mat {
    val out = Mat()
    Imgproc.resize(img, out, Size(), k, k, interp)
    return out
}

/** Vùng box của ảnh (không sao chép), cắt cho nằm trong ảnh như cắt mảng numpy với toạ độ làm tròn. */
internal fun Mat.cat(x0: Double, y0: Double, x1: Double, y1: Double): Mat {
    val ax0 = pyRound(x0).coerceIn(0, cols())
    val ay0 = pyRound(y0).coerceIn(0, rows())
    val ax1 = pyRound(x1).coerceIn(ax0, cols())
    val ay1 = pyRound(y1).coerceIn(ay0, rows())
    return submat(ay0, ay1, ax0, ax1)
}

/** Mẫu ảnh đã thu nhỏ về WORK, cùng vùng gốc, mốc neo ("tren" | "duoi" | "giua"), khoảng tìm thêm, ngưỡng. */
class Mau(val ten: String, val hop: Box, val neo: String, val le: Int, val nguong: Double, val anh: Mat)

/** Bộ mẫu đọc từ thư mục templates/vi: mẫu màn hình/nút, chữ số lực chiến, mẫu phụ của Thành Tích. */
class BoMau(
    val mau: Map<String, Mau>,
    val manHinh: List<Pair<String, List<String>>>,
    val nutThem: Map<String, List<String>>,
    val chuSo: List<Pair<Char, BooleanArray>>,
    val thuCong: Mat,
    val chuaXepHang: Mat,
) {
    companion object {
        /** read(đường dẫn) trả về nội dung một file trong templates/, list(thư mục con) liệt kê tên file. */
        fun load(read: (String) -> ByteArray, list: (String) -> List<String>): BoMau {
            val js = JSONObject(String(read("vi/mau.json"), Charsets.UTF_8))
            val mauJs = js.getJSONObject("mau")
            val mau = mauJs.keys().asSequence().associateWith { ten ->
                val m = mauJs.getJSONObject(ten)
                val h = m.getJSONArray("hop")
                val goc = decodeImage(read("vi/$ten.png"))
                val anh = scale(goc, WORK)
                goc.release()
                Mau(ten, Box(h.getInt(0), h.getInt(1), h.getInt(2), h.getInt(3)), m.getString("neo"), m.getInt("le"),
                    m.getDouble("nguong"), anh)
            }
            val mhJs = js.getJSONArray("man_hinh")
            val manHinh = (0 until mhJs.length()).map { i ->
                val o = mhJs.getJSONObject(i)
                val can = o.getJSONArray("can")
                o.getString("ten") to (0 until can.length()).map { can.getString(it) }
            }
            val ntJs = js.getJSONObject("nut_them")
            val nutThem = ntJs.keys().asSequence().associateWith { k ->
                val a = ntJs.getJSONArray(k)
                (0 until a.length()).map { a.getString(it) }
            }
            // Tên file <ký tự>_<thứ tự>.png, ảnh nhị phân KY_TU_RONG x KY_TU_CAO (tạo bằng tao_mau.py).
            val chuSo = list("vi/luc_chien").filter { it.endsWith(".png") }.sorted().map { name ->
                val m = decodeImage(read("vi/luc_chien/$name"), Imgcodecs.IMREAD_GRAYSCALE)
                val px = ByteArray(m.rows() * m.cols())
                m.get(0, 0, px)
                m.release()
                name[0] to BooleanArray(px.size) { (px[it].toInt() and 0xFF) > 127 }
            }
            require(chuSo.isNotEmpty()) { "thiếu mẫu chữ số trong templates/vi/luc_chien" }
            return BoMau(mau, manHinh, nutThem, chuSo,
                decodeImage(read("vi/tt_thu_cong.png")), decodeImage(read("vi/tt_chua_xep_hang.png")))
        }
    }
}

class KetQua(
    val manHinh: String,                            // tên màn hình, "khoa" (Game Booster) hoặc "khong_ro"
    val nut: Map<String, Pair<Int, Int>>,           // tên mẫu -> tâm mẫu trên ảnh gốc (để bấm)
    val diem: Map<String, Double>,
    val doSang: Double,
    val cheDo: String?,                             // màn đội hình: "afk" | "huyen_linh"
) {
    /** Đang bật Chiến Đấu Tự Động (thấy dải chữ "Tự Động Chiến Đấu..."). */
    val tuDong get() = "tu_dong_chien_dau" in nut

    override fun toString(): String {
        val extra = (cheDo?.let { " ($it)" } ?: "") + (if (tuDong) " [tự động]" else "")
        return "$manHinh$extra | sáng ${"%.0f".format(doSang)} | " + nut.entries.joinToString { "${it.key}@${it.value.first},${it.value.second}" }
    }
}

/** Kết quả tìm một mẫu: điểm khớp và tâm trên ảnh thu nhỏ (null nếu vùng tìm nhỏ hơn mẫu). */
class Khop(val diem: Double, val x: Int, val y: Int, val coViTri: Boolean)

fun grayMean(img: Mat): Double {
    val g = Mat()
    Imgproc.cvtColor(img, g, Imgproc.COLOR_BGR2GRAY)
    val v = Core.mean(g).`val`[0]
    g.release()
    return v
}

class NhanDien(val bo: BoMau) {
    /** Ảnh thu nhỏ về rộng WORK_W và hệ số đã dùng. Người gọi giải phóng ảnh. */
    fun thuNho(img: Mat): Pair<Mat, Double> {
        val k = WORK_W.toDouble() / img.cols()
        return scale(img, k) to k
    }

    /** Vùng tìm trên ảnh thu nhỏ (rộng WORK_W, cao hWork) cho mẫu m. */
    fun vung(m: Mau, hWork: Int): Box {
        fun y(v: Int): Double = when (m.neo) {
            "tren" -> v * WORK
            "duoi" -> hWork - (REF_H - v) * WORK
            else -> hWork / 2.0 + (v - REF_H / 2.0) * WORK
        }
        val le = m.le * WORK
        return Box(
            max(0, (m.hop.x0 * WORK - le).toInt()), max(0, (y(m.hop.y0) - le).toInt()),
            min(WORK_W, (m.hop.x1 * WORK + le).toInt()), min(hWork, (y(m.hop.y1) + le).toInt()),
        )
    }

    fun tim(small: Mat, ten: String): Khop {
        val m = bo.mau.getValue(ten)
        val v = vung(m, small.rows())
        if (v.height < m.anh.rows() || v.width < m.anh.cols()) return Khop(0.0, 0, 0, false)
        val roi = small.submat(v.y0, v.y1, v.x0, v.x1)
        val r = Mat()
        Imgproc.matchTemplate(roi, m.anh, r, Imgproc.TM_CCOEFF_NORMED)
        val mm = Core.minMaxLoc(r)
        r.release()
        roi.release()
        return Khop(mm.maxVal, v.x0 + mm.maxLoc.x.toInt() + m.anh.cols() / 2, v.y0 + mm.maxLoc.y.toInt() + m.anh.rows() / 2, true)
    }

    fun nhanDien(img: Mat): KetQua {
        val sang = grayMean(img)
        if (sang < LOCKED_BRIGHTNESS) return KetQua("khoa", emptyMap(), emptyMap(), sang, null)
        val (small, k) = thuNho(img)
        val khop = LinkedHashMap<String, Khop>()
        fun thay(ten: String): Boolean {
            val kq = khop.getOrPut(ten) { tim(small, ten) }
            return kq.diem >= bo.mau.getValue(ten).nguong
        }
        var man = "khong_ro"
        for ((ten, can) in bo.manHinh) {
            if (can.all { thay(it) }) {
                man = ten
                bo.nutThem[ten]?.forEach { thay(it) }
                break
            }
        }
        small.release()
        val nut = LinkedHashMap<String, Pair<Int, Int>>()
        for ((t, kq) in khop) {
            if (kq.coViTri && kq.diem >= bo.mau.getValue(t).nguong) nut[t] = pyRound(kq.x / k) to pyRound(kq.y / k)
        }
        val cheDo = if (man == "doi_hinh") when {
            "tieu_de_huyen" in nut -> "huyen_linh"
            "tieu_de_mua_giai" in nut -> "afk"
            else -> null
        } else null
        return KetQua(man, nut, khop.mapValues { it.value.diem }, sang, cheDo)
    }

    /** Điểm khớp của mọi mẫu (để kiểm thử và chỉnh ngưỡng). */
    fun tatCaDiem(img: Mat): Map<String, Double> {
        val (small, _) = thuNho(img)
        val out = bo.mau.keys.associateWith { tim(small, it).diem }
        small.release()
        return out
    }
}

/** Tâm biểu tượng ổ khóa xanh của Game Booster (chép từ hoa-vien-auto), null nếu không thấy. */
fun timOKhoa(img: Mat): Pair<Int, Int>? {
    val w = img.cols()
    val h = img.rows()
    val x0 = (w * 0.25).toInt()
    val y0 = (h * 0.3).toInt()
    val roi = img.submat(y0, (h * 0.7).toInt(), x0, (w * 0.75).toInt())
    val bw = roi.cols()
    val px = ByteArray(roi.rows() * bw * 3)
    val cont = roi.clone()
    cont.get(0, 0, px)
    cont.release()
    roi.release()
    var n = 0
    var sx = 0L
    var sy = 0L
    for (i in 0 until px.size / 3) {
        val b = px[3 * i].toInt() and 0xFF
        val g = px[3 * i + 1].toInt() and 0xFF
        val r = px[3 * i + 2].toInt() and 0xFF
        if (b > 180 && r < 90 && b - g > 40) {
            n++
            sx += i % bw
            sy += i / bw
        }
    }
    if (n < (w * h) / 20000.0) return null
    return (sx / n).toInt() + x0 to (sy / n).toInt() + y0
}
