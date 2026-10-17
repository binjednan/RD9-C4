/* ===== سجل الإنجاز: يعرض داخل الملف نفسه ما أُنجز وما بقي (M.progress يُبنى من docs/RESUME_STATE.md عند كل بناء) ===== */
(function(){
'use strict';
function initProgress(ctx){
  const {M,$,esc}=ctx; const P=M.progress; const box=$('progBox'); if(!box||!P) return;
  const cls=s=>/^تم/.test(s)?'ok':/^(لم|❌)/.test(s)?'no':'part';
  const lab={ok:'منجز',no:'غير منجز',part:'جزئي'};
  const col={ok:'#2e9e6b',no:'#8a8f98',part:'#c58b2a'};
  const fam=Object.entries(P.generated?.by_kit||{}).map(([k,n])=>'<tr><td>'+esc(k)+'</td><td style="text-align:left">'+n.toLocaleString('en')+'</td></tr>').join('');
  box.innerHTML='<div class="pr-note" style="margin:0 0 10px">'+esc(P.note||'')+'</div>'
   +'<div class="hub-tiles" style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px"><div style="flex:1;min-width:120px;padding:8px;border:1px solid #3a4558;border-radius:8px"><small>عناصر النموذج</small><div style="font-size:20px">'+(P.elements||0).toLocaleString('en')+'</div></div>'
   +'<div style="flex:1;min-width:120px;padding:8px;border:1px solid #3a4558;border-radius:8px"><small>مولَّد من العينات</small><div style="font-size:20px">'+(P.generated?.elements||0).toLocaleString('en')+'</div></div>'
   +'<div style="flex:1;min-width:120px;padding:8px;border:1px solid #3a4558;border-radius:8px"><small>تجميعات</small><div style="font-size:20px">'+(P.generated?.assemblies||0).toLocaleString('en')+'</div></div></div>'
   +'<h4 style="margin:6px 0">الإنجاز بالبنود</h4>'+P.items.map(it=>{const c=cls(it.s);return '<div style="border-right:4px solid '+col[c]+';padding:6px 10px;margin:6px 0;background:rgba(255,255,255,.04);border-radius:6px"><b>'+esc(it.k)+' — '+esc(it.t)+'</b> <span style="color:'+col[c]+';font-size:12px">['+lab[c]+']</span><div style="font-size:12.5px;opacity:.88;margin-top:3px;white-space:pre-wrap">'+esc(it.s)+'</div></div>';}).join('')
   +'<h4 style="margin:10px 0 4px">التالي</h4><ul style="margin:0;padding-inline-start:18px">'+(P.next||[]).map(x=>'<li>'+esc(x)+'</li>').join('')+'</ul>'
   +'<details style="margin-top:10px"><summary>العناصر المولَّدة حسب الطقم</summary><table style="width:100%;font-size:12.5px">'+fam+'</table></details>';
}
window.initProgress=initProgress;
})();
