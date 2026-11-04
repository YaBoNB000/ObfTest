-- field aH  (328 chars, kind=function)
aH=function(R,R,F,Y,d,L,O,k)if F<=39 then if F<=37 then return 25,R[3],k,O,L;elseif F<=38 then local v=(L-128)*128+Y;return 39,R,k+2,O,v;else d[O]=L;return 9,R,k,O,L;end;elseif F<=40 then local d,v=O-128,(L-128)*16384;local y=d+(Y*128+v);return 23,R,3+k,y,L;elseif F<=41 then return 24,R,1+k,O,L;else return 39,R,k+1,O,L;end;end
