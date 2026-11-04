-- field m  (329 chars, kind=function)
m=function(R,F,Y,d,L,O,k,v,y)if d<=16 then if d<=15 then local K=v-128;local c=16384*(F-128)+(128*k+K);return 107,3+y,L,O,c;else return 25,y+1,L,O,v;end;elseif d<=17 then local F=R[53](Y,y);return 128>F and 129 or 126,y,L,F,v;elseif d<=18 then return 7,y+1,L,O,v;else local F=R[53](Y,y);return 128>F and 26 or 112,y,F,O,v;end;end
