"""Parsers for Spellbook/Darkfall (Unholy Wars / Rise of Agon) binary asset formats.

Everything is little endian. Formats handled:

  .sfm   SFME  static mesh (D3D9 style vertex declaration, 16/32 bit indices, submeshes)
  .sfc   AABB tree collision scheme (BVH over the triangles of the matching .sfm / .ter)
  .lvl   SFLV  level: list of placed objects (xml path, position, euler rotation)
  .ter   SFTE  terrain tile
"""
import re
import struct

# D3DDECLTYPE -> (struct format, component count)
DECL_TYPES = {
    0: ('f', 1), 1: ('f', 2), 2: ('f', 3), 3: ('f', 4),
    4: ('4B', 4),           # D3DCOLOR
    5: ('4B', 4),           # UBYTE4
    6: ('2h', 2), 7: ('4h', 4),
    8: ('4B', 4),           # UBYTE4N
    9: ('2h', 2), 10: ('4h', 4),
    11: ('2H', 2), 12: ('4H', 4),
    15: ('2e', 2), 16: ('4e', 4),
}
DECL_TYPE_SIZE = {0: 4, 1: 8, 2: 12, 3: 16, 4: 4, 5: 4, 6: 4, 7: 8, 8: 4, 9: 4,
                  10: 8, 11: 4, 12: 8, 15: 4, 16: 8}
USAGE = {0: 'position', 1: 'blendweight', 2: 'blendindices', 3: 'normal', 4: 'psize',
         5: 'texcoord', 6: 'tangent', 7: 'binormal', 8: 'tessfactor', 9: 'positiont',
         10: 'color', 11: 'fog', 12: 'depth', 13: 'sample'}

IMG_EXT = ('.bmp', '.dds', '.tga', '.png', '.jpg', '.psd')


class SfmError(Exception):
    pass


class Submesh:
    __slots__ = ('tex', 'first_face', 'face_count', 'first_vert', 'vert_count', 'name', 'textures', 'palette')

    def __repr__(self):
        return 'Submesh(%s)' % ', '.join('%s=%r' % (k, getattr(self, k, None)) for k in self.__slots__)


