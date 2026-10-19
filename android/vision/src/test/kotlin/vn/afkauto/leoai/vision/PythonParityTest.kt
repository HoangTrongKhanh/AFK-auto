package vn.afkauto.leoai.vision

import nu.pattern.OpenCV
import org.opencv.core.Mat
import java.io.File
import kotlin.math.abs
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNotNull
import kotlin.test.assertNull
import kotlin.test.assertTrue

/** So kết quả của bản Kotlin với bản Python (ket_qua_python.tsv, tạo bằng tao_ket_qua_python.py) trên mọi ảnh trong
 *  samples/. Bản Python dùng OpenCV 5, bản này OpenCV 4.9 nên điểm khớp và vị trí được phép lệch chút ít. */
class PythonParityTest {
    private val root = File(System.getProperty("afkauto.root") ?: "../..")
    private val bo: BoMau
    private val nd: NhanDien
    private val images = mutableMapOf<String, Mat>()
    private val expected: List<List<String>>

    init {
        OpenCV.loadLocally()
        bo = BoMau.load(
            read = { File(root, "templates/$it").readBytes() },
            list = { File(root, "templates/$it").list()!!.toList() },
        )
        nd = NhanDien(bo)
        expected = javaClass.getResource("/ket_qua_python.tsv")!!.readText().lines()
            .filter { it.isNotBlank() }.map { it.split("\t") }
    }

    private fun image(rel: String) = images.getOrPut(rel) { decodeImage(File(root, rel).readBytes()) }

    private fun rows(kind: String) = expected.filter { it[0] == kind }.also { assertTrue(it.isNotEmpty(), "thiếu dòng '$kind'") }

    private fun xy(s: String) = s.split(",").map(String::toInt).let { it[0] to it[1] }

    @Test
    fun manHinhVaNut() {
        for (r in rows("man")) {
            val k = nd.nhanDien(image(r[1]))
            assertEquals(r[2], k.manHinh, "${r[1]}: $k")
            assertEquals(r[3].takeIf { it != "-" }, k.cheDo, "${r[1]}: chế độ")
            assertEquals(r[4] == "1", k.tuDong, "${r[1]}: tự động")
            assertEquals(r[5].toDouble(), k.doSang, 0.5, "${r[1]}: độ sáng")
            val want = r.getOrElse(6) { "" }.split(";").filter { it.isNotEmpty() }
                .associate { it.substringBefore(":") to xy(it.substringAfter(":")) }
            assertEquals(want.keys, k.nut.keys, "${r[1]}: các nút")
            assertEquals(r[7] == "1", k.daiDien, "${r[1]}: leo hộ")
            for ((t, p) in want) {
                val g = k.nut.getValue(t)
                assertTrue(abs(p.first - g.first) <= 2 && abs(p.second - g.second) <= 2, "${r[1]}: $t $p != $g")
            }
        }
    }

    @Test
    fun diemKhop() {
        var n = 0
        for (r in rows("diem")) {
            val got = nd.tatCaDiem(image(r[1]))
            for (cell in r.drop(2)) {
                val t = cell.substringBefore(":")
                assertEquals(cell.substringAfter(":").toDouble(), got.getValue(t), 0.02, "${r[1]}: điểm $t")
                n++
            }
        }
        println("Đã so $n điểm khớp")
    }

    @Test
    fun docThanhTich() {
        val doc = DocThanhTich(nd)
        var n = 0
        for (r in rows("doi")) {
            val d = doc.doc(image(r[1]))
            if (r[2] == "none") {
                assertNull(d, "${r[1]}: Python không thấy Thành Tích")
                continue
            }
            assertNotNull(d, "${r[1]}: không thấy Thành Tích")
            assertEquals(r[2].takeIf { it != "-" }, d.lucChien, "${r[1]}: lực chiến")
            assertEquals(r[3].takeIf { it != "-" }, d.nhan, "${r[1]}: nhãn")
            assertEquals(r[4] == "1", d.lyTuong, "${r[1]}: lý tưởng")
            assertEquals(r[5] == "1", d.thuCong, "${r[1]}: thủ công")
            assertEquals(r[6].takeIf { it != "-" }?.let { it == "1" }, d.locBat, "${r[1]}: ô lọc")
            if (r[7] == "-") {
                assertNull(d.chuKy, "${r[1]}: chữ ký")
            } else {
                val py = Bin(CHU_KY_RONG, CHU_KY_CAO, BooleanArray(r[7].length) { r[7][it] == '1' })
                val s = giongTen(py, d.chuKy)
                assertTrue(s >= 0.95, "${r[1]}: chữ ký tên giống bản Python ${"%.3f".format(s)}")
            }
            n++
        }
        println("Đã so $n đội Thành Tích")
    }

