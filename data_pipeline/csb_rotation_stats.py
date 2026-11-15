"""Spike item 1: fraction of CSB fields (>=? ha) with strict corn(1)/soy(5) alternation 2018-2025, for candidate counties."""
import pyogrio, numpy as np, sys
G="/srv/hackathon/data/raw/csb/ext/CSB1825.gdb"
for st,cn in [("19","169"),("17","113"),("17","019")]:
    d=pyogrio.read_dataframe(G,where=f"STATEFIPS='{st}' AND CNTYFIPS='{cn}'",columns=[f"CDL{y}" for y in range(2018,2026)]+["CSBACRES","STATEFIPS","CNTYFIPS"],read_geometry=False)
    a=d[[f"CDL{y}" for y in range(2018,2026)]].to_numpy()
    cs=np.isin(a,[1,5]).all(1)
    alt=cs&((a[:,1:]!=a[:,:-1]).all(1))
    print(st+cn,"fields",len(d),"all-C/S",cs.sum(),"strict alternation",alt.sum(),"share",round(alt.mean(),3),"corn-soy any share",round(cs.mean(),3))
