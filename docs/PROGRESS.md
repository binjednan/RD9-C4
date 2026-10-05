# C4 3D model — progress notes (scratchpad SP = /private/tmp/claude-501/-Users-binqdair/9a1652f3-ec18-4d97-b6e3-2745ee0d2f2c/scratchpad)

## How to rebuild
cd ~/Downloads && python3 SP/work/make_model.py     -> SP/www/model.json   (viewer dev server: http://127.0.0.1:8765/viewer.html , python http.server in SP/www, still running as bg task)
Electrical symbol extraction (slow, ~2 min): python3 SP/work/elec.py -> SP/work/data/elec_inst.json (ras.py raster matching vs sheet legends)
Overlay QA: python3 SP/work/ovl.py <fam> <TY|1|G|B|R|T> <ELEC1|ELEC2> out.png [x0,y0,x1,y1]

## Done (in model.json)
structure (raft, piles, cols, walls, slabs, beams, stairs), architecture (walls/doors/windows/finishes/facade/stairs/lifts/parapets), HVAC levels 1-5 (FCU, ducts, diffusers, dampers, thermostats),
plumbing levels 1-5 (cold/hot/soil/waste/vent/FF pipes+heads+heaters+valves), electrical devices (light/power/FA/LC/TEL/LTG) all levels via elec_emit.emit_family.
Modules: kb_elec.py (class catalogue, heights from EP-109: sockets 0.40, switches 1.30, FA break glass 1.30, bell 2.20, isolator 1.30, DB top 1.80, tel/tv 0.40, SMDB 80x100, DB 40x60 cm),
elec.py (extraction), elec_emit.py (geometry + wall snapping), ras.py (raster symbol matcher), ovl.py (QA overlay).

## Key doc data found (for the type KB / info cards)
- Light legend TYPE-1..13 (wattage/lumen/IP) in kb_elec.py. Power legend 19 rows. FA/LC/TEL/LTG legends in kb_elec.py.
- SLD (ELEC1 p16): MDB 2000A 4P tinned Cu busbar, 12-way Form-4 Type-6, IP54, 50kA, ACB 2000A TPN; transformer 1000kVA dry 22/0.4kV; ATS 200kVA (generator); capacitor bank 220kVAr;
  MCC-CHILLER 600A busbar: Chiller-1/2 L=120kW each (600A TP), FAHU-1, CHWP 2 duty+1 standby VFD 10kW; SMDB-SR L=157kW (L(ad)=89.6), SMDB-SH L=16.2 (9.4), DB-SH1/2 8.1 (4.7);
  SMDB-1..5 each L=144.8kW (L(ad)=78.4) with DB-F1..F6 (25.6/13.9 for F1.., 21.2/11.4 for F3,F5..), DB-GF 25.2/15.7, DB-SR 15.5/10.0, DB-RF 31.3/16.6, DB-G 14.4/6.8, DB-BF 35.6/21.0, CCU-UPS 5.0 (UPS 7kVA), SMDB-LIFT 30kW (2 lifts 15kW);
  F.F pumps: main 93kW, jockey 5kW (FP-400 fire-rated cable); totals: A/C 285.0kW, other 970.2kW, total 1255.2kW, after diversity 729.5kW. HV panel 11x[1C 630mm2 XLPE] from ADDC.
- Room details EP-108 (ELEC1 p17): 22kV switchgear 2500x900x2350; LV metering panel 600x800x1800; transformer dry 4000x1700x3200; DMS RTU 1000x300x1000; battery rack 1200x500x1290; 48V DC 820x600x2082; doors D1 2300x3500 (steel louvre), D2/D3 2300x3000 aluminium louvre.
- Equipment tag positions: data/equip_tags.json (roof chillers/CHWP etc; ground MDB/GENERATOR/TRANSFORMER; FF pump set; basement tanks).

## Remaining (priority order)
1 string pool for element sources (model.json too big: 9 MB) ; 2 plant equipment + DB/SMDB/MDB panels from tags; 3 cable routes (E.tray: CONNE layers + trays + risers);
4 HVAC B/G/R + CHW + risers; plumbing G/B/R + risers + tanks + storm; 5 lightning; 6 type KB (model.types); 7 clash detection; 8 material legend + audit panels;
9 UI polish (search, legend/clash panes) + single-file build to ~/Downloads/C4-3D-MODEL/ + QA + final Arabic summary.
