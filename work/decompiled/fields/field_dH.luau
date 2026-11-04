-- field dH  (286 chars, kind=function)
dH=function(R,F,Y,d,L,O,k)if k<=2 then local v=R[53](F,3+L);local y,K,c,s,r=2097152*(d-128),(Y-128)*128,(O-128)*16384,v%128,v%128;local Y=2097152*(v-r);v=K+(c+s)+(Y+y);return 2,20,4+L,v,O;elseif k<=3 then local Y=R[53](F,1+L);return 2,not(128<=Y)and 22 or 31,L,d,Y;else return 1;end;end
