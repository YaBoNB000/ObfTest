-- field UH  (200 chars, kind=function)
UH=function(R,F,Y,d,L,O,k)if Y<=18 then local Y=R[53](F,3+O);local R,F,v,y=(k-128)*2097152,128*(d-128),16384*(L-128),Y%128;local d=2097152*(Y-Y%128)+(v+y+F)+R;return 24,O+4,d;else return 7,O,k;end;end