class Sfm:
    """Parsed static mesh.

    positions: list of (x,y,z); normals; uvs: list of (u,v) (first texcoord set), uvs2 optional;
    indices: flat list of triangle indices (global vertex indices);
    submeshes: list of Submesh with face/vertex ranges (indices in each submesh are *global*
    unless `local_indices` is True).
    """

    def __repr__(self):
        return 'Sfm(verts=%d, tris=%d, subs=%d)' % (len(self.positions), len(self.indices) // 3, len(self.submeshes))


def _find_decl(d, start, stride):
    """Find vertex declaration terminator (D3DDECL_END) at/after start, walk backwards over
    8 byte elements. Returns (elements, vertex_data_offset)."""
    end_pat = b'\xff\x00\x00\x00\x11\x00\x00\x00'
    pos = start
    while True:
        i = d.find(end_pat, pos)
        if i < 0:
            raise SfmError('no vertex declaration terminator')
        elems = []
        j = i - 8
        while j >= start:
            stream, off, typ, meth, usage, idx = struct.unpack_from('<HHBBBB', d, j)
            if stream != 0 or typ not in DECL_TYPE_SIZE or usage > 13 or off + DECL_TYPE_SIZE[typ] > stride:
                break
            elems.append((off, typ, usage, idx))
            j -= 8
        elems.reverse()
        if elems and elems[0][0] == 0:
            return elems, i + 8
        pos = i + 1


def parse_sfm(d):
    animated = d[:4] == b'SFAM'
    if d[:4] != b'SFME' and not animated:
        raise SfmError('bad magic')
    ver, vcount, icount, kind, unk, stride, ibits, unk2, nsub, nmap = struct.unpack_from('<10I', d, 4)
    if ibits not in (16, 32):
        raise SfmError('bad index bits %d' % ibits)
    m = Sfm()
    m.version = ver
    m.kind = kind
    m.stride = stride
    m.header = (ver, vcount, icount, kind, unk, stride, ibits, unk2, nsub, nmap)
    # submesh records. first one is at 0x60
    if animated:
        return _parse_sfam(d, m)
    subs = []
    pos = 0x60
    ff = fv = 0
    prev_t = -1
    for n in range(nsub):
        if n > 0:
            # find next record: tex index == n, first_face == ff, first_vert == fv
            found = -1
            for p in range(pos, min(len(d) - 24, pos + 400)):
                t, a, b, c, e, nl = struct.unpack_from('<6I', d, p)
                if a == ff and c == fv and nl < 256 and b > 0 and e > 0:
                    found = p
                    break
            if found < 0:
                raise SfmError('submesh %d record not found' % n)
            rec_end_prev = pos
            pos = found
            # trailer of previous submesh = d[rec_end_prev:pos]
            subs[-1].textures += _strings(d[rec_end_prev:pos])
        t, a, b, c, e, nl = struct.unpack_from('<6I', d, pos)
        if a != ff or c != fv or nl > 256:
            raise SfmError('bad submesh record %d (%r)' % (n, (t, a, b, c, e, nl)))
        last_rec = pos
        prev_t = t
        s = Submesh()
        s.tex, s.first_face, s.face_count, s.first_vert, s.vert_count = t, a, b, c, e
        s.name = d[pos + 24:pos + 24 + nl].split(b'\0')[0].decode('latin1')
        s.textures = [s.name]
        subs.append(s)
        ff += b
        fv += e
        pos = pos + 24 + nl
    m.submeshes = subs
    if ff * 3 != icount or fv != vcount:
        # some files have icount in faces already
        if not (ff == icount and fv == vcount):
            raise SfmError('submesh totals mismatch faces=%d icount=%d verts=%d vcount=%d' % (ff, icount, fv, vcount))
    # a nameless last submesh has no trailer: its (zero) name length doubles as the first decl element
    elems, vpos = _find_decl(d, last_rec + 20, stride)
    if subs:
        subs[-1].textures += _strings(d[pos:max(pos, vpos - 8 * (len(elems) + 1))])
    m.decl = elems
    _read_geometry(d, m, elems, vpos, vcount, ff, ibits, stride)
    return m


def _read_geometry(d, m, elems, vpos, vcount, ntri, ibits, stride):
    """vertex + index buffers (shared by .sfm and .sfam). Skinned meshes also get m.weights
    (4 floats per vertex) and m.joints (4 bone indices per vertex)."""
    isz = ibits // 8
    need = vpos + vcount * stride + ntri * 3 * isz
    if need > len(d):
        raise SfmError('truncated file (need %d have %d)' % (need, len(d)))
    pos_o = nrm_o = bw_o = bi_o = None
    uvs_o = []
    for off, typ, usage, idx in elems:
        if usage == 0 and idx == 0:
            pos_o = off
        elif usage == 3 and idx == 0:
            nrm_o = (off, typ)
        elif usage == 5:
            uvs_o.append((off, typ))
        elif usage == 1:
            bw_o = (off, typ)
        elif usage == 2:
            bi_o = (off, typ)
    if pos_o is None:
        raise SfmError('no position element')
    P, N, UV, UV2, W, J = [], [], [], [], [], []
    u = struct.Struct('<3f').unpack_from
    u2 = struct.Struct('<2f').unpack_from
    for i in range(vcount):
        b = vpos + i * stride
        P.append(u(d, b + pos_o))
        if nrm_o and nrm_o[1] == 2:
            N.append(u(d, b + nrm_o[0]))
        if uvs_o and uvs_o[0][1] == 1:
            UV.append(u2(d, b + uvs_o[0][0]))
        if len(uvs_o) > 1 and uvs_o[1][1] == 1:
            UV2.append(u2(d, b + uvs_o[1][0]))
        if bw_o:
            off, typ = bw_o
            if typ == 3:
                w = struct.unpack_from('<4f', d, b + off)
            elif typ == 2:
                w = struct.unpack_from('<3f', d, b + off)
                w = w + (max(0.0, 1.0 - sum(w)),)
            elif typ == 1:
                w = struct.unpack_from('<2f', d, b + off)
                w = w + (0.0, max(0.0, 1.0 - sum(w)))
            else:
                w = tuple(x / 255.0 for x in d[b + off:b + off + 4])
            W.append(w)
        if bi_o:
            J.append(tuple(d[b + bi_o[0]:b + bi_o[0] + 4]))
    m.positions, m.normals, m.uvs, m.uvs2 = P, N, UV, UV2
    m.weights, m.joints = W, J
    ipos = vpos + vcount * stride
    m.indices = list(struct.unpack_from('<%d%s' % (ntri * 3, 'H' if ibits == 16 else 'I'), d, ipos))
    m.vertex_offset = vpos
    m.index_end = ipos + ntri * 3 * isz
    m.raw_vertex = d[vpos:vpos + vcount * stride]


def _parse_sfam(d, m):
    """Skinned mesh. Layout: header + materials (like .sfm, but the material records are not
    reliable), vertex decl, vertices (pos, blend weights, blend indices, normal, uv), indices, then
    a trailer:

        u32 2, 6, ?, ?, n_sections, n_bones
        n_sections * { flag, idx, first_face, face_count, first_vert, vert_count, palette_count,
                       palette_count * (palette_index, bone_index) }
        n_bones * 100 byte bone records (see parse_bones)

    Vertex blend indices refer to the *palette of the section* the vertex belongs to.
    """
    ver, vcount, icount, kind, unk, stride, ibits, unk2, nsub, nmap = m.header
    elems, vpos = _find_decl(d, 0x60, stride)
    texs = _strings(d[0x60:vpos])
    m.decl = elems
    _read_geometry(d, m, elems, vpos, vcount, icount // 3, ibits, stride)
    m.trailer = d[m.index_end:]
    m.trailer_offset = m.index_end
    t = m.trailer
    h = struct.unpack_from('<7I', t, 0)
    nsec, nbones = h[4], h[5]
    p = 24
    subs = []
    for k in range(nsec):
        flag, idx, ff, fc, fv, vc, pc = struct.unpack_from('<7I', t, p)
        p += 28
        pal = {}
        for i in range(pc):
            a, b = struct.unpack_from('<2I', t, p + 8 * i)
            pal[a] = b
        p += 8 * pc
        s = Submesh()
        s.tex, s.first_face, s.face_count, s.first_vert, s.vert_count = idx, ff, fc, fv, vc
        s.palette = [pal.get(i, 0) for i in range(pc)]
        s.textures = [texs[min(k, len(texs) - 1)]] if texs else []
        s.name = s.textures[0] if s.textures else ''
        subs.append(s)
    m.submeshes = subs
    m.bones = parse_bones(t[p:])
    m.bone_count = nbones
    return m


def parse_bones(t):
    """Bones in the trailer of an .sfam. Each record is 100 bytes: a null terminated name plus
    unused (memory dump) pointers, then u32 flag, u32 index, u32 parent_index and the local bind
    pose as translation (3 floats) + rotation quaternion (x y z w). Returns list ordered by index."""
    bones = {}
    p = 0
    n = len(t)
    while p + 100 <= n:
        c = t[p]
        if (65 <= c <= 90 or 97 <= c <= 122) :
            e = t.find(b'\0', p, p + 48)
            name = t[p:e] if e > 0 else b''
            if e > 0 and len(name) >= 2 and all(32 < x < 127 for x in name):
                flag, idx, par = struct.unpack_from('<3I', t, p + 60)
                v = struct.unpack_from('<7f', t, p + 72)
                ql = sum(x * x for x in v[3:])
                if idx < 512 and par < 512 and abs(ql - 1) < 0.01 and all(abs(x) < 1e5 for x in v[:3]):
                    bones[idx] = dict(name=name.decode('latin1'), index=idx, parent=par if idx else -1,
                                      t=v[:3], q=v[3:])
                    p += 100
                    continue
        p += 1
    return [bones[i] for i in sorted(bones)]


def _strings(b):
    out = []
    for s in re.findall(rb'[\x20-\x7e]{4,}', b):
        s = s.decode('latin1')
        if s.lower().endswith(IMG_EXT):
            out.append(s)
    return out


# ------------------------------------------------------------------ collision (.sfc)
class Sfc:
    pass


SFC_KINDS = {0x0c: 'aabbtree', 0x2c: 'aabbtree_geometry', 0x02: 'sphere', 0x0b: 'spheres',
             0x0d: 'obb', 0x0e: 'convexhulls'}


def parse_sfc(d):
    """Collision schemes. 3 byte header `c5 <kind> 00`, then by kind:

    0x0c aabbtree: u32 node_count, nodes (min xyz, max xyz floats, u32 a, u32 b) * n,
        u32 tri_count, tri_count * u32 `tri_order`.
        Node: b == 0 -> interior, children are nodes a and a+1; b > 0 -> leaf holding b triangles,
        tri_order[a:a+b] are *offsets into the index buffer* (first index of each triangle) of the
        mesh (.sfm / .ter) with the same name. The root box equals the mesh bounds.
    0x2c aabbtree_geometry: same, followed by its own geometry: u32 n_idx, idx*u32, u32 n_vert,
        vert*3 floats, u32 n_idx, per-triangle neighbour offsets (adjacency, 3 per triangle).
    0x02 sphere: x y z radius.   0x0b spheres: u32 count, count * (x y z radius).
    0x0d obb: center(3) axes(9) half extents(3) floats.
    0x0e convexhulls: not decoded (raw kept).
    """
    if d[0] != 0xc5 or d[2] != 0:
        raise ValueError('bad sfc prefix')
    s = Sfc()
    s.kind = SFC_KINDS.get(d[1], 'unknown_%02x' % d[1])
    s.trailing = 0
    if s.kind in ('aabbtree', 'aabbtree_geometry'):
        n, = struct.unpack_from('<I', d, 3)
        s.nodes = [struct.unpack_from('<6f2I', d, 7 + 32 * i) for i in range(n)]
        p = 7 + 32 * n
        t, = struct.unpack_from('<I', d, p)
        s.tri_order = list(struct.unpack_from('<%dI' % t, d, p + 4))
        p += 4 + 4 * t
        if s.kind == 'aabbtree_geometry':
            ni, = struct.unpack_from('<I', d, p)
            s.indices = list(struct.unpack_from('<%dI' % ni, d, p + 4))
            p += 4 + 4 * ni
            nv, = struct.unpack_from('<I', d, p)
            s.positions = [struct.unpack_from('<3f', d, p + 4 + 12 * i) for i in range(nv)]
            p += 4 + 12 * nv
            na, = struct.unpack_from('<I', d, p)
            s.adjacency = list(struct.unpack_from('<%dI' % na, d, p + 4))
            p += 4 + 4 * na
        s.trailing = len(d) - p
    elif s.kind == 'sphere':
        s.spheres = [struct.unpack_from('<4f', d, 3)]
    elif s.kind == 'spheres':
        n, = struct.unpack_from('<I', d, 3)
        s.spheres = [struct.unpack_from('<4f', d, 7 + 16 * i) for i in range(n)]
    elif s.kind == 'obb':
        s.obb = struct.unpack_from('<15f', d, 3)
    else:
        s.raw = d[3:]
    return s


# ------------------------------------------------------------------ level (.lvl)
def parse_lvl(d, id_to_path=None):
    """Level file. Version 2 stores the xml path inline; version 1 only stores the resource id of
    the xml (resolve it using the `ID:` column of file.lst, see load_id_map)."""
    if d[:4] != b'SFLV':
        raise ValueError('bad magic')
    ver, = struct.unpack_from('<I', d, 4)
    hdr = struct.unpack_from('<4f', d, 8)
    count, = struct.unpack_from('<I', d, 24)
    objs = []
    p = 28
    for i in range(count):
        oid, typ = struct.unpack_from('<HH', d, p)
        flags = d[p + 4:p + 9]
        x, y, z, rx, ry, rz = struct.unpack_from('<6f', d, p + 9)
        extra, = struct.unpack_from('<I', d, p + 33)
        o = dict(id=oid, type=typ, flags=flags.hex(), pos=(x, y, z), rot=(rx, ry, rz), res=extra)
        if ver >= 2:
            ln, = struct.unpack_from('<I', d, p + 37)
            o['xml'] = d[p + 41:p + 41 + ln].split(b'\0')[0].decode('latin1')
            p += 41 + ln
        else:
            p += 37
            o['xml'] = id_to_path.get(extra) if id_to_path else None
        objs.append(o)
    return dict(version=ver, header=hdr, count=count, objects=objs, trailing=len(d) - p, tail_offset=p)


def load_id_map(file_lst):
    """file.lst written by dfextract -> {resource id: path}"""
    m = {}
    for line in open(file_lst, encoding='utf-8'):
        mm = re.match(r"'(.*)' ID:(\d+) ", line)
        if mm:
            m[int(mm.group(2))] = mm.group(1)
    return m
