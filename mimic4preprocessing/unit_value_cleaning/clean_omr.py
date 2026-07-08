import json
import os
from common_init_filtering import get_dicts
from cleaning_utils import trimmed_mean_from_counter
import math
import numpy as np

filter = "omr"

count_dict, value_dict, unit_dict,  unit_value_dict = get_dicts(filter)

#모든 key에 대해 중간 str이 'nan'이 아님을 확인하는 코드
#assert all(key.split('||')[1].lower() != 'nan' for key in count_dict.keys())

"""  1. value가 float 형식의 feature들을 찾고 이들 중 float 변환이 안되는 값들을 처리 """
print("  1. value가 float 형식의 feature들을 찾고 이들 중 float 변환이 안되는 값들을 처리 ")

def is_floatable(x):
    try:
        v=float(x)
        # nan, inf 제외
        return not (math.isnan(v) or math.isinf(v))
    except (ValueError, TypeError):
        return False

TOPK = 10

str_value_dict = {}
float_value_dict = {}

for itemid, counter in value_dict.items():

    # 빈도 기준 top-10 value
    top_values = sorted(
        counter.items(),
        key=lambda x: x[1],
        reverse=True
    )[:TOPK]

    # top-10 중 float 변환 가능한 value가 있는지
    has_floatable = any(is_floatable(v) for v, _ in top_values)

    if has_floatable:
        float_value_dict[itemid] = counter
    else:
        str_value_dict[itemid] = counter

float_to_str_keys = []  #
for key in float_to_str_keys:
    if key in float_value_dict:
        str_value_dict[key] = float_value_dict.pop(key)

str_to_float_keys = []  #
for key in str_to_float_keys:
    if key in str_value_dict:
        float_value_dict[key] = str_value_dict.pop(key)

float_err_value_dict = {}
float_ok_value_dict = {}
for itemid, counter in float_value_dict.items():

    bad_values = [
        v for v in counter.keys()
        if not is_floatable(v)
    ]

    if len(bad_values) > 0:
        float_err_value_dict[itemid] = {
            "bad_values": bad_values,
            "counter": counter
        }
    else:
        float_ok_value_dict[itemid] = {}



print(f'str_value_dict개수 {len(str_value_dict)} 과 float_value_dict개수 {len(float_value_dict)}를 더하면 {len(str_value_dict)+len(float_value_dict)}; 전체 개수 {len(value_dict)} ')
print(f'Float인데 str값이 잘못 들어가 있는 경우: ',len(float_err_value_dict))
'''
str_value_dict개수 54 과 float_value_dict개수 248를 더하면 302; 전체 개수 302 
Float인데 str값이 잘못 들어가 있는 경우:  234
Float 값의 value들을 갖는 item중에 "nan"값이 들어가 있는 경우의 수: 234
'''
nan_value_items = {}

for itemid, counter in float_value_dict.items():
    if 'nan' in counter:
        nan_value_items[itemid] = counter

print(f'Float 값의 value들을 갖는 item중에 "nan"값이 들어가 있는 경우의 수: {len(nan_value_items)}')

for idx, (_key, _value) in enumerate(float_err_value_dict.items()):
    #pass
    print(f"{idx+1}-th", _key, f"// {[[tt, _value['counter'][tt]] for tt in _value['bad_values']]} // ", sorted(_value['counter'].items(), key=lambda x: x[1], reverse=True)[:10])

'''다음은 float_value_convert 만들때 dict의 구조를 print해주는 helper 함수'''
value_convert = {}
for idx, (_key, _value) in enumerate(float_err_value_dict.items()):
    value_convert[_key] = {'drop':[tt for tt in _value['bad_values']], 'convert':{}}
# 문제 없는 애들도 추가 (왜냐면 float_value_convert 기준으로 여기 없는 key는 제거할거니까)
for _key in float_ok_value_dict.keys():
    value_convert[_key] = {'drop': [], 'convert': {}}
print(value_convert)
'''
여기서 dicts_omr의 float_value_convert 를 생성. 이를 기반으로 다음 코드 실행
'''

"""  2. value가 str 형식의 feature들을 찾고 이들 중 오타 등으로 그룹핑 가능한 애들을 처리 """
print("  2. value가 str 형식의 feature들을 찾고 이들 중 오타 등으로 그룹핑 가능한 애들을 처리 ")
str_convert = {}
for idx, (_key, _value) in enumerate(str_value_dict.items()):
    print(_key, _value)
    str_convert[_key] = {'drop':['nan'], 'convert':{}}
