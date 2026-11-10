package vn.afkauto.leoai
import android.app.Instrumentation
import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.os.Debug
import android.view.WindowManager
import org.json.JSONObject
import org.opencv.android.OpenCVLoader
import java.io.File
import vn.afkauto.leoai.vision.DoiChieuV2

/** Chạy trên bản thử riêng, không đụng dữ liệu hay quyền Trợ năng của ứng dụng chính. */
class V2Instrumentation:Instrumentation() {
 private var mode="parity"
 override fun onCreate(arguments:Bundle?) {super.onCreate(arguments);mode=arguments?.getString("mode")?:"parity";start()}
 override fun onStart() {
  val out=File(targetContext.getExternalFilesDir(null),"parity/result.json");out.parentFile!!.mkdirs()
  try {
   check(OpenCVLoader.initLocal())
   if(mode=="records") {
    val report=ThanhTichChecks.run(this)
    out.writeText(report.toString(2))
    finish(Activity.RESULT_OK,Bundle().apply{putString("report",report.toString())});return
   }
   val activity=startActivitySync(Intent(targetContext,MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
   runOnMainSync { activity.window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON) }
   if(mode=="storage") {
    val report=StorageChecks.run(targetContext.cacheDir){targetContext.assets.open(it).use{f->f.readBytes()}}
    val ui=SampleUiChecks.run(this,activity as MainActivity)
    for(key in ui.keys())report.put(key,ui.get(key))
    report.put("device",android.os.Build.MODEL);out.writeText(report.toString(2));runOnMainSync { activity.finish() }
    finish(Activity.RESULT_OK,Bundle().apply{putString("report",report.toString())});return
   }
   val manifest=JSONObject(targetContext.assets.open("vision-v2/manifest.json").use { String(it.readBytes(),Charsets.UTF_8) })
   val root=File(targetContext.getExternalFilesDir(null),"parity");val expected=JSONObject(File(root,"debug/vision-fixtures/${manifest.getString("version")}/expected.json").readText())
   val report=DoiChieuV2({File(root,it).readBytes()},{targetContext.assets.open(it).use{f->f.readBytes()}}).run(expected)
   report.put("success",true).put("device",android.os.Build.MODEL).put("native_heap_bytes",Debug.getNativeHeapAllocatedSize()).put("java_heap_bytes",Runtime.getRuntime().totalMemory()-Runtime.getRuntime().freeMemory())
   out.writeText(report.toString(2));runOnMainSync { activity.finish() };finish(Activity.RESULT_OK,Bundle().apply{putString("report",report.toString())})
  }catch(e:Throwable){val report=JSONObject().put("success",false).put("error",e.stackTraceToString());out.writeText(report.toString(2));finish(Activity.RESULT_CANCELED,Bundle().apply{putString("error",e.stackTraceToString())})}
 }
}
