package vn.afkauto.leoai.vision

import java.io.File
import kotlin.test.*
import org.json.JSONObject

class HoSoTaiKhoanTest {
    @Test fun migrationAndIsolationSurviveReopen() {
        val root=kotlin.io.path.createTempDirectory("afk-profile-").toFile()
        try {
            File(root,"khung_tay.json").writeText("{\"Rowan\":1}")
            File(root,"tuong_cua_toi.json").writeText("[{\"ten\":\"Rowan\",\"mat\":\"tuong_cua_toi/1.png\"}]")
            File(root,"tuong_cua_toi").mkdirs();File(root,"tuong_cua_toi/1.png").writeBytes(byteArrayOf(1,2,3))
            val store=HoSoTaiKhoan(root);val first=store.current()
            assertEquals(1,JSONObject(File(first.dir,"khung_tay.json").readText()).getInt("Rowan"))
            assertContentEquals(byteArrayOf(1,2,3),File(first.dir,"tuong_cua_toi/1.png").readBytes())
            assertTrue(File(root,"khung_tay.json").exists()) // migration retains the original backup
            val next=store.create("Tài khoản khác");assertFalse(File(next.dir,"khung_tay.json").exists())
            File(next.dir,"khung_tay.json").writeText("{\"Rowan\":0}")
            store.select(first.id);assertEquals(1,JSONObject(File(store.current().dir,"khung_tay.json").readText()).getInt("Rowan"))
            val reopened=HoSoTaiKhoan(root);assertEquals(first.id,reopened.current().id)
            reopened.select(next.id);assertEquals(0,JSONObject(File(reopened.current().dir,"khung_tay.json").readText()).getInt("Rowan"))
            reopened.rename(next.id,"Nhỏ");assertEquals("Nhỏ",reopened.current().ten)
            assertFails { reopened.select("../cu") };assertFails { reopened.create("  ") };assertFails { reopened.create("Nhỏ") }
            assertEquals(2,reopened.list().size)
        } finally {root.deleteRecursively()}
    }
    @Test fun corruptedIndexFailsWithoutReimportingOldData() {
        val root=kotlin.io.path.createTempDirectory("afk-profile-").toFile()
        try {
            val store=HoSoTaiKhoan(root);store.create("Hai")
            File(root,"ho_so/index.json").writeText("bad")
            assertFails { store.current() }
            assertEquals("bad",File(root,"ho_so/index.json").readText())
        } finally {root.deleteRecursively()}
    }
}