print(str_convert)
'''
여기서 dicts_omr의 string_value_convert 를 생성. 이를 기반으로 다음 코드 실행
'''

"""  3. float_value_convert와 string_value_convert 를 사용해서 값을 숫자로 변환하고, 
부적절한 key (남은 value가 너무 적거나, 변환 안되는 value들만 있거나 등등)을 filter함 
unit_value_dict을 수정함"""
print("  3. float_value_convert와 string_value_convert 를 사용해서 값을 숫자로 변환하고...")
from dicts_omr import string_value_convert, float_value_convert
from collections import Counter
def make_float_unit_value_dict(unit_value_dict, float_value_convert):
    float_unit_value_dict = {}

    for key, unit_dict in unit_value_dict.items():

        # 1. convert dict에 없는 key 제거
        if key not in float_value_convert:
            continue

        rule = float_value_convert[key]
        drop_set = set(rule.get("drop", []))
        convert_map = rule.get("convert", {})

        new_unit_dict = {}

        for unit, counter in unit_dict.items():
            new_counter = Counter()

            for val, cnt in counter.items():

                # 2-1. drop
                if val in drop_set:
                    continue

                # 2-2. convert
                if val in convert_map:
                    val = convert_map[val]

                # 3. float 변환 가능 여부 확인
                try:
                    val = float(val)
                except (ValueError, TypeError):
                    raise AttributeError
                    continue

                new_counter[val] += cnt

            # unit 안에 value가 하나도 안 남으면 제거
            if len(new_counter) > 0:
                new_unit_dict[unit] = new_counter

        if len(new_unit_dict) > 0:
            float_unit_value_dict[key] = new_unit_dict

    return float_unit_value_dict

def is_int_castable(x):
    try:
        int(x)
        return True
    except (ValueError, TypeError):
        return False
def make_string_unit_value_dict(unit_value_dict, string_value_convert):
    string_unit_value_dict = {}

    for key, unit_dict in unit_value_dict.items():

        if key not in string_value_convert:
            continue

        rule = string_value_convert[key]
        drop_set = set(rule.get("drop", []))
        convert_map = rule.get("convert", {})

        new_unit_dict = {}

        for unit, counter in unit_dict.items():
            new_counter = Counter()

            for val, cnt in counter.items():

                if val in drop_set:
                    continue

                if val in convert_map:
                    try:
                        val = convert_map[val]
                    except:
                        print(key,convert_map)
                        raise AttributeError

                # 🔑 int로 변환 가능한지 확인
                if not is_int_castable(val):
                    continue

                val = int(val)
                new_counter[val] += cnt

            if len(new_counter) > 0:
                new_unit_dict[unit] = new_counter

        if len(new_unit_dict) > 0:
            string_unit_value_dict[key] = new_unit_dict

    return string_unit_value_dict

float_unit_value_dict = make_float_unit_value_dict(unit_value_dict, float_value_convert)
string_unit_value_dict = make_string_unit_value_dict(unit_value_dict, string_value_convert)

print('여기서 float value들 float으로, string value들 int로 처리 됨')
print(f'converted float unit_value_dict length: ', len(float_unit_value_dict))
print(f'converted string unit_value_dict length: ', len(string_unit_value_dict))
'''
converted float unit_value_dict length:  229
converted string unit_value_dict length:  25
'''


"""  4. unit이 2개 이상인 feature들을 찾고, 합치거나 drop하는등의 처리 """
# string_value_convert 먼저 간단하게 처리
def make_unit_convert_to_main(unit_value_dict):
    unit_convert_dict = {}

    for key, unit_dict in unit_value_dict.items():

        # nan 제외한 unit 후보
        candidates = {
            unit: sum(counter.values())
            for unit, counter in unit_dict.items()
            if unit != "nan"
        }

        # nan 말고 unit이 하나도 없으면 skip
        if not candidates:
            continue

        # 🔑 value 개수 가장 많은 unit 선택
        main_unit = max(candidates, key=candidates.get)

        convert_map = {}

        for unit in unit_dict:
            if unit != main_unit:
                convert_map[unit] = main_unit

        if convert_map:
            unit_convert_dict[key] = {"convert": convert_map}

    return unit_convert_dict
