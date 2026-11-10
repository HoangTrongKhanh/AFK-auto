package vn.afkauto.leoai.vision

import org.opencv.core.*
import org.opencv.imgproc.Imgproc
import kotlin.math.*

data class TheCan(val anh:Mat,val legacy:Mat,val y:Double,val q:ChatLuongThe) {fun release(){anh.release();legacy.release()}}
fun catTheHoiTruongV2(img:Mat,cap:Mat,dau:Mat):List<TheCan> {
    data class Hit(val score:Double,val x:Int,val y:Int,val scale:Double)
    val ref=scale(img,REF_W.toDouble()/img.cols());val g=gray(ref);val small=scale(g,.5);val ht=scale(dau,.5);val rr=Mat();Imgproc.matchTemplate(small,ht,rr,Imgproc.TM_CCOEFF_NORMED);val topPage=Core.minMaxLoc(rr).maxVal>=.8;small.release();ht.release();rr.release()
    val bottom=ref.rows()-(if(topPage)260 else 490);val y0=260;val y1=bottom+20;val hits=mutableListOf<Hit>()
    try {
        val area=roi(g,100,y0,1490,y1)
        for(s in listOf(.95,1.0,1.15,1.2,1.25)) {
            val t=scale(cap,s,Imgproc.INTER_LINEAR);val r=Mat();Imgproc.matchTemplate(area,t,r,Imgproc.TM_CCOEFF_NORMED)
            for(i in 0 until 80){val m=Core.minMaxLoc(r);if(m.maxVal<.65)break;val x=m.maxLoc.x.toInt();val y=m.maxLoc.y.toInt();hits.add(Hit(m.maxVal,x+100,y+y0,s));val z=r.submat(max(0,y-50),min(r.rows(),y+51),max(0,x-50),min(r.cols(),x+51));z.setTo(Scalar(0.0));z.release()};r.release();t.release()
        };area.release()
        val kept=mutableListOf<Hit>();for(h in hits.sortedWith(compareByDescending<Hit>{it.score}.thenByDescending{it.x}.thenByDescending{it.y}.thenByDescending{it.scale}))if(kept.none{abs(h.x-it.x)<65 && abs(h.y-it.y)<35})kept.add(h)
        val rows=mutableListOf<MutableList<Hit>>();for(h in kept.sortedBy{it.y}){val row=rows.firstOrNull{abs(median(it.map{v->v.y.toDouble()})-h.y)<22};if(row==null)rows.add(mutableListOf(h))else row.add(h)}
        val large=mutableListOf<Pair<Double,Double>>();var grid=mutableListOf<Pair<Double,Double>>()
        for(row in rows){if(row.size<2 && row[0].score<.83)continue;val big=median(row.map{it.scale})>1.08;val size=if(big)1.15 else 1.0;val top=median(row.map{it.y.toDouble()})-234*size;(if(big)large else grid).add(top to row.sumOf{it.score})}
        val gridTop=large.maxOfOrNull{it.first+290*1.15+150}?:y0.toDouble()
        if(grid.isEmpty() && large.isNotEmpty()) {
            val ya=max(0,gridTop.toInt());val yb=min(ref.rows(),bottom)
            if(yb-ya>=240){val r=roi(ref,100,ya,1490,yb);val mask=maskVien(r);r.release();val (lab,stats)=components(mask);lab.release();mask.release();val groups=mutableListOf<MutableList<Pair<Double,Int>>>()
                for(v in stats){val (x,y,w,h)=v;if(w !in 150..265 || h !in 240..355)continue;val cx=100+x+w/2.0;val col=pyRound((cx-250)/218.5);if(col !in 0..5 || abs(cx-(250+218.5*col))>35)continue;val rough=ya+y+h/2.0-145;val group=groups.firstOrNull{abs(median(it.map{a->a.first})-rough)<25};if(group==null)groups.add(mutableListOf(rough to col))else group.add(rough to col)}
                grid=groups.filter{it.map{v->v.second}.toSet().size>=2}.map{median(it.map{v->v.first}) to it.map{v->v.second}.toSet().size.toDouble()}.toMutableList()
            }
        }
        val positions=large.map{it.first to true}.toMutableList()
        if(grid.isNotEmpty()){val anchor=grid.maxBy{it.second}.first;for(j in -12..12){val t=anchor+j*308;if(t>=gridTop && t+290<=bottom)positions.add(t to false)}}
        val out=mutableListOf<TheCan>()
        for((top,big) in positions.sortedWith(compareBy<Pair<Double,Boolean>>{it.first}.thenBy{it.second})) {
            val size=if(big)1.15 else 1.0;if(top<y0 || top+290*size>bottom)continue;val centers=if(big)(0..4).map{249+268.5*it}else(0..5).map{250+218.5*it};val k=130/(218*size);val sm=scale(ref,k)
            for(cx in centers){if(!topPage && cx+100*size>1340 && top+290*size>ref.rows()-650)continue;val x=(cx*k).toInt();val y=(top*k).toInt()-15;if(y<0 || y+205>sm.rows() || x-65<0 || x+65>sm.cols())continue
                val c=roi(sm,x-65,y,x+65,y+205);val face=roi(c,21,55,109,140);val fg=gray(face);face.release();val ok=sd(c)>=18 && sd(fg)>=12;fg.release();if(!ok){c.release();continue}
                val (aligned,q)=canKhung(ref,cx,top,size,if(big)y0.toDouble() else gridTop,bottom.toDouble());q.tamX=cx;q.tamY=top+145*size;out.add(TheCan(aligned?:c.clone(),c.clone(),q.tamY,q));c.release()
            };sm.release()
        }
        supplementSingle(ref,cap,out)
        return out
    } finally {g.release();ref.release()}
}
private fun supplementSingle(ref:Mat,cap:Mat,out:MutableList<TheCan>) {
    if(out.size!=5 || out.withIndex().any{abs(it.value.q.tamX-(249+268.5*it.index))>8})return
    val top=(out.maxOf{it.q.tamY+145*1.15}+150).toInt();val bottom=ref.rows()-490;if(bottom-top<260)return;val candidates=mutableListOf<TheCan>()
    for(col in 0..5){val cx=250+218.5*col;val xa=pyRound(cx-109);val xb=pyRound(cx+109);val r=roi(ref,xa,top,xb,bottom);val mask=maskVien(r);val original=bytes(mask);val pad=Mat();Core.copyMakeBorder(mask,pad,32,32,32,32,Core.BORDER_CONSTANT,Scalar(0.0));val closed=Mat();val kernel=Mat.ones(31,31,CvType.CV_8U);Imgproc.morphologyEx(pad,closed,Imgproc.MORPH_CLOSE,kernel);pad.release();kernel.release();val joined=roi(closed,32,32,closed.cols()-32,closed.rows()-32);val (lab,stats)=components(joined);lab.release();joined.release();closed.release();mask.release();val width=r.cols()
        fun at(x:Int,y:Int)=original[y*width+x].toInt()!=0
        for(v in stats){val (x,y,w,h)=v;if(w !in 160..210 || h !in 240..365 || x<=1 || x+w>=width-1 || y<15 || y+h>r.rows()-15)continue;val side=max(4,pyRound(w*.06));val ys=pyRound(h*.25);val ye=pyRound(h*.85);val sup=listOf(0,w-side).map{xx->(ys until ye).count{yy->(xx until xx+side).any{at(x+it,y+yy)}}.toDouble()/(ye-ys)}
            val corners=listOf(0,w-36).map{xx->(0 until 24).sumOf{yy->(xx until xx+36).count{at(x+it,y+yy)}}.toDouble()/(24*36)};val floor=(h-24 until h).sumOf{yy->(0 until w).count{at(x+it,y+yy)}}.toDouble()/(24*w)
            if(sup.min()<.2 || corners.min()<.1 || floor<.25)continue
            val cut=roi(r,x,y+(h*.65).toInt(),x+w,y+h);val gg=gray(cut);cut.release();var score=-1.0;var capY=0
            for(s in listOf(.95,1.0)){val tpl=scale(cap,s,Imgproc.INTER_LINEAR);val res=Mat();Imgproc.matchTemplate(gg,tpl,res,Imgproc.TM_CCOEFF_NORMED);val m=Core.minMaxLoc(res);if(m.maxVal>score){score=m.maxVal;capY=y+(h*.65).toInt()+m.maxLoc.y.toInt()+top};res.release();tpl.release()};gg.release();if(score<.55)continue
            val box=Bien(xa+x,top+y,xa+x+w,top+y+h);val (aligned,chuan)=canvas(ref,box,r);val rowTop=capY-234;val k=130.0/218;val sm=scale(ref,k);val xx=(cx*k).toInt();val yy=(rowTop*k).toInt()-15
            if(yy<0 || yy+205>sm.rows() || xx-65<0 || xx+65>sm.cols()){sm.release();aligned.release();continue}
            val old=roi(sm,xx-65,yy,xx+65,yy+205).clone();sm.release();val ff=roi(old,21,55,109,140);val fg=gray(ff);ff.release();val ok=sd(fg)>=12;fg.release();if(!ok){old.release();aligned.release();continue}
            val q=ChatLuongThe(true,"bien_day_du_mot_the_tach_manh",box,chuan,cx,rowTop+145.0,sup,true,true)
            candidates.add(TheCan(aligned,old,q.tamY,q))
        };r.release()
    }
    if(candidates.size==1)out.add(candidates.single())else candidates.forEach{it.release()}
}
