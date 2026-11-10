package vn.afkauto.leoai.vision

import org.json.*
import org.opencv.core.Mat
import org.opencv.imgcodecs.Imgcodecs
import kotlin.math.abs

/** Cùng một phép đối chiếu chạy trên JVM và ngay trên Android. Không học từ ảnh kiểm tra. */
class DoiChieuV2(private val read:(String)->ByteArray,private val assets:(String)->ByteArray) {
    fun run(expected:JSONObject):JSONObject {
        org.opencv.core.Core.setNumThreads(2);val started=System.nanoTime();val bundle=BoNhanDang.load {assets("vision-v2/$it")}
        check(bundle.version==expected.getString("version"));check(sha256(assets("vision-v2/manifest.json"))==expected.getString("bundle_sha256"))
        val tv=ThuVienTuong.load(assets);bundle.apply(tv,assets);val engine=requireNotNull(tv.engineV2)
        val cap=decodeImage(assets("vi/ht_cap.png"),Imgcodecs.IMREAD_GRAYSCALE);val top=requireNotNull(tv.mocDau)
        var nc=0;var np=0;var nh=0;var maxStar=0.0;var maxFeature=0.0
        fun image(path:String,hash:String?=null):Mat {val b=read(path);if(hash!=null)check(sha256(b)==hash){"Ảnh thay đổi: $path"};return decodeImage(b)}
        fun quality(o:JSONObject):ChatLuongThe {
            fun box(key:String)=o.optJSONArray(key)?.let{Bien(it.getInt(0),it.getInt(1),it.getInt(2),it.getInt(3))}
            return ChatLuongThe(o.optBoolean("day_du"),o.getString("ly_do"),box("bien"),box("bien_chuan"),o.optDouble("tam_x",0.0),o.optDouble("tam_y",0.0),emptyList(),o.optBoolean("vung_sao_day_du"),o.optBoolean("vien_day_du"))
        }
        fun checkQuality(q:ChatLuongThe,w:JSONObject,tag:String) {
            check(q.dayDu==w.optBoolean("day_du")){"$tag: chất lượng ${q.json()} != $w"}
            check(q.bien?.json()?.toString()==w.optJSONArray("bien")?.toString()){"$tag: biên ${q.json()} != $w"}
            check(q.lyDo==w.getString("ly_do")){"$tag: lý do ${q.lyDo} != ${w.getString("ly_do")}"}
            if(q.dayDu)check(q.chuan?.json()?.toString()==w.getJSONArray("bien_chuan").toString()){"$tag: canvas"}
        }
        fun checkResult(g:KetQuaKhung,w:JSONObject,tag:String) {
            val k=if(w.isNull("khung"))KHUNG_CHUA_RO else w.getInt("khung")
            check(g.khung==k && g.lyDo==w.getString("ly_do")){"$tag: khung ${g.json()} != $w"}
            if(g.sao!=null){val delta=abs(g.sao.diem-w.getDouble("diem_sao"));maxStar=maxOf(maxStar,delta);check(delta<.003){"$tag: điểm sao $delta"}}
        }
        try {
            val cards=expected.getJSONArray("cards")
            for(i in 0 until cards.length()) {val o=cards.getJSONObject(i);val tag=o.getString("image");val m=image(tag,o.getString("sha256"));try{val q=quality(o.getJSONObject("quality"));checkResult(engine.danhGia(m,q),o.getJSONObject("result"),tag);val f=engine.dacTrung(m,q);val w=o.getJSONArray("features");val delta=f.indices.maxOf{abs(f[it]-w.getDouble(it))};maxFeature=maxOf(maxFeature,delta);check(delta<.00002){"$tag: đặc trưng $delta"};nc++}finally{m.release()}}
            println("V2: $nc thẻ đạt");val pages=expected.getJSONArray("pages")
            for(i in 0 until pages.length()){val o=pages.getJSONObject(i);val tag=o.getString("image");val m=image(tag,o.getString("sha256"));val cs=try{catTheHoiTruongV2(m,cap,top)}finally{m.release()};try{val w=o.getJSONArray("cards");check(cs.size==w.length()){"$tag: số thẻ ${cs.size} != ${w.length()}"};for(j in cs.indices){val want=w.getJSONObject(j);checkQuality(cs[j].q,want.getJSONObject("quality"),"$tag#$j");checkResult(engine.danhGia(cs[j].anh,cs[j].q),want.getJSONObject("result"),"$tag#$j")};np++}finally{cs.forEach{it.release()}}}
            println("V2: $np ảnh đạt");val groups=expected.getJSONArray("groups")
            for(i in 0 until groups.length()){val o=groups.getJSONObject(i);val doc=DocDanhSach(tv,cap);val ps=o.getJSONArray("pages");for(j in 0 until ps.length()){val m=image(ps.getString(j));try{doc.them(m)}finally{m.release()}};val ds=doc.xong();try{val ws=o.getJSONArray("heroes");check(ds.size==ws.length()){"Nhóm ${o.getString("name")}: ${ds.size} != ${ws.length()}"};for(j in ds.indices){val w=ws.getJSONObject(j);val x=ds[j];checkQuality(requireNotNull(x.chatLuong),w.getJSONObject("quality"),"${o.getString("name")}#$j");val k=if(w.isNull("frame"))KHUNG_CHUA_RO else w.getInt("frame");check(x.ten==w.optString("name").takeUnless{w.isNull("name")} && x.goiY==w.optString("suggestion").takeUnless{w.isNull("suggestion")} && x.khung==k && x.lyDoTen==w.getString("name_reason")){"Nhóm ${o.getString("name")}#$j: ${x.ten}/${x.goiY}/${x.khung}/${x.lyDoTen} != $w"};nh++};println("V2: nhóm ${o.getString("name")} ${ds.size} thẻ đạt")}finally{ds.forEach{it.anh.release();it.mat.release()};doc.lastGridFaces.forEach{it.release()}}}
        }finally{cap.release();tv.release()}
        return JSONObject().put("version",bundle.version).put("cards",nc).put("pages",np).put("heroes",nh).put("max_star_delta",maxStar).put("max_feature_delta",maxFeature).put("elapsed_ms",(System.nanoTime()-started)/1_000_000)
    }
}
