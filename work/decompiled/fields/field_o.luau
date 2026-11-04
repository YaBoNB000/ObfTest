-- field o  (345 chars, kind=function)
o=function(R,F,Y,d,L,O,k,v,y,K)if O<=98 then local c=R[53](d,1+v);return not not(c>=128)and 65 or 110,Y,k,c;elseif O<=99 then local R,d,O=F[1],F[5],F[2];local v,c=R+d,d<=0;d,R=v>=O,v<=O;O=c and d or not c and R;F[1]=v;if O then return 8,Y,k,v;else return 125,Y,k,y;end;else local R=k-128;local F=16384*(K-128)+(R+128*L);return 31,3+Y,F,y;end;end
