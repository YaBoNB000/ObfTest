-- field HH  (334 chars, kind=function)
HH=function(R,F,Y,d,L,O,k,v,y)if y<=26 then local K=R[53](d,L);return 128>K and 42 or 32,v,d,Y,L,O,F,K;elseif y<=27 then local y=v[2];R.F=L;local K,c,s=R.F,R[34],{};local r,G=R[53](K,c),c+1;s[7]=r~=0;r=R[53](K,G);return not not(128<=r)and 33 or 41,y,K,s,G,r,F,k;else local F=R[53](d,L+1);return 128>F and 13 or 6,v,d,Y,L,O,F,k;end;end
