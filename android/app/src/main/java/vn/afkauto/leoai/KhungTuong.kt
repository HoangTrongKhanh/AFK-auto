package vn.afkauto.leoai

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

/** Khung tướng của bạn, dùng chung cho màn hình app và bot (tệp trong thư mục riêng của app):
 *  - các tướng quan trọng (theo thư viện tướng): tướng mà ít nhất 5% bản ghi dùng có khung;
 *  - khung bạn tự đánh dấu (luôn thay kết quả tự đọc);
 *  - thẻ ứng viên của từng tướng quan trọng ở lần đọc danh sách gần nhất, và thẻ bạn đã xác nhận đúng là tướng đó (bot thêm
 *    mặt thẻ vào thư viện và viền thẻ vào bước xếp khung, lần đọc sau nhận đúng ngay). */
object KhungTuong {
    const val TEP_TAY = "khung_tay.json"            // {tên: 1 có khung | 0 không khung | -1 chưa có tướng}
    const val TEP_TU_DOC = "tuong_cua_toi.json"     // kết quả tự đọc (Leo.docDanhSachTuong)
    const val TEP_UNG_VIEN = "ung_vien.json"        // {tên: [{anh, khung, diem}]}
    const val THU_MUC_UNG_VIEN = "ung_vien"
    const val TEP_XAC_NHAN = "xac_nhan.json"        // {tên: {anh, khung}}
    const val THU_MUC_XAC_NHAN = "xac_nhan"
    private const val QUAN_TRONG = 0.05
    private const val KHUNG_CAN = 0.5               // như vision.KHUNG_CAN: tướng bản ghi ít dùng có khung thì không cần so

    const val CO = 1
    const val KHONG = 0
    const val CHUA_CO = -1

    data class TuongQuanTrong(val ten: String, val phan: Double)
    data class UngVien(val anh: String, val khung: Int, val diem: Double, val trongDoi: Boolean = false)
    data class XacNhan(val anh: String, val khung: Int)

    /** Tướng quan trọng, giảm dần theo phần bản ghi dùng tướng đó có khung. */
    fun quanTrong(ctx: Context): List<TuongQuanTrong> = runCatching {
        val js = JSONObject(ctx.assets.open("vi/tuong/tuong.json").use { String(it.readBytes(), Charsets.UTF_8) })
        val tuong = js.getJSONObject("tuong")
        val ds = tuong.keys().asSequence().map { it to tuong.getJSONObject(it) }.toList()
        val n = js.optInt("so_ban_ghi", 0).takeIf { it > 0 } ?: maxOf(1, ds.sumOf { it.second.optInt("so_lan") } / 5)
        ds.filter { it.second.optInt("so_lan") > 0 && it.second.optDouble("co_khung") >= KHUNG_CAN }
            .map { TuongQuanTrong(it.first, it.second.optInt("so_lan") * it.second.optDouble("co_khung") / n) }
            .filter { it.phan >= QUAN_TRONG }.sortedByDescending { it.phan }
    }.getOrDefault(emptyList())

    fun docTay(dir: File): MutableMap<String, Int> = docObj(File(dir, TEP_TAY)).let { o ->
        o.keys().asSequence().associateWith { o.getInt(it) }.toMutableMap()
    }

    fun ghiTay(dir: File, tay: Map<String, Int>) =
        File(dir, TEP_TAY).writeText(JSONObject(tay.toSortedMap() as Map<*, *>).toString(1))

    /** Kết quả tự đọc: tên -> khung (lấy khung cao nhất nếu một tướng có nhiều thẻ), TRONG_DOI nếu chỉ thấy thẻ của tướng
     *  đang trong đội: game phủ xanh thẻ đó nên không đọc được khung (14/10: Eryndor có khung bị đọc thành không khung). */
    fun docTuDoc(dir: File): Map<String, Int> = runCatching {
        val arr = JSONArray(File(dir, TEP_TU_DOC).readText())
        val out = mutableMapOf<String, Int>()
        for (i in 0 until arr.length()) {
            val o = arr.getJSONObject(i)
            if (!o.has("ten")) continue
            val t = o.getString("ten")
            if (o.optBoolean("trong_doi")) { if (t !in out) out[t] = TRONG_DOI; continue }
            out[t] = maxOf(out[t]?.takeIf { it != TRONG_DOI } ?: 0, o.getInt("khung"))
        }
        out
    }.getOrDefault(emptyMap())

    const val TRONG_DOI = -2

    fun docUngVien(dir: File): Map<String, List<UngVien>> = docObj(File(dir, TEP_UNG_VIEN)).let { o ->
        o.keys().asSequence().associateWith { t ->
            val a = o.getJSONArray(t)
            (0 until a.length()).map { a.getJSONObject(it) }
                .map { UngVien(it.getString("anh"), it.getInt("khung"), it.getDouble("diem"), it.optBoolean("trong_doi")) }
        }
    }

    fun ghiUngVien(dir: File, uv: Map<String, List<UngVien>>) {
        val o = JSONObject()
        for ((t, ds) in uv) o.put(t, JSONArray(ds.map {
            JSONObject().put("anh", it.anh).put("khung", it.khung).put("diem", it.diem).put("trong_doi", it.trongDoi)
        }))
        File(dir, TEP_UNG_VIEN).writeText(o.toString(1))
    }

    fun docXacNhan(dir: File): MutableMap<String, XacNhan> = docObj(File(dir, TEP_XAC_NHAN)).let { o ->
        o.keys().asSequence().associateWith { o.getJSONObject(it).let { x -> XacNhan(x.getString("anh"), x.getInt("khung")) } }.toMutableMap()
    }

    fun ghiXacNhan(dir: File, xn: Map<String, XacNhan>) {
        val o = JSONObject()
        for ((t, x) in xn) o.put(t, JSONObject().put("anh", x.anh).put("khung", x.khung))
        File(dir, TEP_XAC_NHAN).writeText(o.toString(1))
    }

    private fun docObj(f: File) = runCatching { JSONObject(f.readText()) }.getOrDefault(JSONObject())
}
