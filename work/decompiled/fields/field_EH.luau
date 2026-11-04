-- field EH  (176 chars, kind=function)
EH=function(R,F,Y,d,L,O,k,v)if O<=5 then local O,y=L-128,(d-128)*16384;local d=128*F+(O+y);return 24,3+k,d,v;else local F=R[53](Y,2+k);return not(128>F)and 2 or 0,k,L,F;end;end
