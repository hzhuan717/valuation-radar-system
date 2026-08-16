function cssVar(name, fb){ try{ const v = getComputedStyle(document.documentElement).getPropertyValue(name); return (v && v.trim()) ? v.trim() : fb; }catch(e){ return fb; } }
/* ============ K线图引擎 v2（Canvas 分层渲染 + SVG 交互覆盖层） ============
   设计规则：
   1. 所有渲染颜色经 getComputedStyle 读取 CSS 变量（--candle-up/--candle-dn/--hair/--sub2…），
      暗色主题 html[data-theme="dark"] 自动适配；
   2. 物理像素 = CSS像素 × DPR，1px 线条统一对齐 0.5px 网格保证锐利；
   3. 分层渲染：网格(虚线) → 估值色带 → 成交量副图 → 蜡烛 → 均线 → 呼吸点；
   4. 布局：右侧 Y 轴 56px 毛玻璃面板（CSS axis-panel）、底部 24px 时间轴、
      成交量副图约占 24%（与主图共享 X 轴，1px --hair 分割线）；
   5. 动效：切换周期/股票时蜡烛自底部生长 + 均线从左向右裁剪（--dur-layout 320ms）；
   6. 交互：SVG 十字光标（主题蓝 .35 + 4px 白边圆点）、Tooltip 溢出自动翻转、
      滚轮指针居中缩放（最少 20 根）、拖拽平移 + 200ms 惯性、键盘 ←/→ 移动光标 ↑/↓ 聚焦MA。 */

const KCOL = { up: cssVar('--candle-up', '#d94a47'), dn: cssVar('--candle-dn', '#178a59') };

function hexA(hex, a){
  const h = String(hex).replace('#', '');
  if(h.length !== 6) return hex;
  const n = parseInt(h, 16);
  return 'rgba(' + ((n >> 16) & 255) + ',' + ((n >> 8) & 255) + ',' + (n & 255) + ',' + a + ')';
}

const MADASH = {5:[], 10:[], 20:[], 60:[6,5], 120:[6,5], 250:[2,5]};

function niceStep(range, ticks){
  if(!(range > 0) || !isFinite(range)) return 1;
  const raw = range / (ticks || 5);
  const mag = Math.pow(10, Math.floor(Math.log(raw) / Math.LN10));
  const norm = raw / mag;
  const s = norm <= 1 ? 1 : norm <= 2 ? 2 : norm <= 2.5 ? 2.5 : norm <= 5 ? 5 : 10;
  return s * mag;
}

function packLbl(items, gap){
  items.sort((a,b) => a.y - b.y);
  let last = -Infinity;
  for(const it of items){
    it.yy = Math.max(it.y, last + gap);
    last = it.yy;
  }
  return items;
}

/* 双列防重叠：右列（MA/斐波/锚标签）与左列（S/R 徽章）互检，
   冲突时右标签向下让位 6px，6 次仍冲突则隐藏（_hidden） */
function packLblMutual(left, right, gapL, gapR, crossGap){
  packLbl(left, gapL);
  packLbl(right, gapR);
  for(const it of right){
    let guard = 0;
    while(guard++ < 6){
      const clash = left.filter(l => Math.abs(l.yy - it.yy) < crossGap);
      if(!clash.length) break;
      it.yy = Math.max(it.y, clash[0].yy + crossGap + 2);
    }
    if(guard >= 6 && left.some(l => Math.abs(l.yy - it.yy) < crossGap)) it._hidden = true;
  }
  return right;
}

class ValuationChartEngine {
  constructor(containerId, stockData){
    this.wrap = document.getElementById(containerId);
    this.cv = document.getElementById('klineCv');
    this.sv = document.getElementById('klineSvg');
    this.tip = document.getElementById('chartTip');
    this.ctx = this.cv ? this.cv.getContext('2d') : null;
    this.st = null; this.rows = []; this.N = 0;
    this.maC = {}; this.volC = {}; this.crosses = [];
    this.slot = 6; this.viewStart = 0; this.rangeN = 250;
    this.maVis = {5:true, 10:true, 20:true, 60:true, 120:true, 250:true};
    this.bandVis = true;
    this.hollow = (() => { try{ return localStorage.getItem('radar_hollow') === '1'; }catch(e){ return false; } })();
    this.pinned = false; this.pinIdx = -1; this._pinY = null; this._tipIdx = -1;
    this._drag = null; this._raf = 0; this._anim = null; this._resT = null; this._ro = null;
    this._ch = null; this._animateSR = false; this._custom = false;
    this._dataTok = 0;
    this._yShift = 0; this._yAnim = null; this._bandAnim = null; this._dashShift = 0;
    this._growAnim = null;
    this._loopOn = false; this._hoverOn = false; this._hoverT = null; this._flashT = null; this._hl = [];
    this._isMobile = window.matchMedia ? window.matchMedia('(max-width:699px)').matches : false;
    if(this.tip) this.tip.classList.toggle('mobile', this._isMobile);
    this._theme();
    this._bind();
    if(stockData) this.setData(stockData);
  }

  /* ---- 主题取色：Canvas/SVG 全部颜色从 getComputedStyle 动态读取 ---- */
  _theme(){
    const V = (name, fb) => cssVar(name, fb);
    this.C = {
      up:   V('--candle-up',  '#d94a47'),
      dn:   V('--candle-dn',  '#178a59'),
      ink:  V('--ink',        '#1d1d1f'),
      sub:  V('--sub',        '#6e6e73'),
      sub2: V('--sub2',       '#48484a'),
      hair: V('--hair',       'rgba(0,0,0,.08)'),
      hair2:V('--hair2',      'rgba(0,0,0,.14)'),
      bg2:  V('--bg2',        '#ffffff'),
      blue: V('--blue',       '#0071e3'),
      green:V('--green',      '#34c759'),
      red:  V('--red',        '#ff3b30'),
      gold: V('--gold',       '#a0742f'),
      violet:V('--violet',    '#5e5ce6'),
    };
    this._maCol = {5:this.C.blue, 10:this.C.violet, 20:this.C.gold, 60:this.C.sub, 120:this.C.violet, 250:this.C.green};
  }

  /* ---- 事件绑定 ---- */
  _bind(){
    const sv = this.sv;
    sv.addEventListener('pointermove', e => this._onMove(e));
    sv.addEventListener('pointerdown', e => this._onDown(e));
    sv.addEventListener('pointerup', e => this._onUp(e));
    sv.addEventListener('pointercancel', () => { this._drag = null; });
    sv.addEventListener('pointerleave', () => {
      this._hoverReset();
      if(!this.pinned){ this._hideCross(); this.tip.classList.remove('show'); }
    });
    sv.addEventListener('wheel', e => { e.preventDefault(); this._zoom(e); }, {passive:false});
    sv.addEventListener('dblclick', e => { e.preventDefault(); this.setRange(250); });
    /* 键盘导航：←/→ 逐根移动十字光标，↑/↓ 在 MA 芯片间移动焦点 */
    document.addEventListener('keydown', e => this._onKey(e));
    /* 尺寸监听：ResizeObserver 防抖 100ms（替代 window.resize） */
    if(window.ResizeObserver){
      this._ro = new ResizeObserver(() => {
        clearTimeout(this._resT);
        this._resT = setTimeout(() => { this.resize(); }, 100);
      });
      this._ro.observe(this.wrap);
    }
  }

  _onKey(e){
    if(VIEW !== 'stock' || this.N < 2) return;
    const ae = document.activeElement;
    if(ae && (ae.tagName === 'INPUT' || ae.tagName === 'TEXTAREA' || ae.tagName === 'SELECT')) return;
    if(e.key === 'ArrowLeft' || e.key === 'ArrowRight'){
      e.preventDefault();
      const cur = (this.pinned && this.pinIdx >= 0) ? this.pinIdx : this.N - 1;
      const ni = Math.max(0, Math.min(this.N - 1, cur + (e.key === 'ArrowRight' ? 1 : -1)));
      this.pinned = true; this.pinIdx = ni; this._tipIdx = ni;
      const bars = this.barsPerView();
      if(ni < this.viewStart) this.viewStart = ni;
      else if(ni > this.viewStart + bars - 1) this.viewStart = Math.max(0, Math.min(this.N - bars, ni - Math.floor(bars / 2)));
      this._clampView();
      this._renderTip(ni);
      this._updateCross(ni, this.yOf(this.rows[ni].c));
      this._positionTip(this.xOf(ni), this.yOf(this.rows[ni].c));
      this.tip.classList.add('show');
      this._scheduleDraw();
    } else if(e.key === 'ArrowUp' || e.key === 'ArrowDown'){
      const chips = Array.from(document.querySelectorAll('.ma-chip[data-ma]:not(.off)'));
      if(!chips.length) return;
      const idx = chips.indexOf(document.activeElement);
      const nxt = chips[(idx < 0 ? 0 : (idx + (e.key === 'ArrowDown' ? 1 : chips.length - 1)) % chips.length)];
      e.preventDefault(); nxt.focus();
    }
  }

  /* ---- 布局与比例 ---- */
  layout(){
    const w = Math.max(260, this.wrap.clientWidth || 800);
    const h = Math.max(180, this.wrap.clientHeight || 540);
    this.W = w; this.H = h;
    this.dpr = Math.min(2, window.devicePixelRatio || 1);
    this.AX = 56;                      /* 右侧 Y 轴毛玻璃面板宽 */
    this.GUT = w < 560 ? 64 : 84;      /* 右缘标签槽：锚/MA/斐波标签专用，K线不进入 */
    this.TL = 12; this.BX = 24;        /* 顶部留白 12，底部时间轴 24 */
    this.px0 = 8; this.px1 = w - this.AX - this.GUT;
    this.axX = w - this.AX;
    this.hideVol = w < 600;            /* 窄屏隐藏成交量副图，释放垂直空间 */
    this.priceH = (h - this.TL - this.BX) * (this.hideVol ? 1 : 0.76);
    this.volTop = this.TL + this.priceH + 6;
    this.volBot = this.hideVol ? this.volTop : h - this.BX;
    this.volH = this.volBot - this.volTop;
    const wpx = Math.round(w * this.dpr), hpx = Math.round(h * this.dpr);
    if(this.cv.width !== wpx || this.cv.height !== hpx){ this.cv.width = wpx; this.cv.height = hpx; }
    this._theme();
  }

