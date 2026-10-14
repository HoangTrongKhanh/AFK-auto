package vn.afkauto.leoai.vision

import org.json.JSONObject
import org.opencv.core.Core
import org.opencv.core.CvType
import org.opencv.core.Mat
import org.opencv.core.MatOfDouble
import org.opencv.core.Size
import org.opencv.imgcodecs.Imgcodecs
import org.opencv.imgproc.Imgproc
import java.nio.ByteBuffer
import java.nio.ByteOrder

// Thẻ tướng: tách thẻ trong Thành Tích, nhận tướng bằng ảnh mặt, đọc khung thẻ (phẩm tướng), đọc danh sách tướng ở màn
// đội hình, so khung tướng của bản ghi với tướng của bạn. Chuyển từ thong_ke_tuong.py và doc_tuong_cua_toi.py.

// Dải dưới sơ đồ ô của Thành Tích: cổ vật (+ vật phẩm Huyền Linh) rồi 5 thẻ tướng (máy gốc, dời theo mốc nắm đấm).
private val DAI_TUONG = Box(245, 1690, 1345, 1895)
const val BUOC_THE = 130            // thẻ tướng trong dải cách đều bấy nhiêu px
private const val TAM_CUOI = 61     // tâm thẻ cuối cách mép phải của phần không phải nền kem
const val SO_TUONG = 5
private const val MAT_Y0 = 55       // phần mặt: dưới hàng sao, trên dòng "Cấp 600"
private const val MAT_Y1 = 140
private const val MAT_RONG = 44
private const val LE = 4            // độ lệch cho phép khi so 2 mặt
const val MAT_CO = 48               // ảnh mặt chuẩn hoá MAT_CO x MAT_CO
// Khung thẻ: điểm khớp mẫu ngôi sao < SAO_KHONG là không khung, >= SAO_CO là có khung; ở giữa thì xếp theo viền thẻ.
private const val SAO_KHONG = 0.62
private const val SAO_CO = 0.75
private const val LANG_GIENG = 7

// Danh sách tướng ở màn đội hình (máy gốc, bám mép dưới).
private const val DS_Y0 = 1530
private const val DS_Y1 = 2295
const val KHE_X = 234               // khe kem giữa cột thẻ 1 và 2: vuốt ở đây để không kéo trúng thẻ tướng
private const val BUOC_COT = 227
private const val BUOC_HANG = 326
private const val KHE_HANG = 33
private const val CAO_THE = 290
private const val XANH_TRONG_DOI = 0.3
const val NHAN_TUONG = 0.85         // thẻ thường: khớp mặt >= mức này mới tự nhận là tướng đó
private const val GOI_Y = 0.6
private const val TRONG_DOI_DIEM = 0.5
private const val TRONG_DOI_HON = 0.12
const val CUNG_THE = 0.85           // 2 thẻ (ở 2 lần chụp) khớp mặt >= mức này là cùng một thẻ
// Chỉ so khung tướng mà bản ghi thường dùng có khung (đo 13/10: thiếu khung Saida thắng 1/14, Mehira 3/5).
const val KHUNG_CAN = 0.5
// Nút lọc tròn ở góc dưới phải danh sách đè lên thẻ (máy gốc, bám mép dưới; đo 14/10): bỏ thẻ chạm vùng này, thẻ đó sẽ
// hiện trọn ở lần chụp khác (vuốt nửa hàng mỗi lần).
private val NUT_LOC = Box(1410, 2080, 1585, 2255)
const val QUAN_TRONG = 0.05         // tướng quan trọng: ít nhất bấy nhiêu phần bản ghi dùng tướng này có khung

/** Mặt nạ điểm màu kem của nền bảng. */
fun nenKem(img: Mat) = Bin.hsv(img, doubleArrayOf(0.0, 0.0, 201.0), doubleArrayOf(180.0, 59.0, 255.0))

/** Chuẩn hoá ảnh mặt về MAT_CO x MAT_CO. */
fun chuanMat(m: Mat): Mat {
    val out = Mat()
    Imgproc.resize(m, out, Size(MAT_CO.toDouble(), MAT_CO.toDouble()), 0.0, 0.0, Imgproc.INTER_AREA)
    return out
}

/** Thẻ tướng: ảnh mặt (đã chuẩn hoá) và ảnh cả thẻ (khổ thẻ bản ghi, rộng tối đa 130, cao 205). */
class The(val mat: Mat, val anh: Mat) {
    fun release() { mat.release(); anh.release() }
}

