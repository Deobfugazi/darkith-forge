/* Raw DEFLATE (RFC 1951) + gzip wrapper (RFC 1952) decoder.
   Written for this reader so the corpus opens in any browser, including
   engines without DecompressionStream (older Safari, some Android WebViews).
   Bit reader is LSB-first, as the format requires. */
var Inflate = (function () {
  "use strict";

  var LEN_BASE = [3,4,5,6,7,8,9,10,11,13,15,17,19,23,27,31,35,43,51,59,67,83,99,115,131,163,195,227,258];
  var LEN_EXTRA = [0,0,0,0,0,0,0,0,1,1,1,1,2,2,2,2,3,3,3,3,4,4,4,4,5,5,5,5,0];
  var DIST_BASE = [1,2,3,4,5,7,9,13,17,25,33,49,65,97,129,193,257,385,513,769,1025,1537,2049,3073,
                   4097,6145,8193,12289,16385,24577];
  var DIST_EXTRA = [0,0,0,0,1,1,2,2,3,3,4,4,5,5,6,6,7,7,8,8,9,9,10,10,11,11,12,12,13,13];
  var CL_ORDER = [16,17,18,0,8,7,9,6,10,5,11,4,12,3,13,2,14,1,15];

  function Huffman(lengths) {
    var counts = new Uint16Array(16), offs = new Uint16Array(16), symbols = new Uint16Array(lengths.length);
    var i, left = 0;
    for (i = 0; i < lengths.length; i++) counts[lengths[i]]++;
    counts[0] = 0;
    for (i = 1; i < 16; i++) { offs[i] = left; left += counts[i]; }
    for (i = 0; i < lengths.length; i++) if (lengths[i]) symbols[offs[lengths[i]]++] = i;
    this.counts = counts; this.symbols = symbols;
  }

  function Buf(size) { this.b = new Uint8Array(size || 1 << 20); this.n = 0; }
  Buf.prototype.ensure = function (extra) {
    if (this.n + extra <= this.b.length) return;
    var want = this.b.length * 2;
    while (want < this.n + extra) want *= 2;
    var nb = new Uint8Array(want); nb.set(this.b.subarray(0, this.n)); this.b = nb;
  };
  Buf.prototype.push = function (byte) { this.ensure(1); this.b[this.n++] = byte; };
  Buf.prototype.extend = function (dist, len) {
    this.ensure(len);
    var b = this.b, src = this.n - dist;
    for (var i = 0; i < len; i++) b[this.n++] = b[src + i];
  };

  function inflateRaw(data, start) {
    var pos = start || 0, bitbuf = 0, bitcnt = 0;
    var out = new Buf(Math.max(1 << 16, data.length * 4));
    var fixedLit = null, fixedDist = null;

    function need(n) {
      while (bitcnt < n) {
        if (pos >= data.length) throw new Error("inflate: input exhausted");
        bitbuf |= data[pos++] << bitcnt;
        bitcnt += 8;
      }
    }
    function bits(n) {
      if (n === 0) return 0;
      need(n);
      var v = bitbuf & ((1 << n) - 1);
      bitbuf >>>= n; bitcnt -= n;
      return v;
    }
    function decode(h) {
      var code = 0, first = 0, index = 0;
      for (var len = 1; len < 16; len++) {
        code |= bits(1);
        var count = h.counts[len];
        if (code - first < count) return h.symbols[index + (code - first)];
        index += count; first += count; first <<= 1; code <<= 1;
      }
      throw new Error("inflate: bad huffman code");
    }
    function buildFixed() {
      var l = new Uint8Array(288), i;
      for (i = 0; i < 144; i++) l[i] = 8;
      for (; i < 256; i++) l[i] = 9;
      for (; i < 280; i++) l[i] = 7;
      for (; i < 288; i++) l[i] = 8;
      fixedLit = new Huffman(l);
      var d = new Uint8Array(30);
      for (i = 0; i < 30; i++) d[i] = 5;
      fixedDist = new Huffman(d);
    }

    var last = 0;
    while (!last) {
      last = bits(1);
      var type = bits(2);
      if (type === 0) {
        bitbuf = 0; bitcnt = 0;
        if (pos + 4 > data.length) throw new Error("inflate: truncated stored block");
        var len = data[pos] | (data[pos + 1] << 8);
        var nlen = data[pos + 2] | (data[pos + 3] << 8);
        pos += 4;
        if ((len ^ 0xffff) !== nlen) throw new Error("inflate: stored length mismatch");
        if (pos + len > data.length) throw new Error("inflate: truncated stored data");
        out.ensure(len);
        out.b.set(data.subarray(pos, pos + len), out.n);
        out.n += len; pos += len;
        continue;
      }
      var lit, dist;
      if (type === 1) {
        if (!fixedLit) buildFixed();
        lit = fixedLit; dist = fixedDist;
      } else if (type === 2) {
        var hlit = bits(5) + 257, hdist = bits(5) + 1, hclen = bits(4) + 4;
        var clens = new Uint8Array(19), i;
        for (i = 0; i < hclen; i++) clens[CL_ORDER[i]] = bits(3);
        var clh = new Huffman(clens);
        var lens = new Uint8Array(hlit + hdist), idx = 0;
        while (idx < hlit + hdist) {
          var sym = decode(clh);
          if (sym < 16) { lens[idx++] = sym; continue; }
          var rep, val = 0;
          if (sym === 16) {
            if (idx === 0) throw new Error("inflate: repeat with no previous length");
            val = lens[idx - 1]; rep = 3 + bits(2);
          } else if (sym === 17) rep = 3 + bits(3);
          else rep = 11 + bits(7);
          if (idx + rep > hlit + hdist) throw new Error("inflate: length overflow");
          while (rep--) lens[idx++] = val;
        }
        lit = new Huffman(lens.subarray(0, hlit));
        dist = new Huffman(lens.subarray(hlit));
      } else {
        throw new Error("inflate: bad block type " + type);
      }
      for (;;) {
        var s = decode(lit);
        if (s < 256) { out.push(s); continue; }
        if (s === 256) break;
        s -= 257;
        if (s >= 29) throw new Error("inflate: bad length symbol");
        var length = LEN_BASE[s] + bits(LEN_EXTRA[s]);
        var ds = decode(dist);
        if (ds >= 30) throw new Error("inflate: bad distance symbol");
        var distance = DIST_BASE[ds] + bits(DIST_EXTRA[ds]);
        if (distance > out.n) throw new Error("inflate: distance beyond output");
        out.extend(distance, length);
      }
    }
    return out.b.subarray(0, out.n);
  }

  function gunzip(data) {
    if (data.length < 18 || data[0] !== 0x1f || data[1] !== 0x8b) throw new Error("gunzip: not gzip");
    if (data[2] !== 8) throw new Error("gunzip: unsupported method");
    var flg = data[3], p = 10;
    if (flg & 4) p += 2 + (data[p] | (data[p + 1] << 8));
    if (flg & 8) { while (p < data.length && data[p] !== 0) p++; p++; }
    if (flg & 16) { while (p < data.length && data[p] !== 0) p++; p++; }
    if (flg & 2) p += 2;
    return inflateRaw(data, p);
  }

  function utf8(bytes) {
    if (typeof TextDecoder !== "undefined") return new TextDecoder("utf-8").decode(bytes);
    var s = "", i = 0;
    while (i < bytes.length) {
      var c = bytes[i++];
      if (c < 0x80) s += String.fromCharCode(c);
      else if (c < 0xe0) s += String.fromCharCode(((c & 0x1f) << 6) | (bytes[i++] & 0x3f));
      else if (c < 0xf0) s += String.fromCharCode(((c & 0x0f) << 12) | ((bytes[i++] & 0x3f) << 6) | (bytes[i++] & 0x3f));
      else {
        var cp = ((c & 0x07) << 18) | ((bytes[i++] & 0x3f) << 12) | ((bytes[i++] & 0x3f) << 6) | (bytes[i++] & 0x3f);
        cp -= 0x10000;
        s += String.fromCharCode(0xd800 + (cp >> 10), 0xdc00 + (cp & 0x3ff));
      }
    }
    return s;
  }

  return { raw: inflateRaw, gunzip: gunzip, utf8: utf8 };
})();
if (typeof module !== "undefined" && module.exports) module.exports = Inflate;