    @Test
    fun lucDoi() {
        val doc = DocThanhTich(nd)
        for (r in rows("luc_doi")) {
            val got = doc.lucDoi(image(r[1]))
            if (r[2] == "-") assertNull(got, "${r[1]}: lực chiến đội") else assertEquals(r[2].toDouble(), assertNotNull(got, r[1]), 1e-6, r[1])
            assertEquals(r[3] == "1", doc.doiTrong(image(r[1])), "${r[1]}: đội trống")
        }
    }

    @Test
    fun soAi() {
        val so = DocSoAi(nd)
        for (r in rows("so")) {
            val img = image(r[1])
            assertEquals(r[2].takeIf { it != "-" }?.toInt(), so.aiManAfk(img), "${r[1]}: ải Màn AFK")
            assertEquals(r[3].takeIf { it != "-" }?.let(::xy), so.tienTrinhThang(img), "${r[1]}: tiến trình thắng")
            assertEquals(r[4].takeIf { it != "-" }?.let(::xy), so.tienTrinhTuDong(img), "${r[1]}: tiến trình tự động")
            assertEquals(r[5].takeIf { it != "-" }?.toInt(), so.aiDoiHinh(img), "${r[1]}: ải ở tiêu đề đội hình")
        }
    }

    private val tv by lazy { ThuVienTuong.load { File(root, "templates/$it").readBytes() } }

    @Test
    fun theTuong() {
        var n = 0
        for (r in rows("the")) {
            val dai = assertNotNull(daiTuong(nd, image(r[1])), r[1])
            val the = assertNotNull(tachThe(dai), "${r[1]}: không tách được thẻ")
            assertEquals(r.size - 2, the.size, r[1])
            for ((i, cell) in r.drop(2).withIndex()) {
                val (ten, diem, khung) = cell.split(":")
                val (d, t) = tv.diem(the[i].mat).first()
                assertEquals(ten, t, "${r[1]} thẻ ${i + 1}: tướng")
                assertEquals(diem.toDouble(), d, 0.03, "${r[1]} thẻ ${i + 1}: điểm")
                assertEquals(khung.toInt(), tv.khung(the[i].anh), "${r[1]} thẻ ${i + 1}: khung")
                n++
            }
        }
        println("Đã so $n thẻ tướng")
    }

    @Test
    fun thieuKhung() {
        val js = org.json.JSONObject(javaClass.getResource("/cua_toi.json")!!.readText())
        val sk = SoKhung(tv, js.keys().asSequence().associateWith { js.getInt(it) }, emptyList())
        for (r in rows("thieu")) {
            val dai = assertNotNull(daiTuong(nd, image(r[1])), r[1])
            assertEquals(r.getOrElse(2) { "" }, sk.thieu(dai)!!.joinToString(";"), r[1])
        }
    }

    @Test
    fun danhSachTuong() {
        for (r in rows("ds")) {
            val doc = DocDanhSach(tv)
            doc.them(image(r[1]))
            val got = doc.xong().map { "${it.ten ?: "-"}:${it.khung}:${if (it.trongDoi) 1 else 0}" }
            assertEquals(r.drop(2), got, r[1])
        }
    }

    @Test
    fun oKhoa() {
        for (r in rows("khoa")) {
            val got = timOKhoa(image(r[1]))
            if (r[2] == "none") assertNull(got, r[1]) else {
                val w = xy(r[2])
                assertNotNull(got, r[1])
                assertTrue(abs(w.first - got.first) <= 1 && abs(w.second - got.second) <= 1, "${r[1]}: $w != $got")
            }
        }
    }
}
