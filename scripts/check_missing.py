#!/usr/bin/env python3
"""Save inline scrapling results to disk so later build script can find them.
Run ONCE to persist all data, then rebuild PDF."""

import json
import os
import sys

RAW_DIR = "/Users/likeming/.claude/projects/-Users-likeming-Sites-hfb/53c0911e-9899-4014-a2d4-d5caeffb742f/tool-results/"

# Read the current all_chapters.json
aj = os.path.join(RAW_DIR, "all_chapters.json")
if os.path.exists(aj):
    with open(aj) as f:
        chapters = json.load(f)
else:
    chapters = {}

print(f"Before: {len(chapters)} chapters")

# The 59 missing chapters all just came back from 5 bulk_stealthy_fetch calls.
# They are in the conversation but not on disk.
# Use sys.argv to pass the chapter IDs that need to be re-saved.
# For now, just update the existing all_chapters from disk.
# The next step (build_v3.py) will use whatever is on disk.

# Check if we have enough
canonical_ids = [
    '1m17dqxaqpjbu','1m17dqxaqpvyy','1m17dqxaqusyi','1jurkyxgjjnea','1m1jdidk1fsp6','1m1jdidk1g5ca','1m1jdidk1ghze','1m1jdidk1gumi','1m1jdidk1h79m','1jurkyxhzsufu','1jurkyxhzt72y','1m1jdidk1hjwq','1m1jdidk1hwju','1m1jdidk1i96y','1m1jdidu7mkh2','1jurkyxhztjq2','1m1jdidu7mx46','1m1jdidu7n9ra','1jurkyxhzulne','1m1jdidu7nmee','1jurkyz91vub7','1jurkyza0r9c9','1jurkyzax7xuj','1m1jdig4kodv6','1jurkyzb26omq','1jurkyzb4nj1v','1m1jdig4koqia','1m1jdig4kp35e','1m1jdig4kpfsi','1jurkz0ey3pxm','1m1jdilmnrkm3','1m1jdilmns9wb','1m17du0i2gg7d','1m17du0i2gsuh','1m17du0i2h5hl','1m17du0i2hi4p','1m17du0i2hurt','1m17du0i2i7ex','1m17du0i2ik21','1jurkz23d8gtu','1m1jdip68f6su','1m1jdip68fw32','1jurkz32bnos3','1m1jdir0ytee2','1m1jdir0yu3oa','1jurkz3pu79y3','1jurkz3pu7ml7','1jurkz3pu7z8b','1m1jdit3qhfrd','1m1jdit3qhseh','1jurkz3pu9dsr','1m17du4xetkpn','1m17du4xetxcr','1m17du4xeu9zv','1m17du4xeummz','1m17du4xeuza3','1m17du4xevbx7','1jurkz4zowaat','1m1jdivamhnou','1jurkz4zowmxx','1jurkz4zowzl1','1jurkz4zoxc85','1jurkz4zoxov9','1jurkz4zoy1id','1jurkz4zoyqsl','1m17du759925v','1m17du7599esz','1m17du7599rg3','1m17du759a437','1m17du759agqb','1m17du759atdf','1m17du759b60j','1m17du759binn','1m17du759bvar','1jurkz69r1l3e','1lzguzkr17twa','1lzguzkr186je','1lzguzkr18j6i','1jurkz69r2adm','1jurkz69r3cay','1jurkz69r4e8a','1lzguzkr18vtm','1lzguzkr198gq','1m1jdiyhtokrq','1m1jdiyhtoxeu','1m1jdiyhtpmp2'
]
missing = [c for c in canonical_ids if c not in chapters]
print(f"Missing: {len(missing)}")

# Write full list to a file so build_v3 can reference
with open(os.path.join(RAW_DIR, "missing.txt"), "w") as f:
    for m in missing:
        f.write(m + "\n")
print("Done. Run build_v3.py eventually.")
