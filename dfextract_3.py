import bz2, struct, os, stat
from io import BytesIO

sfai = open('dfdata.sfai', 'rb')

h = struct.unpack('128L', sfai.read(0x200))
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
        files[x] = open('dfdata_%04d.sfad' % x, 'rb')
        csizes[x] = 0
        fcount[x] = 0
        fsizes[x] = os.path.getsize('dfdata_%04d.sfad' % x)
    except FileNotFoundError:
        break

num_tomes = len(files)

if not os.path.isdir('out'):
    os.mkdir('out')
log = open('out/file.lst', 'w')

while True:
    x = idx.read(0xBD)
    if not x:
        break
    n = x[0:x.find(0)].decode('utf-8')
    id, t, s1, fn, p, s2, u3, u4 = struct.unpack('7Lb', x[160:189])
    csizes[fn] += s2
    fcount[fn] += 1
    pp = 'out/'
    for y in n.split('/')[:-1]:
        pp += y + '/'
        if not os.path.isdir(pp):
            os.mkdir(pp)
    print("%(n)r ID:%(id)d @ %(p)08X (T%(fn)02d) Size:%(s1)d/%(s2)d %(u3)08X %(u4)02X" % locals(), file=log)
    files[fn].seek(p)
    buff = files[fn].read(s2)
    if s1 != s2:
        if buff[:4] == b'SFZM':
            buff = b'BZh9' + buff[4:]
            buff = bz2.decompress(buff)
        else:
            print('Warning! %r unknown compression.' % n)
    f = open('out/' + n, 'wb')
    f.write(buff)
    f.close()

log.close()
for x in range(num_tomes):
    files[x].close()

print("================ DONE ==================")
for x in range(num_tomes):
    print("Tome %02d - %d files, %.3f%% lost" % (x, fcount[x], 100.0 * (fsizes[x] - csizes[x]) / fsizes[x]))
