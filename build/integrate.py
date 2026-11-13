#!/usr/bin/env python3
"""
Build "darkith forge.html" -- one zero-dependency, OS-agnostic file that fuses:

    darkith home forge.html   the shell  (launcher, files, vault, settings, taskkit)
    darkith code studio.html  the engine (embedded, becomes the shell's Codebase Manager)

How it works
------------
The studio is carried verbatim inside a <script type="text/plain" id="studio-src">
block (its closing tag defused so it cannot end the carrier early).  At runtime the
shell materialises that text into an <iframe srcdoc>.  A srcdoc frame is SAME-ORIGIN
even under file://, so the shell drives the studio directly -- no network, no second
file, no server.  Verified: blob: URLs and relative-src iframes are cross-origin under
file:// and were rejected in favour of srcdoc.

The patch layer below rewrites the shell so its Codebase Manager *is* the studio:
  * view-codebase renders the studio frame instead of the textarea card list
  * the card list + version manager stay, but drive the studio's document
  * app HTML is loaded into the studio, audited, edited, and saved back
  * native-only actions (APK build, /sdcard writes) degrade cleanly with no bridge
"""
import sys, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parent.parent
SHELL  = ROOT / "darkith home forge.html"
STUDIO = ROOT / "darkith code studio.html"
OUT    = ROOT / "darkith forge.html"

shell  = SHELL.read_text(encoding="utf-8")
studio = STUDIO.read_text(encoding="utf-8")

# ---------------------------------------------------------------- carrier text
# Instrument the studio so it can signal readiness and broadcast verdicts to the
# host.  Injected just before its final </body>; kept tiny and additive.
STUDIO_HOOK = r"""
<script>
/* DARKITH FORGE · studio-side hook (added by the integrator, harmless standalone) */
(function(){
  "use strict";
  function host(){ try{ return (window.parent && window.parent!==window) ? window.parent : null; }catch(e){ return null; } }
  function post(type,payload){ var p=host(); if(p) try{ p.postMessage({__studio:type,payload:payload},'*') }catch(_){} }
  // ready beacon + the host also polls for our globals
  post('ready',{version:(window.SAVF&&SAVF.version)||null});
  // broadcast every audit verdict
  if(window.SAVF && typeof SAVF.runAudit==='function'){
    var _run=SAVF.runAudit;
    SAVF.runAudit=function(){
      var r=_run.apply(this,arguments);
      try{ post('verdict',{verdict:r&&r.verdict,total:(r&&r.results&&r.results.length)||0}); }catch(_){}
      return r;
    };
  }
})();
</script>
"""
_bi = studio.rfind("</body>")
if _bi < 0:
    sys.exit("studio has no </body>")
studio = studio[:_bi] + STUDIO_HOOK + "\n" + studio[_bi:]
studio_carried = studio.replace("</script", "<\\/script")
assert "</script" not in studio_carried.lower(), "studio still closes the carrier"

# ---------------------------------------------------------------- CSS additions
CSS = r"""
/* ===== DARKITH FORGE · studio panel (Codebase Manager) ===== */
#cb-studio-wrap{position:relative;height:62vh;min-height:360px;border:1px solid var(--line-bright);
  border-radius:18px;overflow:hidden;background:var(--panel-solid);margin:2px 0 12px}
#studio-frame{width:100%;height:100%;border:0;display:block;background:#0e0f12}
.cb-studio-bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:0 0 10px}
.cb-studio-bar .chip{flex:0 0 auto}
.cb-studio-note{font-size:11px;color:var(--dim);font-family:var(--mono);margin:0 0 10px;line-height:1.5}
.cb-studio-note b{color:var(--accent)}
.cb-status{display:inline-flex;align-items:center;gap:6px;font-size:11px;font-family:var(--mono);color:var(--dim)}
.cb-status .dot{width:8px;height:8px;border-radius:50%;background:var(--dim)}
.cb-status.on .dot{background:var(--green)}
.cb-status.err .dot{background:var(--red)}
"""

