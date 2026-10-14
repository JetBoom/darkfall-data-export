import bz2, struct, os, stat, sys
from io import BytesIO

DATA = sys.argv[1] if len(sys.argv) > 1 else '.'
OUT = sys.argv[2] if len(sys.argv) > 2 else 'out'

sfai = open(os.path.join(DATA, 'dfdata.sfai'), 'rb')

h = struct.unpack('<128I', sfai.read(0x200))
assert h[0] == 0x49414653 # "SFAI"
start = h[6]
size = h[7]
print("INDEX: %08X => %08X" % (start, start + size))
sfai.seek(start)
buff = sfai.read(size)

buff = b'BZh9' + buff[4:]
idx = BytesIO(bz2.decompress(buff))

csizes = {}
files = {}
fsizes = {}
fcount = {}
for x in range(0, 32):
    try:
        files[x] = open(os.path.join(DATA, 'dfdata_%04d.sfad' % x), 'rb')
        csizes[x] = 0
        fcount[x] = 0
        fsizes[x] = os.path.getsize(os.path.join(DATA, 'dfdata_%04d.sfad' % x))
    except FileNotFoundError:
        break

num_tomes = len(files)

os.makedirs(OUT, exist_ok=True)
log = open(os.path.join(OUT, 'file.lst'), 'w')

while True:
    x = idx.read(0xBD)
    if not x:
        break
    n = x[0:x.find(0)].decode('utf-8')
    id, t, s1, fn, p, s2, u3, u4 = struct.unpack('<7Ib', x[160:189])
    csizes[fn] += s2
    fcount[fn] += 1
    os.makedirs(os.path.join(OUT, *n.split('/')[:-1]), exist_ok=True)
    print("%(n)r ID:%(id)d @ %(p)08X (T%(fn)02d) Size:%(s1)d/%(s2)d %(u3)08X %(u4)02X" % locals(), file=log)
    files[fn].seek(p)
    buff = files[fn].read(s2)
    if s1 != s2:
        if buff[:4] == b'SFZM':
            buff = b'BZh9' + buff[4:]
            buff = bz2.decompress(buff)
        else:
            print('Warning! %r unknown compression.' % n)
    f = open(os.path.join(OUT, n), 'wb')
    f.write(buff)
    f.close()

log.close()
for x in range(num_tomes):
    files[x].close()

print("================ DONE ==================")
for x in range(num_tomes):
    print("Tome %02d - %d files, %.3f%% lost" % (x, fcount[x], 100.0 * (fsizes[x] - csizes[x]) / fsizes[x]))
