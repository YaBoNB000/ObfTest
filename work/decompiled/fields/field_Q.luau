-- field Q  (287 chars, kind=function)
Q=function(R,F,Y,d,L,O,k)if k<=1 then if k<=0 then local v=R[53](Y,d);return 128>v and 81 or 52,d,F,L,v;else local v=R[53](Y,L+2);return not not(128<=v)and 115 or 161,d,v,L,O;end;elseif k<=2 then return 89,d,F,L+1,O;elseif k<=3 then return 132,d,F,L+4,O;else return 156,1+L,F,L,O;end;end
