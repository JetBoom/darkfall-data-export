#!/usr/bin/env python3
"""Convert extracted Darkfall: Unholy Wars / Rise of Agon assets (output of dfextract_3.py) to
glTF binary (.glb), PNG and JSON. Python 3 stdlib only.

  python3 sfexport.py models    SRC OUT [--limit N] [--name SUBSTR]   .sfm  -> OUT/models/*.glb
  python3 sfexport.py terrain   SRC OUT                               .ter  -> OUT/terrain/*.glb
  python3 sfexport.py collision SRC OUT                               .sfc  -> OUT/collision/*.glb (+ bvh/*.json)
  python3 sfexport.py animated  SRC OUT                               .sfam -> OUT/animated/*.glb (skinned, bind pose)
  python3 sfexport.py maps      SRC OUT [--name SUBSTR]               .lvl  -> OUT/maps/*.json (+ *.glb)

SRC is the directory dfextract_3.py wrote to (contains mesh/, texture/, level/, xml/, file.lst ...).

Coordinates: the game uses a left handed, Y-up system. GLBs are converted to glTF's right handed
Y-up by negating Z (and flipping triangle winding). The JSON files keep the *original* game
coordinates.
"""
import argparse
import array
import json
import math
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sfimg  # noqa: E402
import sflib  # noqa: E402


# ---------------------------------------------------------------- source tree helpers
class Src:
    def __init__(self, root):
        self.root = root
        self._tex_index = None
        self._xml_cache = {}
        self.ids = sflib.load_id_map(os.path.join(root, 'file.lst'))

    def path(self, *p):
        return os.path.join(self.root, *p)

    def read(self, *p):
        with open(self.path(*p), 'rb') as f:
            return f.read()

    def texture_path(self, name):
        """texture names in sfm files are .bmp/.tga but the usable data is in texture/dds"""
        if self._tex_index is None:
            idx = {}
            for sub in ('texture', 'texture/dds', 'bitmap'):
                d = self.path(sub)
                if os.path.isdir(d):
                    for fn in os.listdir(d):
                        if os.path.isfile(os.path.join(d, fn)):
                            idx.setdefault((sub, fn.lower()), os.path.join(d, fn))
            self._tex_index = idx
        base = os.path.basename(name.replace('\\', '/')).lower()
        stem = os.path.splitext(base)[0]
        for sub, fn in (('texture/dds', stem + '.dds'), ('texture', base), ('texture', stem + '.tga'),
                        ('texture', stem + '.png'), ('texture', stem + '.bmp'), ('bitmap', base)):
            p = self._tex_index.get((sub, fn))
            if p:
                return p
        return None

    def xml_info(self, xml_path):
        """Resolve an object xml to its mesh, collision file and default textures."""
        key = xml_path.lstrip('/').lower()
        if key in self._xml_cache:
            return self._xml_cache[key]
        info = None
        p = self.path(xml_path.lstrip('/'))
        if os.path.isfile(p):
            t = open(p, encoding='latin1').read()
            m = re.search(r'<FileName>.*?<Normal>.*?<SFString Value="([^"]*)"', t, re.S)
            c = re.search(r'<StaticScheme>.*?<FileName Value="([^"]*)"', t, re.S)
            rt = re.search(r'ResourceType Value="([^"]*)"', t)
            sub = {}
            for sm in re.finditer(r'<Subset(\d+)>\s*<Texture0>\s*<SFString Value="([^"]*)"', t):
                sub[int(sm.group(1))] = sm.group(2)
            info = dict(mesh=m.group(1) if m else None, collision=c.group(1) if c else None,
                        type=rt.group(1) if rt else None, textures=sub)
        self._xml_cache[key] = info
        return info


