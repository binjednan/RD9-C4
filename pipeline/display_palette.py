"""Analytical presentation palette. Never a physical material specification."""
import json, os
DATA=os.path.join(os.path.dirname(__file__),"data","display_palette.json")
def load():
    with open(DATA,encoding="utf-8") as f:return json.load(f)
def apply(M):
    P=load();M["displayPalette"]=P
    for L in M.get("layers",[]):L["color"]=P["disciplines"].get(L["id"],"#69788C")
    return P
