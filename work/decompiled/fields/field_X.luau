-- field X  (353 chars, kind=function)
X=function(R,F,Y,d,L,O,k,v,y,K,c)if Y<=78 then local s,r=y-128,16384*(O-128);local O=s+128*d+r;return 89,F,3+k,c,K,O;elseif Y<=79 then local Y=R[53](v,3+F);local d,O,s,r,G=2097152*(c-128),(K-128)*128,(L-128)*16384,Y%128,Y%128;local L=2097152*(Y-G);Y=r+(s+O+L+d);return 31,4+F,k,Y,K,y;else local Y=R[53](v,2+F);return 128>Y and 97 or 20,F,k,c,Y,y;end;end
