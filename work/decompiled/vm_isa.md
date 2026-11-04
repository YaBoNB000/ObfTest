# Payload VM instruction set

Recovered mechanically from field `[49]` of the obfuscated chunk by
`tools/isa_extract.py` + `tools/vm_isatree.py` (which walk the real Luau
AST produced by `tools/astdump.cpp`). Nothing here is hand-transcribed:
every body is quoted from the source, so it can be re-derived and checked.

## How the dispatcher is layered

`[49]` is **not** one `if`-tree. It contains a main interpreter loop plus
three secondary dispatch loops, switched by a continuation marker `g`:

```lua
while true do local h=k[I]; ... end          -- h: the bytecode interpreter
if g==150 then while true do local v=k[I]   -- v: continuation loop
if g==102 then while true do local v=O[I]   -- v: second variant
if g==160 then while true do local Z=k[I]   -- Z: constant-pool loop
```

## Ranges that actually exist

The tables were rebuilt by walking each dispatch tree with the real value
interval, so we can say exactly which opcode values are reachable:

| dispatcher | reachable range | distinct opcodes | above the range |
|---|---|---:|---|
| `h` (interpreter) | 0..95 | **96**, all distinct | 96..255 collapse onto 2 padding bodies |
| `Z` (constant pool) | 0..29 | **30**, all distinct | 30..255 collapse onto 1 body |
| `v` (continuation) | 0..49 | **50**, all distinct | 50..255 collapse onto a few bodies |

96 real opcodes is exactly what an 8-bit opcode byte with a *sparse*
encoding looks like: the loader never emits a value it has no handler for,
and the obfuscator filled the unused tail of the tree with a couple of
junk branches so that the tree still spans 0..255 and hides the real
extent. `h=94` is a deliberate hole (its handler body is empty).

## Register file

Instruction words are unpacked into parallel arrays by the loader
(`k[I]` is the opcode byte; the `SUPEROP/*` handlers below do the
unpacking with the 32-bit multiply helper). Handlers read:

| word | role |
|---|---|
| `L`,`O`,`s`,`k` | operand fields of the current instruction |
| `r`,`c`,`Y` | constant-pool / upvalue indices |
| `e` | the register stack (values) |
| `X` | upvalue objects (`X[n][6][n][5]` is the captured cell) |
| `I` | instruction pointer |
| `g` | continuation marker (150 / 102 / 160) |

## Dispatcher `h` — bytecode interpreter (0..95)

