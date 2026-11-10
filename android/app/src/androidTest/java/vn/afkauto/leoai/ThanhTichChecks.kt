package vn.afkauto.leoai

import android.app.Instrumentation
import android.os.SystemClock
import android.view.InputDevice
import android.view.MotionEvent
import org.json.JSONObject
import org.opencv.android.Utils
import org.opencv.core.Mat
import org.opencv.imgproc.Imgproc
import java.io.File
import vn.afkauto.leoai.vision.*

/** Thử trực tiếp trên bảng Thành Tích đang mở ở đội 3; không bắt đầu trận đánh. */
object ThanhTichChecks {
    fun run(test: Instrumentation): JSONObject {
        val ctx = test.targetContext
        val nd = NhanDien(BoMau.load(
            { ctx.assets.open(it).use { f -> f.readBytes() } },
            { ctx.assets.list(it)!!.toList() }))
        val doc = DocThanhTich(nd)
        val folder = File(ctx.getExternalFilesDir(null), "thanh-tich-check").apply { mkdirs() }
        fun capture(name: String): Pair<Mat, KetQua> {
            val bmp = checkNotNull(test.uiAutomation.takeScreenshot())
            File(folder, "$name.png").outputStream().use { bmp.compress(android.graphics.Bitmap.CompressFormat.PNG, 100, it) }
            val rgba = Mat(); val bgr = Mat()
            Utils.bitmapToMat(bmp, rgba); Imgproc.cvtColor(rgba, bgr, Imgproc.COLOR_RGBA2BGR)
            rgba.release(); bmp.recycle()
            return bgr to nd.nhanDien(bgr)
        }
        fun tap(p: Pair<Int, Int>) {
            val now = SystemClock.uptimeMillis()
            for ((action, at) in listOf(MotionEvent.ACTION_DOWN to now, MotionEvent.ACTION_UP to now + 80)) {
                val e = MotionEvent.obtain(now, at, action, p.first.toFloat(), p.second.toFloat(), 0)
                e.source = InputDevice.SOURCE_TOUCHSCREEN
                try { check(test.uiAutomation.injectInputEvent(e, true)) } finally { e.recycle() }
            }
            SystemClock.sleep(1500)
        }
        var current = capture("start-third")
        val third = try {
            check(current.second.manHinh == "thanh_tich") { current.second.toString() }
            checkNotNull(doc.doc(current.first)).also { check(it.lucChien == "13073M" && !it.thuCong) }
        } finally { current.first.release() }
        var fourth: DoiThanhTich? = null
        var fourthMatch = 0.0
        var thirdMatch = 0.0
        for ((name, arrow, power) in listOf(
            Triple("right-fourth", "tt_mui_ten_phai", "14022M"),
            Triple("right-fifth", "tt_mui_ten_phai", "11609M"),
            Triple("left-fourth", "tt_mui_ten_trai", "14022M"),
            Triple("left-third", "tt_mui_ten_trai", "13073M"))) {
            tap(current.second.nut.getValue(arrow))
            current = capture(name)
            try {
                check(current.second.manHinh == "thanh_tich") { "$name: ${current.second}" }
                val d = checkNotNull(doc.doc(current.first))
                check(d.lucChien == power) { "$name: $d" }
                if (name == "right-fourth") fourth = d
                if (name == "left-fourth") {
                    fourthMatch = giongTen(fourth!!.chuKy, d.chuKy)
                    check(cungDoi(fourth!!, d)) { "Đội 4: $fourthMatch" }
                }
                if (name == "left-third") {
                    thirdMatch = giongTen(third.chuKy, d.chuKy)
                    check(cungDoi(third, d)) { "Đội 3: $thirdMatch" }
                }
            } finally { current.first.release() }
        }
        tap(current.second.nut.getValue("tt_sao_chep"))
        current = capture("copied")
        try {
            check(current.second.manHinh == "doi_hinh") { "Sau chép: ${current.second}" }
            return JSONObject().put("success", true).put("chosen_power", third.lucChien)
                .put("third_name_match", thirdMatch).put("fourth_name_match", fourthMatch)
                .put("copied", true).put("team_power_m", doc.lucDoi(current.first))
        } finally { current.first.release() }
    }
}