  barsPerView(){ return (this.px1 - this.px0) / Math.max(this.slot, 0.05); }
  xOf(i){ return this.px0 + (i - this.viewStart + 0.5) * this.slot; }

  _clampView(){
    const bars = this.barsPerView();
    if(bars >= this.N){
      this.slot = (this.px1 - this.px0) / Math.max(1, this.N);
      this.viewStart = 0;
    } else {
      this.viewStart = Math.max(0, Math.min(this.N - bars, this.viewStart));
    }
  }

  _range(){
    const bars = this.barsPerView();
    const i0 = Math.max(0, Math.floor(this.viewStart - 1));
    const i1 = Math.min(this.N - 1, Math.ceil(this.viewStart + bars + 1));
    let lo = Infinity, hi = -Infinity;
    for(let i = i0; i <= i1; i++){
      const r = this.rows[i];
      if(r.l < lo) lo = r.l;
      if(r.h > hi) hi = r.h;
    }
    if(!isFinite(lo)){ const c = this.rows[this.N-1].c; lo = c - 1; hi = c + 1; }
    const st = this.st;
    const vlow = +st.v_low, vmid = +st.v_mid, vhigh = +st.v_high;
    const hasV = this.bandVis && isFinite(vlow) && isFinite(vmid) && isFinite(vhigh) && vlow > 0 && vlow < vmid && vmid < vhigh;
    if(hasV){ lo = Math.min(lo, vlow); hi = Math.max(hi, vhigh); }
    (st.support||[]).concat(st.resistance||[]).forEach(sr => {
      const v = +sr.level;
      if(isFinite(v) && v > 0){ lo = Math.min(lo, v); hi = Math.max(hi, v); }
    });
    const pad = (hi - lo) * 0.08;
    if(this._yAnim){
      const e = Math.min(1, (performance.now() - this._yAnim.t0) / this._yAnim.dur);
      const p = 1 - Math.pow(1 - e, 3);
      this._yShift = this._yAnim.from + (this._yAnim.to - this._yAnim.from) * p;
      if(e >= 1) this._yAnim = null;
    }
    let ys = this._yShift || 0;
    this._pr = { pmin: lo - pad + ys, pmax: hi + pad + ys, hasV, vlow, vmid, vhigh, i0, i1, bars };
    return this._pr;
  }

  yOf(p){ const pr = this._pr; return this.TL + this.priceH - (p - pr.pmin) / (pr.pmax - pr.pmin) * this.priceH; }
  _volMax(){
    const vs = [];
    for(let i = this._pr.i0; i <= this._pr.i1; i++) vs.push(this.rows[i].v);
    vs.sort((a,b) => a - b);
    let vmax = vs.length ? vs[Math.min(vs.length - 1, Math.floor(vs.length * 0.98))] : 1;
    if(!isFinite(vmax) || vmax <= 0) vmax = 1;
    return vmax;
  }

  _growE(){
    if(!this._growAnim) return 1;
    const e = Math.min(1, (performance.now() - this._growAnim.t0) / this._growAnim.dur);
    if(e >= 1){ this._growAnim = null; return 1; }
    return 1 - Math.pow(1 - e, 3);   /* easeOutCubic，与 --ease-spring 一致 */
  }

  /* ---- Canvas 分层绘制 ---- */
  _drawGrid(ctx){
    const pr = this._pr, y = p => this.yOf(p);
    ctx.save();
    ctx.strokeStyle = this.C.hair;
    ctx.lineWidth = 1;
    ctx.setLineDash([2, 4]);   /* 虚线网格 */
    ctx.beginPath();
    ctx.rect(this.px0, this.TL, this.px1 - this.px0, this.priceH);
    ctx.clip();
    const step = niceStep(pr.pmax - pr.pmin, 5);
    for(let p = Math.ceil(pr.pmin / step) * step; p <= pr.pmax + 1e-9; p += step){
      const yy = Math.round(y(p)) + 0.5;
      ctx.beginPath(); ctx.moveTo(this.px0, yy); ctx.lineTo(this.px1, yy); ctx.stroke();
    }
    const dstep = Math.max(1, Math.ceil(60 / Math.max(this.slot, 0.5)));
    for(let i = pr.i0; i <= pr.i1; i += dstep){
      const x = Math.round(this.xOf(i)) + 0.5;
      ctx.beginPath(); ctx.moveTo(x, this.TL); ctx.lineTo(x, this.TL + this.priceH); ctx.stroke();
    }
    ctx.setLineDash([]);
    ctx.restore();
    /* 成交量副图分隔线（1px --hair） */
    if(!this.hideVol && this.volH > 8){
      ctx.strokeStyle = this.C.hair;
      ctx.lineWidth = 1;
      const yy = Math.round(this.volTop) + 0.5;
      ctx.beginPath(); ctx.moveTo(this.px0, yy); ctx.lineTo(this.px1, yy); ctx.stroke();
    }
  }

  _drawBands(ctx){
    const pr = this._pr;
    if(!pr.hasV) return;
    const yLow = this.yOf(pr.vlow), yMid = this.yOf(pr.vmid), yHigh = this.yOf(pr.vhigh);
    const w = this.px1 - this.px0;
    let hot = null;
    const hovered = this._tipIdx != null && this._tipIdx >= 0 && this._tipIdx < this.N ? this.rows[this._tipIdx] : null;
    if(hovered){
      const c = hovered.c;
      hot = c < pr.vlow ? 'low' : (c <= pr.vhigh ? 'mid' : 'high');
    }
    const A = {
      low:  hot === 'low' ? 0.12 : (hot ? 0.02 : 0.08),
      mid:  hot === 'mid' ? 0.12 : (hot ? 0.02 : 0.06),
      high: hot === 'high' ? 0.12 : (hot ? 0.02 : 0.06),
    };
    ctx.save();
    ctx.beginPath();
    ctx.rect(this.px0, this.TL, w, Math.max(1, this.priceH));
    ctx.clip();
    ctx.fillStyle = hexA(this.C.green, A.low);
    ctx.fillRect(this.px0, yLow, w, this.TL + this.priceH - yLow);
    ctx.fillStyle = hexA(this.C.blue, A.mid);
    ctx.fillRect(this.px0, yMid, w, yLow - yMid);
    ctx.fillStyle = hexA(this.C.red, A.high);
    ctx.fillRect(this.px0, this.TL, w, yMid - this.TL);
    ctx.setLineDash([6, 4]);
    ctx.lineWidth = 1;
    ctx.lineDashOffset = -this._dashShift || 0;
    ctx.strokeStyle = hot === 'low' ? hexA(this.C.green, .5) : hexA(this.C.green, .28);
    ctx.beginPath(); ctx.moveTo(this.px0, Math.round(yLow) + 0.5); ctx.lineTo(this.px1, Math.round(yLow) + 0.5); ctx.stroke();
    ctx.strokeStyle = hot === 'mid' ? hexA(this.C.blue, .5) : hexA(this.C.blue, .28);
    ctx.beginPath(); ctx.moveTo(this.px0, Math.round(yMid) + 0.5); ctx.lineTo(this.px1, Math.round(yMid) + 0.5); ctx.stroke();
    ctx.strokeStyle = hot === 'high' ? hexA(this.C.red, .5) : hexA(this.C.red, .28);
    ctx.beginPath(); ctx.moveTo(this.px0, Math.round(yHigh) + 0.5); ctx.lineTo(this.px1, Math.round(yHigh) + 0.5); ctx.stroke();
    ctx.setLineDash([]);
    ctx.restore();
  }

  _drawBreath(ctx){
    if(this.N < 2 || !this._pr) return;
    const x = this.xOf(this.N - 1);
    const yy = this.yOf(this.rows[this.N - 1].c);
    if(!isFinite(yy) || x < this.px0 - 4 || x > this.px1 + 4) return;
    const col = this._zoneColOf(this.rows[this.N - 1].c);
    const b = this.pinned ? 0.5 : (0.5 + 0.5 * Math.sin(Date.now() / 400));
    ctx.fillStyle = col;
    ctx.globalAlpha = 0.12 * b;
    ctx.beginPath(); ctx.arc(x, yy, 10, 0, Math.PI * 2); ctx.fill();
    ctx.globalAlpha = 0.25 * b;
    ctx.beginPath(); ctx.arc(x, yy, 6, 0, Math.PI * 2); ctx.fill();
    ctx.globalAlpha = 0.8;
    ctx.beginPath(); ctx.arc(x, yy, 3, 0, Math.PI * 2); ctx.fill();
    ctx.globalAlpha = 1;
  }

  _zoneColOf(c){
    const pr = this._pr;
    if(!pr || !pr.hasV) return this.C.blue;
    if(c < pr.vlow) return this.C.green;
    if(c < pr.vhigh) return this.C.blue;
    return this.C.red;
  }

  _zoneCard(c, pr){
    if(!pr.hasV) return null;
    const mob = this._isMobile;
    let name, col, dist;
    if(c < pr.vlow){ name = '深度低估'; col = this.C.green; dist = '低于保守线'; }
    else if(c < pr.vmid){ name = '低估区'; col = this.C.green; dist = '距基准线 ' + ((pr.vmid / c - 1) * 100).toFixed(1) + '%'; }
    else if(c <= pr.vhigh){ name = '合理区'; col = this.C.blue; dist = '距乐观线 ' + ((pr.vhigh / c - 1) * 100).toFixed(1) + '%'; }
    else { name = '高估区'; col = this.C.red; dist = '高于乐观线'; }
    const w = mob ? 110 : 140, h = mob ? 34 : 52;
    const x0 = this.px0 + 8;
    const svg = y0 => {
      let t = '<rect x="' + x0 + '" y="' + y0.toFixed(1) + '" width="' + w + '" height="' + h + '" rx="6" fill="' + this.C.bg2 + '" fill-opacity=".96" stroke="' + this.C.hair + '"/>';
      if(mob){
        t += '<text x="' + (x0 + 8) + '" y="' + (y0 + 14).toFixed(1) + '" font-size="10" font-weight="700" fill="' + col + '" font-family="SF Mono,monospace">¥' + fmt2(c) + '</text>'
           + '<text x="' + (x0 + 8) + '" y="' + (y0 + 27).toFixed(1) + '" font-size="10" fill="' + col + '" font-family="SF Mono,monospace">' + name + '</text>';
      } else {
        t += '<text x="' + (x0 + 8) + '" y="' + (y0 + 17).toFixed(1) + '" font-size="11" font-weight="700" fill="' + col + '" font-family="SF Mono,monospace">现价 ¥' + fmt2(c) + '</text>'
           + '<text x="' + (x0 + 8) + '" y="' + (y0 + 33).toFixed(1) + '" font-size="11" fill="' + col + '" font-family="SF Mono,monospace">处于 · ' + name + '</text>'
           + '<text x="' + (x0 + 8) + '" y="' + (y0 + 47).toFixed(1) + '" font-size="11" fill="' + this.C.sub + '" font-family="SF Mono,monospace">' + dist + '</text>';
      }
      return t;
    };
    return { w, h, svg };
  }

