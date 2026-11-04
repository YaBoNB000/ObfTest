-- field N  (303 chars, kind=function)
N=function(R,F,Y,d,L,O,k,v,y)if L<=113 then local K=Y+128*(v-128);return 54,k,y,2+F,K;elseif L<=114 then local Y=R[53](O,F+1);return Y<128 and 51 or 1,k,Y,F,v;else local Y=R[53](O,3+F);local R,L,O,K=(k-128)*2097152,(y-128)*128,(d-128)*16384,Y%128;return 156,R+(2097152*(Y-Y%128)+L+(O+K)),4+F,F,v;end;end