| # | mnemonic | handler body (verbatim from `[49]`) |
|---:|---|---|
| 0 | `CALL0 O` | `e[O[I]]()` |
| 1 | `SUPEROP/load` | `H,m=s[I],O[I]+1;for T=1,L[I],1 do H=P(Q(H,(w(H,13))),536870911);H=Q(H,(U(H,13)));H=P(Q(H,(w(H,14))),536870911);s[m]=Q(s[m],(P(U(H,0),127)));O[m]=Q(O[m],(P(U(H,7),127)));L[m]=Q(L[m],(P(U(H,14),127)));k[m]=Q(k[m],(P(U(H,21),127)));m=m+1;end;k[I]=94` |
| 2 | `CMP L O < s` | `e[L[I]]=e[O[I]]<s[I]` |
| 3 | `SETTABLE L [key] O` | `e[L[I]][s[I]]=e[O[I]]` |
| 4 | `ADD O C K` | `e[O[I]]=Y[I]+c[I]` |
| 5 | `CLOSURE` | `a,m,H={[5]=F,[8]=a,[6]=b,[7]=G},s[I],V(p);H(R,e[m],e[m+1],e[m+2]);I,F=L[I],H` |
| 6 | `IDIV O L s` | `e[O[I]]=e[L[I]]//e[s[I]]` |
| 7 | `CMP L s ~= O` | `e[L[I]]=e[s[I]]~=O[I]` |
| 8 | `JUMP s` | `I=e[s[I]]` |
| 9 | `GETIMPORT O` | `e[O[I]]=R[L[I]]` |
| 10 | `GETUPVAL` | `m=X[L[I]];e[O[I]]=m[6][m[5]]` |
| 11 | `SETUPVALIDX` | `m=X[s[I]];m[6][m[5]][e[O[I]]]=e[L[I]]` |
| 12 | `CMP O s <= L` | `e[O[I]]=e[s[I]]<=L[I]` |
| 13 | `CMP L O > s` | `e[L[I]]=e[O[I]]>s[I]` |
| 14 | `VARARG` | `m,H={...},L[I];i(m,1,O[I],H,e)` |
| 15 | `CMP L s >= O` | `e[L[I]]=e[s[I]]>=e[O[I]]` |
| 16 | `JUMPIF <` | `I=if O[I]<e[s[I]]then L[I]else I` |
| 17 | `--` | `e[L[I]]=e[s[I]]()` |
| 18 | `TAILCALL/JUMP` | `g=O[I];I=L[I]+1;break` |
| 19 | `TOSTRING s` | `e[s[I]]=u(O[I])` |
| 20 | `JUMPIF <` | `I=if e[s[I]]<L[I]then O[I]else I` |
| 21 | `SETTABLE L [key] s` | `e[L[I]][e[O[I]]]=e[s[I]]` |
| 22 | `LOAD s s` | `e[s[I]]=s` |
| 23 | `LOAD L r` | `e[L[I]]=r[I]` |
| 24 | `CALLVAR/unc` | `m=L[I];local T,Rq,Fq=F();if T then e[m+1]=Rq;e[m+2]=Fq;I=s[I];else end;H,M,N=T,Rq,Fq` |
| 25 | `SUB O L s` | `e[O[I]]=e[L[I]]-s[I]` |
| 26 | `--` | `e[O[I]]=e[L[I]](c[I])` |
| 27 | `--` | `e[s[I]]=e[L[I]][e[O[I]]]` |
| 28 | `SUPEROP/decode` | `H,m=(Q(O[I],(P(Q(B,(P(U(B,29),7))),536870911)))),s[I]+1;for T=1,L[I],1 do H=P(Q(H,(w(H,13))),536870911);H=Q(H,(U(H,13)));H=P(Q(H,(w(H,14))),536870911);s[m]=Q(s[m],(P(U(H,0),127)));O[m]=Q(O[m],(P(U(H,7),127)));L[m]=Q(L[m],(P(U(H,14),127)));k[m]=Q(k[m],(P(U(H,21),127)));m=m+1;end;k[I]=94` |
| 29 | `CALL/UNPACK` | `m,H,M,N=Q(J,P(U(J,14),262143),(P(U(J,28),15))),O[I],s[I],L[I];C=N<2097152 and 7 or 14;z,j=P(N,w(1,C)-1),U(N,C);k[I]=Q(j,43,(P(U(m,21),127)));s[I]=Q(M,117,(P(m,127)));O[I]=Q(H,3,(P(U(m,7),127)));L[I]=Q(z,13,(P(U(m,14),127)));I=I-1` |
| 30 | `CALL1 L` | `e[L[I]](e[O[I]])` |
| 31 | `ADD L s O` | `e[L[I]]=e[s[I]]+O[I]` |
| 32 | `--` | `e[L[I]]=X[O[I]]` |
| 33 | `JUMPIF <=` | `I=if e[O[I]]<=s[I]then L[I]else I` |
| 34 | `--` | `e[O[I]]=e[s[I]][L[I]]` |
| 35 | `SETUPVAL` | `m=X[s[I]];m[6][m[5]]=e[O[I]]` |
| 36 | `FLOOR/tonumber` | `local T,Rq,Fq=s[I],e[O[I]];repeat local Yq=Rq%4294967296;if Yq~=Yq then Fq=0;break;end;Fq=Yq-Yq%1;until true;e[T]=Fq` |
| 37 | `--` | `e[L[I]]=e[s[I]]*r[I]` |
| 38 | `--` | `e[s[I]]=e[O[I]](e[L[I]])` |
| 39 | `CMP L s == O` | `e[L[I]]=e[s[I]]==e[O[I]]` |
| 40 | `MOD O L s` | `e[O[I]]=e[L[I]]%e[s[I]]` |
| 41 | `SUB O s L` | `e[O[I]]=e[s[I]]-e[L[I]]` |
| 42 | `MULTI` | `e[L[I]]=e[s[I]];e[L[I+1]]=e[s[I+1]];I+=1` |
| 43 | `--` | `e[O[I]]=y` |
| 44 | `CMP L s == O` | `e[L[I]]=e[s[I]]==O[I]` |
| 45 | `LOAD O B` | `e[O[I]]=B` |
| 46 | `SETUPVALIDX` | `m=X[O[I]];m[6][m[5]][e[L[I]]]=c[I]` |
| 47 | `IDIV O s L` | `e[O[I]]=e[s[I]]//L[I]` |
| 48 | `--` | `B=e[s[I]]` |
| 49 | `FLOOR/tonumber` | `local T,Rq,Fq=O[I],e[s[I]],L[I];local Yq,dq=P(Rq,4294967295),P(Fq,4294967295);local Rq,Fq,Lq,Oq=P(Yq,65535),U(Yq,16),P(dq,65535),U(dq,16);dq=P(Rq*Lq+w(P(Rq*Oq+Fq*Lq,65535),16),4294967295);Oq=nil;repeat Fq=dq%4294967296;if Fq~=Fq then Oq=0;break;end;Oq=Fq-Fq%1;until true;e[T]=Oq` |
| 50 | `GETIMPORT L` | `e[L[I]]=R[c[I]]` |
| 51 | `MULTI` | `e[s[I]]=L[I];e[L[I+1]]=e[s[I+1]];I+=1` |
| 52 | `--` | `local T;local Rq=r[I];if Rq then local Fq=#Rq/3;if Fq>0 then T={};local Yq,dq=A,x;for Lq=1,Fq,1 do local Fq=(Lq-1)*3;local Oq,kq=Rq[Fq+3],Rq[Fq+2];if Oq==1 then Yq=if not Yq then{}else Yq;local vq=Yq[kq];if not vq then vq={[6]=e,[5]=kq};Yq[kq]=vq;else end;T[Lq]=vq;else if Oq==0 then T[Lq]=e[kq];else if Oq==2 then T[Lq]=X[kq];else if Oq==3 then dq=if not dq then{}else dq;local Oq=dq[kq];if not Oq then Oq={[4]=Rq[Fq+1],[5]=kq,[6]=e};dq[kq]=Oq;else end;T[Lq]=Oq;else end;end;end;end;end;A,x=Yq,dq;else end;else end;H=Y[I](nil,T);l(H,Z);e[s[I]]=H;m=T` |
| 53 | `JUMPIF ==` | `I=if e[O[I]]==s[I]then L[I]else I` |
| 54 | `--` | `e[L[I]]=s[I]-e[O[I]]` |
| 55 | `SUB O L C` | `e[O[I]]=e[L[I]]-c[I]` |
| 56 | `--` | `m,H,M=L[I],s[I],O[I];N=m+H;e[m]=o(e[m](f(e,m+1,N)))` |
| 57 | `FLOOR/tonumber` | `local T,Rq,Fq=s[I],Q(O[I],(P(Q(B,(P(U(B,29),7))),536870911))),y[5];local Yq=Q(Fq[T],535359694);Fq[T]=Yq;Fq,T=y[4],Yq+1;Yq=n(Fq,T);local dq,Lq;if Yq<128 then dq,Lq=Yq,T+1;else local Oq=n(Fq,T+1);if Oq<128 then dq,Lq=(Yq-128)*128+Oq,T+2;else local kq=n(Fq,T+2);if kq<128 then dq,Lq=Yq-128+(Oq-128)*16384+kq*128,T+3;else local vq=n(Fq,T+3);dq,Lq=(Yq-128)*2097152+(Oq-128)*128+(kq-128)*16384+vq%128+(vq-vq%128)*2097152,T+4;end;end;end;T,Yq=Rq*16843009,Lq+dq;local Oq=Yq-dq%4;for dq=Lq,Oq-1,4 do t(Fq,dq,(Q(_(Fq,dq),T)));end;for T=Oq,Yq-1,1 do S(Fq,T,(Q(n(Fq,T),Rq)));end;s[I]=140;O[I]=162;L[I]=209;k[I]=94` |
| 58 | `--` | `m=X[L[I]];e[s[I]]=m[6][m[5]][e[O[I]]]` |
| 59 | `--` | `m=X[s[I]];m[6][m[5]]=Y[I]` |
| 60 | `LOAD O J` | `e[O[I]]=J` |
| 61 | `--` | `m,H,M=O[I],s[I],L[I];N=e[m];i(e,m+1,m+H,M+1,N)` |
| 62 | `MOD O L s` | `e[O[I]]=e[L[I]]%s[I]` |
| 63 | `ADD L O C` | `e[L[I]]=e[O[I]]+c[I]` |
| 64 | `CMP O s <= L` | `e[O[I]]=e[s[I]]<=e[L[I]]` |
| 65 | `--` | `F,G,b=a[5],a[7],a[6];a=a[8]` |
| 66 | `MUL L O s` | `e[L[I]]=e[O[I]]*s[I]` |
| 67 | `FLOOR/tonumber` | `local T,Rq,Fq=L[I],e[s[I]],e[O[I]];local Yq,dq=P(Rq,4294967295),P(Fq,4294967295);local Rq,Lq,Oq,kq=P(Yq,65535),U(Yq,16),P(dq,65535),U(dq,16);Fq=P(Rq*Oq+w(P(Rq*kq+Lq*Oq,65535),16),4294967295);Oq=nil;repeat dq=Fq%4294967296;if dq~=dq then Oq=0;break;end;Oq=dq-dq%1;until true;e[T]=Oq` |
| 68 | `CALL/UNPACK` | `m,H,M,N=O[I],L[I],s[I],Q(J,P(U(J,14),262143),(P(U(J,28),15)));C=m<16384 and 7 or(m<2097152 and 14 or 21);z,j=P(m,w(1,C)-1),U(m,C);O[I]=Q(z,58,(P(U(N,7),127)));L[I]=Q(H,54,(P(U(N,14),127)));s[I]=Q(M,75,(P(N,127)));k[I]=Q(j,75,(P(U(N,21),127)));I=I-1` |
| 69 | `CLOSEUPVAL` | `local T=L[I];if A then local Rq=A[T];if Rq then Rq[6]=Rq;Rq[4]=e[T];Rq[5]=4;A[T]=nil;end;end` |
| 70 | `--` | `m,H,M=s[I],{...},L[I];i(H,1,m-1,M,e);e[M+m-1]=o(T(m,...))` |
| 71 | `--` | `m,H=O[I],L[I];M={n=H-m+1};i(e,m,H,1,M);e[s[I]]=M` |
| 72 | `--` | `e[O[I]]=R` |
| 73 | `CMP s L >= O` | `e[s[I]]=e[L[I]]>=O[I]` |
| 74 | `FLOOR/tonumber` | `local T,Rq,Fq=O[I],s[I],y[5];local Yq=Q(Fq[T],535359694);Fq[T]=Yq;T,Fq=y[4],Yq+1;Yq=n(T,Fq);local dq,Lq;if Yq<128 then dq,Lq=Yq,Fq+1;else local Oq=n(T,Fq+1);if Oq<128 then dq,Lq=(Yq-128)*128+Oq,Fq+2;else local kq=n(T,Fq+2);if kq<128 then dq,Lq=Yq-128+(Oq-128)*16384+kq*128,Fq+3;else local vq=n(T,Fq+3);dq,Lq=(Yq-128)*2097152+(Oq-128)*128+(kq-128)*16384+vq%128+(vq-vq%128)*2097152,Fq+4;end;end;end;Yq,Fq=Rq*16843009,Lq+dq;local Oq=Fq-dq%4;for dq=Lq,Oq-1,4 do t(T,dq,(Q(_(T,dq),Yq)));end;for Yq=Oq,Fq-1,1 do S(T,Yq,(Q(n(T,Yq),Rq)));end;O[I]=112;s[I]=103;L[I]=0;k[I]=94` |
| 75 | `LOAD L O` | `e[L[I]]=O` |
| 76 | `--` | `e[s[I]]=e[O[I]]>=Y[I]` |
| 77 | `JUMPIF` | `I=if e[O[I]]then L[I]else s[I]` |
| 78 | `--` | `e[L[I]]=e[s[I]](f(e[O[I]],1,e[O[I]].n))` |
| 79 | `NEWTABLE O` | `e[O[I]]={}` |
| 80 | `NOT s L` | `e[s[I]]=not e[L[I]]` |
| 81 | `FLOOR/tonumber` | `local T,Rq,Fq=L[I],r[I],e[s[I]];local Yq,dq=P(Rq,4294967295),P(Fq,4294967295);local Rq,Fq,Lq,Oq=P(Yq,65535),U(Yq,16),P(dq,65535),U(dq,16);Yq=P(Rq*Lq+w(P(Rq*Oq+Fq*Lq,65535),16),4294967295);dq=nil;repeat Lq=Yq%4294967296;if Lq~=Lq then dq=0;break;end;dq=Lq-Lq%1;until true;e[T]=dq` |
| 82 | `MOVE L s` | `e[L[I]]=e[s[I]]` |
| 83 | `--` | `J=e[O[I]]` |
| 84 | `ADD s I O` | `e[s[I]]=L[I]+e[O[I]]` |
| 85 | `CMP O L == c` | `e[O[I]]=e[L[I]]==c[I]` |
| 86 | `RETURN/CALLVAR` | `m,H,M=s[I],O[I],L[I];N,C,z=m+M-1,m+H,o(e[m](f(e,m+1,m+H)));i(z,1,M,m,e)` |
| 87 | `LOAD s L` | `e[s[I]]=L[I]` |
| 88 | `CALL2 s` | `e[s[I]](Y[I],r[I])` |
| 89 | `--` | `I=s[I]` |
| 90 | `MUL L s O` | `e[L[I]]=e[s[I]]*e[O[I]]` |
| 91 | `UNM L O` | `e[L[I]]=-e[O[I]]` |
| 92 | `CALL R M N` | `m=s[I];H,M,N=e[m],e[m+1],e[m+2];e[m]=H(M,N)` |
| 93 | `--` | `e[L[I]]=r[I]+e[s[I]]` |
| 94 | `NOP` | `(empty)` |
| 95 | `SUPEROP/decode` | `H,m=(Q(O[I],(P(Q(J,(P(U(J,29),7))),536870911)))),s[I]+1;for T=1,L[I],1 do H=P(Q(H,(w(H,13))),536870911);H=Q(H,(U(H,13)));H=P(Q(H,(w(H,14))),536870911);s[m]=Q(s[m],(P(U(H,0),127)));O[m]=Q(O[m],(P(U(H,7),127)));L[m]=Q(L[m],(P(U(H,14),127)));k[m]=Q(k[m],(P(U(H,21),127)));m=m+1;end;k[I]=94` |