/** Tách 5 thẻ tướng trong dải tướng của Thành Tích, trái sang phải; null nếu không tách được. */
fun tachThe(dai: Mat): List<The>? {
    if (dai.empty()) return null
    val kem = nenKem(dai).crop(0, 40, dai.cols(), minOf(170, dai.rows()))
    val cs = kem.colSums()
    val coThe = BooleanArray(kem.w) { cs[it].toDouble() / kem.h <= 0.85 }
    val cuoiX = coThe.indices.lastOrNull { coThe[it] } ?: return null
    val cuoi = cuoiX + 1 - TAM_CUOI
    val out = mutableListOf<The>()
    for (i in SO_TUONG - 1 downTo 0) {
        val c = cuoi - i * BUOC_THE
        val a = maxOf(0, c - 40)
        val b = minOf(coThe.size, c + 40)
        if (c - MAT_RONG < 0 || b <= a || (a until b).count { coThe[it] }.toDouble() / (b - a) < 0.9) {
            out.forEach { it.release() }
            return null
        }
        val m = dai.cat((c - MAT_RONG).toDouble(), MAT_Y0.toDouble(), (c + MAT_RONG).toDouble(), MAT_Y1.toDouble())
        val anh = dai.cat(maxOf(0, c - BUOC_THE / 2).toDouble(), 0.0, (c + BUOC_THE / 2).toDouble(), dai.rows().toDouble())
        out.add(The(chuanMat(m), anh.clone()))
    }
    return out
}

private fun khopMax(img: Mat, tpl: Mat): Double {
    if (img.rows() < tpl.rows() || img.cols() < tpl.cols()) return 0.0
    val r = Mat()
    Imgproc.matchTemplate(img, tpl, r, Imgproc.TM_CCOEFF_NORMED)
    val v = Core.minMaxLoc(r).maxVal
    r.release()
    return v
}

/** Mức khớp (0-1) của 2 ảnh mặt: phần giữa của ảnh này trượt trong ảnh kia (lệch tối đa LE px), lấy chiều thấp hơn. */
fun giongMat(a: Mat, b: Mat): Double {
    fun motChieu(x: Mat, y: Mat): Double {
        val giua = y.submat(LE, y.rows() - LE, LE, y.cols() - LE)
        return khopMax(x, giua)
    }
    return minOf(motChieu(a, b), motChieu(b, a))
}

/** Điểm khớp cao nhất của mẫu ngôi sao trong phần trên thẻ. */
fun diemSao(the: Mat, mauSao: List<Mat>): Double {
    val g = Mat()
    Imgproc.cvtColor(the.cat(0.0, 5.0, the.cols().toDouble(), 70.0), g, Imgproc.COLOR_BGR2GRAY)
    val d = mauSao.maxOf { khopMax(g, it) }
    g.release()
    return d
}

/** Đặc trưng viền thẻ (độ bão hoà và độ sáng của mép trên, mép trái, mép phải), đã chuẩn hoá. */
fun dacTrungVien(the: Mat): FloatArray {
    val hsv8 = Mat()
    Imgproc.cvtColor(the, hsv8, Imgproc.COLOR_BGR2HSV)
    val hsv = Mat()
    hsv8.convertTo(hsv, CvType.CV_32F)
    hsv8.release()
    val out = ArrayList<Float>()
    for (kenh in listOf(1, 2)) {
        val x = Mat()
        Core.extractChannel(hsv, x, kenh)
        val w = x.cols()
        for ((vung, co) in listOf(
            x.submat(5, 60, 0, w) to Size(26.0, 11.0),
            x.submat(40, 195, 0, 14) to Size(4.0, 20.0),
            x.submat(40, 195, w - 14, w) to Size(4.0, 20.0),
        )) {
            val r = Mat()
            Imgproc.resize(vung, r, co)
            val buf = FloatArray((r.total()).toInt())
            r.get(0, 0, buf)
            buf.forEach { out.add(it) }
            r.release()
        }
        x.release()
    }
    hsv.release()
    val tb = out.average()
    val dl = kotlin.math.sqrt(out.sumOf { (it - tb) * (it - tb) } / out.size)
    return FloatArray(out.size) { ((out[it] - tb) / (dl + 1e-6)).toFloat() }
}

/** Thư viện tướng templates/vi/tuong/ (tao_thu_vien_tuong.py): mặt các tướng đã đặt tên, tỉ lệ có khung của từng tướng
 *  trong bản ghi, thẻ mẫu viền đã biết khung. */
