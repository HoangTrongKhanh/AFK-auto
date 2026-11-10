package vn.afkauto.leoai

import android.app.Instrumentation
import android.os.Bundle
import android.view.accessibility.AccessibilityNodeInfo
import android.view.View
import android.view.ViewGroup
import android.widget.CheckBox
import android.widget.Button
import org.json.JSONObject
import org.opencv.core.MatOfByte
import org.opencv.imgcodecs.Imgcodecs
import java.io.File
import java.util.UUID
import vn.afkauto.leoai.vision.decodeImage

/** Exercises the real listeners in the separately installed validation application. */
object SampleUiChecks {
    fun run(test: Instrumentation, activity: MainActivity): JSONObject {
        val ctx=test.targetContext;check(ctx.packageName.endsWith(".validation"))
        val profile=KhungTuong.hoSo(ctx).create("Kiểm tra nút ${UUID.randomUUID().toString().take(8)}")
        val store=KhungTuong.kho(ctx);val before=store.current().samples.getJSONArray("face_ids").length()
        fun face(seed:Int):ByteArray {
            val im=decodeImage(ctx.assets.open("vi/tuong/Rolan.png").use{it.readBytes()});val view=im.submat(0,48,0,48);val crop=view.clone();view.release();im.release();crop.put(0,0,byteArrayOf(seed.toByte(),2,3));val buffer=MatOfByte()
            return try{check(Imgcodecs.imencode(".png",crop,buffer));buffer.toArray()}finally{crop.release();buffer.release()}
        }
        fun ui(block:()->Unit) { var error:Throwable?=null;test.runOnMainSync {try{block()}catch(e:Throwable){error=e}};error?.let{throw it} }
        fun render() {ui {test.callActivityOnPause(activity);test.callActivityOnResume(activity);activity.findViewById<View>(R.id.tabHeroes).performClick()};test.waitForIdleSync()}
        fun views(v:View):List<View> = listOf(v)+if(v is ViewGroup)(0 until v.childCount).flatMap{views(v.getChildAt(it))}else emptyList()
        val png=face(71);val id=store.stage("Rolan",png,"c".repeat(64));store.review(id,true)
        val card=File(profile.dir,"xac_nhan/Rolan.png");card.parentFile!!.mkdirs();card.writeBytes(png)
        File(profile.dir,"xac_nhan.json").writeText(JSONObject().put("Rolan",JSONObject().put("anh","xac_nhan/Rolan.png").put("khung",1).put("mau_id",id)).toString())
        render()
        ui {val box=activity.findViewById<View>(R.id.khungTuong);val checked=views(box).filterIsInstance<CheckBox>().single{it.isChecked};checked.performClick()}
        check(store.status(id)=="rejected");check(store.current().samples.getJSONArray("face_ids").length()==before)
        check(!JSONObject(File(profile.dir,"xac_nhan.json").readText()).has("Rolan"))
        val id2=store.stage("Rolan",face(72),"d".repeat(64));store.review(id2,true);render()
        ui {val button=views(activity.findViewById(R.id.khungTuong)).filterIsInstance<Button>().single{it.text.toString()=="Thu hồi mẫu"};check(button.performClick())}
        check(store.status(id2)=="rejected");check(store.current().samples.getJSONArray("face_ids").length()==before)
        ui {views(activity.findViewById(R.id.accountProfiles)).filterIsInstance<Button>().single{it.text.toString()=="Thêm tài khoản"}.performClick()}
        test.waitForIdleSync()
        fun nodes(n:AccessibilityNodeInfo):List<AccessibilityNodeInfo> = listOf(n)+(0 until n.childCount).mapNotNull{n.getChild(it)}.flatMap{nodes(it)}
        val window=requireNotNull(test.uiAutomation.rootInActiveWindow)
        val input=nodes(window).single{it.className?.toString()=="android.widget.EditText"}
        val name="UI account ${UUID.randomUUID().toString().take(8)}"
        check(input.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT,Bundle().apply{putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE,name)}))
        check(window.findAccessibilityNodeInfosByText("Lưu").single().performAction(AccessibilityNodeInfo.ACTION_CLICK))
        test.waitForIdleSync();check(KhungTuong.hoSo(ctx).current().ten==name);check(!activity.isFinishing)
        ui {check(views(activity.findViewById(R.id.accountProfiles)).filterIsInstance<android.widget.Spinner>().single().selectedItem.toString()==name)}
        return JSONObject().put("uncheck_approved_sample",true).put("withdraw_button",true).put("create_profile_dialog",true)
    }
}
