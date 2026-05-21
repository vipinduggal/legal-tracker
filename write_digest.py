import os

home = os.path.expanduser("~")
path = os.path.join(home, "legal-tracker", "src", "digest.html")

html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Weekly Outreach Digest</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&family=DM+Mono&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{--navy:#0F2240;--blue:#1E56A0;--bl:#EBF2FC;--teal:#0A7C6E;--tl:#E6F5F2;--amber:#B45309;--al:#FEF3C7;--red:#991B1B;--rl:#FEE2E2;--green:#166534;--gl:#DCFCE7;--g0:#F9FAFB;--g1:#F3F4F6;--g2:#E5E7EB;--g4:#9CA3AF;--g5:#6B7280;--g6:#4B5563;--g7:#374151;--g9:#111827;--f:"DM Sans",sans-serif;--r:10px;--rl:14px}
body{font-family:var(--f);font-size:14px;color:var(--g9);background:var(--g0);min-height:100vh}
.tb{height:52px;background:var(--navy);display:flex;align-items:center;padding:0 20px;gap:16px;position:sticky;top:0;z-index:10}
.tb a{color:rgba(255,255,255,.7);text-decoration:none;font-size:13px}
.tb a:hover{color:#fff}
.tb-t{font-size:15px;font-weight:600;color:#fff}
.tb-sub{font-size:12px;color:rgba(255,255,255,.45);margin-left:4px}
.tb-r{margin-left:auto}
.wrap{max-width:820px;margin:0 auto;padding:28px 20px 60px}
.sbox{background:linear-gradient(135deg,#EBF2FC,#F0F7FF);border:1px solid #BFCFE8;border-radius:var(--rl);padding:18px 20px;margin-bottom:24px}
.slbl{font-size:11px;font-weight:700;color:var(--blue);text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px}
.stxt{font-size:14px;color:var(--navy);line-height:1.7}
.sec{font-size:12px;font-weight:700;color:var(--g4);text-transform:uppercase;letter-spacing:.06em;margin:28px 0 12px;display:flex;align-items:center;gap:8px}
.sec::after{content:"";flex:1;height:1px;background:var(--g2)}
.pc{background:#fff;border:1px solid var(--g2);border-radius:var(--rl);padding:18px 20px;margin-bottom:12px}
.ph{display:flex;align-items:center;gap:10px;margin-bottom:10px}
.rk{width:26px;height:26px;border-radius:50%;background:var(--navy);color:#fff;font-size:11px;font-weight:700;display:flex;align-items:center;justify-content:center;flex-shrink:0}
.an{font-size:15px;font-weight:600;color:var(--g9)}
.ub{font-size:10px;font-weight:600;padding:2px 8px;border-radius:20px}
.uc{background:var(--rl);color:var(--red)}
.uh{background:var(--al);color:var(--amber)}
.um{background:var(--bl);color:var(--blue)}
.tb2{background:var(--g0);border-left:3px solid var(--blue);padding:10px 14px;border-radius:0 6px 6px 0;margin-bottom:12px;font-size:13px;color:var(--g7);line-height:1.6}
.cc{display:inline-flex;align-items:center;gap:5px;background:var(--bl);color:var(--blue);font-size:12px;font-weight:500;padding:4px 10px;border-radius:20px;margin-bottom:10px}
.tp{font-size:13px;font-style:italic;color:var(--g6);background:var(--g0);border:1px solid var(--g2);border-radius:var(--r);padding:10px 13px;margin-bottom:12px;line-height:1.6}
.eb{background:#FAFAFA;border:1px solid var(--g2);border-radius:var(--r);overflow:hidden}
.eh{padding:10px 14px;border-bottom:1px solid var(--g2);display:flex;align-items:center;justify-content:space-between}
.el{font-size:11px;font-weight:600;color:var(--g5);text-transform:uppercase;letter-spacing:.05em}
.cb{font-size:11px;padding:3px 10px;border-radius:5px;border:1px solid var(--g2);background:#fff;cursor:pointer;color:var(--g6);font-family:var(--f)}
.cb:hover{background:var(--bl);border-color:var(--blue);color:var(--blue)}
.cb.ok{background:var(--gl);border-color:var(--green);color:var(--green)}
.es{padding:10px 14px;font-size:13px;font-weight:600;color:var(--g9);border-bottom:1px solid var(--g2)}
.ebody{padding:14px;font-size:13px;color:var(--g7);line-height:1.75;white-space:pre-wrap}
.lb{margin-top:10px;background:var(--bl);border-radius:var(--r);padding:12px 14px}
.ll{font-size:11px;font-weight:600;color:var(--blue);text-transform:uppercase;letter-spacing:.05em;margin-bottom:5px;display:flex;align-items:center;justify-content:space-between}
.lt{font-size:13px;color:var(--navy);line-height:1.6}
.ac{background:#fff;border:1px solid var(--rl);border-left:4px solid var(--red);border-radius:var(--rl);padding:14px 16px;margin-bottom:10px}
.at{font-size:11px;font-weight:700;color:var(--red);text-transform:uppercase;letter-spacing:.06em;margin-bottom:4px}
.aa{font-size:14px;font-weight:600;color:var(--g9);margin-bottom:4px}
.as{font-size:13px;color:var(--g6);line-height:1.5;margin-bottom:6px}
.aac{font-size:13px;color:var(--amber);font-weight:500}
.wc{background:#fff;border:1px solid #A7D7D0;border-left:4px solid var(--teal);border-radius:var(--rl);padding:14px 16px;margin-bottom:10px}
.wp{font-size:14px;font-weight:600;color:var(--g9);margin-bottom:2px}
.wa{font-size:12px;color:var(--teal);font-weight:500;margin-bottom:4px}
.wch{font-size:13px;color:var(--g6);margin-bottom:4px}
.ww{font-size:12px;color:var(--amber);font-weight:500}
.ql{background:#fff;border:1px solid var(--g2);border-radius:var(--rl);overflow:hidden}
.qi{padding:11px 16px;border-bottom:1px solid var(--g1);display:flex;align-items:flex-start;gap:10px;font-size:13px}
.qi:last-child{border-bottom:none}
.qn{font-weight:600;color:var(--g9);flex-shrink:0;min-width:160px}
.qac{color:var(--g6);line-height:1.5}
.gb{display:block;width:100%;padding:12px;border:1.5px dashed var(--g2);border-radius:var(--rl);background:transparent;cursor:pointer;font-size:13px;color:var(--g5);font-family:var(--f);margin-top:16px}
.gb:hover{border-color:var(--blue);color:var(--blue);background:var(--bl)}
.nd{text-align:center;padding:60px 20px}
.nd h2{font-size:18px;font-weight:600;color:var(--g7);margin-bottom:8px}
.nd p{font-size:13px;color:var(--g5);margin-bottom:16px;line-height:1.6}
</style>
</head>
<body>
<div class="tb">
  <a href="/">&#8592; Dashboard</a>
  <span class="tb-t">Weekly Outreach Digest</span>
  <span class="tb-sub" id="tbd"></span>
  <div class="tb-r">
    <button class="cb" onclick="genNew()" id="gnb" style="padding:5px 12px;font-size:12px">&#8635; Generate new</button>
  </div>
</div>
<div class="wrap" id="wrap"><p style="text-align:center;padding:40px;color:#9CA3AF">Loading digest...</p></div>
<script>
function esc(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\n/g,'<br>');}

async function load(){
  try{
    var r=await fetch('/api/digest');
    var d=await r.json();
    if(d.message){nodig();return;}
    show(d);
  }catch(e){document.getElementById('wrap').innerHTML='<p style="text-align:center;padding:40px;color:#991B1B">Error: '+esc(e.message)+'</p>';}
}

function show(d){
  var w=document.getElementById('wrap');
  if(d.savedAt)document.getElementById('tbd').textContent='Generated '+new Date(d.savedAt).toLocaleDateString('en-US',{weekday:'long',month:'long',day:'numeric',year:'numeric'});
  var h='';
  if(d.week_summary)h+='<div class="sbox"><div class="slbl">This week</div><div class="stxt">'+esc(d.week_summary)+'</div></div>';
  var pp=d.priority_accounts||[];
  if(pp.length){
    h+='<div class="sec">Priority outreach &mdash; top '+pp.length+' accounts</div>';
    pp.forEach(function(p,i){
      var uc=p.urgency==='Critical'?'uc':p.urgency==='High'?'uh':'um';
      h+='<div class="pc"><div class="ph"><div class="rk">'+p.priority_rank+'</div><div class="an">'+esc(p.account_name)+'</div>';
      if(p.urgency)h+='<span class="ub '+uc+'">'+p.urgency+'</span>';
      h+='</div>';
      if(p.trigger)h+='<div class="tb2">'+esc(p.trigger)+'</div>';
      if(p.contact){h+='<div><span class="cc">'+esc(p.contact.name)+' &middot; '+esc(p.contact.title)+'</span>';if(p.contact.why_them)h+='<span style="font-size:12px;color:var(--g5);margin-left:8px">'+esc(p.contact.why_them)+'</span>';h+='</div>';}
      if(p.talking_point)h+='<div class="tp">&ldquo;'+esc(p.talking_point)+'&rdquo;</div>';
      if(p.email){
        h+='<div class="eb"><div class="eh"><span class="el">Suggested email</span><button class="cb" id="cb'+i+'" onclick="cpEmail('+i+')">Copy email</button></div>';
        h+='<div class="es">Subject: '+esc(p.email.subject)+'</div>';
        h+='<div class="ebody" id="eb'+i+'">'+esc(p.email.body)+'</div></div>';
      }
      if(p.linkedin_message){h+='<div class="lb"><div class="ll"><span>LinkedIn InMail</span><button class="cb" id="lc'+i+'" onclick="cpLi('+i+')">Copy</button></div><div class="lt" id="li'+i+'">'+esc(p.linkedin_message)+'</div></div>';}
      h+='</div>';
    });
  }
  var ff=d.new_filings_alert||[];
  if(ff.length){h+='<div class="sec">New filings alert</div>';ff.forEach(function(f){h+='<div class="ac"><div class="at">'+esc(f.filing_type)+'</div><div class="aa">'+esc(f.account_name)+'</div><div class="as">'+esc(f.summary)+'</div>'+(f.suggested_action?'<div class="aac">'+esc(f.suggested_action)+'</div>':'')+'</div>';});}
  var pw=d.personnel_watch||[];
  if(pw.length){h+='<div class="sec">Personnel watch</div>';pw.forEach(function(p){h+='<div class="wc"><div class="wp">'+esc(p.person)+'</div><div class="wa">'+esc(p.account_name)+'</div><div class="wch">'+esc(p.change)+'</div>'+(p.window?'<div class="ww">Window: '+esc(p.window)+'</div>':'')+'</div>';});}
  var qt=d.quick_touches||[];
  if(qt.length){h+='<div class="sec">Quick touches</div><div class="ql">';qt.forEach(function(q){h+='<div class="qi"><span class="qn">'+esc(q.account_name)+'</span><span class="qac">'+esc(q.action)+'</span></div>';});h+='</div>';}
  h+='<button class="gb" onclick="genNew()">&#8635; Generate new digest based on latest research</button>';
  w.innerHTML=h;
  window._digest=d;
}

function nodig(){document.getElementById('wrap').innerHTML='<div class="nd"><h2>No digest yet</h2><p>Your first weekly digest arrives Monday at 8 AM.<br>Or click Generate new above to create one now.</p></div>';}

function cpEmail(i){
  var eb=document.getElementById('eb'+i);
  var es=eb?eb.previousElementSibling:null;
  var subj=es?es.textContent.replace('Subject: ',''):'';
  var txt=(subj?'Subject: '+subj+'\\n\\n':'')+eb.textContent;
  navigator.clipboard.writeText(txt).then(function(){var b=document.getElementById('cb'+i);if(b){b.textContent='Copied!';b.classList.add('ok');setTimeout(function(){b.textContent='Copy email';b.classList.remove('ok');},2000);}});
}

function cpLi(i){
  var el=document.getElementById('li'+i);
  if(!el)return;
  navigator.clipboard.writeText(el.textContent).then(function(){var b=document.getElementById('lc'+i);if(b){b.textContent='Copied!';b.classList.add('ok');setTimeout(function(){b.textContent='Copy';b.classList.remove('ok');},2000);}});
}

async function genNew(){
  var btn=document.getElementById('gnb');
  if(btn){btn.textContent='Generating...';btn.disabled=true;}
  try{
    var r=await fetch('/api/digest/generate',{method:'POST'});
    var d=await r.json();
    if(d.queued)alert('Digest generation started. Takes 1-2 minutes. Refresh the page after.');
  }catch(e){alert('Run in terminal: npm run digest:weekly');}
  if(btn){btn.textContent='\\u21bb Generate new';btn.disabled=false;}
}

load();
</script>
</body>
</html>"""

with open(path, 'w') as f:
    f.write(html)

print("Done — digest.html written to " + path)
print("File size: " + str(os.path.getsize(path)) + " bytes")
print("")
print("Restart: pkill -f 'node src/index.js' && npm start")
print("Then open: http://localhost:3000/digest")