class ThuVienTuong(
    mat: Map<String, List<Mat>>,
    val coKhung: Map<String, Double>,
    vien: Array<FloatArray>,
    nhanVien: ByteArray,
    private val mauSao: List<Mat>,
    val soLan: Map<String, Int> = emptyMap(),
    val soBanGhi: Int = 0,
) {
    val mat: MutableMap<String, MutableList<Mat>> = mat.mapValues { it.value.toMutableList() }.toMutableMap()
    private val vien = vien.toMutableList()
    private val nhanVien = nhanVien.toMutableList()

    /** Mặt tướng bạn đã xác nhận (lấy từ chính danh sách của bạn): đặt lên đầu để lần sau khớp gần như tuyệt đối. */
    fun themMat(ten: String, m: Mat) { mat.getOrPut(ten) { mutableListOf() }.add(0, m) }

    /** Thẻ danh sách đã biết khung: thêm vào bước xếp theo viền. */
    fun themVien(f: FloatArray, khung: Int) { vien.add(f); nhanVien.add(khung.toByte()) }

    /** 1 = thẻ có khung (phẩm chuẩn), 0 = không khung (phẩm thấp). */
    fun khung(the: Mat): Int = khungTin(the).first

    /** (khung, độ tin): độ tin là khoảng cách của điểm sao tới giữa 2 ngưỡng (càng xa càng chắc). */
    fun khungTin(the: Mat): Pair<Int, Double> {
        val d = diemSao(the, mauSao)
        val tin = kotlin.math.abs(d - (SAO_KHONG + SAO_CO) / 2)
        if (d < SAO_KHONG) return 0 to tin
        if (d >= SAO_CO) return 1 to tin
        val f = dacTrungVien(the)
        val kc = vien.indices.map { i ->
            var s = 0.0
            val v = vien[i]
            for (j in f.indices) { val t = (v[j] - f[j]).toDouble(); s += t * t }
            s to i
        }.sortedBy { it.first }.take(LANG_GIENG)
        return (if (kc.map { nhanVien[it.second].toInt() }.average() >= 0.5) 1 else 0) to tin
    }

    /** Tướng quan trọng: (tên, phần bản ghi dùng tướng này có khung), giảm dần. Bỏ tướng bản ghi ít dùng có khung. */
    fun quanTrong(): List<Pair<String, Double>> {
        val n = if (soBanGhi > 0) soBanGhi else maxOf(1, soLan.values.sum() / SO_TUONG)
        return soLan.filter { (t, sl) -> sl > 0 && (coKhung[t] ?: 0.0) >= KHUNG_CAN }
            .map { (t, sl) -> t to sl * (coKhung[t] ?: 0.0) / n }
            .filter { it.second >= QUAN_TRONG }.sortedByDescending { it.second }
    }

    /** Điểm khớp cao nhất với từng tướng, giảm dần: list (điểm, tên). */
    fun diem(m: Mat): List<Pair<Double, String>> =
        mat.map { (t, v) -> v.maxOf { giongMat(m, it) } to t }.sortedByDescending { it.first }

    companion object {
        fun load(read: (String) -> ByteArray): ThuVienTuong {
            val js = JSONObject(String(read("vi/tuong/tuong.json"), Charsets.UTF_8))
            val tuong = js.getJSONObject("tuong")
            val mat = mutableMapOf<String, List<Mat>>()
            val coKhung = mutableMapOf<String, Double>()
            val soLan = mutableMapOf<String, Int>()
            for (t in tuong.keys()) {
                val o = tuong.getJSONObject(t)
                val tam = decodeImage(read("vi/tuong/$t.png"))
                mat[t] = (0 until o.getInt("so_mat")).map { tam.submat(0, MAT_CO, it * MAT_CO, (it + 1) * MAT_CO).clone() }
                tam.release()
                coKhung[t] = o.getDouble("co_khung")
                soLan[t] = o.optInt("so_lan", 0)
            }
            val v = js.getJSONObject("vien")
            val so = v.getInt("so")
            val chieu = v.getInt("chieu")
            val fb = ByteBuffer.wrap(read("vi/tuong/vien.bin")).order(ByteOrder.LITTLE_ENDIAN).asFloatBuffer()
            val vien = Array(so) { FloatArray(chieu).also { a -> fb.get(a) } }
            val nhan = read("vi/tuong/vien_nhan.bin")
            val mauSao = listOf("sao_khung_cam", "sao_khung_mong").map { decodeImage(read("vi/$it.png"), Imgcodecs.IMREAD_GRAYSCALE) }
            return ThuVienTuong(mat, coKhung, vien, nhan, mauSao, soLan, js.optInt("so_ban_ghi", 0))
        }
    }
}

