import json

def transform_map(map_file):

    with open(map_file, "r") as fp: 
            input_map = json.load(fp)

    ip_address = input_map["ip"]
    id_value = int(ip_address[-3:-1])
    
    bias = input_map["fbk_op_bias"] + input_map["hpk_op_bias"]
    bias += [0] * (5-len(bias))

    trim = [0] * 40

    for id,ch in enumerate(input_map["fbk"]):
          trim[ch] = 0 if input_map["fbk_op_trim"][id] == 'None' else input_map["fbk_op_trim"][id]
    for id,ch in enumerate(input_map["hpk"]):
          trim[ch] = 0 if input_map["hpk_op_trim"][id] == 'None' else input_map["hpk_op_trim"][id] 

    print(bias)
    print(trim)
    
    output_map = {
        ip_address: {
            "id": id_value,
            "bias": bias,  # Ensure we only take the first 5 elements
            "trim": trim  # Ensure we only take the first 48 elements
        }
    }
    
    return output_map

map_list = [
      './../maps/10.73.137.104_dic.json',
      './../maps/10.73.137.105_dic.json',
      './../maps/10.73.137.107_dic.json',
      './../maps/10.73.137.109_dic.json',
      './../maps/10.73.137.111_dic.json',
      './../maps/10.73.137.112_dic.json',
      './../maps/10.73.137.113_dic.json'
]

map_list_latest = [
    f'/nfs/home/aminotti/PDS/data/iv_analysis/May-28-2024_run00/May-28-2024_1941_IvCurves_trim_np04_apa{apa}_ip10.73.137.{100+i}/10.73.137.{100+i}_dic.json'
    for [i,apa] in [[4,1],[5,1],[7,1],[9,2],[11,3],[12,4],[13,4]]
]
global_map = {}

for map in map_list:
    transformed_map = transform_map(map)
    global_map = dict(global_map, **transformed_map)

print(global_map)

with open('config.json', 'w') as f:
    json.dump(global_map, f)