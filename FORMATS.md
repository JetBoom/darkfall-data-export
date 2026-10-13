# Binary formats (Darkfall: Unholy Wars / Rise of Agon)

All little endian. Verified against the full data set (counts in parentheses). Parsers: `sflib.py`, `sfexport.py`.

## Archives
`dfdata.sfai` is a 0x200 byte header (`SFAI`, index offset at +0x18, size at +0x1c) followed by a bz2 index
(magic `SFZM` replaces `BZh9`) of 0xBD byte entries: 160 byte path, then `id, type, size, tome, offset, csize, ?, ?`
(`'<7Ib'`, note: `L` is 8 bytes on 64 bit Python). Data lives in `dfdata_NNNN.sfad`; entries with
`size != csize` are `SFZM` bz2 streams. Level `.lvl` version 1 refers to objects by this `id`.

## `.sfm` static mesh (`SFME`, 13357 / 13357 parse)
Header (u32): ver, vert_count, index_count, kind, ?, vertex_stride, index_bits (16/32), ?, n_submeshes, ?.
At 0x60 one record per submesh: `tex, first_face, face_count, first_vert, vert_count, name_len, name` followed by
a variable material trailer (found by searching for the next record: its `first_face/first_vert` are the running sums).
Then a D3D9 `D3DVERTEXELEMENT9` vertex declaration (8 byte elements, terminated by `ff00 0000 1100 0000`),
vertices, indices (global, triangle lists). Layouts seen: pos+normal+uv, +tangent(float3/4), +D3DCOLOR.
Triangle winding is CW in the game's left handed space.

## `.sfam` skinned mesh (`SFAM`, 637 / 637)
Same header/decl/vertex/index layout (vertex has blend weights (float3/4) + blend indices (4 bytes)); the material
records in the header are unreliable. Trailer after the index buffer:
`u32 2, 6, ?, ?, n_sections, n_bones`, then `n_sections * { flag, idx, first_face, face_count, first_vert, vert_count,
palette_count, palette_count * (palette_index, bone_index) }` (vertex blend indices index the section palette), then
`n_bones` 100 byte records: null terminated name + padding/pointers, `u32 ?, index, parent`, local bind pose
translation (3f) and rotation quaternion (xyzw).

## `.sfas` animation set (`SFAS`, partial)
A memory dump of C++ objects (pointer values are garbage). `u32 version=2, u32 n_animations`, then per animation
name + per bone record(s). A bone record (starts at the null terminated bone name) has a fixed 0x98 byte-ish header
containing `fe ff ff ff, bone_index, ?, duration(float), n_keys`, then a u32 descriptor with one nibble per channel
(tx ty tz qx qy qz qw): `0xc` = constant channel stored as one float32, other values = animated channel stored as
`02 00 NN` + 4 floats + 1 byte + 4 floats (36 bytes). How these 8 floats expand to `n_keys` samples is *not* decoded.

## `.sfc` collision schemes (`c5 <kind> 00 ...`)
* `0c` AABB tree (9021): `u32 n`, n * (6 float AABB, u32 a, u32 b), `u32 t`, t * u32 `tri_order`.
  Node: `b == 0` interior with children `a`, `a+1`; `b > 0` leaf with `b` triangles `tri_order[a:a+b]`, which are
  offsets into the index buffer of the same-named `.sfm`/`.ter`. Root box == mesh bounds. (85 terrain trees have no `.ter` in the data.)
* `2c` AABB tree with embedded geometry (591): as above, then `u32 n_idx, idx, u32 n_vert, vert*3f, u32 n, adjacency`.
* `02` sphere `x y z r`, `0b` `u32 n` spheres, `0d` OBB (center, 3 axes, half extents) -> `collision/shapes.json`.
* `0e` convex hulls (31): not decoded.

## `.ter` terrain tile (`SFTE`, 634)
Header `u32 ver, n_verts, n_indices, n_groups, 1`, then per group `n_mats, mat ids...`, then per group
`tri_count, tri_start, vert_start, vert_count`; 32 byte vertices (pos 3f, normal 3f, 8 u8 blend weights),
u32 indices. Tile is 1024x1024, local coordinates centred on the tile; its world position is the `terrain_xxx.xml`
object in the level. Material id is an index into `xml/terrain/terrainmaterials.xml` (0..32, one per splat layer),
not the `NN_` prefix of `texture/dds/NN_tex_terrain_*.dds`. The shader's albedo is that entry's `Near` texture
(`terrain_rock_alfar_01.dds` for id 19, the dark alfar rock). The 8 blend weights are two B,G,R,A-ordered dwords: material k of a group uses byte `[2,1,0,3,6,5,4,7][k]` (1 material: byte 2; 2: bytes 2,1; ...; 7: bytes 2,1,0,3,6,5,4). No UVs (derive from world xz).

## `.lvl` level (`SFLV`, 1257 / 1257)
`u32 version, 4 floats (bounds?), u32 count`, then objects: `u16 id, u16 type, 5 bytes, pos 3f, rot 3f (D3DX yaw/pitch/roll:
x=pitch, y=yaw, z=roll), u32 resource id`; version 2 appends `u32 len, xml path`, version 1 only has the resource id
(resolve through `file.lst`). The object xml (`/xml/...`) names the mesh, collision file and textures. Trailing tables
after the objects (lists of ids) are not decoded.