# ---------------------------------------------------------------- bridge + panel
BRIDGE_JS = r"""
<script type="text/plain" id="studio-src">__STUDIO__</script>
<script>
(function(){
  "use strict";
  var STUDIO_HTML = document.getElementById('studio-src').textContent
                      .split('<\\/script').join('</scr'+'ipt');

  var Bridge = {
    frame:null, ready:false, status:'idle', _waiters:[], _eventFn:null, _poll:null,
    mount:function(container, onReady){
      var self=this;
      if(this.frame && this.frame.parentNode){ this.frame.parentNode.removeChild(this.frame); }
      var f=document.createElement('iframe');
      f.id='studio-frame'; f.title='DARKITH Code Studio';
      // No `sandbox` attribute: the studio is our own trusted, same-origin code and
      // sandboxing it only suppresses autofocus (focus-without-user-activation) while
      // adding nothing -- the studio is already fully offline and self-contained.
      container.appendChild(f);
      this.frame=f; this.ready=false; this.status='mounting';
      this._onReady=onReady||function(){};
      f.addEventListener('load',function(){ self._onLoad(); });
      f.srcdoc=STUDIO_HTML;
      return f;
    },
    _onLoad:function(){
      var self=this; this.ready=false;
      clearInterval(this._poll);
      this._poll=setInterval(function(){
        var w; try{ w=self.frame.contentWindow; }catch(e){ return; }
        if(w && typeof w.dispatchCommand==='function' && typeof w.renderAll==='function' && w.STATE){
          clearInterval(self._poll); self.ready=true; self.status='ready';
          var q=self._waiters; self._waiters=[];
          q.forEach(function(fn){ try{ fn(self) }catch(e){ console.error('bridge waiter',e) } });
          self._onReady(self);
        }
      },60);
      setTimeout(function(){ if(self._poll)clearInterval(self._poll); if(!self.ready){ self.status='timeout'; self._onReady(self); } },7000);
    },
    whenReady:function(fn){ if(this.ready) fn(this); else this._waiters.push(fn); },
    win:function(){ try{ return this.frame && this.frame.contentWindow }catch(e){ return null } },
    doc:function(){ try{ return this.frame && this.frame.contentDocument }catch(e){ return null } },
    getSource:function(){ var w=this.win(); return w&&w.STATE?String(w.STATE.doc||''):''; },
    getLanguage:function(){ var w=this.win(); return w&&w.STATE?w.STATE.language:null; },
    setLanguage:function(lang){
      var w=this.win(); if(!w||!w.STATE) return false;
      try{ w.STATE.language=lang; var s=w.document.getElementById('lang'); if(s) s.value=lang; w.renderAll(); w.updateStatus(); return true; }
      catch(e){ console.error('setLanguage',e); return false; }
    },
    setSource:function(text,lang){
      var w=this.win(); if(!w||!w.STATE) return false;
      try{
        if(lang){ w.STATE.language=lang; var s=w.document.getElementById('lang'); if(s) s.value=lang; }
        w.STATE.doc=String(text==null?'':text);
        if(w.STATE.undo) w.STATE.undo.length=0;
        if(w.STATE.redo) w.STATE.redo.length=0;
        var ed=w.document.getElementById('input'); if(ed) ed.value=w.STATE.doc;
        w.STATE.prevCaret=0;
        if(ed){ try{ ed.setSelectionRange(0,0); }catch(_){} }
        w.renderAll(); w.updateStatus();
        var sc=w.document.getElementById('scroll'); if(sc) sc.scrollTop=0;
        return true;
      }catch(e){ console.error('setSource',e); return false; }
    },
    audit:function(){
      var w=this.win(); if(!w||typeof w.runAudit!=='function') return null;
      try{ w.runAudit(); return (w.STATE&&w.STATE.auditResult)||null; }
      catch(e){ console.error('audit',e); return null; }
    },
    dispatch:function(cmd){ var w=this.win(); if(w&&typeof w.dispatchCommand==='function'){ w.dispatchCommand(cmd); return true } return false; },
    setTheme:function(t){ var w=this.win(); if(w&&typeof w.setTheme==='function'){ w.setTheme(t,false); return true } return false; },
    version:function(){ var w=this.win(); return w&&w.SAVF?w.SAVF.version:null; },
    onEvent:function(fn){ this._eventFn=fn; },
    emit:function(type,payload){ var w=this.win(); if(w) try{ w.postMessage({__host:type,payload:payload},'*') }catch(e){} }
  };
  window.addEventListener('message',function(e){
    var d=e.data; if(!d||typeof d!=='object') return;
    if(d.__darkith==='ready') Bridge.ready=true;
    if(Bridge._eventFn) try{ Bridge._eventFn(d) }catch(_){}
  });
  window.DarkithBridge=Bridge;
})();
</script>
"""

