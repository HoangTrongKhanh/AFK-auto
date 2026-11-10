package vn.afkauto.leoai

import org.json.JSONObject
import org.json.JSONArray
import org.opencv.core.MatOfByte
import org.opencv.imgcodecs.Imgcodecs
import java.io.File
import java.util.UUID
import vn.afkauto.leoai.vision.*

/** Native filesystem/PNG checks in an isolated directory, never production account data. */
object StorageChecks {
    fun run(cache: File, assets: (String)->ByteArray): JSONObject {
        val root=File(cache,"storage-${UUID.randomUUID()}");root.mkdirs()
        try {
            val files=File(root,"profiles");files.mkdirs();File(files,"khung_tay.json").writeText("{\"Rowan\":1}")
            File(files,"tuong_cua_toi.json").writeText("[{\"ten\":\"Rowan\",\"mat\":\"tuong_cua_toi/a.png\"}]")
            File(files,"tuong_cua_toi").mkdirs();File(files,"tuong_cua_toi/a.png").writeBytes(byteArrayOf(1,2,3))
            val profiles=HoSoTaiKhoan(files);val old=profiles.current();val firstHash=sha256(File(old.dir,"khung_tay.json").readBytes())
            val other=profiles.create("Kiểm tra");check(!File(other.dir,"khung_tay.json").exists());File(other.dir,"khung_tay.json").writeText("{\"Rowan\":0}")
            profiles.select(old.id);check(sha256(File(profiles.current().dir,"khung_tay.json").readBytes())==firstHash)
            check(File(old.dir,"tuong_cua_toi/a.png").readBytes().contentEquals(byteArrayOf(1,2,3)))
            check(HoSoTaiKhoan(files).current().id==old.id);check(File(files,"khung_tay.json").exists())
            var data=listOf("manifest.json","faces.png","samples.json","model.json","protected.json").associateWith{assets("vision-v2/$it")}.toMutableMap()
            val store=KhoMauAndroid(File(root,"model")){data.getValue(it)};val base=store.current();val n=base.samples.getJSONArray("face_ids").length()
            val im=decodeImage(assets("vi/tuong/Rowan.png"));val view=im.submat(0,48,0,48);val face=view.clone();view.release();im.release();face.put(0,0,byteArrayOf(37,2,3))
            val buffer=MatOfByte();val png=try{check(Imgcodecs.imencode(".png",face,buffer));buffer.toArray()}finally{face.release();buffer.release()}
            val id=store.stage("Rowan",png,"f".repeat(64));check(store.current().version==base.version);val approved=store.review(id,true)
            val m=JSONObject(String(data.getValue("manifest.json")));m.put("version","v-native-new").put("python_version","v-native-new");data["manifest.json"]=m.toString().toByteArray()
            check(store.current().samples.getJSONArray("face_ids").length()==n+1);check(store.status(id)=="approved")
            check(store.rollback()==approved);check(store.current().version==approved)
            store.review(id,false);check(store.current().samples.getJSONArray("face_ids").length()==n);check(store.status(id)=="rejected")
            check(store.current().read("model.json").contentEquals(base.read("model.json")))
            store.restorePackaged();check(store.current().samples.getJSONArray("face_ids").length()==n);check(!store.usingOlderPackage())
            return JSONObject().put("success",true).put("profile_migration",true).put("profile_isolation",true).put("pending_not_active",true).put("approved_withdrawal",true).put("package_migration",true).put("cross_package_rollback",true).put("frame_model_unchanged",true)
        } finally { root.deleteRecursively() }
    }
}