// ---------------------------------------------------------------- danh sách tướng ở màn đội hình

private fun doan(mask: BooleanArray): List<Pair<Int, Int>> {
    val out = mutableListOf<Pair<Int, Int>>()
    var bd = -1
    for (i in 0..mask.size) {
        val c = i < mask.size && mask[i]
        if (c && bd < 0) bd = i
        else if (!c && bd >= 0) { out.add(bd to i); bd = -1 }
    }
    return out
}

private fun median(v: List<Int>): Double {
    val s = v.sorted()
    return if (s.size % 2 == 1) s[s.size / 2].toDouble() else (s[s.size / 2 - 1] + s[s.size / 2]) / 2.0
}

/** Vị trí các cột thẻ (theo máy gốc) đo ở ảnh đầu; ảnh sau (cuối danh sách có ô trống) dùng lại. */
class CotDanhSach(val cot: List<Pair<Int, Int>>)

/** Thẻ thấy trọn trong danh sách tướng: thẻ theo khổ thẻ bản ghi (130x205) và tâm y theo máy gốc. */
class TheDanhSach(val anh: Mat, val tamY: Double)

/** Vùng danh sách tướng (theo máy gốc) để so 2 ảnh liên tiếp xem danh sách còn trôi không. */
fun vungDanhSach(img: Mat): Mat {
    val ref = veGoc(img)
    val h = ref.rows()
    val v = ref.submat(h - (REF_H - DS_Y0), h - (REF_H - DS_Y1), 0, ref.cols())
    val out = Mat()
    Imgproc.resize(v, out, Size(160.0, 76.0), 0.0, 0.0, Imgproc.INTER_AREA)
    if (ref !== img) ref.release()
    return out
}

/** Các thẻ thấy trọn trong danh sách tướng của màn đội hình; trả về (thẻ, các cột). */
fun catTheDanhSach(img: Mat, cot0: CotDanhSach?): Pair<List<TheDanhSach>, CotDanhSach?> {
    val ref = veGoc(img)
    try {
        val h = ref.rows()
        val y0 = h - (REF_H - DS_Y0)
        val y1 = h - (REF_H - DS_Y1)
        val vung = ref.submat(y0, y1, 0, ref.cols())
        val kem = nenKem(vung)
        val cot = cot0 ?: run {
            val cs = kem.colSums()
            CotDanhSach(doan(BooleanArray(kem.w) { cs[it].toDouble() / kem.h <= 0.6 }).filter { it.second - it.first > 150 })
        }
        if (cot.cot.size < 3) return emptyList<TheDanhSach>() to null
        val buoc = median(cot.cot.zipWithNext { a, b -> b.first - a.first })
        val k = BUOC_THE / buoc
        // Hàng: lưới đều; tìm độ lệch sao cho các khe kem ngang giữa 2 hàng thẻ trùng nhiều nhất.
        val p = buoc * BUOC_HANG / BUOC_COT
        val rs = IntArray(kem.h) { y -> (0 until kem.w).count { x -> kem[x, y] } }
        val g = DoubleArray(kem.h) { rs[it].toDouble() / kem.w }
        val khe = pyRound(KHE_HANG * buoc / BUOC_COT)
        val soJ = (g.size / p).toInt()
        fun diemLech(o: Int): Double {
            val ds = (-1..soJ).mapNotNull { j ->
                val s = (o + j * p).toInt()
                if (s >= 0 && s + khe <= g.size) (s until s + khe).sumOf { g[it] } / khe else null
            }
            return ds.average()
        }
        val o = (0 until p.toInt()).maxByOrNull { diemLech(it) } ?: 0
        val cao = pyRound(CAO_THE * buoc / BUOC_COT)
        val hang = (-1..soJ).mapNotNull { j ->
            val tren = (o + j * p).toInt() + khe
            if (tren >= 0 && tren + cao <= g.size) tren to tren + cao else null
        }
        val nho0 = scale(vung, k)
        val nho = Mat()
        Core.copyMakeBorder(nho0, nho, 40, 40, 80, 80, Core.BORDER_REPLICATE)
        nho0.release()
        val xam = Mat()
        Imgproc.cvtColor(vung, xam, Imgproc.COLOR_BGR2GRAY)
        val ly0 = h - (REF_H - NUT_LOC.y0) - y0
        val ly1 = h - (REF_H - NUT_LOC.y1) - y0
        val out = mutableListOf<TheDanhSach>()
        for ((ha, hb) in hang) for ((ca, cb) in cot.cot) {
            if (ca < NUT_LOC.x1 && cb > NUT_LOC.x0 && ha < ly1 && hb > ly0) continue     // bị nút lọc che
            // Ô trống gần như một màu; thẻ tướng lông trắng (Faramor) có nhiều điểm giống màu kem nên ngưỡng kem thấp.
            val o2 = kem.crop(ca, ha, cb, hb)
            if (1.0 - o2.mean() < 0.35) continue
            val tb = MatOfDouble(); val dl = MatOfDouble()
            Core.meanStdDev(xam.submat(ha, hb, ca, cb), tb, dl)
            if (dl.toArray()[0] < 15) continue          // thẻ đang trong đội (phủ xanh) chỉ ~26
            val cx = ((ca + cb) / 2.0 * k).toInt() + 80
            val ty = (ha * k).toInt() + 40
            if (ty - 15 < 0 || cx - 65 < 0 || ty + 190 > nho.rows() || cx + 65 > nho.cols()) continue
            out.add(TheDanhSach(nho.submat(ty - 15, ty + 190, cx - 65, cx + 65).clone(), y0 + (ha + hb) / 2.0))
        }
        nho.release()
        xam.release()
        return out to cot
    } finally {
        if (ref !== img) ref.release()
    }
}

