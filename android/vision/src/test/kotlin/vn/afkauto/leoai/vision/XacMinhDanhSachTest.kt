package vn.afkauto.leoai.vision
import java.io.File
import nu.pattern.OpenCV
import org.opencv.imgcodecs.Imgcodecs
import kotlin.test.*
class XacMinhDanhSachTest {
 @Test fun requiresExternalCountFullBordersAndDistinctFaces() {
  OpenCV.loadLocally();val root=File(System.getProperty("afkauto.root"));val img=decodeImage(File(root,"debug/danh-sach-ngan-dien-mao-20261109/loc_thien_6/03.png").readBytes());val cap=decodeImage(File(root,"templates/vi/ht_cap.png").readBytes(),Imgcodecs.IMREAD_GRAYSCALE);val top=decodeImage(File(root,"templates/vi/ht_dau.png").readBytes(),Imgcodecs.IMREAD_GRAYSCALE)
  val cs=catTheHoiTruongV2(img,cap,top)
  try {
   assertEquals(6,cs.size);assertEquals(6,assertNotNull(xacMinhDanhSachNgan(cs,6,true)).size)
   assertNull(xacMinhDanhSachNgan(cs,null,true));assertNull(xacMinhDanhSachNgan(cs,48,true));assertNull(xacMinhDanhSachNgan(cs,6,false))
   assertNull(xacMinhDanhSachNgan(cs.dropLast(1)+cs.first(),6,true))
   cs.last().q.dayDu=false;assertNull(xacMinhDanhSachNgan(cs,6,true))
  }finally{cs.forEach{it.release()};img.release();cap.release();top.release()}
 }
}