omr_str_unit_convert = {}

for key, value in string_unit_value_dict.items():
    if len(value) != 1:
        print(key, value)

omr_str_unit_convert = make_unit_convert_to_main(string_unit_value_dict)
print("간단하게 만들어진 string unit converter: ",omr_str_unit_convert)

omr_float_unit_convert = {}

unit_value_dict_sub = {
    k: v for k, v in float_unit_value_dict.items()
    if isinstance(v, dict) and len(v) >= 2
}
#print(len(unit_value_dict_sub)) #53 <-- unit이 두종류인 key 개수

itemid_unit_trimmed_mean = {}

for itemid, unit_dict in unit_value_dict_sub.items():

    unit_stats = {}

    for unit, value_counter in unit_dict.items():
        mean_val, n_used = trimmed_mean_from_counter(value_counter)

        if mean_val is not None and n_used > 0:
            unit_stats[unit] = {
                "mean": mean_val,
                "n": n_used
            }

        else:
            unit_stats[unit] = {
                "mean": mean_val,
                "n": n_used
            }

    if len(unit_stats) > 0:
        itemid_unit_trimmed_mean[itemid] = unit_stats

print("")
for idx, (itemid, unit_stats) in enumerate(itemid_unit_trimmed_mean.items()):
    print(f"\n{idx+1}th - {itemid}")
    for unit, stats in unit_stats.items():
        print(
            f"  {unit:10s} → mean (trimmed) = {stats['mean']:.3f} "
            f"(n = {sum(unit_value_dict[itemid][unit].values()):,} -> {stats['n']:,})"
        )
    print(unit_value_dict[itemid])


for itemid, unit_stats in itemid_unit_trimmed_mean.items():
    # unit_stats: {unit: {"mean": x, "n": y}}

    # unit별 n 기준으로 정렬
    sorted_units = sorted(
        unit_stats.items(),
        key=lambda x: x[1]["n"],
        reverse=True
    )

    if len(sorted_units) <= 1:
        continue  # unit이 하나뿐이면 skip

    major_unit = sorted_units[0][0]

    convert_map = {}

    for unit, stats in sorted_units[1:]:
        if unit != major_unit:
            convert_map[unit] = major_unit

    if len(convert_map) > 0:
        omr_float_unit_convert[itemid] = {
            "convert": convert_map
        }

print('')
print(' === unit 이 두개 이상인 경우 convert할지 제거할지 판단하는 dict 만드는것 도와주는 코드 === ')
print(omr_float_unit_convert)
print('^ 이걸 사용해서 omr_float_unit_convert 만듬')

##만들어진 omr_str_unit_convert 및 omr_float_unit_convert 불러오기
from dicts_omr import omr_float_unit_convert, omr_str_unit_convert

"""
float_value_dict의 key만 사용해서 unit_value_dict으로부터 float_unit_value_dict 을 생성해. 
그리고 float_unit_value_dict 에서 앞서 만든 omr_float_unit_convert을 사용해서 서로 다른 unit을 변환할거야 
omr_float_unit_convert는 '225677||Phosphorous||chartevents': {'convert': {'nan': 'mg/dL'}}, 이런식으로 생겼는데 
drop에 있는 unit은 drop하고, convert에 있는 unit은 대응되는 것으로 바꿔줘. 
만약 'convert': {'kg': ['lb', lambda x: x * 2.2046226218]} 이런식으로 unit의 value가 list인 경우에는 단순 변환만 하는게 아니라 
각 값들에 뒤쪽의 함수를 적용해서 변경해줘. key별 unit이 하나가 된 것을 확인하고 변경된 value들의 20-80percentile 기준의 중앙값, 평균값, 
그리고 전체의 5% 및 95%percentile 값, 최대값, 최소값을 dict (float_value_stats)으로 만들어줘. 
즉 key:{unit:{'center':#, 'mean':#, '5-percentile':#, '95-percentile':#, min: #, max:#} 이런식으로 만들어줘
"""
### STR 변환
str_unit_value_dict_converted = {}
for itemid, unit_dict in string_unit_value_dict.items():

    convert_rule = omr_str_unit_convert.get(itemid, {})
    convert_map = convert_rule.get("convert")
    drop_units = set(convert_rule.get("drop", []))

    new_unit_dict = {}

    for unit, value_counter in unit_dict.items():

        # drop
        if unit in drop_units:
            continue

        target_unit = unit
        transform_fn = None

        if convert_map and unit in convert_map:
            rule = convert_map[unit]

            if isinstance(rule, list):
                target_unit, transform_fn = rule
            else:
                target_unit = rule

        if target_unit not in new_unit_dict:
            new_unit_dict[target_unit] = Counter()

        # value 펼치기
        for v_str, cnt in value_counter.items():

            if transform_fn:
                v_str = transform_fn(v_str)

            new_unit_dict[target_unit][v_str] += cnt

    # unit 하나만 남은 key만 유지
    if len(new_unit_dict) == 1:
        str_unit_value_dict_converted[itemid] = new_unit_dict
    else:
        print(itemid, new_unit_dict)
        raise NotImplementedError

