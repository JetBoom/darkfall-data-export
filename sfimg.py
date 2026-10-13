"""Pure python (stdlib only) image helpers: DDS (DXT1/3/5/uncompressed), BMP and TGA -> PNG."""
import struct
import zlib


def write_png(w, h, rgba):
    """rgba: bytes/bytearray of w*h*4. Writes RGB when fully opaque."""
    opaque = all(a == 255 for a in rgba[3::4])
    ch = 3 if opaque else 4
    raw = bytearray()
    stride = w * 4
    for y in range(h):
        row = rgba[y * stride:(y + 1) * stride]
        raw.append(0)
        if opaque:
            raw += _strip_alpha(row)
        else:
            raw += row

    def chunk(t, data):
        c = struct.pack('>I', len(data)) + t + data
        return c + struct.pack('>I', zlib.crc32(t + data) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2 if ch == 3 else 6, 0, 0, 0)) +
            chunk(b'IDAT', zlib.compress(bytes(raw), 6)) + chunk(b'IEND', b''))


def _strip_alpha(row):
    out = bytearray(len(row) // 4 * 3)
    out[0::3] = row[0::4]
    out[1::3] = row[1::4]
    out[2::3] = row[2::4]
    return out


def _c565(c):
    r = (c >> 11) & 31
    g = (c >> 5) & 63
    b = c & 31
    return ((r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2))


def _decode_dxt(data, off, w, h, fmt):
    """returns bytearray RGBA w*h*4"""
    out = bytearray(w * h * 4)
    bw, bh = max(1, (w + 3) // 4), max(1, (h + 3) // 4)
    bsz = 8 if fmt == 1 else 16
    p = off
    for by in range(bh):
        for bx in range(bw):
            blk = data[p:p + bsz]
            p += bsz
            if len(blk) < bsz:
                continue
            alpha = None
            if fmt == 3:
                a64, = struct.unpack_from('<Q', blk, 0)
                alpha = [((a64 >> (4 * i)) & 15) * 17 for i in range(16)]
            elif fmt == 5:
                a0, a1 = blk[0], blk[1]
                if a0 > a1:
                    pal = [a0, a1] + [((7 - i) * a0 + i * a1) // 7 for i in range(1, 7)]
                else:
                    pal = [a0, a1] + [((5 - i) * a0 + i * a1) // 5 for i in range(1, 5)] + [0, 255]
                bits = int.from_bytes(blk[2:8], 'little')
                alpha = [pal[(bits >> (3 * i)) & 7] for i in range(16)]
            c0, c1, bits = struct.unpack_from('<HHI', blk, bsz - 8)
            r0, g0, b0 = _c565(c0)
            r1, g1, b1 = _c565(c1)
            if c0 > c1 or fmt != 1:
                pal = [(r0, g0, b0, 255), (r1, g1, b1, 255),
                       ((2 * r0 + r1) // 3, (2 * g0 + g1) // 3, (2 * b0 + b1) // 3, 255),
                       ((r0 + 2 * r1) // 3, (g0 + 2 * g1) // 3, (b0 + 2 * b1) // 3, 255)]
            else:
                pal = [(r0, g0, b0, 255), (r1, g1, b1, 255),
                       ((r0 + r1) // 2, (g0 + g1) // 2, (b0 + b1) // 2, 255), (0, 0, 0, 0)]
            for i in range(16):
                x = bx * 4 + (i & 3)
                y = by * 4 + (i >> 2)
                if x >= w or y >= h:
                    continue
                px = pal[(bits >> (2 * i)) & 3]
                o = (y * w + x) * 4
                out[o] = px[0]
                out[o + 1] = px[1]
                out[o + 2] = px[2]
                out[o + 3] = alpha[i] if alpha else px[3]
    return out


def dds_to_png(data, max_size=512):
    """Decode a DDS to PNG bytes, picking the largest mip <= max_size. Returns (png, w, h)."""
    if data[:4] != b'DDS ':
        raise ValueError('not a dds')
    h, w, pitch, depth, mips = struct.unpack_from('<5I', data, 12)
    mips = max(mips, 1)
    pf_flags, fourcc = struct.unpack_from('<I4s', data, 80)
    bpp, rm, gm, bm, am = struct.unpack_from('<5I', data, 88)
    off = 128
    level = 0
    cw, ch = w, h
    while max(cw, ch) > max_size and level < mips - 1:
        off += _level_size(cw, ch, fourcc, pf_flags, bpp)
        cw, ch = max(1, cw // 2), max(1, ch // 2)
        level += 1
    if pf_flags & 4:
        fmt = {b'DXT1': 1, b'DXT3': 3, b'DXT5': 5, b'DXT2': 3, b'DXT4': 5}.get(fourcc)
        if fmt is None:
            raise ValueError('unsupported fourcc %r' % fourcc)
        rgba = _decode_dxt(data, off, cw, ch, fmt)
    else:
        if bpp != 32:
            raise ValueError('unsupported dds rgb bpp %d' % bpp)
        rgba = bytearray(cw * ch * 4)
        for i in range(cw * ch):
            v, = struct.unpack_from('<I', data, off + 4 * i)
            rgba[4 * i] = (v & rm) >> (rm & -rm).bit_length() - 1 if rm else 0
            rgba[4 * i + 1] = (v & gm) >> (gm & -gm).bit_length() - 1 if gm else 0
            rgba[4 * i + 2] = (v & bm) >> (bm & -bm).bit_length() - 1 if bm else 0
            rgba[4 * i + 3] = ((v & am) >> (am & -am).bit_length() - 1) if am else 255
    return write_png(cw, ch, rgba), cw, ch


def _level_size(w, h, fourcc, pf_flags, bpp):
    if pf_flags & 4:
        return max(1, (w + 3) // 4) * max(1, (h + 3) // 4) * (8 if fourcc == b'DXT1' else 16)
    return w * h * bpp // 8


def bmp_to_png(data):
    if data[:2] != b'BM':
        raise ValueError('not a bmp')
    off, = struct.unpack_from('<I', data, 10)
    hsz, w, h, planes, bpp, comp = struct.unpack_from('<IiiHHI', data, 14)
    top_down = h < 0
    h = abs(h)
    if comp not in (0, 3) or bpp not in (24, 32, 8):
        raise ValueError('unsupported bmp (bpp=%d comp=%d)' % (bpp, comp))
    pal = None
    if bpp == 8:
        ncol = struct.unpack_from('<I', data, 46)[0] or 256
        pal = [data[14 + hsz + 4 * i:14 + hsz + 4 * i + 3][::-1] for i in range(ncol)]
    rowsize = (w * bpp + 31) // 32 * 4
    rgba = bytearray(w * h * 4)
    for y in range(h):
        sy = y if top_down else h - 1 - y
        row = data[off + sy * rowsize: off + (sy + 1) * rowsize]
        for x in range(w):
            if bpp == 8:
                r, g, b = pal[row[x]]
                a = 255
            else:
                b, g, r = row[x * bpp // 8], row[x * bpp // 8 + 1], row[x * bpp // 8 + 2]
                a = row[x * 4 + 3] if bpp == 32 else 255
            o = (y * w + x) * 4
            rgba[o:o + 4] = bytes((r, g, b, a))
    return write_png(w, h, rgba), w, h


def tga_to_png(data):
    idlen, cmap, itype = data[0], data[1], data[2]
    w, h = struct.unpack_from('<HH', data, 12)
    bpp, desc = data[16], data[17]
    if cmap or itype not in (2, 10) or bpp not in (24, 32):
        raise ValueError('unsupported tga')
    p = 18 + idlen
    n = bpp // 8
    px = bytearray()
    if itype == 2:
        px = data[p:p + w * h * n]
    else:
        while len(px) < w * h * n:
            c = data[p]
            p += 1
            cnt = (c & 127) + 1
            if c & 128:
                px += data[p:p + n] * cnt
                p += n
            else:
                px += data[p:p + n * cnt]
                p += n * cnt
    rgba = bytearray(w * h * 4)
    for y in range(h):
        sy = y if desc & 0x20 else h - 1 - y
        for x in range(w):
            i = (sy * w + x) * n
            o = (y * w + x) * 4
            rgba[o:o + 4] = bytes((px[i + 2], px[i + 1], px[i], px[i + 3] if n == 4 else 255))
    return write_png(w, h, rgba), w, h


def dds_average_color(data):
    """average RGBA of a DDS (decodes the smallest mip level) -> (r, g, b, a) 0..255"""
    return _avg_from_dds(data)


def _avg_from_dds(data):
    h, w, pitch, depth, mips = struct.unpack_from('<5I', data, 12)
    mips = max(mips, 1)
    pf_flags, fourcc = struct.unpack_from('<I4s', data, 80)
    bpp = struct.unpack_from('<I', data, 88)[0]
    off, cw, ch = 128, w, h
    for _ in range(mips - 1):
        if cw <= 4 and ch <= 4:
            break
        off += _level_size(cw, ch, fourcc, pf_flags, bpp)
        cw, ch = max(1, cw // 2), max(1, ch // 2)
    fmt = {b'DXT1': 1, b'DXT3': 3, b'DXT5': 5}.get(fourcc)
    if not (pf_flags & 4) or fmt is None:
        raise ValueError('unsupported dds for average color')
    px = _decode_dxt(data, off, cw, ch, fmt)
    n = cw * ch
    return tuple(sum(px[i::4]) // n for i in range(4))
