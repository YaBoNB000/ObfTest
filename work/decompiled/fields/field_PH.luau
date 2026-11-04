-- field PH  (250 chars, kind=function)
PH=function(R,F,Y,d,L,O,k,v,y)if L<=0 then local L,K=O-128,(Y-128)*16384;local Y=L+(128*d+K);return 20,3+F,Y,d;else local Y,L,K=R[53](k,F+3),2097152*(d-128),128*(y-128);local R=(v-128)*16384+(K+(Y%128+(2097152*(Y-Y%128)+L)));return 39,F+4,O,R;end;end
