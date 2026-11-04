-- field x  (274 chars, kind=function)
x=function(R,F,Y,d,L,O,k,v,y,K,c)if O<=116 then local s,r=K-128,(k-128)*16384;return 152,L*128+(r+s),Y+3,c,d,y;elseif O<=117 then local O=R[53](L,c);return not(128>O)and 63 or 70,L,Y,c,d,O;else local R,O=d-128,16384*(F-128);local F=R+(128*v+O);return 132,L,Y,c+3,F,y;end;end
