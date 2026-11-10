package vn.afkauto.leoai.vision
import nu.pattern.OpenCV
import org.json.JSONObject
import java.io.File
import kotlin.test.Test
class V2ParityTest {
 @Test fun pinnedPythonRelease() {
  OpenCV.loadLocally();val root=File(System.getProperty("afkauto.root"))
  val manifest=JSONObject(File(root,"android/app/src/main/assets/vision-v2/manifest.json").readText())
  val fixture=File(root,"debug/vision-fixtures/${manifest.getString("version")}/expected.json")
  val expected=JSONObject(fixture.readText())
  val report=DoiChieuV2({File(root,it).readBytes()},{File(root,if(it.startsWith("vision-v2/"))"android/app/src/main/assets/$it" else "templates/$it").readBytes()}).run(expected)
  File(fixture.parentFile,"jvm.json").writeText(report.toString(2));println(report)
 }
}