float_unit_value_dict_converted = {}

for itemid, unit_dict in float_unit_value_dict.items():

    convert_rule = omr_float_unit_convert.get(itemid, {})
    convert_map = convert_rule.get("convert")
    drop_units = set(convert_rule.get("drop", []))

    new_unit_dict = {}

    for unit, value_counter in unit_dict.items():

        # drop
        if unit in drop_units:
            continue

        target_unit = unit
        transform_fn = None

        if convert_map and unit in convert_map:
            rule = convert_map[unit]

            if isinstance(rule, list):
                target_unit, transform_fn = rule
            else:
                target_unit = rule

        if target_unit not in new_unit_dict:
            new_unit_dict[target_unit] = Counter()

        # value 펼치기
        for v_str, cnt in value_counter.items():
            if not is_floatable(v_str):
                continue

            v = float(v_str)
            if transform_fn:
                v = transform_fn(v)

            new_unit_dict[target_unit][v] += cnt

    # unit 하나만 남은 key만 유지
    if len(new_unit_dict) == 1:
        float_unit_value_dict_converted[itemid] = new_unit_dict
float_value_stats = {}

for itemid, unit_dict in float_unit_value_dict_converted.items():

    unit, value_counter = next(iter(unit_dict.items()))

    if len(value_counter) == 0:
        continue

    # Counter → array (필요한 시점에만)
    values = np.repeat(
        np.fromiter(value_counter.keys(), dtype=float),
        np.fromiter(value_counter.values(), dtype=int)
    )

    # 전체 분포 통계
    p5 = np.percentile(values, 5)
    p95 = np.percentile(values, 95)
    vmin = values.min()
    vmax = values.max()

    # 20–80 trimming
    low = np.percentile(values, 20)
    high = np.percentile(values, 80)
    trimmed = values[(values >= low) & (values <= high)]

    if len(trimmed) == 0:
        continue

    stats = {
        "center": float(np.median(trimmed)),
        "mean": float(trimmed.mean()),
        "5-percentile": float(p5),
        "95-percentile": float(p95),
        "min": float(vmin),
        "max": float(vmax),
        "n_total": int(len(values)),
        "n_trimmed": int(len(trimmed)),
    }

    float_value_stats[itemid] = {
        unit: stats
    }

print("")
def print_dict_in_chunks(d, chunk_size=50):
    items = list(d.items())

    for i in range(0, len(items), chunk_size):
        print(f"\n--- items {i} ~ {i + chunk_size - 1} ---")
        for k, v in items[i:i + chunk_size]:
            print(k, v)

print_dict_in_chunks(float_value_stats, 50)
print(len(float_value_stats))
"""
다음은 EHR에서 뽑은 float 형태의 clinical measurement야.
우리는 이중 기기 오류나 사람의 잘못된 작성으로 나온 outlier들을 처리하기 위해 각 값들의 상한과 하한 inclusion criteria를 만들거야. 그리고 각 값의 소수점을 몇자리까지 처리하면 될지 n_decimal도 함께 표시할거야
최종적으로 만들어진 dict은 float_inclusion_dict으로
'227442||Potassium (serum)||chartevents': {inclusion:[##, ##], decimal:#}
이런 형태의 dict이 될거야
decimal은 'center', '5-percentile', '95-percentile' 등의 값을 참고해서 이 값을 표현하는데 소수점 몇자리까지 필요할지 판단해서 정수로 표현한다면 0, 소수점 한자리면 1, ... 이렇게 작성해줘

네가 처리해야 할 clinical measurement는 다음과 같아:
#############
잘했어 하지만 대부분의 경우에서 0이 inclusion에 들어가는 것은 바람직 하지 않아.
왜냐면 glucose나 Potassium, ALT등이 0이 나오는 상황은 기기 오류나 기록 오류로 봐야 해. 하지만 실제로 0으로 적힌 경우들이 많이 있고 이런 기록들이 drop되기를 원해 이를 생각해서 캔버스 내용을 수정해줘
"""

