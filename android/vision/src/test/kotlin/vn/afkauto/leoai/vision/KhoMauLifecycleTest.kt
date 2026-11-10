package vn.afkauto.leoai.vision

import java.io.File
import nu.pattern.OpenCV
import org.json.JSONObject
import org.json.JSONArray
import org.opencv.core.MatOfByte
import org.opencv.imgcodecs.Imgcodecs
import kotlin.test.*

class KhoMauLifecycleTest {
    private val repo=File(System.getProperty("afkauto.root"))
    private fun packaged():MutableMap<String,ByteArray> {
        OpenCV.loadLocally();val dir=File(repo,"android/app/src/main/assets/vision-v2")
        return listOf("manifest.json","faces.png","samples.json","model.json","protected.json").associateWith{File(dir,it).readBytes()}.toMutableMap()
    }
    private fun upgrade(data:Map<String,ByteArray>,version:String,protectedSource:String?=null):MutableMap<String,ByteArray> {
        val out=data.toMutableMap()
        if(protectedSource!=null){val p=JSONObject(String(out.getValue("protected.json")));p.getJSONArray("sources").put(protectedSource);out["protected.json"]=p.toString().toByteArray()}
        val m=JSONObject(String(out.getValue("manifest.json")));m.put("version",version).put("python_version",version)
        for(n in m.getJSONObject("files").keys())m.getJSONObject("files").put(n,sha256(out.getValue(n)))
        out["manifest.json"]=m.toString().toByteArray();return out
    }
    private fun face(seed:Int):ByteArray {
        val im=decodeImage(File(repo,"templates/vi/tuong/Rowan.png").readBytes());val crop=im.submat(0,48,0,48).clone();im.release()
        crop.put(0,0,byteArrayOf(seed.toByte(),2,3));val encoded=MatOfByte()
        return try {assertTrue(Imgcodecs.imencode(".png",crop,encoded));encoded.toArray()}finally{crop.release();encoded.release()}
    }
    private fun ids(b:BoNhanDang):Set<String> = b.samples.getJSONArray("face_ids").let{a->(0 until a.length()).map{a.getString(it)}.toSet()}
    @Test fun withdrawingApprovedSamplePreservesOthersAndHistory() {
        val data=packaged();val dir=kotlin.io.path.createTempDirectory("afk-lifecycle-").toFile()
        try {
            val store=KhoMauAndroid(dir){data.getValue(it)};val original=store.current();val id1=store.stage("Rowan",face(17),"c".repeat(64));store.review(id1,true)
            val one=store.current().version;val id2=store.stage("Rowan",face(18),"d".repeat(64));store.review(id2,true);val both=store.current().version
            store.review(id1,false);assertFalse(id1 in ids(store.current()));assertTrue(id2 in ids(store.current()));assertEquals("rejected",store.status(id1))
            assertContentEquals(original.read("model.json"),store.current().read("model.json"))
            assertEquals(both,store.rollback());assertEquals("approved",store.status(id1));assertEquals(one,store.rollback())
            assertTrue(id1 in ids(store.current()));assertFalse(id2 in ids(store.current()));assertEquals(original.version,store.rollback());assertEquals("rejected",store.status(id1))
            assertNull(store.previousVersion());assertFails{store.rollback()}
        }finally{dir.deleteRecursively()}
    }
    @Test fun updatingPackageMigratesOnlyActivePersonalSamplesAndKeepsPending() {
        var data=packaged();val dir=kotlin.io.path.createTempDirectory("afk-lifecycle-").toFile()
        try {
            val store=KhoMauAndroid(dir){data.getValue(it)};val original=store.current();val id=store.stage("Rowan",face(21),"c".repeat(64));val localVersion=store.review(id,true)
            val waiting=store.stage("Rowan",face(22),"d".repeat(64));val reject=store.stage("Rowan",face(23),"e".repeat(64));store.review(reject,false)
            data=upgrade(data,"v-new-package");val migrated=store.current()
            assertEquals("v-new-package",migrated.manifest.getString("python_version"));assertTrue(id in ids(migrated));assertEquals(ids(original).size+1,ids(migrated).size)
            assertEquals("pending",store.status(waiting));assertEquals("rejected",store.status(reject));assertContentEquals(original.read("model.json"),migrated.read("model.json"))
            assertEquals(localVersion,store.rollback());assertEquals(localVersion,KhoMauAndroid(dir){data.getValue(it)}.current().version);assertTrue(store.usingOlderPackage())
            assertEquals(original.version,store.rollback());data=upgrade(data,"v-third-package")
            assertFalse(id in ids(store.current()));assertEquals("pending",store.status(waiting));assertEquals("inactive",store.status(id))
        }finally{dir.deleteRecursively()}
    }
    @Test fun newProtectionQuarantinesLocalSampleAndCannotBeBypassedByRollback() {
        var data=packaged();val dir=kotlin.io.path.createTempDirectory("afk-lifecycle-").toFile()
        try {
            val store=KhoMauAndroid(dir){data.getValue(it)};val png=face(31);val source="b".repeat(64);val id=store.stage("Rowan",png,source);store.review(id,true)
            data=upgrade(data,"v-protected-package",source);val active=store.current();assertFalse(id in ids(active));assertEquals(1,active.samples.getJSONArray("migration_notes").length())
            assertFails{store.stage("Rowan",png,source)};assertFails{store.rollback()};assertEquals(active.version,store.current().version)
        }finally{dir.deleteRecursively()}
    }
    @Test fun explicitlyConfirmingWithdrawnSampleAllowsReviewAgain() {
        val data=packaged();val dir=kotlin.io.path.createTempDirectory("afk-lifecycle-").toFile()
        try {
            val store=KhoMauAndroid(dir){data.getValue(it)};val png=face(51);val source="a".repeat(64)
            val id=store.stage("Rowan",png,source);store.review(id,true);store.review(id,false)
            assertEquals("rejected",store.status(id));assertEquals(id,store.stage("Rowan",png,source));assertEquals("pending",store.status(id))
            store.review(id,true);assertEquals("approved",store.status(id));assertTrue(id in ids(store.current()))
            val f=File(dir,"pending/$id.json");val stale=JSONObject(f.readText());store.review(id,false);f.writeText(stale.put("status","pending").toString())
            assertEquals("rejected",store.status(id));assertFalse(id in ids(store.current()))
        }finally{dir.deleteRecursively()}
    }
    @Test fun approvedSnapshotIsAuthoritativeAfterInterruptedCatalogWrite() {
        val data=packaged();val dir=kotlin.io.path.createTempDirectory("afk-lifecycle-").toFile()
        try {
            val store=KhoMauAndroid(dir){data.getValue(it)};val id=store.stage("Rowan",face(41),"a".repeat(64));store.review(id,true)
            val file=File(dir,"pending/$id.json");val record=JSONObject(file.readText()).put("status","pending");file.writeText(record.toString())
            assertEquals("approved",store.localSamples().single().getString("status"));assertFails{store.review(id,true)}
            store.review(id,false);assertEquals("rejected",store.status(id));assertFalse(id in ids(store.current()))
        }finally{dir.deleteRecursively()}
    }
}
