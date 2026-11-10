package vn.afkauto.leoai.vision
import org.json.JSONObject
import org.opencv.imgcodecs.Imgcodecs
import java.security.MessageDigest
fun sha256(bytes:ByteArray)=MessageDigest.getInstance("SHA-256").digest(bytes).joinToString(""){"%02x".format(it)}
class BoNhanDang(val manifest:JSONObject,val samples:JSONObject,val protection:JSONObject,val read:(String)->ByteArray) {
 val version:String get()=manifest.getString("version")
 fun apply(tv:ThuVienTuong,baseRead:(String)->ByteArray) {
  val names=samples.getJSONArray("names");val ids=samples.getJSONArray("face_ids");require(names.length()==ids.length());val records=samples.getJSONObject("records");val sheet=decodeImage(read("faces.png"));require(sheet.rows()==48 && sheet.cols()==names.length()*48)
  try {for(i in 0 until names.length()){val r=records.getJSONObject(ids.getString(i));require(r.getString("kind")=="face" && r.getString("status")=="approved" && r.getString("role")=="train" && r.getString("label")==names.getString(i));val part=sheet.submat(0,48,i*48,(i+1)*48);tv.themMat(names.getString(i),part.clone());part.release()}}finally{sheet.release()}
  val model=JSONObject(String(read("model.json"),Charsets.UTF_8));val training=samples.getJSONArray("training_ids");val labels=model.getJSONArray("labels");val heroIds=model.getJSONArray("ids");require(training.length()==labels.length())
  for(i in 0 until training.length()){val r=records.getJSONObject(training.getString(i));require(r.getString("kind")=="frame" && r.getString("status")=="approved" && r.getString("role")=="train" && r.getInt("label")==labels.getInt(i));val sources=r.getJSONArray("sources");require((0 until sources.length()).any{sources.getJSONObject(it).optInt("hero_id",-1)==heroIds.getInt(i)})}
  val stars=listOf("sao_khung_cam.png","sao_khung_mong.png").map{decodeImage(baseRead("vi/$it"),Imgcodecs.IMREAD_GRAYSCALE)};tv.engineV2=KhungV2(model,stars);tv.phienBan=version;tv.mocDau=decodeImage(baseRead("vi/ht_dau.png"),Imgcodecs.IMREAD_GRAYSCALE)
 }
 companion object {fun load(read:(String)->ByteArray):BoNhanDang {
  val m=JSONObject(String(read("manifest.json"),Charsets.UTF_8));require(m.getInt("schema")==1 && m.getInt("engine")==1 && m.getString("inference_policy")=="v2" && m.getString("name_policy")=="v2");val files=m.getJSONObject("files");require(files.keys().asSequence().toSet()==setOf("faces.png","model.json","samples.json","protected.json"));for(n in files.keys())require(sha256(read(n))==files.getString(n)){"Bộ mẫu bị thay đổi: $n"}
  return BoNhanDang(m,JSONObject(String(read("samples.json"),Charsets.UTF_8)),JSONObject(String(read("protected.json"),Charsets.UTF_8)),read)
 }}
}
