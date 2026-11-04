-- field hH  (300 chars, kind=function)
hH=function(R,F,Y,d,L,O,k,v,y,K)if K<=15 then local c,s=R[70](F,O),R[53](F,4+O);local R=4294967296*s+c;local r=Y[R];if not r then return 7,F,c,s,R,k;else return 10,F,r,d,v,k;end;elseif K<=16 then return 23,F+1,O,d,v,k;else local R,Y=k-128,16384*(L-128);local L=R+y*128+Y;return 39,F+3,O,d,v,L;end;end
