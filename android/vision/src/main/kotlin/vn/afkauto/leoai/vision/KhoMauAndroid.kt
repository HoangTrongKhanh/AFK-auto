package vn.afkauto.leoai.vision

import org.json.*
import org.opencv.core.*
import org.opencv.imgcodecs.Imgcodecs
import java.io.File
import java.io.FileOutputStream
import java.util.UUID
import java.util.concurrent.ConcurrentHashMap

/** Bản mẫu bất biến, lịch sử và mẫu cá nhân được giữ khi đổi bộ đóng gói. */
class KhoMauAndroid(private val root: File, private val packaged: (String) -> ByteArray) {
    private val lock = locks.computeIfAbsent(root.canonicalPath) { Any() }
    private fun atomic(file: File, data: ByteArray) {
        file.parentFile!!.mkdirs(); val tmp = File(file.parentFile, ".${UUID.randomUUID()}")
        try { FileOutputStream(tmp).use { it.write(data); it.fd.sync() }; check(tmp.renameTo(file)) { "Không đổi được bản mẫu" } } finally { tmp.delete() }
    }
    private fun load(dir: File) = BoNhanDang.load { File(dir, it).readBytes() }
    private fun pointer() = File(root, "current.json")
    private fun history(p: JSONObject): MutableList<String> = p.optJSONArray("history")?.let { a -> (0 until a.length()).map { a.getString(it) }.toMutableList() }
        ?: mutableListOf<String>().apply { if (!p.isNull("previous")) p.optString("previous").takeIf { it.isNotBlank() }?.let { add(it) } }
    private fun setPointer(b: BoNhanDang, past: List<String>, packagedVersion: String) {
        val dir = File(root, "versions/${b.version}")
        atomic(pointer(), JSONObject().put("version", b.version).put("sha256", sha256(File(dir, "manifest.json").readBytes()))
            .put("history", JSONArray(past)).put("previous", past.lastOrNull() ?: JSONObject.NULL).put("packaged_version", packagedVersion).toString().toByteArray())
    }
    private fun install(b: BoNhanDang, read: (String) -> ByteArray, packagedVersion: String) {
        require(b.version.matches(Regex("[a-z0-9-]+")))
        val dir = File(root, "versions/${b.version}")
        if (!dir.exists()) {
            val tmp = File(root, "versions/.${UUID.randomUUID()}"); tmp.mkdirs()
            try {
                for (n in b.manifest.getJSONObject("files").keys().asSequence() + sequenceOf("manifest.json")) File(tmp, n).writeBytes(read(n))
                load(tmp); check(tmp.renameTo(dir)) { "Không lưu được bản mẫu" }
            } finally { tmp.deleteRecursively() }
        }
        load(dir); check(sha256(File(dir, "manifest.json").readBytes()) == sha256(read("manifest.json"))) { "Phiên bản mẫu bị trùng nội dung khác" }
        val old = if (pointer().exists()) JSONObject(pointer().readText()) else null
        val past = old?.let { history(it) } ?: mutableListOf()
        if (old != null && old.getString("version") != b.version) past.add(old.getString("version"))
        setPointer(b, past, packagedVersion)
    }
    fun current(): BoNhanDang = synchronized(lock) {
        val base = BoNhanDang.load(packaged)
        if (!pointer().exists()) { install(base, packaged, base.version); return@synchronized current() }
        val p = JSONObject(pointer().readText()); val version = p.getString("version"); require(version.matches(Regex("[a-z0-9-]+")))
        val dir = File(root, "versions/$version")
        check(sha256(File(dir, "manifest.json").readBytes()) == p.getString("sha256")) { "Con trỏ bộ mẫu bị hỏng" }
        val active = load(dir)
        val seen = p.optString("packaged_version").ifBlank { active.manifest.getString("python_version") }
        if (seen != base.version) return@synchronized migrate(active, base)
        if (!p.has("packaged_version")) setPointer(active, history(p), base.version)
        active
    }
    private fun catalog(): List<JSONObject> = File(root, "pending").listFiles()?.filter { it.extension == "json" }?.sortedBy { it.name }?.map { JSONObject(it.readText()) } ?: emptyList()
    fun pending(): List<JSONObject> = synchronized(lock) { catalog() }
    private fun pixel(face: Mat) = sha256("(48, 48, 3)|u1".toByteArray() + bytes(face))
    private fun validate(name: String, face: Mat, source: String, base: BoNhanDang) {
        require(name.isNotBlank() && name.length <= 80 && source.matches(Regex("[a-f0-9]{64}")))
        require(face.rows() == 48 && face.cols() == 48 && face.channels() == 3)
        val px = pixel(face)
        for (b in listOf(base, BoNhanDang.load(packaged))) {
            val p = b.protection
            require((0 until p.getJSONArray("sources").length()).none { p.getJSONArray("sources").getString(it) == source }) { "Ảnh thuộc bộ kiểm tra, không đưa vào mẫu học" }
            require((0 until p.getJSONArray("pixels").length()).none { p.getJSONArray("pixels").getString(it) == px }) { "Mẫu thuộc bộ kiểm tra" }
        }
        val records = base.samples.getJSONObject("records")
        for (id in records.keys()) {
            val r = records.getJSONObject(id)
            if (r.getString("kind") == "face" && r.getString("status") == "approved" && r.getString("pixel_sha256") == px) {
                require(r.getString("label") == name) { "Cùng ảnh đã mang tên khác" }
                error("Ảnh này đã có trong bộ mẫu đang dùng")
            }
        }
    }
    fun stage(name: String, facePng: ByteArray, sourceSha: String): String = synchronized(lock) {
        val b = current(); val face = decodeImage(facePng)
        val px = try { validate(name, face, sourceSha, b); pixel(face) } finally { face.release() }
        require(catalog().none { it.getString("status") == "pending" && it.getString("pixel_sha256") == px && it.getString("label") != name }) { "Loại nhãn đang chờ trước khi đặt tên khác cho cùng ảnh" }
        val id = "android-" + sha256((name + px + sourceSha).toByteArray()).take(24)
        atomic(File(root, "pending/$id.png"), facePng)
        atomic(File(root, "pending/$id.json"), JSONObject().put("id", id).put("label", name).put("pixel_sha256", px).put("image_sha256", sha256(facePng))
            .put("source_sha256", sourceSha).put("request",UUID.randomUUID().toString()).put("status", "pending").put("role", "train").toString().toByteArray())
        id
    }
    private fun faceIds(b: BoNhanDang): List<String> = b.samples.getJSONArray("face_ids").let { a -> (0 until a.length()).map { a.getString(it) } }
    fun status(id: String): String = synchronized(lock) {
        val b = current(); val r = b.samples.getJSONObject("records").optJSONObject(id)
        val c=catalog().singleOrNull { it.getString("id") == id }
        if (id in faceIds(b) && r?.optString("status") == "approved") "approved"
        else if (c?.optString("status")=="pending" && (r?.optString("status")!="rejected" || c.optString("request")!=r.optString("request"))) "pending"
        else if (r?.optString("status")=="rejected" || c?.optString("status")=="rejected") "rejected"
        else "inactive"
    }
    fun localSamples(): List<JSONObject> = synchronized(lock) {
        current(); catalog().map { r -> JSONObject(r.toString()).put("status", status(r.getString("id"))) }
    }
    /** Rebuild the sheet by ID, preserving packaged faces, all frame bytes and rejected records. */
    private fun publish(base: BoNhanDang, removed: Set<String> = emptySet(), extras: List<Pair<JSONObject, Mat>> = emptyList(), notes: List<String>? = null, reason: String): BoNhanDang {
        val s = JSONObject(base.samples.toString()); val records = s.getJSONObject("records")
        val ids = JSONArray(); val names = JSONArray(); val faces = mutableListOf<Mat>(); val old = decodeImage(base.read("faces.png")); val sheet = Mat()
        try {
            for ((i, id) in faceIds(base).withIndex()) {
                if (id in removed) {
                    val pendingFile=File(root,"pending/$id.json")
                    val request=if(pendingFile.exists())JSONObject(pendingFile.readText()).optString("request") else records.getJSONObject(id).optString("request")
                    records.getJSONObject(id).put("status", "rejected").put("review", "user_withdrawn").put("request",request); continue
                }
                ids.put(id); names.put(records.getJSONObject(id).getString("label")); val view=old.submat(0, 48, i * 48, (i + 1) * 48);try{faces.add(view.clone())}finally{view.release()}
            }
            for ((r, face) in extras) { val id = r.getString("id"); require(id !in faceIds(base)); ids.put(id); names.put(r.getString("label")); records.put(id, JSONObject(r.toString())); faces.add(face.clone()) }
            require(faces.isNotEmpty()); Core.hconcat(faces, sheet)
            val encoded = MatOfByte(); val png = try { check(Imgcodecs.imencode(".png", sheet, encoded)); encoded.toArray() } finally { encoded.release() }
            s.put("face_ids", ids).put("names", names)
            if(notes!=null)s.put("migration_notes", JSONArray(notes))
            val sampleBytes = s.toString().toByteArray(); val m = JSONObject(base.manifest.toString())
            m.getJSONObject("files").put("samples.json", sha256(sampleBytes)).put("faces.png", sha256(png))
            m.put("version", "a-" + sha256(base.version.toByteArray() + sampleBytes + png).take(20)).put("change", reason)
            val all = mapOf("faces.png" to png, "samples.json" to sampleBytes, "model.json" to base.read("model.json"), "protected.json" to base.read("protected.json"), "manifest.json" to m.toString().toByteArray())
            val read = { n: String -> all.getValue(n) }; val b = BoNhanDang.load(read)
            install(b, read, BoNhanDang.load(packaged).version); return b
        } finally { faces.forEach { it.release() }; old.release(); sheet.release() }
    }
    fun review(id: String, approve: Boolean): String = synchronized(lock) {
        require(id.matches(Regex("android-[a-f0-9]{24}")))
        val b = current(); val f = File(root, "pending/$id.json"); val r = JSONObject(f.readText())
        if (!approve) {
            val version = if (id in faceIds(b)) publish(b, removed = setOf(id), reason = "withdraw").version else b.version
            r.put("status", "rejected"); atomic(f, r.toString().toByteArray()); return@synchronized version
        }
        require(status(id) == "pending") { "Mẫu không còn trong danh sách chờ duyệt" }
        val png = pendingImage(id).readBytes(); check(sha256(png) == r.getString("image_sha256")) { "Ảnh mẫu đã đổi" }
        val face = decodeImage(png)
        try {
            validate(r.getString("label"), face, r.getString("source_sha256"), b)
            require(pixel(face) == r.getString("pixel_sha256"))
            r.put("kind", "face").put("status", "approved").put("review", "user_confirmed").put("sources", JSONArray().put(JSONObject().put("source_sha256", r.getString("source_sha256")).put("label_source", "user_confirmed")))
            val version = publish(b, extras = listOf(r to face), reason = "approve").version
            atomic(f, r.toString().toByteArray()); version
        } finally { face.release() }
    }
    private fun migrate(active: BoNhanDang, base: BoNhanDang): BoNhanDang {
        val extras = mutableListOf<Pair<JSONObject, Mat>>(); val notes = mutableListOf<String>(); val old = decodeImage(active.read("faces.png"))
        try {
            for ((i, id) in faceIds(active).withIndex()) if (id.startsWith("android-")) {
                val r = active.samples.getJSONObject("records").getJSONObject(id); val view=old.submat(0, 48, i * 48, (i + 1) * 48);val face=try{view.clone()}finally{view.release()}
                try { validate(r.getString("label"), face, r.getString("source_sha256"), base); extras.add(JSONObject(r.toString()) to face) }
                catch (e: IllegalArgumentException) { notes.add("${r.getString("label")}: ${e.message}"); face.release() }
                catch (e: IllegalStateException) { notes.add("${r.getString("label")}: ${e.message}"); face.release() }
            }
            if (extras.isEmpty() && notes.isEmpty()) { install(base, packaged, base.version); return base }
            return publish(base, extras = extras, notes = notes, reason = "package_update")
        } finally { extras.forEach { it.second.release() }; old.release() }
    }
    fun pendingImage(id: String): File { require(id.matches(Regex("android-[a-f0-9]{24}"))); return File(root, "pending/$id.png") }
    fun previousVersion(): String? = synchronized(lock) {
        current(); val p = JSONObject(pointer().readText()); history(p).lastOrNull()?.also { require(it.matches(Regex("[a-z0-9-]+"))); load(File(root, "versions/$it")) }
    }
    fun rollback(): String = synchronized(lock) {
        current(); val p = JSONObject(pointer().readText()); val past = history(p); val previous = past.removeLastOrNull() ?: error("Chưa có bản trước")
        require(previous.matches(Regex("[a-z0-9-]+"))); val b = load(File(root, "versions/$previous"))
        val latest=BoNhanDang.load(packaged)
        val records=b.samples.getJSONObject("records")
        for(id in faceIds(b).filter{it.startsWith("android-")}) {
            val r=records.getJSONObject(id);val protected=latest.protection
            require((0 until protected.getJSONArray("sources").length()).none{protected.getJSONArray("sources").getString(it)==r.getString("source_sha256")} &&
                (0 until protected.getJSONArray("pixels").length()).none{protected.getJSONArray("pixels").getString(it)==r.getString("pixel_sha256")}) { "Bản cũ chứa mẫu thuộc bộ kiểm tra mới, không thể khôi phục" }
        }
        setPointer(b, past, latest.version); b.version
    }
    fun usingOlderPackage(): Boolean = synchronized(lock) { current().manifest.getString("python_version") != BoNhanDang.load(packaged).version }
    fun restorePackaged(): String = synchronized(lock) { migrate(current(), BoNhanDang.load(packaged)).version }
    companion object { private val locks = ConcurrentHashMap<String, Any>() }
}