  _redrawCanvas(){
    this.layout();
    const ctx = this.ctx;
    ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    ctx.clearRect(0, 0, this.W, this.H);
    if(this.N < 2) return;
    this._dashShift = (this._dashShift + 0.5) % 10;
    this._range();
    this._drawGrid(ctx);
    this._drawBands(ctx);
    this._drawVolume(ctx);
    this._drawCandles(ctx);
    this._drawMAs(ctx);
    this._drawBreath(ctx);
  }

  _drawCandles(ctx){
    const y = p => this.yOf(p);
    const e = this._growE();
    const bodyW = Math.max(1, Math.min(12, this.slot * 0.72));
    const thin = this.slot < 2.2;
    if(this.slot < 1.2){ this._drawDense(ctx, y); return; }
    ctx.save();
    if(e < 1){
      ctx.translate(0, this.TL + this.priceH);
      ctx.scale(1, e);
      ctx.translate(0, -(this.TL + this.priceH));
    }
    for(let i = this._pr.i0; i <= this._pr.i1; i++){
      const r = this.rows[i];
      const cx = this.xOf(i);
      if(cx < this.px0 - 4 || cx > this.px1 + 4) continue;
      const up = r.c >= r.o;
      const col = up ? this.C.up : this.C.dn;
      if(!thin){
        ctx.strokeStyle = col;
        ctx.lineWidth = 1;
        const wx = Math.round(cx) + 0.5;
        ctx.beginPath();
        ctx.moveTo(wx, y(r.h));
        ctx.lineTo(wx, y(r.l));
        ctx.stroke();
      }
      const yo = y(Math.max(r.o, r.c));
      const bh = Math.max(1, Math.abs(y(r.o) - y(r.c)));
      const bw = Math.max(1, bodyW);
      if(this.hollow && up && !thin){
        ctx.strokeStyle = col;
        ctx.lineWidth = 1.2;
        ctx.strokeRect(cx - bw / 2, yo, bw, bh);
        ctx.fillStyle = hexA(this.C.up, .14);
        ctx.fillRect(cx - bw / 2, yo, bw, bh);
      } else {
        ctx.fillStyle = col;
        ctx.fillRect(cx - bw / 2, yo, bw, bh);
      }
    }
    ctx.restore();
  }

  _drawDense(ctx, y){
    ctx.save();
    ctx.beginPath();
    ctx.rect(this.px0, this.TL, this.px1 - this.px0, this.priceH);
    ctx.clip();
    ctx.fillStyle = hexA(this.C.blue, .08);
    ctx.beginPath();
    let started = false;
    for(let i = this._pr.i0; i <= this._pr.i1; i++){
      const cx = this.xOf(i), cy = y(this.rows[i].c);
      if(!started){ ctx.moveTo(cx, cy); started = true; }
      else ctx.lineTo(cx, cy);
    }
    ctx.lineTo(this.xOf(this._pr.i1), this.TL + this.priceH);
    ctx.lineTo(this.xOf(this._pr.i0), this.TL + this.priceH);
    ctx.closePath();
    ctx.fill();
    ctx.strokeStyle = this.C.blue;
    ctx.lineWidth = 1;
    ctx.beginPath();
    started = false;
    for(let i = this._pr.i0; i <= this._pr.i1; i++){
      const cx = this.xOf(i), cy = y(this.rows[i].c);
      if(!started){ ctx.moveTo(cx, cy); started = true; }
      else ctx.lineTo(cx, cy);
    }
    ctx.stroke();
    ctx.restore();
  }

  _drawVolume(ctx){
    if(this.hideVol) return;
    const vmax = this._volMax();
    const bodyW = Math.max(1.5, Math.min(12, this.slot * 0.7));
    for(let i = this._pr.i0; i <= this._pr.i1; i++){
      const r = this.rows[i];
      const cx = this.xOf(i);
      if(cx < this.px0 - 4 || cx > this.px1 + 4) continue;
      const up = r.c >= r.o;
      const col = up ? this.C.up : this.C.dn;
      const capped = r.v > vmax;
      const vh = Math.max(1.5, capped ? (this.volH - 8) : (r.v / vmax * (this.volH - 8)));
      ctx.globalAlpha = 0.32;
      ctx.fillStyle = col;
      ctx.fillRect(cx - bodyW / 2, this.volBot - vh, bodyW, vh);
      ctx.globalAlpha = 1;
      if(capped){ ctx.fillStyle = col; ctx.fillRect(cx - 1, this.volTop, 2, 2); }
    }
    [5,10].forEach(w => {
      const a = this.volC[w];
      if(!a) return;
      ctx.strokeStyle = w === 5 ? hexA(this.C.sub, .55) : hexA(this.C.sub, .32);
      ctx.lineWidth = 1;
      ctx.beginPath();
      let started = false;
      for(let i = this._pr.i0; i <= this._pr.i1; i++){
        const v = a[i];
        if(!isFinite(v)) continue;
        const cx = this.xOf(i);
        const cy = this.volBot - Math.max(1, v / vmax * (this.volH - 8));
        if(!started){ ctx.moveTo(cx, cy); started = true; }
        else ctx.lineTo(cx, cy);
      }
      ctx.stroke();
    });
  }