*72 of 96 rows have an inferred mnemonic; the rest are genuine multi-step handlers listed verbatim.*

## Dispatcher `Z` — constant-pool loop (0..29)

| # | mnemonic | handler body (verbatim from `[49]`) |
|---:|---|---|
| 0 | `GETIMPORT O` | `e[O[I]]=R[L[I]]` |
| 1 | `SUB L O s` | `e[L[I]]=e[O[I]]-e[s[I]]` |
| 2 | `CALLVAR` | `m,H,M=O[I],L[I],s[I];N,C,z=m+M-1,m+H,o(e[m](f(e,m+1,m+H)));i(z,1,M,m,e)` |
| 3 | `CALL0 O` | `e[O[I]]()` |
| 4 | `LOADK D` | `D=e[L[I]]` |
| 5 | `GETIMPORT L` | `e[L[I]]=R[r[I]]` |
| 6 | `SETUPVAL` | `m=X[L[I]];m[6][m[5]]=e[O[I]]` |
| 7 | `--` | `if A then for F in q,A,nil do if A then W=A[F];if W then W[6]=W;W[4]=e[F];W[5]=4;A[F]=nil;end;end;end;end;if x then for F,d in q,x,nil do E=d[4];if x then local d=x[F];if d then local k,v=F+E,u(E);i(e,F,k-1,1,v);d[6]=v;d[5]=1;x[F]=nil;end;end;end;end;return` |
| 8 | `--` | `local F=O[I];if A then local d=A[F];if d then d[6]=d;d[4]=e[F];d[5]=4;A[F]=nil;end;end` |
| 9 | `NOT L s` | `e[L[I]]=not e[s[I]]` |
| 10 | `MOVE O L` | `e[O[I]]=e[L[I]]` |
| 11 | `--` | `R[s[I]]=e[L[I]]` |
| 12 | `JUMPIF` | `I=if e[L[I]]then s[I]else O[I]` |
| 13 | `--` | `if A then for F in q,A,nil do if A then local d=A[F];if d then d[6]=d;d[4]=e[F];d[5]=4;A[F]=nil;end;end;end;end;if x then for F,d in q,x,nil do local k=d[4];if x then local d=x[F];if d then local v=u(k);i(e,F,F+k-1,1,v);d[6]=v;d[5]=1;x[F]=nil;end;end;end;end;return e[L[I]](f(e[s[I]],1,e[s[I]].n))` |
| 14 | `LOAD s L` | `e[s[I]]=L[I]` |
| 15 | `LOAD L D` | `e[L[I]]=D` |
| 16 | `--` | `if A then for R in q,A,nil do if A then local F=A[R];if F then F[6]=F;F[4]=e[R];F[5]=4;A[R]=nil;end;end;end;end;if x then for R,F in q,x,nil do local Y=F[4];if x then local F=x[R];if F then local d=u(Y);i(e,R,R+Y-1,1,d);F[6]=d;F[5]=1;x[R]=nil;end;end;end;end;return e[s[I]]` |
| 17 | `--` | `m=X[O[I]];m[6][m[5]]=c[I]` |
| 18 | `ADD s O L` | `e[s[I]]=e[O[I]]+L[I]` |
| 19 | `ADD s O L` | `e[s[I]]=e[O[I]]+e[L[I]]` |
| 20 | `CALL2 L` | `e[L[I]](r[I],c[I])` |
| 21 | `NUMFLOOR` | `local R,F,Y=L[I],e[s[I]];repeat local d=F%4294967296;if d~=d then Y=0;break;end;Y=d-d%1;until true;e[R]=Y` |
| 22 | `JUMP O` | `I=e[O[I]]` |
| 23 | `--` | `if A then for F in q,A,nil do if A then local d=A[F];if d then d[6]=d;d[4]=e[F];d[5]=4;A[F]=nil;end;end;end;end;if x then for F,d in q,x,nil do local k=d[4];if x then local d=x[F];if d then local v,y=F+k-1,u(k);i(e,F,v,1,y);d[6]=y;d[5]=1;x[F]=nil;end;end;end;end;return c[I]` |
| 24 | `JUMPI O` | `I=O[I]` |
| 25 | `--` | `if A then for F in q,A,nil do if A then local d=A[F];if d then d[6]=d;d[4]=e[F];d[5]=4;A[F]=nil;end;end;end;end;if x then for F,d in q,x,nil do local k=d[4];if x then local d=x[F];if d then local v=u(k);i(e,F,F+k-1,1,v);d[6]=v;d[5]=1;x[F]=nil;end;end;end;end;return f(e[s[I]],1,e[s[I]].n)` |
| 26 | `MOD s O L` | `e[s[I]]=e[O[I]]%L[I]` |
| 27 | `MUL O L s` | `e[O[I]]=L[I]*e[s[I]]` |
| 28 | `GETUPVAL` | `m=X[s[I]];e[O[I]]=m[6][m[5]]` |
| 29 | `--` | `R[Y[I]]=e[O[I]]` |

