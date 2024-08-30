import struct,os,binascii

for files in os.listdir('.'):
    if (os.path.isfile(files)==True) and (files.endswith('.sfm')==True):
        if not os.path.isdir('obj'): os.mkdir('obj')
        try:
	        fobj=file('obj/'+files+'.obj','wb')
	        fmtl=file('obj/'+files+'.mtl','wb')
	        fobj.write(b'\x23\x20\x57\x61\x76\x65\x46\x72\x6F\x6E\x74\x20\x2A\x2E\x6F\x62\x6A\x20\x66\x69\x6C\x65\x0A\x0A')
	        fobj.write('mtllib '+files+'.mtl'+b'\x0A\x0A')
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
	            f.read(52)
	            for x in xrange(0,ntex):
	                if(tga==5) and (nMapX==1):
	                    n8=f.read(20)
	                    texno,btri,etri,bvert,evert=struct.unpack('<5L', n8[0:20])
	                    texinfo[x] = texno,btri,etri,bvert,evert
	                    tbx=binascii.hexlify(f.read(4))
	                    tb=struct.unpack('<4B', tbx.decode('hex'))[0]
	                    if(tb==0):
	                        f.read(20)
	                        break
	                    if(tb==1):
	                        f.read(52)
	                        break
	                    tf[x]=f.read(tb-4)
	                    f.read(4)
	                    fmtl.write(b'\x0A'+'newmtl '+objname+'_'+str(x)+b'\x0A')
	                    fmtl.write(b'\x09'+'Ns 10.0000'+b'\x0A')
	                    fmtl.write(b'\x09'+'Ni 1.5000'+b'\x0A')
	                    fmtl.write(b'\x09'+'d 0.0000'+b'\x0A')
	                    fmtl.write(b'\x09'+'Tr 0.0000'+b'\x0A')
	                    fmtl.write(b'\x09'+'Tf 1.0000 1.0000 1.0000'+b'\x0A')
	                    fmtl.write(b'\x09'+'illum 2'+b'\x0A')
	                    fmtl.write(b'\x09'+'Ka 0.5880 0.5880 0.5880'+b'\x0A')
	                    fmtl.write(b'\x09'+'Kd 0.5880 0.5880 0.5880'+b'\x0A')
	                    fmtl.write(b'\x09'+'Ks 0.0000 0.0000 0.0000'+b'\x0A')
	                    fmtl.write(b'\x09'+'Ke 0.0000 0.0000 0.0000'+b'\x0A')
	                    
	                    fmtl.write(b'\x09'+'map_Ka ')
	                    fmtl.write('tex'+b'\x5C')
	                    fmtl.write(tf[x]+'dds'+b'\x0A')

	                    fmtl.write(b'\x09'+'map_Kd ')
	                    fmtl.write('tex'+b'\x5C')
	                    fmtl.write(tf[x]+'tex'+b'\x0A')
	                    
	                    if(x+1 < ntex):
	                        f.read(56)
	                    else:
	                        f.read(0)
	                        break
	                if(tga==4) and (nMapX==1):
	                    n8=f.read(20)
	                    texno,btri,etri,bvert,evert=struct.unpack('<5L', n8[0:20])
	                    texinfo[x] = texno,btri,etri,bvert,evert
	                    tbx=binascii.hexlify(f.read(4))
	                    tb=struct.unpack('<4B', tbx.decode('hex'))[0]
	                    if(tb==0):
	                        f.read(20)
	                        break
	                    if(tb==1):
	                        f.read(52)
	                        break
	                    tf[x]=f.read(tb-4)
	                    f.read(4)
	                    fmtl.write(b'\x0A'+'newmtl '+objname+'_'+str(x)+b'\x0A')
	                    fmtl.write(b'\x09'+'Ns 10.0000'+b'\x0A')
	                    fmtl.write(b'\x09'+'Ni 1.5000'+b'\x0A')
	                    fmtl.write(b'\x09'+'d 0.0000'+b'\x0A')
	                    fmtl.write(b'\x09'+'Tr 0.0000'+b'\x0A')
	                    fmtl.write(b'\x09'+'Tf 1.0000 1.0000 1.0000'+b'\x0A')
	                    fmtl.write(b'\x09'+'illum 2'+b'\x0A')
	                    fmtl.write(b'\x09'+'Ka 0.5880 0.5880 0.5880'+b'\x0A')
	                    fmtl.write(b'\x09'+'Kd 0.5880 0.5880 0.5880'+b'\x0A')
	                    fmtl.write(b'\x09'+'Ks 0.0000 0.0000 0.0000'+b'\x0A')
	                    fmtl.write(b'\x09'+'Ke 0.0000 0.0000 0.0000'+b'\x0A')
	                    
	                    fmtl.write(b'\x09'+'map_Ka ')
	                    fmtl.write('tex'+b'\x5C')
	                    fmtl.write(tf[x]+'dds'+b'\x0A')

	                    fmtl.write(b'\x09'+'map_Kd ')
	                    fmtl.write('tex'+b'\x5C')
	                    fmtl.write(tf[x]+'tex'+b'\x0A')
	                    
	                    
	                    if(x+1 < ntex):
	                        f.read(56)
	                    else:
	                        f.read(0)
	                        break
	                if(tga==4) and (nMapX==4):
	                    n8=f.read(20)
	                    texno,btri,etri,bvert,evert=struct.unpack('<5L', n8[0:20])
	                    texinfo[x] = texno,btri,etri,bvert,evert
	                    tbx=binascii.hexlify(f.read(4))
	                    tb=struct.unpack('<4B', tbx.decode('hex'))[0]
	                    tf[x]=f.read(tb-4)
	                    f.read(4)
	                    fmtl.write(b'\x0A'+'newmtl '+objname+'_'+str(x)+b'\x0A')
	                    fmtl.write(b'\x09'+'Ns 10.0000'+b'\x0A')
	                    fmtl.write(b'\x09'+'Ni 1.5000'+b'\x0A')
	                    fmtl.write(b'\x09'+'d 0.0000'+b'\x0A')
	                    fmtl.write(b'\x09'+'Tr 0.0000'+b'\x0A')
	                    fmtl.write(b'\x09'+'Tf 1.0000 1.0000 1.0000'+b'\x0A')
	                    fmtl.write(b'\x09'+'illum 2'+b'\x0A')
	                    fmtl.write(b'\x09'+'Ka 0.5880 0.5880 0.5880'+b'\x0A')
	                    fmtl.write(b'\x09'+'Kd 0.5880 0.5880 0.5880'+b'\x0A')
	                    fmtl.write(b'\x09'+'Ks 0.0000 0.0000 0.0000'+b'\x0A')
	                    fmtl.write(b'\x09'+'Ke 0.0000 0.0000 0.0000'+b'\x0A')
	                    
	                    fmtl.write(b'\x09'+'map_Ka ')
	                    fmtl.write('tex'+b'\x5C')
	                    fmtl.write(tf[x]+'tex'+b'\x0A')

	                    fmtl.write(b'\x09'+'map_Kd ')
	                    fmtl.write('tex'+b'\x5C')
	                    fmtl.write(tf[x]+'tex'+b'\x0A')
	                    
	                    
	                    if(x+1 < ntex):
	                        f.read(71)
	                    else:
	                        f.read(0)
	                        break
	                if(tga==5) and (nMapX==4):
	                    n8=f.read(20)
	                    texno,btri,etri,bvert,evert=struct.unpack('<5L', n8[0:20])
	                    texinfo[x] = texno,btri,etri,bvert,evert
	                    tbx=binascii.hexlify(f.read(4))
	                    tb=struct.unpack('<4B', tbx.decode('hex'))[0]
	                    tf[x]=f.read(tb-4)
	                    f.read(4)
	                    fmtl.write(b'\x0A'+'newmtl '+objname+'_'+str(x)+b'\x0A')
	                    fmtl.write(b'\x09'+'Ns 10.0000'+b'\x0A')
	                    fmtl.write(b'\x09'+'Ni 1.5000'+b'\x0A')
	                    fmtl.write(b'\x09'+'d 0.0000'+b'\x0A')
	                    fmtl.write(b'\x09'+'Tr 0.0000'+b'\x0A')
	                    fmtl.write(b'\x09'+'Tf 1.0000 1.0000 1.0000'+b'\x0A')
	                    fmtl.write(b'\x09'+'illum 2'+b'\x0A')
	                    fmtl.write(b'\x09'+'Ka 0.5880 0.5880 0.5880'+b'\x0A')
	                    fmtl.write(b'\x09'+'Kd 0.5880 0.5880 0.5880'+b'\x0A')
	                    fmtl.write(b'\x09'+'Ks 0.0000 0.0000 0.0000'+b'\x0A')
	                    fmtl.write(b'\x09'+'Ke 0.0000 0.0000 0.0000'+b'\x0A')
	                    
	                    fmtl.write(b'\x09'+'map_Ka ')
	                    fmtl.write('tex'+b'\x5C')
	                    fmtl.write(tf[x]+'tex'+b'\x0A')

	                    fmtl.write(b'\x09'+'map_Kd ')
	                    fmtl.write('tex'+b'\x5C')
	                    fmtl.write(tf[x]+'tex'+b'\x0A')
	                    
	                    
	                    if(x+1 < ntex):
	                        f.read(71)
	                    else:
	                        f.read(0)
	                        break
	                if(tga==7) and (nMapX==4): #NORMAL;NO ALPHA
	                    n8=f.read(20)
	                    texno,btri,etri,bvert,evert=struct.unpack('<5L', n8[0:20])
	                    texinfo[x] = texno,btri,etri,bvert,evert
	                    tbx=binascii.hexlify(f.read(4))
	                    tb=struct.unpack('<4B', tbx.decode('hex'))[0]
	                    tf[x]=f.read(tb-4)
	                    f.read(4)
	                    tbnx=binascii.hexlify(f.read(4))
	                    tbn=struct.unpack('<4B', tbnx.decode('hex'))[0]
	                    tn[x]=f.read(tbn-4)
	                    f.read(4)
	                    fmtl.write(b'\x0A'+'newmtl '+objname+'_'+str(x)+b'\x0A')
	                    fmtl.write(b'\x09'+'Ns 10.0000'+b'\x0A')
	                    fmtl.write(b'\x09'+'Ni 1.5000'+b'\x0A')
	                    fmtl.write(b'\x09'+'d 0.0000'+b'\x0A')
	                    fmtl.write(b'\x09'+'Tr 0.0000'+b'\x0A')
	                    fmtl.write(b'\x09'+'Tf 1.0000 1.0000 1.0000'+b'\x0A')
	                    fmtl.write(b'\x09'+'illum 2'+b'\x0A')
	                    fmtl.write(b'\x09'+'Ka 0.5880 0.5880 0.5880'+b'\x0A')
	                    fmtl.write(b'\x09'+'Kd 0.5880 0.5880 0.5880'+b'\x0A')
	                    fmtl.write(b'\x09'+'Ks 0.0000 0.0000 0.0000'+b'\x0A')
	                    fmtl.write(b'\x09'+'Ke 0.0000 0.0000 0.0000'+b'\x0A')
	                    
	                    fmtl.write(b'\x09'+'map_Ka ')
	                    fmtl.write('tex'+b'\x5C')
	                    fmtl.write(tf[x]+'tex'+b'\x0A')

	                    fmtl.write(b'\x09'+'map_Kd ')
	                    fmtl.write('tex'+b'\x5C')
	                    fmtl.write(tf[x]+'tex'+b'\x0A')

	                    fmtl.write(b'\x09'+'map_bump -bm 0.3000 ')
	                    fmtl.write('tex'+b'\x5C')
	                    fmtl.write(tn[x]+'tex'+b'\x0A')

	                    fmtl.write(b'\x09'+'bump -bm 0.3000 ')
	                    fmtl.write('tex'+b'\x5C')
	                    fmtl.write(tn[x]+'tex'+b'\x0A')

	                    
	                    
	                    if(x+1 < ntex):
	                        f.read(66)
	                    else:
	                        f.read(0)
	                        break
	                if(tga==8) and (nMapX==4): #NORMAL AND ALPHA
	                    n8=f.read(20)
	                    texno,btri,etri,bvert,evert=struct.unpack('<5L', n8[0:20])
	                    texinfo[x] = texno,btri,etri,bvert,evert
	                    tbx=binascii.hexlify(f.read(4))
	                    tb=struct.unpack('<4B', tbx.decode('hex'))[0]
	                    tf[x]=f.read(tb-4)
	                    f.read(4)
	                    tbnx=binascii.hexlify(f.read(4))
	                    tbn=struct.unpack('<4B', tbnx.decode('hex'))[0]
	                    tn[x]=f.read(tbn-4)
	                    f.read(9)
	                    tganx=binascii.hexlify(f.read(4))
	                    tgan=struct.unpack('<4B', tganx.decode('hex'))[0]
	                    tg[x]=f.read(tgan-4)
	                    f.read(4)
	                    fmtl.write(b'\x0A'+'newmtl '+objname+'_'+str(x)+b'\x0A')
	                    fmtl.write(b'\x09'+'Ns 10.0000'+b'\x0A')
	                    fmtl.write(b'\x09'+'Ni 1.5000'+b'\x0A')
	                    fmtl.write(b'\x09'+'d 0.0000'+b'\x0A')
	                    fmtl.write(b'\x09'+'Tr 0.0000'+b'\x0A')
	                    fmtl.write(b'\x09'+'Tf 1.0000 1.0000 1.0000'+b'\x0A')
	                    fmtl.write(b'\x09'+'illum 2'+b'\x0A')
	                    fmtl.write(b'\x09'+'Ka 0.5880 0.5880 0.5880'+b'\x0A')
	                    fmtl.write(b'\x09'+'Kd 0.5880 0.5880 0.5880'+b'\x0A')
	                    fmtl.write(b'\x09'+'Ks 0.0000 0.0000 0.0000'+b'\x0A')
	                    fmtl.write(b'\x09'+'Ke 0.0000 0.0000 0.0000'+b'\x0A')
	                    fmtl.write(b'\x09'+'map_Ka '+'tex'+b'\x5C'+tf[x]+'dds'+b'\x0A')
	                    fmtl.write(b'\x09'+'map_Kd '+'tex'+b'\x5C'+tf[x]+'dds'+b'\x0A')
	                    fmtl.write(b'\x09'+'map_bump -bm 0.3000 '+'tex'+b'\x5C'+tn[x]+'dds'+b'\x0A')
	                    fmtl.write(b'\x09'+'bump -bm 0.3000 '+'tex'+b'\x5C'+tn[x]+'dds'+b'\x0A')
	                    if(x+1 < ntex):
	                        f.read(56)
	                    else:
	                        f.read(0)
	                        break
	            uvs=[]
	            mcrd=[]
	            fces=[]
	            fmtl.close()
	            for x in range(0,128,1):
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
	                            if(bdv==60):
	                                xcor,ycor,zcor,xnrm,ynrm,znrm,padd,utex,vtex,wtex,padd2,uk1,uk2,uk3,padd3=struct.unpack('<15f', nvs[0:60])
	                                mcrd.append('v '+str(xcor)+' '+str(ycor)+' '+str(zcor)+b'\x0A')
	                                uvs.append('vt '+str(utex)+' '+str(1-vtex)+' '+str(wtex)+b'\x0A')
	                            if(bdv==68):
	                                xcor,ycor,zcor,xnrm,ynrm,znrm,padd,utex,vtex,wtex,padd2,uk1,uk2,uk3,padd3,padd4,padd5=struct.unpack('<17f', nvs[0:68])
	                                mcrd.append('v '+str(xcor)+' '+str(ycor)+' '+str(zcor)+b'\x0A')
	                                uvs.append('vt '+str(utex)+' '+str(1-vtex)+' '+str(wtex)+b'\x0A')
	                        for i in range(0,fc):
	                            if(bitd2==16):
	                                nfc=f.read((bitd2/8)*3)
	                                if(len(nfc)==6):
	                                    idx1,idx2,idx3=struct.unpack('<3H', nfc[0:6])
	                                    fces.append('f '+str(idx1+1)+'/'+str(idx1+1)+' '+str(idx2+1)+'/'+str(idx2+1)+' '+str(idx3+1)+'/'+str(idx3+1)+b'\x0A')
	                                else:
	                                   break
	                            if(bitd2==32):
	                                nfc=f.read((bitd2/8)*3)
	                                if(len(nfc)==12):
	                                    idx1,idx2,idx3=struct.unpack('<3I',nfc[0:12])
	                                    fces.append('f '+str(idx1+1)+'/'+str(idx1+1)+' '+str(idx2+1)+'/'+str(idx2+1)+' '+str(idx3+1)+'/'+str(idx3+1)+b'\x0A')
	                                else:
	                                    break
	                        break
	            f.close()
	            for tt in range(0,ntex):
	                bvert=texinfo[tt][3]
	                evert=texinfo[tt][4]
	                cvert=texinfo[tt][3]+texinfo[tt][4]-1
	                bface=texinfo[tt][1]
	                eface=texinfo[tt][2]
	                cface=texinfo[tt][1]+texinfo[tt][2]-1
	                fobj.write('g '+objname+'_'+str(texinfo[tt][0])+b'\x0A'+'usemtl '+objname+'_'+str(texinfo[tt][0])+b'\x0A')
	                for xt in range(bvert,bvert+evert):
	                    fobj.write(mcrd[xt])
	                fobj.write(b'\x0A')
	                for xi in range(bvert,bvert+evert):
	                    fobj.write(uvs[xi])
	                fobj.write(b'\x0A')
	                for xz in range(bface,bface+eface):
	                    fobj.write(fces[xz])
	                fobj.write(b'\x0A')
	        fobj.close()
        except Exception:
    		pass
                            
                        
                        





















                            