  _drawMAs(ctx){
    const y = p => this.yOf(p);
    const e = this._growE();
    ctx.save();
    if(e < 1){
      const cw = this.px0 + (this.px1 - this.px0) * e;
      ctx.beginPath();
      ctx.rect(this.px0, this.TL, Math.max(1, cw - this.px0), this.priceH);
      ctx.clip();
    }
    [5,10,20,60,120,250].forEach(w => {
      if(!this.maVis[w]) return;
      const a = this.maC[w];
      if(!a) return;
      ctx.strokeStyle = this._maCol[w];
      ctx.lineWidth = w <= 20 ? 1.5 : 1.2;
      ctx.setLineDash(MADASH[w]);
      ctx.beginPath();
      let started = false;
      for(let i = this._pr.i0; i <= this._pr.i1; i++){
        const m = a[i];
        if(!isFinite(m)) continue;
        const cx = this.xOf(i);
        const cy = y(m);
        if(!isFinite(cy)) continue;
        if(!started){ ctx.moveTo(cx, cy); started = true; }
        else ctx.lineTo(cx, cy);
      }
      ctx.stroke();
      ctx.setLineDash([]);
    });
    ctx.restore();
  }/* ---- SVG 覆盖层（锚线/S-R/斐波/标签/轴/徽章/十字光标） ---- */
  overlay(){
    const pr = this._pr;
    const s = [];
    const W = this.W, H = this.H, y = p => this.yOf(p);
    const small = W < 480;
    if(this.N < 2){
      s.push('<text x="' + (W/2).toFixed(1) + '" y="' + (H/2).toFixed(1) + '" text-anchor="middle" font-size="13" fill="' + this.C.sub + '">暂无足够K线数据</text>');
      this.sv.innerHTML = s.join('');
      this._ch = null;
      return;
    }
    s.push('<style>.srl{animation:srmarch .8s ease-out}@keyframes srmarch{to{stroke-dashoffset:-28}}.srtouch{animation:srflash .9s ease-out 1}@keyframes srflash{0%{stroke-width:2.6;opacity:1}100%{stroke-width:1;opacity:.55}}.sr-pulse{animation:srpulse 1.2s ease-in-out infinite}@keyframes srpulse{0%,100%{opacity:1}50%{opacity:.55}}.srlbl{animation:srlabel .4s ease-out}@keyframes srlabel{from{transform:translateX(-12px);opacity:0}to{transform:none;opacity:1}}</style>');
    const st = this.st;
    const priceB = this.TL + this.priceH;
    const lastClose = this.rows[this.N-1].c;
    const sup = (st.support||[]).filter(x => isFinite(+x.level) && (x.method||'').indexOf('估值锚') !== 0);
    const res = (st.resistance||[]).filter(x => isFinite(+x.level) && (x.method||'').indexOf('估值锚') !== 0);
    const edgeTop = [], edgeBot = [];
    const srLbls = [];
    const hl = [];
    const SR_STYLE = {
      A: {sw: 2.2, up: this.C.green, dn: this.C.red, op: .90, dash: ''},
      B: {sw: 1.6, up: hexA(this.C.green, .9), dn: hexA(this.C.red, .9), op: .75, dash: '8 4'},
      C: {sw: 1.2, up: hexA(this.C.green, .7), dn: hexA(this.C.red, .7), op: .55, dash: '4 4'},
    };
    const mo = this._isMobile ? 0.3 : 0;
    let srSeq = 0;

    const srRows = [];
    sup.forEach((sr, idx) => srRows.push({sr, isSup: true, idx}));
    res.forEach((sr, idx) => srRows.push({sr, isSup: false, idx}));
    const evOrder = {A: 0, B: 1, C: 2};
    const inViewRows = srRows.filter(rr => {
      const vv = +rr.sr.level;
      const yy = y(vv);
      return isFinite(yy) && yy >= this.TL - 6 && yy <= priceB + 6;
    });
    inViewRows.sort((a, b) => evOrder[a.sr.level_ev] - evOrder[b.sr.level_ev] || +a.sr.level - +b.sr.level);

    inViewRows.forEach(rr => {
      const sr = rr.sr, isSup = rr.isSup;
      const vv = +sr.level;
      const yy = y(vv);
      const ev = sr.level_ev === 'A' ? 'A' : (sr.level_ev === 'C' ? 'C' : 'B');
      const stl = SR_STYLE[ev];
      const touch = Math.abs(lastClose / vv - 1) <= 0.008;
      const lw = Math.max(0.9, stl.sw - mo + (touch ? 1 : 0));
      const col = touch ? (isSup ? '#0a5c28' : '#8b0000') : (isSup ? stl.up : stl.dn);
      const labCol = touch ? col : (isSup ? this.C.green : this.C.red);
      const cls = [];
      if(this._animateSR) cls.push('srl');
      if(touch) cls.push('sr-pulse');
      const cattr = cls.length ? ' class="' + cls.join(' ') + '"' : '';
      const lineId = 'sr-' + (srSeq++);
      const priceTxt = fmt0(vv);
      const methodTxt = (!this._isMobile && ev !== 'C') ? ((sr.method || '').slice(0, 8)) : '';
      const badgeW = this._isMobile ? 64 : (20 + 18 + priceTxt.length * 6.6 + (methodTxt ? methodTxt.length * 5.4 + 10 : 0) + 8);
      const x0 = Math.min(6 + badgeW + 30, this.px1 - 24);
      s.push('<line' + cattr + ' id="' + lineId + '" x1="' + x0.toFixed(0) + '" y1="' + yy.toFixed(1) + '" x2="' + this.px1 + '" y2="' + yy.toFixed(1) + '" stroke="' + col + '" stroke-width="' + lw.toFixed(1) + '"' + (stl.dash ? ' stroke-dasharray="' + stl.dash + '"' : '') + ' opacity="' + stl.op + '"/>');
      s.push('<line x1="' + (6 + badgeW + 2).toFixed(0) + '" y1="' + yy.toFixed(1) + '" x2="' + x0.toFixed(0) + '" y2="' + yy.toFixed(1) + '" stroke="' + col + '" stroke-width="1" stroke-dasharray="2 3" opacity=".4"/>');
      if(isSup){
        s.push('<polygon points="' + (x0 - 3).toFixed(0) + ',' + (yy - 2).toFixed(1) + ' ' + (x0 + 3).toFixed(0) + ',' + (yy - 2).toFixed(1) + ' ' + x0.toFixed(0) + ',' + (yy - 7).toFixed(1) + '" fill="' + col + '"/>');
      } else {
        s.push('<polygon points="' + (x0 - 3).toFixed(0) + ',' + (yy + 2).toFixed(1) + ' ' + (x0 + 3).toFixed(0) + ',' + (yy + 2).toFixed(1) + ' ' + x0.toFixed(0) + ',' + (yy + 7).toFixed(1) + '" fill="' + col + '"/>');
      }
      if(touch && !this._isMobile){
        s.push('<circle cx="' + (this.px1 - 4).toFixed(0) + '" cy="' + yy.toFixed(1) + '" r="8" fill="' + col + '" opacity=".15"/>'
             + '<circle cx="' + (this.px1 - 4).toFixed(0) + '" cy="' + yy.toFixed(1) + '" r="4" fill="' + col + '" opacity=".8"/>');
      }
      hl.push({id: lineId, yy, price: vv, name: sr.method || '', ev, isSup, sw: lw, op: stl.op, kind: 'sr'});
      if(inViewRows.length > 8 && ev === 'C') return;
      srLbls.push({y: yy, type: (isSup?'S':'R') + (rr.idx + 1), price: priceTxt, methodTxt, ev, isSup, col: labCol});
    });

    srRows.forEach(rr => {
      const vv = +rr.sr.level;
      const yy = y(vv);
      if(isFinite(yy) && yy >= this.TL - 6 && yy <= priceB + 6) return;
      const isSup = rr.isSup;
      const col = isSup ? this.C.green : this.C.red;
      if(vv > pr.pmax) edgeTop.push({lab: (isSup?'S':'R') + (rr.idx + 1) + ' ¥' + fmt0(vv), col, method: rr.sr.method || '', up: true, sup: isSup});
      else if(vv < pr.pmin) edgeBot.push({lab: (isSup?'S':'R') + (rr.idx + 1) + ' ¥' + fmt0(vv), col, method: rr.sr.method || '', up: false, sup: isSup});
    });

    packLbl(srLbls, 22).forEach(it => {
      if(it.yy < this.TL + 11 || it.yy > priceB - 11) return;
      const ev = it.ev;
      const bgA = hexA(it.isSup ? this.C.green : this.C.red, .12);
      const bgB = hexA(it.isSup ? this.C.green : this.C.red, .08);
      const badgeW = this._isMobile ? 64 : (20 + 18 + it.price.length * 6.6 + (it.methodTxt ? it.methodTxt.length * 5.4 + 10 : 0) + 8);
      const gOpen = this._animateSR ? '<g class="srlbl">' : '<g>';
      s.push(gOpen);
      if(ev === 'C'){
        s.push('<rect x="6" y="' + (it.yy - 10).toFixed(1) + '" width="' + badgeW.toFixed(0) + '" height="20" rx="10" fill="' + this.C.bg2 + '" fill-opacity=".95" stroke="' + it.col + '" stroke-width="1"/>');
      } else {
        s.push('<rect x="6" y="' + (it.yy - 10).toFixed(1) + '" width="' + badgeW.toFixed(0) + '" height="20" rx="10" fill="' + (ev === 'A' ? bgA : bgB) + '"/>');
      }
      if(ev === 'A') s.push('<circle cx="16" cy="' + it.yy.toFixed(1) + '" r="4" fill="' + it.col + '"/>');
      else if(ev === 'B') s.push('<circle cx="16" cy="' + it.yy.toFixed(1) + '" r="4" fill="' + it.col + '" opacity=".35"/><circle cx="16" cy="' + it.yy.toFixed(1) + '" r="2.2" fill="' + it.col + '"/>');
      else s.push('<circle cx="16" cy="' + it.yy.toFixed(1) + '" r="3.5" fill="none" stroke="' + it.col + '" stroke-width="1.2"/>');
      s.push('<text x="24" y="' + (it.yy + 3.5).toFixed(1) + '" font-size="10" font-weight="700" fill="' + it.col + '" font-family="SF Mono,monospace">' + it.type + '</text>');
      s.push('<text x="46" y="' + (it.yy + 4).toFixed(1) + '" font-size="11" font-weight="600" fill="' + it.col + '" font-family="SF Mono,monospace">¥' + it.price + '</text>');
      if(it.methodTxt){
        s.push('<text x="' + (52 + it.price.length * 6.6).toFixed(0) + '" y="' + (it.yy + 4).toFixed(1) + '" font-size="9" fill="' + this.C.sub + '" font-family="SF Mono,monospace">' + it.methodTxt + '</text>');
      }
      s.push('</g>');
    });

    const rightItems = [];
    let zoneY = this.TL + 14;
    if(pr.hasV){
      [['low', pr.vlow, this.C.green, hexA(this.C.green, .22), '保守', this.C.green, '6 4'],
       ['mid', pr.vmid, this.C.blue, hexA(this.C.blue, .22), '基准', this.C.blue, ''],
       ['high', pr.vhigh, this.C.red, hexA(this.C.red, .22), '乐观', this.C.red, '6 4']].forEach(a => {
        const yy = y(a[1]);
        if(isFinite(yy) && yy >= this.TL && yy <= priceB){
          const cls = this._animateSR ? ' class="srl"' : '';
          const dashAttr = a[6] ? ' stroke-dasharray="' + a[6] + '"' : '';
          s.push('<line' + cls + ' id="anchor-' + a[0] + '" x1="0" y1="' + yy.toFixed(1) + '" x2="' + this.px1 + '" y2="' + yy.toFixed(1) + '" stroke="' + a[2] + '" stroke-width="1.6" stroke-linecap="round"' + dashAttr + ' opacity=".8"/>'
               + '<circle cx="8" cy="' + yy.toFixed(1) + '" r="2.5" fill="' + a[2] + '"/>');
          rightItems.push({y: yy, lab: a[4] + ' ¥' + fmt2(a[1]), col: a[2], bg: a[3], bar: a[5]});
          hl.push({id: 'anchor-' + a[0], yy, price: a[1], name: '估值锚 V_' + a[0] + '（' + a[4] + '）', ev: 'A', isSup: a[0] !== 'high', sw: 1.6, op: .7, kind: 'anchor'});
        }
      });
      let guard = 0;
      while(guard++ < 12){
        const hit = srLbls.find(l => Math.abs(zoneY + 26 - l.yy) < 30);
        if(!hit) break;
        zoneY = hit.yy + 28;
      }
      const zoneCard = this._zoneCard(lastClose, pr);
      if(zoneCard && zoneY + zoneCard.h <= priceB - 4){
        s.push(zoneCard.svg(zoneY));
      }
      const zCur = lastClose < pr.vlow ? 'low' : (lastClose <= pr.vhigh ? 'mid' : 'high');
      const zLabels = [
        {key: 'high', t: '高估区', col: this.C.red, y0: this.TL, y1: y(pr.vhigh)},
        {key: 'mid', t: '合理区', col: this.C.blue, y0: y(pr.vhigh), y1: y(pr.vlow)},
        {key: 'low', t: '低估区', col: this.C.green, y0: y(pr.vlow), y1: priceB},
      ];
      const zFs = small ? 10 : 12;
      zLabels.forEach(z => {
        if(z.y1 - z.y0 < 26) return;
        const yy = z.y0 + 15;
        s.push('<text x="' + (this.px1 - 8) + '" y="' + yy.toFixed(1) + '" text-anchor="end" font-size="' + zFs + '" font-weight="700" fill="' + z.col + '" opacity="' + (z.key === zCur ? '.9' : '.55') + '" font-family="PingFang SC,Microsoft YaHei,sans-serif">' + z.t + '</text>');
      });
      if(!st.decision_usable && W >= 560 && (zoneY > this.TL + 80 || !zoneCard)){
        s.push('<rect x="6" y="' + this.TL + '" width="150" height="22" rx="4" fill="' + this.C.bg2 + '" fill-opacity=".94" stroke="' + this.C.hair + '"/>'
             + '<text x="14" y="' + (this.TL + 15) + '" font-size="12" fill="' + this.C.sub2 + '" font-weight="600">参考区间 · 不可执行</text>');
      }
    } else if(isFinite(+st.v_low) && isFinite(+st.v_high)){
      edgeBot.push({lab: 'V_low ¥' + fmt0(+st.v_low), col: this.C.green, method: '', up: false, sup: true});
      edgeTop.push({lab: 'V_high ¥' + fmt0(+st.v_high), col: this.C.red, method: '', up: true, sup: false});
    }

    if(this.N >= 60 && this.barsPerView() >= Math.min(this.N, 240)){
      const seg = this.rows.slice(-250);
      const lo = Math.min.apply(null, seg.map(r => r.l));
      const hi = Math.max.apply(null, seg.map(r => r.h));
      if(hi - lo > 0){
        [0.382, 0.5, 0.618].forEach(rt => {
          const p = lo + (hi - lo) * rt;
          const yy = y(p);
          if(isFinite(yy) && yy >= this.TL && yy <= priceB){
            s.push('<line x1="0" y1="' + yy.toFixed(1) + '" x2="' + this.px1 + '" y2="' + yy.toFixed(1) + '" stroke="' + this.C.gold + '" stroke-width="1" stroke-dasharray="2 4" opacity=".5"/>');
            if(W >= 560) rightItems.push({y: yy, lab: rt + ' ¥' + fmt2(p), col: this.C.gold, bg: hexA(this.C.bg2, .9)});
          }
        });
      }
    }

    [5,10,20,60,120,250].forEach(w => {
      if(!this.maVis[w] || !this.maC[w]) return;
      const v = this.maC[w][this._pr.i1];
      if(!isFinite(v)) return;
      const yy = y(v);
      if(!isFinite(yy) || yy < this.TL - 4 || yy > priceB + 4) return;
      s.push('<circle cx="' + (this.px1 - 2).toFixed(1) + '" cy="' + yy.toFixed(1) + '" r="2.4" fill="' + this._maCol[w] + '"/>');
      if(W >= 560) rightItems.push({y: yy, lab: 'MA' + w + ' ' + fmt2(v), col: this._maCol[w], bg: hexA(this.C.bg2, .92)});
    });

    const chW = small ? 5.2 : 6.3;
    const maxChars = Math.max(4, Math.floor((this.GUT - 14) / chW));
    packLblMutual(srLbls, rightItems, 22, 17, 18).forEach(it => {
      if(it._hidden) return;
      if(it.yy < this.TL + 9 || it.yy > priceB - 9) return;
      let lab = it.lab;
      if(lab.length > maxChars) lab = lab.slice(0, maxChars);
      const wdt = Math.min(this.GUT - 10, 12 + lab.length * chW);
      const xR = this.px1 + this.GUT - 6;
      s.push('<line x1="' + this.px1.toFixed(0) + '" y1="' + it.y.toFixed(1) + '" x2="' + (this.px1 + 4).toFixed(0) + '" y2="' + it.y.toFixed(1) + '" stroke="' + it.col + '" stroke-width="1" opacity=".45"/>');
      if(Math.abs(it.yy - it.y) > 3){
        s.push('<line x1="' + (this.px1 + 4).toFixed(0) + '" y1="' + it.y.toFixed(1) + '" x2="' + (this.px1 + 4).toFixed(0) + '" y2="' + it.yy.toFixed(1) + '" stroke="' + it.col + '" stroke-width="1" opacity=".45"/>');
      }
      if(it.bar){
        s.push('<rect x="' + (xR - wdt - 6).toFixed(0) + '" y="' + (it.yy - 8).toFixed(1) + '" width="3" height="16" rx="1.5" fill="' + it.bar + '"/>');
      }
      s.push('<rect x="' + (xR - wdt).toFixed(0) + '" y="' + (it.yy - 8).toFixed(1) + '" width="' + wdt.toFixed(0) + '" height="16" rx="4" fill="' + it.bg + '"/>'
           + '<text x="' + (xR - wdt + 5).toFixed(0) + '" y="' + (it.yy + 3.5).toFixed(1) + '" font-size="' + (small ? 10 : 11) + '" font-weight="600" fill="' + it.col + '" font-family="SF Mono,monospace">' + lab + '</text>');
    });

    const crossSeen = [];
    for(const c of this.crosses){
      if(c.i < this._pr.i0 || c.i > this._pr.i1) continue;
      const x = this.xOf(c.i);
      if(x < this.px0 + 20 || x > this.px1 - 20) continue;
      const r = this.rows[c.i];
      const yy = c.up ? y(r.h) - 10 : y(r.l) + 18;
      if(!isFinite(yy) || yy < this.TL + 9 || yy > priceB - 9) continue;
      crossSeen.push({x, yy, up: c.up});
    }
    if(crossSeen.length > 8) crossSeen.splice(0, crossSeen.length - 8);
    crossSeen.forEach(k => {
      s.push('<text x="' + k.x.toFixed(1) + '" y="' + k.yy.toFixed(1) + '" text-anchor="middle" font-size="9" fill="' + (k.up ? this.C.green : this.C.red) + '">' + (k.up ? '▲金叉' : '▼死叉') + '</text>');
    });

    const lm = [];
    for(let i = this._pr.i0; i <= this._pr.i1; i++){
      const r = this.rows[i];
      if(!(r.o > 0)) continue;
      const x = this.xOf(i);
      if(x < this.px0 + 12 || x > this.px1 - 12) continue;
      const chg = (r.c - r.o) / r.o;
      if(chg > 0.095) lm.push({x, yy: y(r.h) - 16, t: '涨', col: this.C.up});
      else if(chg < -0.095) lm.push({x, yy: y(r.h) - 16, t: '跌', col: this.C.dn});
    }
    if(lm.length > 6) lm.splice(0, lm.length - 6);
    lm.forEach(k => {
      s.push('<rect x="' + (k.x - 8).toFixed(1) + '" y="' + k.yy.toFixed(1) + '" width="16" height="16" rx="3" fill="' + k.col + '"/>'
           + '<text x="' + k.x.toFixed(1) + '" y="' + (k.yy + 11).toFixed(1) + '" text-anchor="middle" font-size="11" fill="#ffffff">' + k.t + '</text>');
    });

    const vmax = this._volMax();
    const va5 = this.volC[5];
    const fang = [], brk = [];
    const rmax = res.length ? Math.max.apply(null, res.map(x => +x.level)) : null;
    for(let i = this._pr.i0; i <= this._pr.i1; i++){
      const r = this.rows[i];
      const x = this.xOf(i);
      if(x < this.px0 + 10 || x > this.px1 - 10) continue;
      if(va5 && isFinite(va5[i]) && va5[i] > 0 && r.v > va5[i] * 2){
        fang.push({x, yy: Math.max(this.volTop + 10, this.volBot - Math.max(1.5, r.v / vmax * (this.volH - 8)) - 6)});
      }
      if(isFinite(rmax) && i > 0 && r.c > rmax && this.rows[i-1].c <= rmax && va5 && isFinite(va5[i]) && r.v > va5[i] * 1.5){
        brk.push({x, yy: y(r.h) - 26});
      }
    }
    if(fang.length > 6) fang.splice(0, fang.length - 6);
    fang.forEach(k => {
      s.push('<text x="' + k.x.toFixed(1) + '" y="' + k.yy.toFixed(1) + '" text-anchor="middle" font-size="9" fill="' + this.C.gold + '">放量</text>');
    });
    if(brk.length > 3) brk.splice(0, brk.length - 3);
    brk.forEach(k => {
      s.push('<text x="' + k.x.toFixed(1) + '" y="' + k.yy.toFixed(1) + '" text-anchor="middle" font-size="9" fill="' + this.C.gold + '" font-weight="700">突破</text>');
    });

    const yc = y(lastClose);
    if(isFinite(yc) && yc >= this.TL && yc <= priceB){
      s.push('<line x1="0" y1="' + yc.toFixed(1) + '" x2="' + this.px1 + '" y2="' + yc.toFixed(1) + '" stroke="' + this.C.blue + '" stroke-width="1" opacity=".35"/>'
           + '<polygon points="' + (this.px1 + 7) + ',' + (yc - 3.5).toFixed(1) + ' ' + (this.px1 + 7) + ',' + (yc + 3.5).toFixed(1) + ' ' + (this.px1 + 2) + ',' + yc.toFixed(1) + '" fill="' + this.C.blue + '"/>');
    }
    if(pr.hasV){
      const yLow = y(pr.vlow), yHigh = y(pr.vhigh);
      s.push('<defs><linearGradient id="vGauge" x1="0" y1="0" x2="0" y2="1">'
           + '<stop offset="0" stop-color="' + this.C.red + '"/><stop offset=".5" stop-color="' + this.C.blue + '"/><stop offset="1" stop-color="' + this.C.green + '"/>'
           + '</linearGradient></defs>'
           + '<rect x="' + (this.axX - 8) + '" y="' + yHigh.toFixed(1) + '" width="5" height="' + Math.max(1, yLow - yHigh).toFixed(1) + '" rx="2.5" fill="url(#vGauge)" opacity=".55"/>');
      if(isFinite(yc) && yc >= yHigh - 1 && yc <= yLow + 1){
        s.push('<circle cx="' + (this.axX - 5.5).toFixed(1) + '" cy="' + yc.toFixed(1) + '" r="3" fill="' + this.C.blue + '" stroke="#ffffff" stroke-width="1.5"/>');
      }
    }

    const step = niceStep(pr.pmax - pr.pmin, 5);
    const yFs = small ? 10 : 11;
    for(let p = Math.ceil(pr.pmin / step) * step; p <= pr.pmax + 1e-9; p += step){
      const yy = y(p);
      if(!isFinite(yy) || yy < this.TL - 2 || yy > priceB + 2) continue;
      s.push('<text x="' + (this.axX + 7) + '" y="' + (yy + 3.5).toFixed(1) + '" font-size="' + yFs + '" fill="' + this.C.sub2 + '" font-family="SF Mono,monospace">' + fmt2(p) + '</text>');
    }

    const dstep = Math.max(1, Math.ceil(88 / Math.max(this.slot, 0.5)));
    let lastDx = -Infinity;
    for(let i = this._pr.i0; i <= this._pr.i1; i++){
      if(i % dstep !== 0 && i !== this.N - 1) continue;
      const x = this.xOf(i);
      if(x < this.px0 || x > this.px1) continue;
      if(x - lastDx < (small ? 56 : 80)) continue;
      lastDx = x;
      const d = String(this.rows[i].d || '').slice(2, 10);
      const day = String(this.rows[i].d || '').slice(8, 10);
      if(small && day !== '01' && i !== this.N - 1) continue;
      s.push('<text x="' + x.toFixed(1) + '" y="' + (this.volBot + 16) + '" font-size="' + yFs + '" fill="' + this.C.sub2 + '" text-anchor="middle" font-family="SF Mono,monospace">' + d + '</text>');
    }

    const edge = (arr, yTop) => {
      let ex = 6;
      arr.slice(0, 3).forEach(x => {
        const yy = yTop ? this.TL + 4 : priceB - 20;
        const lab = (x.up ? '↑ ' : '↓ ') + x.lab;
        const wdt = 16 + lab.length * 6.2;
        s.push('<rect x="' + ex + '" y="' + yy + '" width="' + wdt.toFixed(0) + '" height="16" rx="4" fill="' + this.C.bg2 + '" fill-opacity=".92" stroke="' + this.C.hair + '" opacity=".85">'
             + '<title>' + x.method + '</title></rect>'
             + '<text x="' + (ex + 8) + '" y="' + (yy + 11.5) + '" font-size="11" fill="' + x.col + '" font-family="SF Mono,monospace">' + lab + '</text>');
        ex += wdt + 6;
      });
    };
    if(edgeTop.length) edge(edgeTop, true);
    if(edgeBot.length) edge(edgeBot, false);

    s.push('<g id="hoverHl" opacity="0">'
      + '<rect id="hoverHlR" x="0" y="0" width="120" height="38" rx="6" fill="' + this.C.bg2 + '" fill-opacity=".96" stroke="' + this.C.hair + '"/>'
      + '<text id="hoverHlT1" x="8" y="0" font-size="11" font-weight="700" fill="' + this.C.ink + '" font-family="SF Mono,monospace"></text>'
      + '<text id="hoverHlT2" x="8" y="0" font-size="10" fill="' + this.C.sub + '" font-family="SF Mono,monospace"></text>'
      + '</g>');

    const crossCol = hexA(this.C.blue, .35);
    s.push('<g id="chG" opacity="0">'
      + '<line id="chV" x1="0" y1="0" x2="0" y2="0" stroke="' + crossCol + '" stroke-width="1" stroke-dasharray="3 3"/>'
      + '<line id="chH" x1="0" y1="0" x2="0" y2="0" stroke="' + crossCol + '" stroke-width="1" stroke-dasharray="3 3"/>'
      + '<rect id="chYpill" x="0" y="0" width="' + (this.AX - 4) + '" height="16" rx="4" fill="' + this.C.ink + '" opacity="0"/>'
      + '<text id="chYtxt" x="0" y="0" font-size="11" fill="#ffffff" font-family="SF Mono,monospace"></text>'
      + '<rect id="chXpill" x="0" y="0" width="78" height="16" rx="4" fill="' + this.C.ink + '" opacity="0"/>'
      + '<text id="chXtxt" x="0" y="0" font-size="11" fill="#ffffff" text-anchor="middle" font-family="SF Mono,monospace"></text>'
      + '<circle id="chDot" r="4" fill="' + this.C.blue + '" stroke="#ffffff" stroke-width="2" opacity="0"/>'
      + '</g>');
    this.sv.innerHTML = s.join('');
    this._ch = {
      g: document.getElementById('chG'),
      v: document.getElementById('chV'), h: document.getElementById('chH'),
      ypill: document.getElementById('chYpill'), ytxt: document.getElementById('chYtxt'),
      xpill: document.getElementById('chXpill'), xtxt: document.getElementById('chXtxt'),
      dot: document.getElementById('chDot')
    };
    this._hl = hl;
    this._animateSR = false;
  }

