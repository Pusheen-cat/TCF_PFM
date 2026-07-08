import json
import os

root = "/path/to/PFM_data/"

count_path = "itemid_count.json"
value_path = "itemid_value_count.json"
unit_path  = "itemid_unit_count.json"

# json 로드
with open(os.path.join(root, count_path)) as f:
    count_dict = json.load(f)

with open(os.path.join(root, value_path)) as f:
    value_dict = json.load(f)

with open(os.path.join(root, unit_path)) as f:
    unit_dict = json.load(f)

# -------------------------
# 1. key 종류(set) 동일한지
# -------------------------
keys_count = set(count_dict.keys())
keys_value = set(value_dict.keys())
keys_unit  = set(unit_dict.keys())

print("key set 동일 여부:",
      keys_count == keys_value == keys_unit)

if not (keys_count == keys_value == keys_unit):
    print("count - value 차이:", keys_count - keys_value)
    print("count - unit  차이:", keys_count - keys_unit)

# -------------------------
# 2. key 순서(order) 동일한지
#    (json load는 python3.7+에서 순서 보존)
# -------------------------
keys_count_order = list(count_dict.keys())
keys_value_order = list(value_dict.keys())
keys_unit_order  = list(unit_dict.keys())

print("key 순서 동일 여부:",
      keys_count_order == keys_value_order == keys_unit_order)

# 만약 순서가 다르다면, 처음 다른 지점 찾기
if not (keys_count_order == keys_value_order == keys_unit_order):
    for i, (k1, k2, k3) in enumerate(zip(keys_count_order,
                                        keys_value_order,
                                        keys_unit_order)):
        if not (k1 == k2 == k3):
            print(f"첫 불일치 index: {i}")
            print("count:", k1)
            print("value:", k2)
            print("unit :", k3)
            break