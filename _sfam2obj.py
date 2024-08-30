import struct,os,binascii,math
from cStringIO import StringIO
import io

for files in os.listdir('.'):
    if (os.path.isfile(files)==True) and (files.endswith('.sfam')==True):
        if not os.path.isdir('obj'): os.mkdir('obj')
        fobj=file('obj/'+files+'.obj','wb')
        #fmtl=file('obj/'+files+'.mtl','wb')
        #header
        fobj.write(b'\x23\x20\x57\x61\x76\x65\x46\x72\x6F\x6E\x74\x20\x2A\x2E\x6F\x62\x6A\x20\x66\x69\x6C\x65\x0A\x0A')
        #fobj.write('mtllib '+files+'.mtl'+b'\x0A\x0A')
        with open(files, "rb") as f:
            objname=files[:-4]
            print files
            fh=f.read(8)
            mn,vz=struct.unpack('<2L', fh[0:8])
            n6=f.read(8)
            vt,fc=struct.unpack('<2L', n6[0:8])
            tn=int(fc)/3
            n7=f.read(28)
            tga,uk9,bdv,bitd2,uk0,ntex,nMapX=struct.unpack('<7L', n7[0:28])
            tf = {}
            tn = {}
            tg = {}
            texinfo = {}
            #r1,r2,rn1,rna=int(tga*nMapX)
            #f.read(52)
            #
            # FIX NORMAL DETECTION
            #
            '''
            for tex in range(0,ntex):
                f.read(72)
                texnam=binascii.hexlify(f.read(4))
                texnamelen=struct.unpack('<L', texnam.decode('hex'))[0]
                f.read(texnamelen)
            '''
            uvs=[]
            mcrd=[]
            fces=[]
            nrmls=[]
            #fmtl.close()
            for x in range(0,512,1):
                byt=f.read(8)
                f.seek(-7,1)
                tbyt=binascii.hexlify(byt)
                if(tbyt=='ff00000011000000'):
                        f.read(7)
                        for v in range(0,vt):
                            nvs=f.read(bdv)
                            if(bdv==32):
                                xcor,ycor,zcor,xnrm,ynrm,znrm,utex,vtex=struct.unpack('<8f', nvs[0:32])
                                mcrd.append('v '+str(xcor)+' '+str(ycor)+' '+str(zcor)+b'\x0A')
                                uvs.append('vt '+str(utex)+' '+str(1-vtex)+b'\x0A')
                            if(bdv==36):
                                xcor,ycor,zcor,xnrm,ynrm,znrm,padd,utex,vtex=struct.unpack('<9f', nvs[0:36])
                                mcrd.append('v '+str(xcor)+' '+str(ycor)+' '+str(zcor)+b'\x0A')
                                uvs.append('vt '+str(utex)+' '+str(1-vtex)+b'\x0A')
                            if(bdv==44):
                                xcor,ycor,zcor,xnrm,ynrm,znrm,padd,utex,vtex,wtex,padd2=struct.unpack('<11f', nvs[0:44])
                                mcrd.append('v '+str(xcor)+' '+str(ycor)+' '+str(zcor)+b'\x0A')
                                uvs.append('vt '+str(utex)+' '+str(1-vtex)+' '+str(wtex)+b'\x0A')
                            if(bdv==48):
                                padd3,padd2,padd4,xnrm,ynrm,znrm,padd1,xcor,ycor,zcor,utex,vtex=struct.unpack('<12f', nvs[0:48])
                                mcrd.append('v '+str(xcor)+' '+str(ycor)+' '+str(0)+b'\x0A')
                                nrmls.append('vn '+str(xnrm)+' '+str(ynrm)+' '+str(znrm)+b'\x0A')
                                uvs.append('vt '+str(utex)+' '+str(1-vtex)+' '+str(0)+b'\x0A')
                            if(bdv==60):
                                xcor,ycor,zcor,xnrm,ynrm,znrm,padd,utex,vtex,wtex,padd2,uk1,uk2,uk3,padd3=struct.unpack('<15f', nvs[0:60])
                                mcrd.append('v '+str(xcor)+' '+str(ycor)+' '+str(zcor)+b'\x0A')
                                
                                uvs.append('vt '+str(utex)+' '+str(1-vtex)+' '+str(wtex)+b'\x0A')
                            if(bdv==68):
                                xcor,ycor,zcor,xnrm,ynrm,znrm,padd,utex,vtex,wtex,padd2,uk1,uk2,uk3,padd3,padd4,padd5=struct.unpack('<17f', nvs[0:68])
                                mcrd.append('v '+str(xcor)+' '+str(ycor)+' '+str(zcor)+b'\x0A')
                                uvs.append('vt '+str(utex)+' '+str(1-vtex)+' '+str(wtex)+b'\x0A')
                            if(bdv==72):
                                xcor,ycor,zcor,xnrm,ynrm,znrm,hui3,dsdssd,jjhfd,dsdssdd,utex,vtex,eee2d,ee,ee2,uk3,padd3,padd7=struct.unpack('<18f', nvs[0:72])
                                mcrd.append('v '+str(xcor)+' '+str(ycor)+' '+str(zcor)+b'\x0A')
                                uvs.append('vt '+str(utex)+' '+str(1-vtex)+' '+str(0)+b'\x0A')
                        for i in range(0,fc):
                            if(bitd2==16):
                                nfc=f.read((bitd2/8)*3)
                                if(len(nfc)==6):
                                    idx1,idx2,idx3=struct.unpack('<3H', nfc[0:6])
                                    fces.append('f '+str(idx1+1)+'/'+str(idx1+1)+'/'+str(idx1+1)+' '+str(idx2+1)+'/'+str(idx2+1)+'/'+str(idx2+1)+' '+str(idx3+1)+'/'+str(idx3+1)+'/'+str(idx3+1)+b'\x0A')
                                else:
                                   break
                            if(bitd2==32):
                                nfc=f.read((bitd2/8)*3)
                                if(len(nfc)==12):
                                    idx1,idx2,idx3=struct.unpack('<3I',nfc[0:12])
                                    fces.append('f '+str(idx1+1)+'/'+str(idx1+1)+'/'+str(idx1+1)+' '+str(idx2+1)+'/'+str(idx2+1)+'/'+str(idx2+1)+' '+str(idx3+1)+'/'+str(idx3+1)+'/'+str(idx3+1)+b'\x0A')
                                else:
                                    break
                        break
            f.close()
            for xt in range(0,vt):
                fobj.write(mcrd[xt])
            fobj.write(b'\x0A')
            #for xtt in range(0,vt):
                #fobj.write(nrmls[xtt])
            #fobj.write(b'\x0A')
            #for xi in range(0,vt):
                #fobj.write(uvs[xi])
            #fobj.write(b'\x0A')
            fcsd=fc/3
            for tt in range(0,ntex):
                fobj.write('g '+objname+'_'+str(tt)+b'\x0A')
                if(tt==0):
                    print 'succ'
                    for xz in range(0,fcsd/ntex):
                        fobj.write(fces[xz])
                    fobj.write(b'\x0A')
                if(tt==1):
                    print 'succ2'
                    for xzz in range(fcsd/ntex,fcsd/ntex+fcsd/ntex):
                        fobj.write(fces[xzz])
                    fobj.write(b'\x0A')
                if(tt==2):
                    print 'succ3'
                    for xzzz in range(fcsd/ntex+fcsd/ntex,fcsd/ntex+fcsd/ntex+fcsd/ntex):
                        fobj.write(fces[xzzz])
                    fobj.write(b'\x0A')
        fobj.close()
                            
                        
                        





















                            