  /* ---- 主绘制入口 ---- */
  draw(){
    this._redrawCanvas();
    this.overlay();
    if(this.pinned && this.pinIdx >= 0 && this._pinY != null) this._updateCross(this.pinIdx, this._pinY);
  }

  _scheduleDraw(){
    if(this._raf) return;
    this._raf = requestAnimationFrame(() => { this._raf = 0; this.draw(); });
  }

  /* ---- 十字光标与 Tooltip ---- */
  _barAt(mx){
    const bi = Math.round((mx - this.px0) / Math.max(this.slot, 0.05) + this.viewStart - 0.5);
    return Math.max(0, Math.min(this.N - 1, bi));
  }

  _hideCross(){
    if(this._ch) this._ch.g.setAttribute('opacity', '0');
    if(this._tipIdx !== -1){ this._tipIdx = -1; this._scheduleDraw(); }
  }

  _updateCross(bi, my){
    const ch = this._ch;
    if(!ch || bi < 0 || bi >= this.N){ if(ch) ch.g.setAttribute('opacity','0'); return; }
    const x = this.xOf(bi);
    const cy = Math.max(this.TL, Math.min(this.volBot, my));
    const inPrice = cy <= this.TL + this.priceH;
    ch.g.setAttribute('opacity', '1');
    ch.v.setAttribute('x1', x.toFixed(1)); ch.v.setAttribute('x2', x.toFixed(1));
    ch.v.setAttribute('y1', this.TL); ch.v.setAttribute('y2', this.volBot);
    const r = this.rows[bi];
    ch.dot.setAttribute('cx', x.toFixed(1)); ch.dot.setAttribute('cy', this.yOf(r.c).toFixed(1));
    ch.dot.setAttribute('opacity', '1');
    if(inPrice){
      const p = this._pr.pmin + (this._pr.pmax - this._pr.pmin) * (1 - (cy - this.TL) / this.priceH);
      ch.h.setAttribute('x1', this.px0); ch.h.setAttribute('x2', this.px1);
      ch.h.setAttribute('y1', cy.toFixed(1)); ch.h.setAttribute('y2', cy.toFixed(1));
      ch.h.setAttribute('opacity', '1');
      const ly = Math.max(this.TL, Math.min(this.TL + this.priceH - 16, cy - 8));
      ch.ypill.setAttribute('x', this.axX + 1); ch.ypill.setAttribute('y', ly.toFixed(1));
      ch.ypill.setAttribute('opacity', '1');
      ch.ytxt.setAttribute('x', this.axX + 5); ch.ytxt.setAttribute('y', (ly + 11.5).toFixed(1));
      ch.ytxt.textContent = fmt2(p);
    } else {
      ch.h.setAttribute('opacity', '0');
      ch.ypill.setAttribute('opacity', '0');
      ch.ytxt.textContent = '';
    }
    const lx = Math.max(this.px0, Math.min(this.px1 - 78, x - 39));
    ch.xpill.setAttribute('x', lx.toFixed(1)); ch.xpill.setAttribute('y', this.volBot + 2);
    ch.xpill.setAttribute('opacity', '1');
    ch.xtxt.setAttribute('x', (lx + 39).toFixed(1)); ch.xtxt.setAttribute('y', this.volBot + 13);
    ch.xtxt.textContent = String(r.d || '');
  }

