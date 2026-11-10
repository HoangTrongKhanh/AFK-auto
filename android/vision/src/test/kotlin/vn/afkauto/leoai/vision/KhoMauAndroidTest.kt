package vn.afkauto.leoai.vision
import java.io.File
import nu.pattern.OpenCV
import org.json.JSONObject
import kotlin.test.*
class KhoMauAndroidTest {
 @Test fun reviewProtectionAndRollback() {
  OpenCV.loadLocally();val repo=File(System.getProperty("afkauto.root"));val dir=kotlin.io.path.createTempDirectory("afk-model-").toFile()
  try {
   val store=KhoMauAndroid(dir){File(repo,"android/app/src/main/assets/vision-v2/$it").readBytes()};val base=store.current();val data=File(repo,"templates/vi/tuong/Rowan.png").readBytes();val img=decodeImage(data);val face=img.submat(0,48,0,48);face.put(0,0,byteArrayOf(1,2,3));val bytes=org.opencv.core.MatOfByte();org.opencv.imgcodecs.Imgcodecs.imencode(".png",face,bytes);face.release();img.release();val png=bytes.toArray();bytes.release()
   val id=store.stage("Rowan",png,"f".repeat(64));assertEquals(base.version,store.current().version);assertEquals("pending",store.pending().single().getString("status"))
   val version=store.review(id,true);assertNotEquals(base.version,version);assertEquals(base.samples.getJSONArray("names").length()+1,store.current().samples.getJSONArray("names").length());assertContentEquals(base.read("model.json"),store.current().read("model.json"));assertEquals(base.version,store.rollback())
   val blocked=base.protection.getJSONArray("sources").getString(0);assertFailsWith<IllegalArgumentException>{store.stage("Rowan",png,blocked)}
   val id2=store.stage("Rowan",png,"e".repeat(64));store.review(id2,false);assertEquals(base.version,store.current().version)
   val current=JSONObject(File(dir,"current.json").readText());File(dir,"versions/${current.getString("version")}/model.json").appendText(" ")
   assertFailsWith<IllegalArgumentException>{store.current()}
  }finally{dir.deleteRecursively()}
 }
}