# ---------------------------------------------------------------- math
def euler_to_quat_gltf(rx, ry, rz):
    """D3DX yaw/pitch/roll (row vector matrices Rz*Rx*Ry, left handed) -> glTF quaternion
    (right handed, Z negated)."""
    def rot(axis, a):
        c, s = math.cos(a), math.sin(a)
        if axis == 'x':
            return [[1, 0, 0], [0, c, s], [0, -s, c]]
        if axis == 'y':
            return [[c, 0, -s], [0, 1, 0], [s, 0, c]]
        return [[c, s, 0], [-s, c, 0], [0, 0, 1]]

    def mul(a, b):
        return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
    m = mul(mul(rot('z', rz), rot('x', rx)), rot('y', ry))   # row vector convention
    m = [[m[j][i] for j in range(3)] for i in range(3)]       # -> column vectors
    f = (1, 1, -1)
    m = [[m[i][j] * f[i] * f[j] for j in range(3)] for i in range(3)]  # conjugate with Z flip
    tr = m[0][0] + m[1][1] + m[2][2]
    if tr > 0:
        s = math.sqrt(tr + 1) * 2
        q = ((m[2][1] - m[1][2]) / s, (m[0][2] - m[2][0]) / s, (m[1][0] - m[0][1]) / s, 0.25 * s)
    elif m[0][0] > m[1][1] and m[0][0] > m[2][2]:
        s = math.sqrt(1 + m[0][0] - m[1][1] - m[2][2]) * 2
        q = (0.25 * s, (m[0][1] + m[1][0]) / s, (m[0][2] + m[2][0]) / s, (m[2][1] - m[1][2]) / s)
    elif m[1][1] > m[2][2]:
        s = math.sqrt(1 + m[1][1] - m[0][0] - m[2][2]) * 2
        q = ((m[0][1] + m[1][0]) / s, 0.25 * s, (m[1][2] + m[2][1]) / s, (m[0][2] - m[2][0]) / s)
    else:
        s = math.sqrt(1 + m[2][2] - m[0][0] - m[1][1]) * 2
        q = ((m[0][2] + m[2][0]) / s, (m[1][2] + m[2][1]) / s, 0.25 * s, (m[1][0] - m[0][1]) / s)
    return q