  _renderTip(bi){
    if(bi < 0 || bi >= this.N){ this.tip.innerHTML = ''; return; }
    const r = this.rows[bi];
    const pr = this._pr;
    const st = this.st;
    const prev = bi > 0 ? this.rows[bi - 1].c : r.c;
    const chg = r.c - prev;
    const pct = prev ? chg / prev * 100 : 0;
    const ccol = chg > 0 ? this.C.up : (chg < 0 ? this.C.dn : this.C.sub);
    const volTxt = r.v >= 1e8 ? (r.v / 1e8).toFixed(2) + '亿' : (r.v / 1e4).toFixed(1) + '万';
    const amtTxt = (r.v * r.c) >= 1e8 ? ((r.v * r.c) / 1e8).toFixed(2) + '亿' : ((r.v * r.c) / 1e4).toFixed(1) + '万';
    const ampTxt = prev > 0 ? ((r.h - r.l) / prev * 100).toFixed(2) + '%' : '—';
    const wk = ['周日','周一','周二','周三','周四','周五','周六'][new Date(r.d + 'T00:00:00').getDay()] || '';
    const zm = zmeta(st);
    const zoneCol = [this.C.green, this.C.green, this.C.gold, this.C.gold, this.C.red, this.C.red, this.C.sub][zm.c] || this.C.sub;
    let t = '<div class="ztip"><span class="zone-badge" style="background:' + hexA(this.C.sub, .12) + ';color:' + zoneCol + '">' + (st.decision_usable ? zm.label : (st.reference_zone ? '参考 ' + st.reference_zone : zm.label)) + '</span>'
      + '<span class="kdate">' + r.d + ' ' + wk + '</span></div>'
      + '<div class="krow"><span class="tk">开盘</span><span>' + fmt2(r.o) + '</span><span class="tk">最高</span><span>' + fmt2(r.h) + '</span></div>'
      + '<div class="krow"><span class="tk">收盘</span><b style="color:' + ccol + '">' + fmt2(r.c) + '</b><span class="tk">最低</span><span>' + fmt2(r.l) + '</span></div>'
      + '<div class="krow"><span class="tk">涨跌</span><b style="color:' + ccol + '">' + (chg >= 0 ? '+' : '') + fmt2(chg) + ' (' + (pct >= 0 ? '+' : '') + pct.toFixed(2) + '%)</b></div>'
      + '<div class="krow"><span class="tk">幅·量·额</span><span>' + ampTxt + ' / ' + volTxt + ' / ' + amtTxt + '</span></div>';
    const va5 = this.volC[5] && isFinite(this.volC[5][bi]) && this.volC[5][bi] > 0 ? this.volC[5][bi] : null;
    if(va5) t += '<div class="krow"><span class="tk">量比</span><span>VOL5 ' + (r.v / va5).toFixed(2) + '×</span></div>';
    let mline = '';
    [5,10,20,60,120,250].forEach(w => {
      if(this.maVis[w] && this.maC[w] && isFinite(this.maC[w][bi])) mline += '<span class="mma"><i style="background:' + this._maCol[w] + '"></i>MA' + w + ' ' + fmt2(this.maC[w][bi]) + '</span>';
    });
    if(mline) t += '<div class="krow ma">' + mline + '</div>';
    if(pr.hasV){
      let z = null;
      if(r.c < pr.vlow) z = {t: '深度低估', c: this.C.green};
      else if(r.c < pr.vmid) z = {t: '低估区', c: this.C.green};
      else if(r.c <= pr.vhigh) z = {t: '合理区', c: this.C.blue};
      else z = {t: '高估区', c: this.C.red};
      const dv = (r.c / pr.vlow - 1) * 100;
      t += '<div class="krow"><span class="tk">估值位置</span><b style="color:' + z.c + '">' + z.t + '</b><span>距保守 ¥' + fmt2(pr.vlow) + ' ' + (dv >= 0 ? '+' : '') + dv.toFixed(1) + '%</span></div>';
    }
    const supLv = (st.support || []).map(x => ({v: +x.level, m: x.method || ''})).filter(x => isFinite(x.v) && x.v > 0);
    const resLv = (st.resistance || []).map(x => ({v: +x.level, m: x.method || ''})).filter(x => isFinite(x.v) && x.v > 0);
    const nearS = supLv.filter(x => x.v < r.c).sort((a,b) => b.v - a.v)[0];
    const nearR = resLv.filter(x => x.v > r.c).sort((a,b) => a.v - b.v)[0];
    const mShort = m => m ? (m.length > 10 ? m.slice(0, 10) + '…' : m) : '';
    if(nearS || nearR){
      const inS = nearS && Math.abs(r.c / nearS.v - 1) <= 0.02;
      const inR = nearR && Math.abs(r.c / nearR.v - 1) <= 0.02;
      t += '<div class="krow"><span class="tk">最近</span>'
        + (nearS ? '<span class="' + (inS ? 'near-s' : '') + '">支撑 ¥' + fmt2(nearS.v) + '</span>' + (mShort(nearS.m) ? '<span>（' + mShort(nearS.m) + '）</span>' : '') : '')
        + (nearS && nearR ? '<span>　</span>' : '')
        + (nearR ? '<span class="' + (inR ? 'near-r' : '') + '">阻力 ¥' + fmt2(nearR.v) + '</span>' + (mShort(nearR.m) ? '<span>（' + mShort(nearR.m) + '）</span>' : '') : '')
        + '</div>';
    }
    this.tip.innerHTML = t;
    const live = document.getElementById('chartLive');
    if(live){
      const zmTxt = (st.decision_usable ? zm.label : (st.reference_zone ? '参考 ' + st.reference_zone : zm.label));
      live.textContent = r.d + ' 收盘 ' + fmt2(r.c) + ' 涨跌 ' + (chg>=0?'+':'') + fmt2(chg) + ' ' + (pct>=0?'+':'') + pct.toFixed(2) + '%，估值区 ' + zmTxt + '，成交量 ' + volTxt;
    }
    const spark = (() => {
      const pts = [];
      for(let k = 0; k < 3; k++){
        const j = bi - 2 + k;
        if(j >= 0 && j < this.N) pts.push({d: this.rows[j].d, c: this.rows[j].c});
      }
      if(pts.length < 2) return '';
      const min = Math.min.apply(null, pts.map(p => p.c)), max = Math.max.apply(null, pts.map(p => p.c));
      const rng = (max - min) || 1;
      const W = 120, H = 20, pad = 3;
      const x = i => pad + i * (W - pad * 2) / (pts.length - 1);
      const y = c => H - pad - (c - min) / rng * (H - pad * 2);
      const line = pts.map((p, i) => x(i).toFixed(1) + ',' + y(p.c).toFixed(1)).join(' ');
      const up = pts[pts.length - 1].c >= pts[0].c;
      const col = up ? 'var(--candle-up)' : 'var(--candle-dn)';
      return '<svg class="spark" width="' + W + '" height="' + H + '" aria-hidden="true" viewBox="0 0 ' + W + ' ' + H + '">'
        + '<polyline points="' + line + '" stroke="' + col + '"/>'
        + '<circle class="last-dot" cx="' + x(pts.length - 1).toFixed(1) + '" cy="' + y(pts[pts.length - 1].c).toFixed(1) + '" r="2"/>'
        + '</svg>';
    })();
    if(spark) this.tip.insertAdjacentHTML('beforeend', spark);
  }

