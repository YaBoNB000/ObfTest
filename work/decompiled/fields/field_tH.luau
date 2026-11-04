-- field tH  (290 chars, kind=function)
tH=function(R,F,Y,d,L,O,k,v)if d<=1 then if d<=0 then local y=R[53](F,1+O);return 128>y and 10 or 32,O,Y,y;else return 3,O,Y,v;end;elseif d<=2 then local R=Y-128;local F=(k-128)*16384+v*128+R;return 24,3+O,F,v;else local R=L[6];if not R then return 27,O,Y,v;else return 19,R,Y,v;end;end;end
