import json, zipfile, os

os.makedirs("pencil_doc", exist_ok=True)

content = {
    "id": "graph-viewer-ui",
    "name": "Graph Viewer",
    "pages": ["page1"]
}

page = {
    "name": "Graph Viewer",
    "shapes": [
        {"type":"rect","x":0,"y":0,"w":360,"h":900,"text":"Left Panel"},
        {"type":"rect","x":360,"y":0,"w":860,"h":900,"text":"Graph Canvas"},
        {"type":"rect","x":1220,"y":0,"w":380,"h":900,"text":"Node Details"},
        {"type":"text","x":20,"y":20,"text":"Graph Viewer"},
        {"type":"text","x":20,"y":70,"text":"Mode"},
        {"type":"rect","x":20,"y":90,"w":320,"h":36,"text":"Ingest Rules"},
        {"type":"text","x":20,"y":140,"text":"Graph View"},
        {"type":"rect","x":20,"y":160,"w":320,"h":36,"text":"MetaGraph"},
        {"type":"rect","x":20,"y":210,"w":160,"h":30,"text":"Rules Prompt"},
        {"type":"rect","x":180,"y":210,"w":160,"h":30,"text":"Cypher Expression"},
        {"type":"rect","x":20,"y":240,"w":320,"h":120,"text":"All units must have at least one door"},
        {"type":"rect","x":20,"y":370,"w":320,"h":40,"text":"Send Rules"},
        {"type":"rect","x":20,"y":420,"w":320,"h":40,"text":"Clear the Graph"},
        {"type":"text","x":1240,"y":20,"text":"Node details"},
        {"type":"rect","x":1240,"y":60,"w":80,"h":25,"text":"Rule"},
        {"type":"text","x":1240,"y":100,"text":"Key"},
        {"type":"text","x":1400,"y":100,"text":"Value"},
        {"type":"rect","x":1240,"y":120,"w":320,"h":30,"text":"<id>: 31"},
        {"type":"rect","x":1240,"y":160,"w":320,"h":30,"text":"Rule_Id: R_UNIT_MIN_DOOR_1_V"},
        {"type":"rect","x":1240,"y":200,"w":320,"h":30,"text":"kind: violation"},
        {"type":"rect","x":1240,"y":240,"w":320,"h":30,"text":"graph: Metagraph"},
        {"type":"rect","x":1240,"y":280,"w":320,"h":40,"text":"Add property"}
    ]
}

with open("pencil_doc/content.json","w") as f:
    json.dump(content,f)

with open("pencil_doc/page1.json","w") as f:
    json.dump(page,f)

with zipfile.ZipFile("graph_viewer.ep","w") as z:
    z.write("pencil_doc/content.json","content.json")
    z.write("pencil_doc/page1.json","page1.json")

print("graph_viewer.ep created")