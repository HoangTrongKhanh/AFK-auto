package vn.afkauto.leoai.vision

import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.io.FileOutputStream
import java.util.UUID
import java.util.concurrent.ConcurrentHashMap

/** Chỉ dữ liệu sở hữu/khung thuộc hồ sơ; bộ nhận diện tên dùng chung. */
class HoSoTaiKhoan(private val files: File) {
    data class HoSo(val id: String, val ten: String, val dir: File)
    private val root = File(files, "ho_so")
    private val lock = locks.computeIfAbsent(root.canonicalPath) { Any() }
    private val index get() = File(root, "index.json")
    private fun write(value: JSONObject) {
        root.mkdirs()
        val tmp = File(root, ".${UUID.randomUUID()}")
        try {
            FileOutputStream(tmp).use { it.write(value.toString(2).toByteArray()); it.fd.sync() }
            check(tmp.renameTo(index)) { "Không lưu được hồ sơ tài khoản" }
        } finally { tmp.delete() }
    }
    private fun read(): JSONObject {
        if (!index.exists()) {
            val target = File(root, "data/cu")
            if (!target.exists()) {
                val tmp = File(root, "data/.${UUID.randomUUID()}")
                tmp.mkdirs()
                try {
                    for (name in LEGACY) {
                        val src = File(files, name)
                        if (src.exists()) check(src.copyRecursively(File(tmp, name))) { "Không chuyển được $name" }
                    }
                    val copied=JSONObject()
                    for(name in LEGACY) {
                        val src=File(files,name)
                        val originals=if(src.isDirectory) src.walkTopDown().filter{it.isFile}.toList() else if(src.isFile) listOf(src) else emptyList()
                        for(f in originals) {
                            val relative=f.relativeTo(files).path; val hash=sha256(f.readBytes())
                            check(sha256(File(tmp,relative).readBytes())==hash) { "Dữ liệu chuyển không khớp: $relative" }
                            copied.put(relative,hash)
                        }
                    }
                    File(tmp,"chuyen_du_lieu.json").writeText(JSONObject().put("files",copied).put("originals_retained",true).toString(2))
                    check(tmp.renameTo(target)) { "Không chuyển được dữ liệu cũ" }
                } finally { tmp.deleteRecursively() }
            }
            val count = runCatching { JSONArray(File(target, "tuong_cua_toi.json").readText()).length() }.getOrDefault(0)
            val name = if (count > 0) "Tài khoản $count tướng" else "Tài khoản hiện tại"
            write(JSONObject().put("schema", 1).put("active", "cu").put("profiles", JSONArray().put(JSONObject().put("id", "cu").put("name", name))))
        }
        val value = JSONObject(index.readText())
        require(value.getInt("schema") == 1)
        val entries = value.getJSONArray("profiles")
        val ids = (0 until entries.length()).map { entries.getJSONObject(it).getString("id") }
        require(ids.isNotEmpty() && ids.toSet().size == ids.size && ids.all { it.matches(Regex("[a-z0-9-]{1,50}")) }) { "Hồ sơ tài khoản không hợp lệ" }
        require(value.getString("active") in ids)
        return value
    }
    private fun profiles(value: JSONObject): List<HoSo> {
        val a = value.getJSONArray("profiles")
        return (0 until a.length()).map { a.getJSONObject(it) }.map { HoSo(it.getString("id"), it.getString("name"), File(root, "data/${it.getString("id")}")) }
    }
    fun list(): List<HoSo> = synchronized(lock) { profiles(read()) }
    fun current(): HoSo = synchronized(lock) { val v = read(); profiles(v).single { it.id == v.getString("active") }.also { it.dir.mkdirs() } }
    fun select(id: String): HoSo = synchronized(lock) {
        val v = read(); val selected = profiles(v).singleOrNull { it.id == id } ?: error("Không tìm thấy hồ sơ")
        selected.dir.mkdirs(); v.put("active", id); write(v); selected
    }
    private fun validName(name: String, others: List<HoSo>): String {
        val n = name.trim(); require(n.isNotEmpty() && n.length <= 80 && n.none { it.isISOControl() }) { "Tên tài khoản cần từ 1 đến 80 ký tự" }
        require(others.none { it.ten.equals(n, true) }) { "Tên hồ sơ này đã có" }; return n
    }
    fun create(name: String): HoSo = synchronized(lock) {
        val v = read(); val n = validName(name, profiles(v)); val id = UUID.randomUUID().toString()
        val dir = File(root, "data/$id"); check(dir.mkdirs())
        v.getJSONArray("profiles").put(JSONObject().put("id", id).put("name", n)); v.put("active", id); write(v)
        HoSo(id, n, dir)
    }
    fun rename(id: String, name: String): HoSo = synchronized(lock) {
        val v = read(); val all = profiles(v); require(all.any { it.id == id }); val n = validName(name, all.filter { it.id != id })
        val a = v.getJSONArray("profiles"); for (i in 0 until a.length()) if (a.getJSONObject(i).getString("id") == id) a.getJSONObject(i).put("name", n)
        write(v); profiles(v).single { it.id == id }
    }
    companion object {
        private val locks = ConcurrentHashMap<String, Any>()
        private val LEGACY = listOf("khung_tay.json", "tuong_cua_toi.json", "tuong_cua_toi.json.bak", "ung_vien.json", "xac_nhan.json", "tuong_cua_toi", "ung_vien", "xac_nhan")
    }
}