  /* Tooltip 定位：默认右下方 12px，超出画布自动翻转（不写死 left/top） */
  _positionTip(mx, my){
    if(this._isMobile) return;
    const tw = this.tip.offsetWidth || 200, th = this.tip.offsetHeight || 120;
    let lx = mx + 12, ty = my + 12;
    if(lx + tw > this.W - 6) lx = mx - tw - 12;
    if(ty + th > this.H - 6) ty = my - th - 12;
    this.tip.style.left = Math.max(2, lx) + 'px';
    this.tip.style.top = Math.max(2, ty) + 'px';
  }/* ---- hover 高亮：S/R 线与估值锚线（≤6px）聚焦 ---- */
  _hoverCheck(mx, my){
    const hls = this._hl || [];
    let hit = null, best = 6;
    for(const h of hls){
      const d = Math.abs(my - h.yy);
      if(d < best){ best = d; hit = h; }
    }
    if(hit){
      clearTimeout(this._hoverT);
      this._hoverT = null;
      if(!this._hoverOn){ this._hoverOn = true; }
      for(const h of hls){
        const el = document.getElementById(h.id);
        if(!el) continue;
        if(h === hit){
          el.setAttribute('stroke-width', (h.sw + 1.5).toFixed(1));
          el.setAttribute('opacity', '1');
        } else {
          el.setAttribute('opacity', '0.3');
        }
      }
      const g = document.getElementById('hoverHl');
      if(g){
        const name = hit.kind === 'anchor' ? hit.name : (hit.name || ((hit.isSup ? '支撑' : '压力') + '位'));
        const t1 = (hit.kind === 'anchor' ? '' : (hit.ev + '级 ')) + name.slice(0, 14) + ' ¥' + fmt2(hit.price);
        const t2 = hit.kind === 'anchor' ? '估值锚边界' : ((hit.isSup ? '支撑 S' : '压力 R') + ' · ' + hit.ev + '级强度');
        const r1 = document.getElementById('hoverHlT1'), r2 = document.getElementById('hoverHlT2');
        if(r1){ r1.textContent = t1; }
        if(r2){ r2.textContent = t2; }
        const tw = Math.max(100, (t1.length > t2.length ? t1.length : t2.length) * 6.4 + 16);
        const rr = document.getElementById('hoverHlR');
        if(rr) rr.setAttribute('width', tw.toFixed(0));
        let gx = mx + 14, gy = my + 10;
        if(gx + tw > this.W - 6) gx = mx - tw - 14;
        if(gy + 38 > this.H - 6) gy = my - 48;
        g.setAttribute('transform', 'translate(' + Math.max(2, gx).toFixed(0) + ',' + Math.max(2, gy).toFixed(0) + ')');
        r1.setAttribute('y', '14'); r2.setAttribute('y', '30');
        g.setAttribute('opacity', '1');
      }
    } else {
      if(this._hoverOn){
        this._hoverOn = false;
        clearTimeout(this._hoverT);
        this._hoverT = setTimeout(() => { this._hoverReset(); }, 200);
      }
    }
  }

  _hoverReset(){
    const hls = this._hl || [];
    for(const h of hls){
      const el = document.getElementById(h.id);
      if(!el) continue;
      el.setAttribute('stroke-width', h.sw);
      el.setAttribute('opacity', h.op);
    }
    const g = document.getElementById('hoverHl');
    if(g) g.setAttribute('opacity', '0');
  }

  /* ---- scrollToPrice：图例点击 → 居中或闪烁 ---- */
  scrollToPrice(level){
    if(!this._pr || !isFinite(+level)) return;
    const pr = this._pr;
    if(level >= pr.pmin && level <= pr.pmax){
      this._flashSR(level);
      return;
    }
    this._centerOn(level);
  }

  _flashSR(level){
    const hit = (this._hl || []).find(h => h.kind === 'sr' && Math.abs(h.price - level) < 0.005);
    if(!hit) return;
    const el = document.getElementById(hit.id);
    if(!el) return;
    el.classList.add('sr-pulse');
    clearTimeout(this._flashT);
    this._flashT = setTimeout(() => {
      try{ el.classList.remove('sr-pulse'); }catch(err){}
    }, 2400);
  }

  _centerOn(level){
    const pr = this._pr;
    const mid = (pr.pmin + pr.pmax) / 2;
    this._yAnim = { from: this._yShift || 0, to: mid - level, t0: performance.now(), dur: 400 };
    this._startLoop();
  }

  _resetYShift(){
    this._yShift = 0;
    this._yAnim = null;
  }

  /* ---- 交互：拖拽平移（200ms 惯性） / 点击固定 / 滚轮缩放（指针居中，最少20根） ---- */
  _onDown(e){
    if(e.button !== 0 || this.N < 2) return;
    this._drag = { startX: e.clientX, startY: e.clientY, vs: this.viewStart, lastX: e.clientX, lastT: performance.now(), vx: 0 };
    try{ this.sv.setPointerCapture(e.pointerId); }catch(err){}
  }

  _onUp(e){
    const d = this._drag; this._drag = null;
    if(!d) return;
    const dist = Math.hypot(e.clientX - d.startX, e.clientY - d.startY);
    if(dist < 5){
      const rect = this.sv.getBoundingClientRect();
      if(rect.width < 2) return;
      const mx = (e.clientX - rect.left) * this.W / rect.width;
      const my = (e.clientY - rect.top) * this.H / rect.height;
      const bi = this._barAt(mx);
      if(this.pinned && bi === this.pinIdx){
        this.pinned = false; this.pinIdx = -1; this._pinY = null;
        this._hideCross(); this.tip.classList.remove('show');
        this._startLoop();
      } else {
        this.pinned = true; this.pinIdx = bi; this._pinY = my; this._tipIdx = bi;
        this._renderTip(bi);
        this._updateCross(bi, my);
        this._positionTip(mx, my);
        this.tip.classList.add('show');
      }
      return;
    }
    /* 平移惯性：按 200ms 的 easeOut 衰减继续滑动 */
    if(Math.abs(d.vx) > 0.6){
      this._glideTo(this.viewStart - d.vx * 220, 200);
    }
  }

  _glideTo(tVS, dur){
    if(this._anim) cancelAnimationFrame(this._anim);
    const fVS = this.viewStart;
    const t0 = performance.now(), D = dur || 200;
    const step = now => {
      const p = Math.min(1, (now - t0) / D);
      const e = 1 - Math.pow(1 - p, 3);
      this.viewStart = fVS + (tVS - fVS) * e;
      this._clampView();
      this.draw();
      if(p < 1) this._anim = requestAnimationFrame(step);
      else this._anim = null;
    };
    this._anim = requestAnimationFrame(step);
  }

