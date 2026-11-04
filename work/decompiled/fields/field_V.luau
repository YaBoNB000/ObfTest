-- field V  (328 chars, kind=function)
V=function(R,R,F,Y,d,L,O,k,v)if R<=67 then local y=(L-128)*128+v;return 14,d+2,Y,O,y;elseif R<=68 then local R=O-128;local v=(k-128)*16384+(R+128*L);return 7,3+d,Y,v,L;else local R,k,v=F[1],F[4],F[3];local y,K=R+k,k<=0;k,R=y>=v,y<=v;v=K and k or not K and R;F[1]=y;if v then return 84,d,y,O,L;else return 105,d,Y,O,L;end;end;end
