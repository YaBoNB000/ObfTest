-- field g  (342 chars, kind=function)
g=function(R,F,Y,d,L,O,k,v,y,K,c)if y<=6 then if y<=5 then local s,r=K-128,(O-128)*16384;local O=128*Y+s+r;return 25,k+3,O,F;else local Y=R[53](L,1);return 128>Y and 85 or 90,Y,K,F;end;elseif y<=7 then c[v]=F;return 99,k,K,F;elseif y<=8 then local Y=R[53](L,k);return not not(Y>=128)and 111 or 18,k,K,Y;else return 83,k,R[53](L,1+d),F;end;end
