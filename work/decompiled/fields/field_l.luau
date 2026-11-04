-- field l  (303 chars, kind=function)
l=function(R,F,Y,d,L,O,k,v,y,K)if d<=47 then local c=(O-128)*128+v;return 17,2+F,c,Y,y;elseif d<=48 then local d=R[53](L,F+2);return 128>d and 77 or 120,F,O,d,y;else local d,v,c=R[53](L,F+3),(y-128)*2097152,(k-128)*128;local R=16384*(K-128)+(d%128+(c+((d-d%128)*2097152+v)));return 117,F+4,O,Y,R;end;end