  _onMove(e){
    if(this.N < 2) return;
    const rect = this.sv.getBoundingClientRect();
    if(rect.width < 2) return;
    const mx = (e.clientX - rect.left) * this.W / rect.width;
    const my = (e.clientY - rect.top) * this.H / rect.height;
    if(this._drag){
      const dx = e.clientX - this._drag.startX;
      this.viewStart = this._drag.vs - dx / Math.max(this.slot, 0.05);
      this._clampView();
      this._resetYShift();
      /* 记录滑动速度（px/ms），用于惯性 */
      const now = performance.now();
      const dt = Math.max(1, now - this._drag.lastT);
      this._drag.vx = (e.clientX - this._drag.lastX) / dt;
      this._drag.lastX = e.clientX; this._drag.lastT = now;
      this._scheduleDraw();
    }
    this._hoverCheck(mx, my);
    if(this.pinned) return;
    const bi = this._barAt(mx);
    this._updateCross(bi, my);
    if(bi !== this._tipIdx){
      this._tipIdx = bi;
      this._renderTip(bi);
    }
    this._positionTip(mx, my);
    this.tip.classList.add('show');
  }

  _zoom(e){
    if(this.N < 2) return;
    const rect = this.sv.getBoundingClientRect();
    if(rect.width < 2) return;
    const mx = (e.clientX - rect.left) * this.W / rect.width;
    const factor = e.deltaY > 0 ? 1.1 : 1 / 1.1;
    const bx = (mx - this.px0) / Math.max(this.slot, 0.05) + this.viewStart;
    const maxSlot = (this.px1 - this.px0) / Math.max(1, this.N);
    const minSlot = (this.px1 - this.px0) / 20;   /* 最少 20 根 */
    const newSlot = Math.max(maxSlot, Math.min(minSlot, this.slot * factor));
    if(Math.abs(newSlot - this.slot) < 1e-9) return;
    this.slot = newSlot;
    this.viewStart = bx - (mx - this.px0) / newSlot;
    this._clampView();
    this._resetYShift();
    this._custom = true;
    document.querySelectorAll('.range-btn').forEach(b => b.classList.remove('on'));
    this._scheduleDraw();
  }

  /* ---- 公共 API：setRange / toggleMA / setData / resize ---- */
  setRange(n){
    this.rangeN = n;
    this._custom = false;
    this._resetYShift();
    document.querySelectorAll('.range-btn').forEach(b => b.classList.toggle('on', +b.dataset.n === n));
    if(this.N < 2) return;
    this.layout();
    const bars = n > 0 ? Math.min(this.N, n) : this.N;
    const tSlot = (this.px1 - this.px0) / Math.max(1, bars);
    const tVS = Math.max(0, this.N - bars);
    this._growAnim = { t0: performance.now(), dur: 320 };   /* 周期切换：蜡烛自底部生长 */
    this._animateTo(tSlot, tVS);
  }

  _animateTo(tSlot, tVS){
    if(this._anim) cancelAnimationFrame(this._anim);
    const fSlot = this.slot, fVS = this.viewStart;
    const t0 = performance.now(), dur = 320;
    const step = now => {
      const p = Math.min(1, (now - t0) / dur);
      const e = 1 - Math.pow(1 - p, 3);
      this.slot = fSlot + (tSlot - fSlot) * e;
      this.viewStart = fVS + (tVS - fVS) * e;
      this.draw();
      if(p < 1) this._anim = requestAnimationFrame(step);
      else this._anim = null;
    };
    this._anim = requestAnimationFrame(step);
  }

  toggleMA(w){
    this.maVis[w] = !this.maVis[w];
    const chip = document.querySelector('.ma-chip[data-ma="' + w + '"]');
    if(chip) chip.classList.toggle('off', !this.maVis[w]);
    this._redrawCanvas();   /* 局部重绘：仅 Canvas，不重建 SVG 覆盖层 */
  }

  toggleBand(){
    this.bandVis = !this.bandVis;
    const chip = document.getElementById('bandChip');
    if(chip) chip.classList.toggle('off', !this.bandVis);
    this._redrawCanvas();
  }

  toggleHollow(){
    this.hollow = !this.hollow;
    const chip = document.getElementById('hollowChip');
    if(chip) chip.classList.toggle('on', this.hollow);
    this._redrawCanvas();
    try{ localStorage.setItem('radar_hollow', this.hollow ? '1' : '0'); }catch(e){}
  }

  setData(st){
    if(!st){ return; }
    if(this._anim){ cancelAnimationFrame(this._anim); this._anim = null; }
    if(this._yAnim){ cancelAnimationFrame(this._yAnim); this._yAnim = null; }
    this._loopOn = false;
    if(this._hoverT){ clearTimeout(this._hoverT); this._hoverT = null; }
    if(this._flashT){ clearTimeout(this._flashT); this._flashT = null; }
    const tok = ++this._dataTok;
    this.st = st;
    const all = (st.kline||[]).filter(r => r && [r.o, r.c, r.h, r.l, r.v].every(v => Number.isFinite(+v)));
    this.rows = all; this.N = all.length;
    this.maC = {}; this.volC = {}; this.crosses = [];
    [5,10,20,60,120,250].forEach(w => {
      if(this.N < w) return;
      const a = new Float64Array(this.N);
      let s = 0;
      for(let i = 0; i < this.N; i++){
        s += all[i].c;
        if(i >= w) s -= all[i - w].c;
        if(i >= w - 1) a[i] = s / w; else a[i] = NaN;
      }
      this.maC[w] = a;
    });
    [5,10].forEach(w => {
      if(this.N < w) return;
      const a = new Float64Array(this.N);
      let s = 0;
      for(let i = 0; i < this.N; i++){
        s += all[i].v;
        if(i >= w) s -= all[i - w].v;
        if(i >= w - 1) a[i] = s / w; else a[i] = NaN;
      }
      this.volC[w] = a;
    });
    [[5,20],[10,60]].forEach(pair => {
      const A = this.maC[pair[0]], B = this.maC[pair[1]];
      if(!A || !B) return;
      let prev = null;
      for(let i = Math.max(pair[0], pair[1]); i < this.N; i++){
        const d = A[i] - B[i];
        if(isFinite(d) && prev != null && isFinite(prev)){
          if((prev < 0 && d >= 0) || (prev > 0 && d <= 0)) this.crosses.push({i, up: d >= 0});
        }
        prev = d;
      }
    });
    this.pinned = false; this.pinIdx = -1; this._pinY = null; this._tipIdx = -1;
    this._animateSR = true;
    this._custom = false;
    this._resetYShift();
    this._bandAnim = { t0: performance.now(), dur: 500 };
    this._growAnim = { t0: performance.now(), dur: 320 };   /* 换股：蜡烛自底部生长 */
    document.getElementById('chartTitle').textContent = st.name + ' · 估值雷达主图（日K）';
    this._updateChartInfo();
    this.tip.classList.remove('show');
    this.wrap.classList.add('fade');
    setTimeout(() => {
      if(tok !== this._dataTok) return;
      this.layout();
      this._fitRange();
      this.draw();
      this._updateSrFoot(st);
      this._updateChartInfo();
      this.wrap.classList.remove('fade');
      this._startLoop();
    }, 130);
  }

  _updateChartInfo(){
    if(!this.N) return;
    const n = Math.max(1, Math.min(this.N, this.rangeN > 0 ? this.rangeN : this.N));
    let hi = -Infinity, lo = Infinity;
    for(let i = this.N - n; i < this.N; i++){
      const r = this.rows[i];
      if(r.h > hi) hi = r.h;
      if(r.l < lo) lo = r.l;
    }
    const amp = lo > 0 ? (hi - lo) / lo * 100 : 0;
    const vs = [];
    for(let i = Math.max(0, this.N - n); i < this.N; i++) vs.push(this.rows[i].v);
    const vavg = vs.length ? vs.reduce((a,b) => a + b, 0) / vs.length : 0;
    const vTxt = vavg >= 1e8 ? (vavg / 1e8).toFixed(2) + '亿' : (vavg / 1e4).toFixed(0) + '万';
    document.getElementById('chartInfo').textContent = this.N < 2
      ? '暂无足够K线数据'
      : '区间高 ' + fmt2(hi) + ' · 低 ' + fmt2(lo) + ' · 振幅 ' + amp.toFixed(1) + '% · 均量 ' + vTxt
        + '（' + DATA.data_date + ' · ' + this.N + ' 根 · 前复权）';
  }

  _updateSrFoot(st){
    const foot = document.getElementById('srFoot');
    if(!foot) return;
    const all = (st.support || []).map(x => Object.assign({}, x, {s: true}))
      .concat((st.resistance || []).map(x => Object.assign({}, x, {s: false})))
      .filter(x => isFinite(+x.level) && (x.method || '').indexOf('估值锚') !== 0);
    const pr = this._pr;
    const inView = all.filter(x => {
      if(!pr) return true;
      const yy = this.yOf(+x.level);
      return isFinite(yy) && yy >= this.TL - 6 && yy <= this.TL + this.priceH + 6;
    });
    const evOrder = {A: 0, B: 1, C: 2};
    inView.sort((a, b) => evOrder[a.level_ev] - evOrder[b.level_ev] || +a.level - +b.level);
    foot.innerHTML = inView.map((x, i) =>
      '<button class="cap ' + (x.s ? 's' : 'r') + '" title="' + (x.method || '') + ' ¥' + fmt2(+x.level) + '" onclick="KENGINE.scrollToPrice(' + (+x.level) + ')">'
      + '<i></i><span class="v">' + (x.s ? 'S' : 'R') + (i + 1) + ' ¥' + fmt2(+x.level) + '</span></button>').join('');
  }

  _fitRange(){
    const bars = this.rangeN > 0 ? Math.min(this.N, this.rangeN) : this.N;
    this.slot = (this.px1 - this.px0) / Math.max(1, bars);
    this.viewStart = Math.max(0, this.N - bars);
  }

  _startLoop(){
    if(this._loopOn) return;
    this._loopOn = true;
    const tick = () => {
      if(!this._loopOn) return;
      const need = (this._bandAnim != null) || (this._yAnim != null) || (this._growAnim != null) || (!this.pinned && this.N >= 2);
      if(need) this._redrawCanvas();
      if(this._bandAnim != null || this._yAnim != null || this._growAnim != null || (!this.pinned && this.N >= 2)){
        requestAnimationFrame(tick);
      } else {
        this._loopOn = false;
      }
    };
    requestAnimationFrame(tick);
  }

  resize(){
    this.layout();
    if(this.N < 2){ this.draw(); return; }
    const bars = Math.max(10, Math.min(this.N, this.barsPerView()));
    this.slot = (this.px1 - this.px0) / bars;
    this._clampView();
    this._resetYShift();
    this.draw();
    this._updateChartInfo();
  }
}