# ---------------------------------------------------------------- patch layer
PATCH_JS = r"""
<script>
/* =====================================================================
   DARKITH FORGE · integration patch
   Makes the embedded studio the shell's Codebase Manager.
   Reversible, self-contained, and safe when no native bridge is present.
   ===================================================================== */
(function(){
  "use strict";
  // NOTE: the shell declares `const App`, a lexical global -- NOT a window property.
  // Reference it by name; fall back to window.App only if it was ever exported.
  var S = (typeof App !== 'undefined' && App) ? App : window.App;
  if(!S){ console.error('forge: shell App namespace missing'); return; }
  var B = window.DarkithBridge;

  // ---- language auto-detection for a minted app --------------------------
  function langFor(app, code){
    var name=String((app&&(app.label||app.id))||'')+'';
    if(/\.(savf\.json|json)$/i.test(name) && /"(claims|facts|rules)"\s*:/.test(String(code||''))) return 'audit';
    if(/\.md$/i.test(name)) return 'md';
    if(/\.json$/i.test(name)) return 'json';
    if(/\.(html?|htm|svg)$/i.test(name)) return 'js';   // html apps highlight as JS-ish; audit stays available
    if(/\.(py|sol|rs|go|cairo|move|cpp|cc|hpp)$/i.test(name)) return 'audit';
    return 'audit';
  }
  S._studioLangFor=langFor;

  // ---- the studio host panel --------------------------------------------
  // The skeleton is built ONCE and kept; only the app list is re-rendered.
  // Re-building the wrap would detach the iframe and wipe the studio's document.
  S.renderStudioPanel=function(){
    var L=document.getElementById('cb-list'); if(!L) return;
    var wrap=document.getElementById('cb-studio-wrap');
    if(!wrap){
      L.innerHTML =
        '<div class="cb-studio-note">'
        + '<b>Code Studio</b> — the audit engine is embedded here. Open an app below to load it, '
        + 'edit with syntax highlighting, run the <b>SAVF-1 audit</b>, then save a new version.'
        + ' <span class="cb-status" id="cb-bridge-status"><span class="dot"></span><span>engine …</span></span>'
        + '</div>'
        + '<div id="cb-studio-wrap"></div>'
        + '<div id="cb-apps"></div>';
      wrap=document.getElementById('cb-studio-wrap');
    }
    if(!B){ wrap.innerHTML='<div style="padding:20px;color:var(--red)">Studio bridge failed to initialise.</div>'; return; }
    if(!B.frame || !B.frame.parentNode){
      B.mount(wrap, function(b){ S._studioReady(b); });
    } else if(B.frame.parentNode!==wrap){
      wrap.appendChild(B.frame);
      if(B.ready) S._studioReady(B);
    }
    S.renderStudioApps();
  };

  S._studioReady=function(b){
    var st=document.getElementById('cb-bridge-status');
    if(st){ st.className='cb-status '+(b.status==='ready'?'on':b.status==='timeout'?'err':''); st.querySelector('span:last-child').textContent = b.status==='ready' ? ('engine v'+(b.version()||'?')+' ready') : 'engine '+b.status; }
    if(b.status==='ready'){
      b.onEvent(function(msg){
        if(msg && msg.__studio==='verdict') S._onStudioVerdict(msg.payload);
      });
    }
  };

  S._onStudioVerdict=function(v){
    if(!v) return;
    var id=this.editingAppId, a=id&&id!=='forge_new'?this.cbApp(id):null;
    this.log('audit '+(a?('“'+a.label+'”'):'forge')+': '+v.verdict+' ('+(v.total||0)+' claims)',
             v.verdict==='PASS'?'ok':v.verdict==='REVIEW'?'sys':'err');
  };

  // ---- app list under the studio (open / versions / delete) --------------
  S.renderStudioApps=function(){
    var host=document.getElementById('cb-apps'); if(!host) return;
    var html='<div class="vsec-t" style="margin-top:6px">Minted apps</div>';
    if(!this.mintedApps.length){
      html+='<div class="cbhint">No apps yet. Press <b>New Forge</b> to write one in the studio, or <b>Import .html</b>.</div>';
    }
    this.mintedApps.forEach(function(a){
      var open=(S.editingAppId===a.id);
      html+='<div class="cbcard glass'+(open?' open':'')+'"><div class="cbh" data-act="open-unified" data-id="'+esc(a.id)+'">'
        + '<div class="cbi">'+(a.icon||SVG.code)+'</div>'
        + '<div style="flex:1;min-width:0"><div class="cbt">'+esc(a.label)+'</div>'
        + '<div class="cbm">'+(a.exported===false?'⚠ not exported':'✅ safe')+' · v'+(a.ver||1)+' · '+(a.size?(a.size+' B'):'—')+'</div></div>'
        + '<button class="chip" data-act="cb-versions" data-id="'+esc(a.id)+'">🕘</button>'
        + '<button class="chip" data-act="cb-export" data-id="'+esc(a.id)+'">⬇</button>'
        + '<button class="cb-trash" data-act="cb-del" data-id="'+esc(a.id)+'" aria-label="Delete">🗑</button>'
        + '<div style="color:var(--dim)">▸</div></div></div>';
    });
    host.innerHTML=html;
  };

  // ---- open an app (or a new forge) in the studio ------------------------
  S.openUnifiedEditor=function(id){
    var self=this;
    var isNew=!id;
    var app=id?this.cbApp(id):null;
    this.editingAppId=id||'forge_new';
    this.view='codebase';
    var f=document.getElementById('view-forge'); if(f) f.classList.remove('active');
    var cb=document.getElementById('view-codebase'); if(cb) cb.classList.add('active');
    this.renderStudioPanel();
    var sub=document.getElementById('cb-sub');
    if(sub) sub.textContent = isNew ? 'New Forge · live sandbox' : ('Editing · '+(app?app.label:id));
    function load(){
      if(isNew){ B.setSource(self.cbBuf['forge_new']||'', 'audit'); return; }
      self.cbCode(app).then(function(code){
        code = code==null ? '' : code;
        self.cbBuf[id]=code;
        B.setSource(code, langFor(app, code));
      }).catch(function(e){ console.error('load app',e); });
    }
    if(B && B.ready) load(); else if(B) B.whenReady(load);
    this.renderTasks();
  };

  // keep the shell's expectations of these two alive
  S.renderUnifiedCodebase=function(){
    if(this.view!=='codebase') return;
    this.renderStudioPanel();
  };
  S.buildUnifiedCard=function(){ return ''; };      // legacy renderer, unused now
  S.handleUnifiedInput=function(id,t){ this.cbBuf[id]=t.value; };

  // ---- saving: pull the studio's current text into the version register --
  function studioSource(){
    if(B && B.ready){ var s=B.getSource(); if(s!=null) return s; }
    return null;
  }

  // Preview, APK and launch read this.cbBuf[id], but the embedded studio owns the
  // live text. Mirror the studio into cbBuf on every edit so those paths see the
  // current source, not a stale copy.
  function syncBuf(){
    if(!(B && B.ready)) return;
    var id=S.editingAppId; if(!id) return;
    var s=B.getSource(); if(s==null) return;
    if(S.cbBuf[id]!==s) S.cbBuf[id]=s;
  }
  S.syncBuf=syncBuf;
  S._studioSource=studioSource;

  // Preview, APK and launch read this.cbBuf[id], but the embedded studio owns the
  // live text. Mirror the studio into cbBuf first, then delegate to the original
  // handlers so every branch (aegis/file/url/html) keeps working.
  var _cbApk=S.cbApk, _cbPreview=S.forgePreviewUnified;
  S.forgePreviewUnified=function(id){
    syncBuf();
    if((this.cbBuf[id]==null||!String(this.cbBuf[id]).trim()) && B && B.ready) this.cbBuf[id]=B.getSource();
    return _cbPreview.call(this,id);
  };
  S.cbApk=function(id){
    syncBuf();
    if((this.cbBuf[id]==null||!String(this.cbBuf[id]).trim()) && B && B.ready) this.cbBuf[id]=B.getSource();
    return _cbApk.call(this,id);
  };

  var _cbSave=S.cbSave;
  S.cbSave=function(id){
    var src=studioSource();
    if(src!=null && id && id!=='forge_new') this.cbBuf[id]=src;
    return _cbSave.call(this,id);
  };

  var _cbCommit=S.cbCommit;
  S.cbCommit=async function(a,code,remark,status){
    if(code==null) code=studioSource();
    return _cbCommit.call(this,a,code,remark,status);
  };

  // ---- New Forge: mint whatever is in the studio -------------------------
  S.forgeSaveNew=async function(){
    var code=studioSource(); if(code==null) code=this.cbBuf['forge_new']||'';
    if(!String(code).trim()) return UI.toast('Source is empty');
    var name=await UI.prompt('Name this app','My Forge App',{ok:'Mint to Desktop'});
    if(name===null||!name.trim()) return;
    var a=await this.cbImport(name.trim(),code,{remark:'Genesis (forged)',exported:false});
    this.cbBuf['forge_new']='';
    this.editingAppId=a.id;
    UI.toast('Minted to Desktop');
    this.renderStudioPanel();
    var sub=document.getElementById('cb-sub'); if(sub) sub.textContent='Editing · '+a.label;
    B && B.ready && B.setSource(code, langFor(a,code));
  };
  S.forgeDiscard=function(){
    this.cbBuf['forge_new']='';
    if(B&&B.ready) B.setSource('', 'audit');
    this.editingAppId=null;
    UI.toast('Forge cleared');
    this.renderStudioPanel();
  };

  // ---- "New Forge" button clears the studio to a blank sandbox -----------
  var _open=S.openUnifiedEditor;
  S.newForge=function(){
    this.cbBuf['forge_new']='';
    this.editingAppId='forge_new';
    this.view='codebase';
    var cb=document.getElementById('view-codebase'); if(cb) cb.classList.add('active');
    this.renderStudioPanel();
    var sub=document.getElementById('cb-sub'); if(sub) sub.textContent='New Forge · live sandbox';
    if(B&&B.ready) B.setSource('', 'audit');
    else if(B) B.whenReady(function(){ B.setSource('','audit'); });
  };

  // ---- guard native-only actions so they degrade gracefully --------------
  S.hasNative=function(m){ return !!(window.darkith && typeof window.darkith[m]==='function'); };
  S.canBuildApk=function(){ return this.hasNative('forgeChimera') && this.hasNative('installApkNative'); };

  // theme sync: keep the studio frame in step with the shell's theme
  function syncTheme(){
    try{
      var s=(S.settings&&S.settings.theme)||'dark';
      var t=(s==='light')?'light':'dark';
      if(B&&B.ready) B.setTheme(t);
    }catch(_){}
  }
  var _applyAll=S.applyAll;
  if(typeof _applyAll==='function'){
    S.applyAll=function(){ var r=_applyAll.apply(this,arguments); syncTheme(); return r; };
  }
  // applyAll is what the shell calls on any theme/settings change; hook `set` too
  var _set=S.set;
  if(typeof _set==='function'){
    S.set=function(k,v){ var r=_set.apply(this,arguments); if(k==='theme') syncTheme(); return r; };
  }
  S.syncTheme=syncTheme;
  // initial sync once the studio is ready
  if(B) B.whenReady(function(){ syncTheme(); });

  // ---- route the Codebase Manager chips to studio-aware handlers ---------
  var _act=S.act;
  S.act=function(a,d,e,el){
    if(a==='open-unified' && !(d&&d.id)) return this.newForge();
    if(a==='cb-new') return this.newForge();
    if(a==='close-unified'){ this.editingAppId=null; this.renderStudioPanel(); return; }
    return _act.call(this,a,d,e,el);
  };
  window.App=S;
})();
</script>
"""

# ---------------------------------------------------------------- assemble
idx = shell.rfind("</body>")
if idx < 0:
    sys.exit("shell has no </body>")

css_block   = "<style>\n" + CSS + "\n</style>\n"
bridge_block = BRIDGE_JS.replace("__STUDIO__", studio_carried)
patch_block  = PATCH_JS

out = shell[:idx] + css_block + bridge_block + patch_block + shell[idx:]
OUT.write_text(out, encoding="utf-8")
print("wrote", OUT.name, len(out), "bytes")