'''
와 float_unit_value_dict_converted를 float_inclusion_dict을 사용해서 outlier를 날리고
str_unit_value_dict_converted의 값이 0-9 사이에 있는지 확인한다.
'''
from dicts_omr import float_inclusion_dict
float_unit_value_dict_ = {}
for itemid, unit_dict in float_unit_value_dict_converted.items():
    assert len(unit_dict) == 1
    # inclusion rule 확인
    inclusion_rule = float_inclusion_dict.get(itemid)
    if inclusion_rule is None:
        print(itemid)
        raise AttributeError

    low, high = inclusion_rule["inclusion"]

    unit, value_counter = next(iter(unit_dict.items()))

    # Counter 필터링
    filtered_counter = Counter({
        v: cnt
        for v, cnt in value_counter.items()
        if low <= v <= high
    })

    if len(filtered_counter) == 0:
        continue  # 전부 drop된 경우 제거

    float_unit_value_dict_[itemid] = {
        unit: filtered_counter
    }

string_unit_value_dict_ = {}
for itemid, unit_dict in str_unit_value_dict_converted.items():
    assert len(unit_dict) == 1
    unit, value_counter = next(iter(unit_dict.items()))
    if len(value_counter) == 0:
        continue  # 전부 drop된 경우 제거
    assert len(value_counter) <= 10
    assert all(isinstance(k, (int, np.integer)) and 0 <= k <= 9 for k in value_counter), \
        f"Invalid key(s): {itemid}, {value_counter.keys()}"
    string_unit_value_dict_[itemid] = {
        unit: value_counter
    }

print("")
print(f'length "float_unit_value_dict_": {len(float_unit_value_dict_)}')  #5
print(f'length "string_unit_value_dict_": {len(string_unit_value_dict_)}')  #0

'''
convert_key 를 사용하여 같은 의학적 측정값을 의미하지만 itemid가 다른 녀석들을 하나로 합친다.
'''
from dicts_omr import convert_key_float

float_unit_value_dict_merged = {}
for itemid, unit_dict in float_unit_value_dict_.items():

    # case 1: 변환 대상 key
    if itemid in convert_key_float:

        rule = convert_key_float[itemid]
        target_key = rule["key"]
        target_unit = rule["unit"]
        convert_fn = rule["convert"]

        unit, value_counter = next(iter(unit_dict.items()))

        # target key 초기화
        if target_key not in float_unit_value_dict_merged:
            float_unit_value_dict_merged[target_key] = {
                target_unit: Counter()
            }

        # 값 변환 후 merge
        target_counter = float_unit_value_dict_merged[target_key][target_unit]
        for v, cnt in value_counter.items():
            target_counter[convert_fn(v)] += cnt

    # case 2: 변환 대상 아님 → 그대로 유지
    else:
        if itemid not in float_unit_value_dict_merged:
            float_unit_value_dict_merged[itemid] = unit_dict
        else:
            # 이론상 거의 없지만 방어 코드
            unit, value_counter = next(iter(unit_dict.items()))
            exist_unit, exist_counter = next(
                iter(float_unit_value_dict_merged[itemid].items())
            )
            assert unit == exist_unit
            exist_counter.update(value_counter)

print(f'length "float_unit_value_dict_merged": {len(float_unit_value_dict_merged)}') #218
float_unit_value_dict_ = float_unit_value_dict_merged

"""
CSV 사이 곂치는 feature 처리를 위한 중간 저장 및 불러오기 코드
float_unit_value_dict_ / string_unit_value_dict_ 저장함
"""
import pickle
save = False
pkl_path = "./data/unit_value_dicts/omr_unit_value_dict.pkl"
pkl_path_update = "./data/unit_value_dicts/omr_unit_value_dict_update.pkl"
if save:
    # 저장/로드 대상 dict
    omr_unit_value_dict = {
        "float": float_unit_value_dict_,
        "string": string_unit_value_dict_,
    }
    with open(pkl_path, "wb") as f:
        pickle.dump(omr_unit_value_dict, f)
    print(f"Saved to {pkl_path}")
    raise "Done"