# ---------------------------------------------------------------- GLB writer
class Glb:
    def __init__(self):
        self.bin = bytearray()
        self.views, self.accessors, self.meshes, self.nodes = [], [], [], []
        self.materials, self.textures, self.images = [], [], []
        self._mat, self._tex = {}, {}
        self.scene_nodes = []
        self.skins = []

    def _view(self, data, target=None):
        while len(self.bin) % 4:
            self.bin.append(0)
        v = {'buffer': 0, 'byteOffset': len(self.bin), 'byteLength': len(data)}
        if target:
            v['target'] = target
        self.bin += data
        self.views.append(v)
        return len(self.views) - 1

    def accessor(self, arr, ctype, atype, target, minmax=False, normalized=False):
        n = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}[atype]
        a = {'bufferView': self._view(arr.tobytes(), target), 'componentType': ctype,
             'count': len(arr) // n, 'type': atype}
        if normalized:
            a['normalized'] = True
        if minmax:
            a['min'] = [min(arr[i::n]) for i in range(n)]
            a['max'] = [max(arr[i::n]) for i in range(n)]
        self.accessors.append(a)
        return len(self.accessors) - 1

    def material(self, key, texture_uri=None, alpha=False, color=None):
        k = (key, texture_uri)
        if k in self._mat:
            return self._mat[k]
        m = {'name': key, 'doubleSided': True,
             'pbrMetallicRoughness': {'metallicFactor': 0.0, 'roughnessFactor': 1.0}}
        if texture_uri:
            if texture_uri not in self._tex:
                self.images.append({'uri': texture_uri})
                self.textures.append({'source': len(self.images) - 1, 'sampler': 0})
                self._tex[texture_uri] = len(self.textures) - 1
            m['pbrMetallicRoughness']['baseColorTexture'] = {'index': self._tex[texture_uri]}
        if color:
            m['pbrMetallicRoughness']['baseColorFactor'] = list(color)
        if alpha:
            m['alphaMode'] = 'MASK'
            m['alphaCutoff'] = 0.5
        self.materials.append(m)
        self._mat[k] = len(self.materials) - 1
        return self._mat[k]

    def add_mesh(self, name, P, N, UV, prims, colors=None, extra_attrs=None):
        """P/N/UV: lists of tuples in *game* space. prims: [(index list, material idx or None)]."""
        pos = array.array('f')
        for x, y, z in P:
            pos.extend((x, y, -z))
        attrs = {'POSITION': self.accessor(pos, 5126, 'VEC3', 34962, True)}
        if N:
            nr = array.array('f')
            for x, y, z in N:
                nr.extend((x, y, -z))
            attrs['NORMAL'] = self.accessor(nr, 5126, 'VEC3', 34962)
        if UV:
            uv = array.array('f')
            for u, v in UV:
                uv.extend((u, v))
            attrs['TEXCOORD_0'] = self.accessor(uv, 5126, 'VEC2', 34962)
        if colors:
            cl = array.array('B')
            for c in colors:
                cl.extend(c)
            attrs['COLOR_0'] = self.accessor(cl, 5121, 'VEC4', 34962, normalized=True)
        for k, v in (extra_attrs or {}).items():
            arr, atype = v[0], v[1]
            ctype, norm = (v[2], v[3]) if len(v) > 2 else (5121, True)
            attrs[k] = self.accessor(arr, ctype, atype, 34962, normalized=norm)
        out = []
        for idx, mat in prims:
            ia = array.array('I')
            for t in range(0, len(idx), 3):
                ia.extend((idx[t], idx[t + 2], idx[t + 1]))   # flip winding (Z mirror)
            p = {'attributes': attrs, 'indices': self.accessor(ia, 5125, 'SCALAR', 34963), 'mode': 4}
            if mat is not None:
                p['material'] = mat
            out.append(p)
        self.meshes.append({'name': name, 'primitives': out})
        return len(self.meshes) - 1

    def add_node(self, mesh=None, name=None, t=None, q=None, extras=None, root=True, skin=None, children=None):
        n = {}
        if skin is not None:
            n['skin'] = skin
        if children:
            n['children'] = children
        if mesh is not None:
            n['mesh'] = mesh
        if name:
            n['name'] = name
        if t:
            n['translation'] = [t[0], t[1], -t[2]]
        if q:
            n['rotation'] = list(q)
        if extras:
            n['extras'] = extras
        self.nodes.append(n)
        if root:
            self.scene_nodes.append(len(self.nodes) - 1)
        return len(self.nodes) - 1

    def save(self, path):
        g = {'asset': {'version': '2.0', 'generator': 'darkfall-data-export sfexport.py'},
             'scene': 0, 'scenes': [{'nodes': self.scene_nodes}], 'nodes': self.nodes,
             'meshes': self.meshes, 'buffers': [{'byteLength': len(self.bin)}],
             'bufferViews': self.views, 'accessors': self.accessors,
             'samplers': [{'magFilter': 9729, 'minFilter': 9987, 'wrapS': 10497, 'wrapT': 10497}]}
        if self.skins:
            g['skins'] = self.skins
        if self.materials:
            g['materials'] = self.materials
        if self.textures:
            g['textures'], g['images'] = self.textures, self.images
        js = json.dumps(g, separators=(',', ':')).encode()
        js += b' ' * (-len(js) % 4)
        b = bytes(self.bin) + b'\0' * (-len(self.bin) % 4)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            f.write(struct.pack('<4sII', b'glTF', 2, 12 + 8 + len(js) + 8 + len(b)))
            f.write(struct.pack('<I4s', len(js), b'JSON') + js)
            f.write(struct.pack('<I4s', len(b), b'BIN\0') + b)


# ---------------------------------------------------------------- textures
class Textures:
    def __init__(self, src, out, size):
        self.src, self.out, self.size = src, out, size
        self.cache = {}

    def get(self, name, rel_to):
        """convert (once) and return (uri relative to `rel_to` dir, has_alpha) or (None, False)"""
        if not name:
            return None, False
        stem = os.path.splitext(os.path.basename(name.replace('\\', '/')))[0].lower()
        if stem not in self.cache:
            res = None
            p = self.src.texture_path(name)
            if p:
                dst = os.path.join(self.out, 'textures', stem + '.png')
                try:
                    if os.path.exists(dst):
                        png = open(dst, 'rb').read()
                    else:
                        data = open(p, 'rb').read()
                        ext = os.path.splitext(p)[1].lower()
                        if ext == '.dds':
                            png = sfimg.dds_to_png(data, self.size)[0]
                        elif ext == '.bmp':
                            png = sfimg.bmp_to_png(data)[0]
                        elif ext == '.tga':
                            png = sfimg.tga_to_png(data)[0]
                        else:
                            png = data
                        os.makedirs(os.path.dirname(dst), exist_ok=True)
                        tmp = '%s.%d.tmp' % (dst, os.getpid())
                        open(tmp, 'wb').write(png)
                        os.replace(tmp, dst)   # atomic: several exporters may run in parallel
                    res = (dst, png[25] == 6)
                except Exception as e:   # noqa
                    print('  texture %s failed: %s' % (name, e), file=sys.stderr)
            self.cache[stem] = res
        r = self.cache[stem]
        if not r:
            return None, False
        return os.path.relpath(r[0], rel_to).replace(os.sep, '/'), r[1]


def mesh_to_glb_mesh(glb, m, texs, rel_dir, name, xml_textures=None):
    prims = []
    for s in m.submeshes:
        idx = m.indices[3 * s.first_face:3 * (s.first_face + s.face_count)]
        tex = None
        for cand in ([xml_textures.get(s.tex)] if xml_textures and xml_textures.get(s.tex) else []) + s.textures:
            uri, alpha = texs.get(cand, rel_dir)
            if uri:
                tex = (uri, alpha, cand)
                break
        mat = glb.material('%s_%d' % (name, s.tex), tex[0], tex[1]) if tex else \
            glb.material('%s_%d' % (name, s.tex), None, False, (0.6, 0.6, 0.6, 1))
        prims.append((idx, mat))
    return glb.add_mesh(name, m.positions, m.normals, m.uvs, prims)


# ---------------------------------------------------------------- terrain
def parse_ter(d):
    """Terrain tile. Header: magic, version, n_verts, n_indices, then the material groups:
    u32 n_groups, u32 1, n_groups * (u32 n_mats, n_mats * u32 material id), then
    n_groups * (tri_count, tri_start, vert_start, vert_count). Followed (at the end of the file) by
    n_verts * 32 byte vertices (pos 3f, normal 3f, 8 u8 blend weights, see terrain_slots) and n_indices * u32 indices. Material ids index
    xml/terrain/terrainmaterials.xml (the shader samples that entry's Near texture, not NN_tex_terrain_*). There are no UVs (the game derives them from world position).
    Returns (P, N, W, I, groups)."""
    if d[:4] != b'SFTE':
        raise ValueError('bad magic')
    ver, nv, ni = struct.unpack_from('<3I', d, 4)
    ng, _one = struct.unpack_from('<2I', d, 16)
    p = 24
    mats = []
    for g in range(ng):
        n, = struct.unpack_from('<I', d, p)
        mats.append(list(struct.unpack_from('<%dI' % n, d, p + 4)))
        p += 4 + 4 * n
    groups = []
    for g in range(ng):
        tc, ts, vst, vc = struct.unpack_from('<4I', d, p)
        groups.append(dict(materials=mats[g], tri_count=tc, tri_start=ts, vert_start=vst, vert_count=vc))
        p += 16
    vs = p
    if vs + 32 * nv + 4 * ni > len(d):
        raise ValueError('truncated terrain')
    P = [struct.unpack_from('<3f', d, vs + 32 * i) for i in range(nv)]
    N = [struct.unpack_from('<3f', d, vs + 32 * i + 12) for i in range(nv)]
    W = [d[vs + 32 * i + 24:vs + 32 * i + 32] for i in range(nv)]
    I = list(struct.unpack_from('<%dI' % ni, d, vs + 32 * nv))   # (a few files carry 4 extra bytes at the end)
    return P, N, W, I, groups


def terrain_slots(n):
    """weight byte used by each of the n materials of a terrain group (materials in the order of the .ter header, ascending ids).
    The 8 blend weights are two D3DCOLOR-style dwords stored as B, G, R, A: material k uses byte [2, 1, 0, 3, 6, 5, 4, 7][k], so a 1-material group
    uses byte 2, 2 materials [2, 1], 3 materials [2, 1, 0], and so on. Verified exactly (zero error) on 60k coincident seam vertices between
    single-material groups and groups of 2..7 materials."""
    return [2, 1, 0, 3, 6, 5, 4, 7][:n]


class TerrainMaterials:
    """terrain material id -> Near texture from xml/terrain/terrainmaterials.xml, plus average colour.

    Ids in a .ter are palette indices (0..32), not the NN_ prefix of NN_tex_terrain_*.dds.
    """
    def __init__(self, src, textures):
        self.src, self.textures = src, textures
        self.files = {}
        table = src.path('xml', 'terrain', 'terrainmaterials.xml')
        if os.path.isfile(table):
            text = open(table, encoding='latin1').read()
            for m in re.finditer(r'<SFMaterial ID="(\d+)"\s*>\s*<Near Texture="([^"]+)"', text):
                fn = m.group(2) + '.dds'
                if os.path.isfile(src.path('texture', 'dds', fn)):
                    self.files[int(m.group(1))] = fn
        if not self.files:
            d = src.path('texture', 'dds')
            for fn in sorted(os.listdir(d)) if os.path.isdir(d) else []:
                m = re.match(r'^(\d+)_tex_terrain_.*\.dds$', fn, re.I)
                if m and not re.search(r'(_normal|_mads|copy)', fn, re.I):
                    self.files.setdefault(int(m.group(1)), fn)
        self.colors = {}

    def color(self, mid):
        if mid not in self.colors:
            c = (128, 128, 128, 255)
            if mid in self.files:
                try:
                    c = sfimg.dds_average_color(open(self.src.path('texture', 'dds', self.files[mid]), 'rb').read())
                except Exception as e:   # noqa
                    print('  terrain material %d: %s' % (mid, e), file=sys.stderr)
            self.colors[mid] = c
        return self.colors[mid]


def terrain_prim(glb, name, d, tm=None, out_dir=None):
    P, N, W, I, groups = parse_ter(d)
    # vertex colour = blend of the average colours of the group's materials (quick preview look);
    # the raw 8 weights are exported as _WEIGHTS0/_WEIGHTS1 for a proper splat shader.
    cols = None
    if tm:
        cols = [(128, 128, 128, 255)] * len(P)
        for g in groups:
            cs = [tm.color(m) for m in g['materials']]
            slots = terrain_slots(len(cs))
            for v in range(g['vert_start'], g['vert_start'] + g['vert_count']):
                w = [W[v][s] for s in slots]
                tot = sum(w) or 1
                cols[v] = tuple(int(sum(w[k] * cs[k][c] for k in range(len(cs))) / tot) for c in range(3)) + (255,)
    extra = {'_WEIGHTS0': (array.array('B', b''.join(w[:4] for w in W)), 'VEC4'),
             '_WEIGHTS1': (array.array('B', b''.join(w[4:8] for w in W)), 'VEC4')}
    mat = glb.material('terrain', None, False, (1, 1, 1, 1))
    prims = []
    for g in groups:
        prims.append((I[3 * g['tri_start']:3 * (g['tri_start'] + g['tri_count'])], mat))
    mi = glb.add_mesh(name, P, N, None, prims, cols, extra)
    glb.meshes[mi]['extras'] = {'groups': [dict(g, slots=terrain_slots(len(g['materials'])), textures=[tm.files.get(m) if tm else None for m in g['materials']])
                                           for g in groups]}
    return mi


# ---------------------------------------------------------------- commands
def iter_files(src, sub, ext, name=None, limit=None):
    n = 0
    for dp, dn, fn in os.walk(src.path(sub)):
        dn.sort()
        for f in sorted(fn):
            if f.lower().endswith(ext) and (not name or name in f):
                yield os.path.join(dp, f)
                n += 1
                if limit and n >= limit:
                    return


def cmd_models(a):
    src, texs = Src(a.src), None
    texs = Textures(src, a.out, a.tex_size)
    ok = bad = 0
    for p in iter_files(src, 'mesh', '.sfm', a.name, a.limit):
        rel = os.path.relpath(p, src.path('mesh'))
        try:
            m = sflib.parse_sfm(open(p, 'rb').read())
            glb = Glb()
            dst = os.path.join(a.out, 'models', os.path.splitext(rel)[0] + '.glb')
            mi = mesh_to_glb_mesh(glb, m, texs, os.path.dirname(dst), os.path.basename(rel), None)
            glb.add_node(mi, os.path.basename(rel))
            glb.save(dst)
            ok += 1
        except Exception as e:
            bad += 1
            print('FAIL', rel, e, file=sys.stderr)
    print('models: %d ok, %d failed' % (ok, bad))


def cmd_terrain(a):
    src = Src(a.src)
    tm = TerrainMaterials(src, None)
    ok = 0
    for p in iter_files(src, 'mesh', '.ter', a.name, a.limit):
        glb = Glb()
        nm = os.path.splitext(os.path.basename(p))[0]
        mi = terrain_prim(glb, nm, open(p, 'rb').read(), tm)
        glb.add_node(mi, nm)
        glb.save(os.path.join(a.out, 'terrain', nm + '.glb'))
        ok += 1
    print('terrain: %d tiles' % ok)


def collision_geometry(src, stem):
    """triangle soup an aabbtree .sfc refers to (same name .sfm/.ter). returns (P, I, source) or None"""
    for cand in (stem + '.sfm', stem + '.ter'):
        p = src.path('mesh', cand)
        if os.path.isfile(p):
            if cand.endswith('.ter'):
                P, N, W, I, _g = parse_ter(open(p, 'rb').read())
                return P, I, cand
            m = sflib.parse_sfm(open(p, 'rb').read())
            return m.positions, m.indices, cand
    return None


def cmd_collision(a):
    """aabb trees -> collision/<name>.glb (+ bvh/<name>.json); spheres / boxes -> collision/shapes.json"""
    src = Src(a.src)
    ok = missing = unknown = 0
    shapes = {}
    for p in iter_files(src, 'collision', '.sfc', a.name, a.limit):
        fn = os.path.basename(p)
        m = re.match(r'(.*?)(?:\.sfm)?\.(static|dynamic|influence)\.(sf\w+)\.sfc$', fn)
        if not m:
            # animated model schemes are named `<name>.sfam<class>.sfc` (sic, no separator)
            m2 = re.match(r'(.*?)\.sf(?:a)?m(sf\w+)\.sfc$', fn)
            if not m2:
                print('odd name', fn, file=sys.stderr)
                continue
            m = (m2.group(1), 'animated', m2.group(2))
            stem, scheme, cls = m
        else:
            stem, scheme, cls = m.groups()
        try:
            sfc = sflib.parse_sfc(open(p, 'rb').read())
            if sfc.kind in ('sphere', 'spheres'):
                shapes.setdefault(stem, {})[scheme] = {'kind': sfc.kind, 'spheres': [list(s) for s in sfc.spheres]}
            elif sfc.kind == 'obb':
                shapes.setdefault(stem, {})[scheme] = {'kind': 'obb', 'center': sfc.obb[:3], 'axes': sfc.obb[3:12],
                                                       'half_extents': sfc.obb[12:15]}
            elif sfc.kind.startswith('aabbtree'):
                if sfc.kind == 'aabbtree_geometry':
                    P, I, source = sfc.positions, sfc.indices, 'embedded'
                else:
                    g = collision_geometry(src, stem)
                    if not g:
                        missing += 1
                        continue
                    P, I, source = g
                glb = Glb()
                mi = glb.add_mesh(stem, P, None, None, [(I, glb.material('collision', None, False, (1, 0, 0, 1)))])
                glb.add_node(mi, stem, extras={'source': source, 'scheme': scheme})
                glb.save(os.path.join(a.out, 'collision', scheme, stem + '.glb'))
                os.makedirs(os.path.join(a.out, 'collision', 'bvh'), exist_ok=True)
                with open(os.path.join(a.out, 'collision', 'bvh', '%s.%s.json' % (stem, scheme)), 'w') as f:
                    json.dump({'geometry': source if source == 'embedded' else 'mesh/' + source,
                               'coordinates': 'game (left handed, Y up)',
                               'note': 'node = [minx,miny,minz,maxx,maxy,maxz,a,b]; b==0: interior, children a and a+1; '
                                       'b>0: leaf with b triangles; tri_order[a:a+b] are offsets into the index buffer '
                                       '(index of the first vertex of each triangle)',
                               'nodes': [[round(x, 5) for x in n[:6]] + [n[6], n[7]] for n in sfc.nodes],
                               'tri_order': sfc.tri_order}, f, separators=(',', ':'))
            else:
                unknown += 1
                continue
            ok += 1
        except Exception as e:
            print('FAIL', fn, e, file=sys.stderr)
    os.makedirs(os.path.join(a.out, 'collision'), exist_ok=True)
    sp = os.path.join(a.out, 'collision', 'shapes.json')
    if os.path.exists(sp):   # merge, so partial reruns (--name) do not drop earlier results
        old = json.load(open(sp))
        for k, v in shapes.items():
            old.setdefault(k, {}).update(v)
        shapes = old
    with open(sp, 'w') as f:
        json.dump(shapes, f, separators=(',', ':'))
    print('collision: %d ok, %d aabb trees without matching mesh, %d undecoded (convex hulls)' % (ok, missing, unknown))


def _bone_worlds(bones):
    """world rigid transforms (R 3x3 row-major, t) of the bind pose in game space"""
    def qmat(q):
        x, y, z, w = q
        return [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]
    W = {}
    for b in sorted(bones, key=lambda b: b['index']):
        R, t = qmat(b['q']), b['t']
        par = b['parent']
        if par < 0 or par == b['index'] or par not in W:
            W[b['index']] = (R, list(t))
        else:
            pR, pt = W[par]
            W[b['index']] = ([[sum(pR[i][k] * R[k][j] for k in range(3)) for j in range(3)] for i in range(3)],
                             [pt[i] + sum(pR[i][k] * t[k] for k in range(3)) for i in range(3)])
    return W


def cmd_animated(a):
    """skinned meshes (.sfam) -> animated/*.glb with skeleton in bind pose (animations are not decoded)"""
    src = Src(a.src)
    texs = Textures(src, a.out, a.tex_size)
    ok = bad = 0
    for p in iter_files(src, 'mesh', '.sfam', a.name, a.limit):
        rel = os.path.relpath(p, src.path('mesh'))
        try:
            raw = open(p, 'rb').read()
            if raw[:4] != b'SFAM':
                continue
            m = sflib.parse_sfm(raw)
            glb = Glb()
            dst = os.path.join(a.out, 'animated', os.path.splitext(os.path.basename(rel))[0] + '.glb')
            nm = os.path.splitext(os.path.basename(rel))[0]
            # vertex joint indices -> bone indices through each section's palette
            J = [(0, 0, 0, 0)] * len(m.positions)
            for s in m.submeshes:
                for i in range(s.first_vert, s.first_vert + s.vert_count):
                    J[i] = tuple(s.palette[j] if j < len(s.palette) else 0 for j in m.joints[i])
            Wt = []
            for w in m.weights:
                t = sum(w) or 1.0
                Wt.append(tuple(x / t for x in w))
            prims = []
            for s in m.submeshes:
                idx = m.indices[3 * s.first_face:3 * (s.first_face + s.face_count)]
                tex = None
                for cand in s.textures:
                    uri, alpha = texs.get(cand, os.path.dirname(dst))
                    if uri:
                        tex = (uri, alpha)
                        break
                mat = glb.material('%s_%d' % (nm, s.tex), tex[0] if tex else None, tex[1] if tex else False,
                                   None if tex else (0.6, 0.6, 0.6, 1))
                prims.append((idx, mat))
            ja = array.array('H')
            wa = array.array('f')
            for j, w in zip(J, Wt):
                ja.extend(j)
                wa.extend(w)
            mi = glb.add_mesh(nm, m.positions, m.normals, m.uvs, prims, None,
                              {'JOINTS_0': (ja, 'VEC4', 5123, False), 'WEIGHTS_0': (wa, 'VEC4', 5126, False)})
            # skeleton: node per bone, children by parent index
            W = _bone_worlds(m.bones)
            bone_nodes = {}
            for b in sorted(m.bones, key=lambda b: b['index']):
                qx, qy, qz, qw = b['q']
                bone_nodes[b['index']] = glb.add_node(None, b['name'], b['t'], (-qx, -qy, qz, qw), root=False)
            roots = []
            for b in m.bones:
                par = b['parent']
                if par < 0 or par == b['index'] or par not in bone_nodes:
                    roots.append(bone_nodes[b['index']])
                else:
                    glb.nodes[bone_nodes[par]].setdefault('children', []).append(bone_nodes[b['index']])
            order = sorted(bone_nodes)
            ibm = array.array('f')
            f = (1, 1, -1)
            for bi in order:
                R, t = W[bi]
                # inverse of rigid world transform, conjugated with the Z flip, column major
                Ri = [[R[j][i] * f[i] * f[j] for j in range(3)] for i in range(3)]       # transpose, then flip
                tf = [t[0], t[1], -t[2]]
                ti = [-sum(Ri[i][k] * tf[k] for k in range(3)) for i in range(3)]
                for c in range(3):
                    ibm.extend((Ri[0][c], Ri[1][c], Ri[2][c], 0.0))
                ibm.extend((ti[0], ti[1], ti[2], 1.0))
            glb.skins.append({'joints': [bone_nodes[i] for i in order],
                              'inverseBindMatrices': glb.accessor(ibm, 5126, 'MAT4', None),
                              'skeleton': roots[0] if roots else bone_nodes[order[0]]})
            top = glb.add_node(mi, nm, skin=0)
            for r in roots:
                glb.scene_nodes.append(r)
            glb.save(dst)
            ok += 1
        except Exception as e:
            bad += 1
            print('FAIL', rel, e, file=sys.stderr)
    print('animated: %d ok, %d failed' % (ok, bad))


def cmd_maps(a):
    src = Src(a.src)
    texs = Textures(src, a.out, a.tex_size)
    tmat = TerrainMaterials(src, texs)
    os.makedirs(os.path.join(a.out, 'maps'), exist_ok=True)
    mesh_cache = {}
    for p in iter_files(src, a.level_dir, '.lvl', a.name, a.limit):
        nm = os.path.splitext(os.path.basename(p))[0]
        try:
            lv = sflib.parse_lvl(open(p, 'rb').read(), src.ids)
        except Exception as e:
            print('FAIL', nm, e, file=sys.stderr)
            continue
        objs = []
        for o in lv['objects']:
            info = src.xml_info(o['xml']) if o['xml'] else None
            objs.append(dict(id=o['id'], xml=o['xml'], pos=o['pos'], rot=o['rot'],
                             mesh=info and info['mesh'], collision=info and info['collision'],
                             type=info and info['type']))
        with open(os.path.join(a.out, 'maps', nm + '.json'), 'w') as f:
            json.dump({'name': nm, 'coordinates': 'game (left handed, Y up); rot = D3DX yaw/pitch/roll '
                       '(x=pitch, y=yaw, z=roll) radians', 'version': lv['version'],
                       'bounds_header': lv['header'], 'objects': objs}, f, separators=(',', ':'))
        if a.no_glb:
            continue
        glb = Glb()
        gm = {}
        count = 0
        for o in objs:
            mesh = o['mesh']
            if not mesh or not mesh.lower().endswith(('.sfm', '.ter')):
                continue
            if mesh not in gm:
                path = src.path('mesh', mesh)
                if not os.path.isfile(path):
                    gm[mesh] = None
                    continue
                try:
                    data = open(path, 'rb').read()
                    if mesh.lower().endswith('.ter'):
                        gm[mesh] = terrain_prim(glb, mesh, data, tmat)
                    else:
                        gm[mesh] = mesh_to_glb_mesh(glb, sflib.parse_sfm(data), texs,
                                                    os.path.join(a.out, 'maps'), mesh)
                except Exception as e:
                    print('  %s: %s: %s' % (nm, mesh, e), file=sys.stderr)
                    gm[mesh] = None
            if gm[mesh] is None:
                continue
            glb.add_node(gm[mesh], os.path.basename(o['xml']), o['pos'], euler_to_quat_gltf(*o['rot']))
            count += 1
        glb.save(os.path.join(a.out, 'maps', nm + '.glb'))
        print('map %s: %d objects placed' % (nm, count))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['models', 'terrain', 'collision', 'animated', 'maps', 'all'])
    ap.add_argument('src')
    ap.add_argument('out')
    ap.add_argument('--limit', type=int)
    ap.add_argument('--name', help='only files whose name contains this')
    ap.add_argument('--tex-size', type=int, default=512, help='max texture size (picks a smaller DDS mip)')
    ap.add_argument('--level-dir', default='level', help='maps: subfolder of src holding the .lvl files (e.g. levelold)')
    ap.add_argument('--no-glb', action='store_true', help='maps: only write json')
    a = ap.parse_args()
    for c in (['models', 'terrain', 'collision', 'animated', 'maps'] if a.cmd == 'all' else [a.cmd]):
        globals()['cmd_' + c](a)


if __name__ == '__main__':
    main()
