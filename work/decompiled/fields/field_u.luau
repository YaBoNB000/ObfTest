-- field u  (351 chars, kind=function)
u=function(R,F,Y,d,L,O,k,v,y,K,c)if v<=75 then local s=R[53](Y,K);return not(128<=s)and 141 or 102,K,L,y,s;elseif v<=76 then local v=R[53](Y,3+K);local R,Y,s,r,G=(L-128)*2097152,128*(k-128),(O-128)*16384,v%128,v%128;local O=(v-G)*2097152;v=R+r+(s+Y+O);return 25,K+4,v,y,F;else local R=y-128;local Y=16384*(c-128)+(128*d+R);return 151,3+K,L,Y,F;end;end
