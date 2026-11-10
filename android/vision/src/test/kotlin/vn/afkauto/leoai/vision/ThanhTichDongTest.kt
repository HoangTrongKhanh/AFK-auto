package vn.afkauto.leoai.vision

import java.io.File
import nu.pattern.OpenCV
import org.opencv.core.Size
import org.opencv.imgproc.Imgproc
import org.opencv.core.Mat
import kotlin.test.*

class ThanhTichDongTest {
    @Test fun doiKhongDoiKhiVienDaiDienChuyenDong() {
        OpenCV.loadLocally()
        val root = File(System.getProperty("afkauto.root"))
        val nd = NhanDien(BoMau.load({ File(root, "templates/$it").readBytes() },
            { File(root, "templates/$it").list()!!.toList() }))
        val doc = DocThanhTich(nd)
        for (width in listOf(1600, 1080, 800)) {
            val ds = listOf("tt-dau", "tt-phai-3", "tt-trai-3", "tt-phai-4", "tt-trai-4").associateWith { name ->
                val source = decodeImage(File(root, "samples/thanh_tich_dong/$name.png").readBytes())
                val img = Mat()
                Imgproc.resize(source, img, Size(width.toDouble(), width * 1.6), 0.0, 0.0, Imgproc.INTER_AREA)
                try {
                    val k = nd.nhanDien(img)
                    assertEquals("thanh_tich", k.manHinh, "$name/$width")
                    assertTrue("tt_nam_dam" in k.nut)
                    assertNotNull(doc.doc(img))
                } finally { source.release(); img.release() }
            }
            for ((i, luc) in listOf(3 to "13073M", 4 to "14022M")) {
                val a = ds.getValue("tt-phai-$i"); val b = ds.getValue("tt-trai-$i")
                assertEquals(luc, a.lucChien)
                assertTrue(cungDoi(a, b), "$width/$i: ${giongTen(a.chuKy, b.chuKy)}")
            }
            assertFalse(cungDoi(ds.getValue("tt-phai-3"), ds.getValue("tt-phai-4")))
            assertFalse(ds.getValue("tt-phai-3").thuCong)
            assertTrue(ds.getValue("tt-phai-4").thuCong)
        }
    }
}