*21 of 30 rows have an inferred mnemonic; the rest are genuine multi-step handlers listed verbatim.*

## Dispatcher `v` — continuation loop (0..49)

| # | mnemonic | handler body (verbatim from `[49]`) |
|---:|---|---|
| 0 | `--` | `m=X[s[I]];e[O[I]]=m[6][m[5]][Y[I]]` |
| 1 | `MOD O s L` | `e[O[I]]=e[s[I]]%e[L[I]]` |
| 2 | `BITOP32` | `local K,T,h=s[I],Y[I],O[I];local Rq,Fq=P(T,4294967295),P(h,4294967295);local T,Yq,dq,Lq=P(Rq,65535),U(Rq,16),P(Fq,65535),U(Fq,16);h=P(T*dq+w(P(T*Lq+Yq*dq,65535),16),4294967295);Yq=nil;repeat dq=h%4294967296;if dq~=dq then Yq=0;break;end;Yq=dq-dq%1;until true;e[K]=Yq` |
| 3 | `GETTABLE O` | `e[O[I]][e[L[I]]]=s[I]` |
| 4 | `CALL2 L` | `e[L[I]](c[I],r[I])` |
| 5 | `MOVE L O` | `e[L[I]]=e[O[I]]` |
| 6 | `--` | `e[O[I]]=e[s[I]]+Y[I]` |
| 7 | `CALL2 O` | `e[O[I]](e[L[I]],e[s[I]])` |
| 8 | `SUB O L s` | `e[O[I]]=e[L[I]]-s[I]` |
| 9 | `LOAD O L` | `e[O[I]]=L` |
| 10 | `--` | `H,m=(Q(s[I],(P(Q(J,(P(U(J,29),7))),536870911)))),L[I]+1;for K=1,O[I],1 do H=P(Q(H,(w(H,13))),536870911);H=Q(H,(U(H,13)));H=P(Q(H,(w(H,14))),536870911);L[m]=Q(L[m],(P(U(H,0),127)));s[m]=Q(s[m],(P(U(H,7),127)));O[m]=Q(O[m],(P(U(H,14),127)));k[m]=Q(k[m],(P(U(H,21),127)));m=m+1;end;k[I]=50` |
| 11 | `JUMPIF <` | `I=if e[L[I]]<s[I]then O[I]else I` |
| 12 | `CMP O L < s` | `e[O[I]]=e[L[I]]<s[I]` |
| 13 | `CMP O s == L` | `e[O[I]]=e[s[I]]==e[L[I]]` |
| 14 | `MUL s O L` | `e[s[I]]=e[O[I]]*e[L[I]]` |
| 15 | `--` | `local K;local T=r[I];if T then local h=#T/3;if h>0 then K={};local Rq,Fq=A,x;for Yq=1,h,1 do local h=(Yq-1)*3;local dq,Lq=T[h+3],T[h+2];if dq==1 then Rq=if not Rq then{}else Rq;local Oq=Rq[Lq];if not Oq then Oq={[6]=e,[5]=Lq};Rq[Lq]=Oq;else end;K[Yq]=Oq;else if dq==0 then K[Yq]=e[Lq];else if dq==2 then K[Yq]=X[Lq];else if dq==3 then Fq=if not Fq then{}else Fq;local dq=Fq[Lq];if not dq then dq={[4]=T[h+1],[5]=Lq,[6]=e};Fq[Lq]=dq;else end;K[Yq]=dq;else end;end;end;end;end;A,x=Rq,Fq;else end;else end;H=c[I](nil,K);l(H,Z);e[L[I]]=H;m=K` |
| 16 | `IDIV s L O` | `e[s[I]]=e[L[I]]//e[O[I]]` |
| 17 | `ADD O L s` | `e[O[I]]=e[L[I]]+e[s[I]]` |
| 18 | `--` | `m=X[s[I]];e[O[I]]=m[6][m[5]][e[L[I]]]` |
| 19 | `--` | `e[s[I]]=e[O[I]](Y[I])` |
| 20 | `--` | `J=e[s[I]]` |
| 21 | `BITOP32` | `local K,T,h=L[I],c[I],e[O[I]];local Rq,Fq=P(T,4294967295),P(h,4294967295);local T,h,Yq,dq=P(Rq,65535),U(Rq,16),P(Fq,65535),U(Fq,16);Rq=P(T*Yq+w(P(T*dq+h*Yq,65535),16),4294967295);Yq=nil;repeat h=Rq%4294967296;if h~=h then Yq=0;break;end;Yq=h-h%1;until true;e[K]=Yq` |
| 22 | `JUMP O` | `I=e[O[I]]` |
| 23 | `NEWTABLE s` | `e[s[I]]={}` |
| 24 | `SETTABLE O [key] L` | `e[O[I]][s[I]]=e[L[I]]` |
| 25 | `--` | `B=e[L[I]]` |
| 26 | `--` | `e[L[I]]=Z[c[I]]` |
| 27 | `TOSTRING O` | `e[O[I]]=u(L[I])` |
| 28 | `BITOP32` | `local K,T,h=O[I],e[s[I]];repeat local Rq=T%4294967296;if Rq~=Rq then h=0;break;end;h=Rq-Rq%1;until true;e[K]=h` |
| 29 | `--` | `if A then for K in q,A,nil do if A then local T=A[K];if T then T[6]=T;T[4]=e[K];T[5]=4;A[K]=nil;end;end;end;end;if x then for K,T in q,x,nil do local h=T[4];if x then local T=x[K];if T then local Rq=u(h);i(e,K,K+h-1,1,Rq);T[6]=Rq;T[5]=1;x[K]=nil;end;end;end;end;return` |
| 30 | `CLOSEUPVAL T` | `local K=O[I];if A then local T=A[K];if T then T[6]=T;T[4]=e[K];T[5]=4;A[K]=nil;end;end` |
| 31 | `LOADK D` | `D=e[L[I]]` |
| 32 | `SETUPVAL` | `m=X[s[I]];m[6][m[5]]=e[L[I]]` |
| 33 | `MUL O L s` | `e[O[I]]=L[I]*e[s[I]]` |
| 34 | `--` | `e[O[I]]=e[s[I]]/L[I]` |
| 35 | `CALL/UNPACK` | `m,H,M,N=O[I],L[I],Q(B,P(U(B,14),262143),(P(U(B,28),15))),s[I];C=m<2097152 and 7 or 14;z,j=P(m,w(1,C)-1),U(m,C);L[I]=Q(H,103,(P(M,127)));O[I]=Q(z,95,(P(U(M,14),127)));s[I]=Q(N,64,(P(U(M,7),127)));k[I]=Q(j,22,(P(U(M,21),127)));I=I-1` |
| 36 | `--` | `e[s[I]]=Y[I]+e[O[I]]` |
| 37 | `SETUPVALIDX` | `m=X[L[I]];m[6][m[5]][c[I]]=e[O[I]]` |
| 38 | `CALL/UNPACK` | `m,H,M,N=s[I],O[I],L[I],Q(B,P(U(B,14),262143),(P(U(B,28),15)));C=m<16384 and 7 or(m<2097152 and 14 or 21);z,j=U(m,C),P(m,w(1,C)-1);L[I]=Q(M,44,(P(N,127)));s[I]=Q(j,65,(P(U(N,7),127)));O[I]=Q(H,19,(P(U(N,14),127)));k[I]=Q(z,53,(P(U(N,21),127)));I=I-1` |
| 39 | `BITOP32` | `local K,T,h=O[I],L[I],e[s[I]];local Rq,Fq=P(T,4294967295),P(h,4294967295);local T,h,Yq,dq=P(Rq,65535),U(Rq,16),P(Fq,65535),U(Fq,16);Fq=P(T*Yq+w(P(T*dq+h*Yq,65535),16),4294967295);Yq=nil;repeat Rq=Fq%4294967296;if Rq~=Rq then Yq=0;break;end;Yq=Rq-Rq%1;until true;e[K]=Yq` |
| 40 | `SUB O L s` | `e[O[I]]=e[L[I]]-e[s[I]]` |
| 41 | `--` | `m,H,M=O[I],s[I],L[I];N=e[m];i(e,m+1,m+H,M+1,N)` |
| 42 | `LOAD s L` | `e[s[I]]=L[I]` |
| 43 | `--` | `e[O[I]]=L[I]%e[s[I]]` |
| 44 | `--` | `e[L[I]]=e[O[I]]()` |
| 45 | `CMP L O <= s` | `e[L[I]]=e[O[I]]<=s[I]` |
| 46 | `CMP O L ~= s` | `e[O[I]]=e[L[I]]~=s[I]` |
| 47 | `CALL0 O` | `e[O[I]]()` |
| 48 | `LEN s O` | `e[s[I]]=#e[O[I]]` |
| 49 | `--` | `elseif not(v==50)then e[s[I]]=e[O[I]][L[I]];end` |

*34 of 50 rows have an inferred mnemonic; the rest are genuine multi-step handlers listed verbatim.*