/** Mặt trên thẻ danh sách (khổ thẻ bản ghi). */
fun matTheDanhSach(the: Mat): Mat {
    val m = the.cat((BUOC_THE / 2 - MAT_RONG).toDouble(), MAT_Y0.toDouble(), (BUOC_THE / 2 + MAT_RONG).toDouble(), MAT_Y1.toDouble())
    return chuanMat(m)
}

/** Thẻ của tướng đang trong đội: game phủ màu xanh lá và dấu tích. */
fun trongDoi(the: Mat) = Bin.hsv(the, doubleArrayOf(35.0, 61.0, 0.0), doubleArrayOf(85.0, 255.0, 255.0)).mean() >= XANH_TRONG_DOI

/** Một thẻ trong danh sách tướng của bạn. */
class TuongCuaToi(var anh: Mat, val mat: Mat, var khung: Int, val trongDoi: Boolean) {
    /** (khung, độ tin) của từng lần thấy thẻ này. */
    val lan = mutableListOf<Pair<Int, Double>>()
    var ten: String? = null
    var goiY: String? = null
    var diem = 0.0
}

/** Gán tên tướng cho các thẻ, mỗi tướng một thẻ: thẻ đang trong đội trước (khớp kém vì lớp phủ nên xét theo độ hơn
 *  tướng thứ 2), rồi thẻ thường theo điểm giảm dần (>= NHAN_TUONG); thẻ khớp 0.6-0.85 ghi tên đoán vào goiY. */
fun ganTen(ds: List<TuongCuaToi>, tv: ThuVienTuong) {
    val diem = ds.map { tv.diem(it.mat) }
    ds.forEachIndexed { i, x -> x.ten = null; x.goiY = null; x.diem = diem[i][0].first }
    val da = mutableSetOf<String>()
    for (i in ds.indices.filter { ds[it].trongDoi }.sortedByDescending { diem[it][0].first }) {
        val (d1, t1) = diem[i][0]
        val d2 = diem[i].getOrNull(1)?.first ?: 0.0
        if (d1 >= TRONG_DOI_DIEM && d1 - d2 >= TRONG_DOI_HON && t1 !in da) {
            ds[i].ten = t1
            da.add(t1)
        }
    }
    val cap = ds.indices.filter { !ds[it].trongDoi }.flatMap { i -> diem[i].filter { it.first >= GOI_Y }.map { Triple(it.first, i, it.second) } }
        .sortedWith(compareByDescending<Triple<Double, Int, String>> { it.first }.thenByDescending { it.second }.thenByDescending { it.third })
    for ((d, i, t) in cap) {
        val x = ds[i]
        if (x.ten != null || t in da) continue
        if (d >= NHAN_TUONG) {
            x.ten = t
            da.add(t)
        } else if (x.goiY == null) {
            x.goiY = t
            x.diem = d
        }
    }
    ds.forEach { if (it.ten != null) it.goiY = null }
}