else:
    # load
    with open(pkl_path_update, "rb") as f:
        omr_unit_value_dict = pickle.load(f)
    float_unit_value_dict_ = omr_unit_value_dict["float"]
    string_unit_value_dict_ = omr_unit_value_dict["string"]
    print(f"Loaded from {pkl_path_update}")

"""
이제 만들어진 unit_value_dict들을 바탕으로 binning에 사용할 threshold를 만든다.
float, string, binary를 나누어서 만드는데
float은 10개의 bin으로 나누고, string과 binary는 각각 sample 개수로 나누어 사용한다. 단 우리는 string들도 다 10개 이하의 int (0,1,2,...,9)를 갖도록 세팅해놓았다.
"""

from binning.make_bin import *
weight_th_list = [10]
exp_list = [0, 0.5, 1, 1.5, 2]
csv_name = 'omr'
save_rootpath = "./data/"


def remove_unit_dict(data):
    """
    {key: {unit: Counter}} → {key: Counter}
    각 key당 unit이 정확히 1개인지 검증
    """
    out = {}
    for k, unit_dict in data.items():
        if not isinstance(unit_dict, dict):
            raise TypeError(f"{k}: value is not a dict")

        if len(unit_dict) != 1:
            raise ValueError(f"{k}: has {len(unit_dict)} units (expected 1)")

        counter = next(iter(unit_dict.values()))

        if not isinstance(counter, Counter):
            raise TypeError(f"{k}: value is not Counter")
        out[k] = counter
    return out

float_value_dict_ = remove_unit_dict(float_unit_value_dict_)
string_value_dict_ = remove_unit_dict(string_unit_value_dict_)

#'''
result_string, result_save_string = create_percentile_bins_str(string_value_dict_, bin = 10, tag = 'string')
for weight_th in weight_th_list:
    for exp_ in exp_list:
        weight_float = assign_weights_to_values(float_value_dict_, weight_th, exp_)
        result_float, result_save_float = create_percentile_bins(float_value_dict_, bin = 10, value_weights = weight_float, tag = 'float')

        result_save = result_string|result_float
        with open(save_rootpath + f'{csv_name}_bin{10}_weight{True}_exp{exp_}_th{weight_th}.pkl', 'wb') as f:
            pickle.dump(result_save, f)


result_float, result_save_float = std_based_bins(float_value_dict_)
result_save = result_string|result_float
with open(save_rootpath + f'{csv_name}_bin{9}_weight{False}.pkl', 'wb') as f:
    pickle.dump(result_save, f)

## STD based bin for TRADE ##
string_stats, _ = mean_std_feature(string_value_dict_)
float_stats , _ = mean_std_feature(float_value_dict_)
result_stats = string_stats|float_stats
with open(save_rootpath + f'{csv_name}_raw_mean_std.pkl', 'wb') as f:
    pickle.dump(result_stats, f)

#'''


'''
만들려는 함수
1.	ID, value, unit 넣으면 --> ID', bin, unit 나오는 함수
2.	ID, bin넣으면 --> ID, value, unit 나오는 함수
'''

total_dict = float_value_dict_|string_value_dict_
from collections import OrderedDict
sorted_counter_dict = OrderedDict(
    sorted(
        total_dict.items(),
        key=lambda x: sum(x[1].values()),
        reverse=True
    )
)

for k_, v_ in sorted_counter_dict.items():
    if sum(v_.values())>10000:
        print(k_, sum(v_.values()))
thresholds = [
    2_000_000,
    1_000_000,
    500_000,
    200_000,
    100_000,
    50_000,
    20_000,
    10_000,
]

# key별 총합 계산
key_totals = {
    k: sum(c.values())
    for k, c in sorted_counter_dict.items()
}

# 구간별 개수 출력
for t in thresholds:
    cnt = sum(1 for v in key_totals.values() if v >= t)
    print(f">= {t:,} : {cnt}")

'''
>= 2,000,000 : 2
>= 1,000,000 : 4
>= 500,000 : 5
>= 200,000 : 5
>= 100,000 : 5
>= 50,000 : 5
>= 20,000 : 5
>= 10,000 : 5
'''