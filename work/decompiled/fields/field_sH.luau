-- field sH  (242 chars, kind=function)
sH=function(R,F,Y,d,L,O,k)if k<=31 then local k=R[53](Y,L+3);local v,y,K,c=(O-128)*2097152,(F-128)*128,(d-128)*16384,k%128;local F=K+(k-k%128)*2097152+v+(y+c);return 22,L+4,F,d;else local F=R[53](Y,L+2);return 128>F and 13 or 31,L,O,F;end;end
