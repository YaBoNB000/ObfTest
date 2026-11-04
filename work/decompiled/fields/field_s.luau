-- field s  (335 chars, kind=function)
s=function(R,F,Y,d,L,O,k,v)if v<=10 then local v=R[53](d,3);local R,d,y,K,c=(O-128)*2097152,128*(F-128),16384*(L-128),v%128,v-v%128;local L,v=y+2097152*c,K+(R+d);return 82,L+v,4,k;else local R,d,L=Y[3],Y[5],Y[2];local v,y=R+d,d<=0;R,d=v>=L,v<=L;L=y and R or not y and d;Y[3]=v;if L then return 39,O,F,v;else return 21,O,F,k;end;end;end
