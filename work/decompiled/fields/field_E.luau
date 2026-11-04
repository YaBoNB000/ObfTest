-- field E  (347 chars, kind=function)
E=function(R,R,F,Y,d,L,O,k,v,y,K,c)if O<=31 then if O<=30 then local s,r=y-128,(k-128)*16384;local k=L*128+(r+s);return 160,d,c,K+3,Y,k;else v[K]=Y;return 86,d,c,K,Y,y;end;elseif O<=32 then return 132,d,c,1+K,Y,y;elseif O<=33 then local L=F+(Y-128)*128;return 31,d+2,c,K,L,y;else local F,L=c-128,16384*(R-128);return 19,d,F+Y*128+L,3+K,Y,y;end;end