/** Đọc danh sách tướng qua nhiều ảnh chụp (vuốt dần xuống): bỏ thẻ trùng giữa các lần chụp, xong thì gán tên. */
class DocDanhSach(private val tv: ThuVienTuong) {
    private var cot: CotDanhSach? = null
    val tuong = mutableListOf<TuongCuaToi>()

    /** Thêm các thẻ của một ảnh chụp danh sách; trả về số thẻ mới. Một thẻ thường hiện ở 2-3 lần chụp: khung lấy theo
     *  đa số các lần, hoà thì theo lần chắc nhất; ảnh thẻ giữ lần chắc nhất. */
    fun them(img: Mat): Int {
        val (ds, c) = catTheDanhSach(img, cot)
        if (cot == null) cot = c
        var moi = 0
        for (t in ds) {
            val m = matTheDanhSach(t.anh)
            val kt = tv.khungTin(t.anh)
            val cu = tuong.firstOrNull { giongMat(m, it.mat) >= CUNG_THE }
            if (cu == null) {
                tuong.add(TuongCuaToi(t.anh, m, kt.first, trongDoi(t.anh)).also { it.lan.add(kt) })
                moi++
                continue
            }
            m.release()
            val chacNhat = cu.lan.maxOf { it.second }
            cu.lan.add(kt)
            if (kt.second > chacNhat) { cu.anh.release(); cu.anh = t.anh } else t.anh.release()
            val co = cu.lan.count { it.first == 1 }
            val khong = cu.lan.size - co
            cu.khung = if (co > khong) 1 else if (khong > co) 0 else cu.lan.maxBy { it.second }.first
        }
        return moi
    }

    fun xong(): List<TuongCuaToi> {
        ganTen(tuong, tv)
        return tuong
    }
}

// ---------------------------------------------------------------- so khung khi chọn đội

/** So khung tướng trong một bản ghi Thành Tích với khung tướng của bạn: bản ghi có tướng mà bản ghi dùng thẻ có khung
 *  còn của bạn không khung thì đội chép về yếu hơn hẳn. cuaToi: tên tướng -> khung của bạn; matCuaToi: (mặt, khung) của
 *  các thẻ không bị phủ xanh, để so trực tiếp khi chưa biết tên tướng. */
class SoKhung(private val tv: ThuVienTuong, val cuaToi: Map<String, Int>, private val matCuaToi: List<Pair<Mat, Int>>) {
    private fun khungCuaToi(m: Mat): Pair<String?, Int?> {
        val (d, ten) = tv.diem(m).first()
        val tenChac = ten.takeIf { d >= NHAN_TUONG }
        if (tenChac != null && tenChac in cuaToi) return tenChac to cuaToi[tenChac]
        val tot = matCuaToi.map { giongMat(m, it.first) to it.second }.maxByOrNull { it.first }
        if (tot != null && tot.first >= NHAN_TUONG) return tenChac to tot.second
        return tenChac to null
    }

    /** Tên các tướng (hoặc "?") của đội đang hiện trong Thành Tích mà bản ghi có khung còn của bạn không khung; null nếu
     *  không tách được thẻ tướng. */
    fun thieu(dai: Mat): List<String>? {
        val the = tachThe(dai) ?: return null
        val out = mutableListOf<String>()
        for (t in the) {
            if (tv.khung(t.anh) == 1) {
                val (ten, k) = khungCuaToi(t.mat)
                val canKhung = ten == null || (tv.coKhung[ten] ?: 1.0) >= KHUNG_CAN
                if (canKhung && k == 0) out.add(ten ?: "?")
            }
            t.release()
        }
        return out
    }
}

/** Dải tướng của đội đang hiện trong Thành Tích (theo máy gốc); null nếu không thấy bảng. */
fun daiTuong(nd: NhanDien, img: Mat): Mat? {
    val (small, _) = nd.thuNho(img)
    val moc = nd.tim(small, "tt_nam_dam")
    small.release()
    if (moc.diem < 0.8) return null
    val ref = veGoc(img)
    val dx = moc.x * 2 - (285 + 365) / 2.0
    val dy = moc.y * 2 - (672 + 772) / 2.0
    val d = ref.cat(DAI_TUONG.x0 + dx, DAI_TUONG.y0 + dy, DAI_TUONG.x1 + dx, DAI_TUONG.y1 + dy).clone()
    if (ref !== img) ref.release()
    return d
}
