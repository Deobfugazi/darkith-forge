#!/usr/bin/env python3
"""Pure-Python zipalign fallback — for Termux, where no zipalign package exists.

Aligns each STORED entry's data to a multiple of ALIGN by extending the local
header's extra field with zero bytes (exactly what the reference tool does;
deflated entries need no alignment). Rewrites local headers + central directory.
Usage: zipalign.py <in.apk> <out.apk> [align]   |   zipalign.py -c <align> <in.apk>
"""
import struct, sys

LFH = b'PK\x03\x04'; CDH = b'PK\x01\x02'; EOCD = b'PK\x05\x06'

def _u32(d,o): return struct.unpack_from('<I', d, o)[0]

def _find_cd(d):
    return _u32(d, d.rfind(EOCD)+16)

def zipalign(data, align=4):
    cd_off = _find_cd(data)
    out = bytearray(data[:cd_off])          # local section, rewritten in place
    entries = []
    off = 0
    while out[off:off+4] == LFH:
        (ver,flags,meth,mt,md,crc,csz,usz,nl,el) = struct.unpack_from('<HHHHHIIIHH', out, off+4)
        lh_off = off
        data_off = off + 30 + nl + el
        pad = 0
        if meth == 0:                        # STORED only
            pad = (-data_off) % align
        if pad:
            new_extra = bytes(el + pad)      # zeros
            struct.pack_into('<H', out, off+28, el+pad)
            out[data_off:data_off] = new_extra
            data_off += pad
        entries.append(dict(name_off=off+30, nl=nl, lh_off=lh_off, cd_extra=el))
        off = data_off + csz
    # central directory: local-header offsets change; EOCD cdoff shifts by total pad
    total_pad = len(out) - cd_off
    cd = bytearray(data[cd_off:])
    coff = 0
    for e in entries:
        struct.pack_into('<I', cd, coff+42, e['lh_off'])
        coff += 46 + e['nl'] + struct.unpack_from('<H', cd, coff+30)[0] \
                + struct.unpack_from('<H', cd, coff+32)[0]
    eocd = cd.rfind(EOCD)
    struct.pack_into('<I', cd, eocd+16, cd_off + total_pad)
    return bytes(out) + bytes(cd)

def check(data, align=4):
    off = 0; bad = 0; n = 0
    while data[off:off+4] == LFH:
        (ver,flags,meth,mt,md,crc,csz,usz,nl,el) = struct.unpack_from('<HHHHHIIIHH', data, off+4)
        if meth == 0:
            n += 1
            if (off+30+nl+el) % align: bad += 1
        off += 30 + nl + el + csz
    return n, bad

if __name__ == '__main__':
    if len(sys.argv) == 4 and sys.argv[1] == '-c':
        align = int(sys.argv[2]); d = open(sys.argv[3],'rb').read()
        n, bad = check(d, align)
        print("Verification %s" % ("succesful" if bad == 0 else "FAILED"))
        sys.exit(0 if bad == 0 else 1)
    if len(sys.argv) < 3:
        sys.exit("usage: zipalign.py <in> <out> [align] | zipalign.py -c <align> <in>")
    align = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    open(sys.argv[2],'wb').write(zipalign(open(sys.argv[1],'rb').read(), align))
    print("aligned %s -> %s (align %d)" % (sys.argv[1], sys.argv[2], align))
