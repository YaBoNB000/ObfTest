-- field KH  (159 chars, kind=function)
KH=function(R,F,Y,d,L,O)if L<=32 then local L=R[53](Y,F+1);return not(128>L)and 8 or 38,O,L;else local L=R[53](Y,1+F);return not(128>L)and 21 or 35,L,d;end;end
