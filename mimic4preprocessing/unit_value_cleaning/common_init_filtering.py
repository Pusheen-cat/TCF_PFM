import json
import os

def get_dicts(filter, min_count = 10000):
    root = "/path/to/PFM_data/"

    count_path = "itemid_count.json"
    value_path = "itemid_value_count.json"
    unit_path  = "itemid_unit_count.json"
    unit_value_path = "itemid_unit_value_count.json"

    assert filter in ["chartevents", "labevents", "outputevents", "omr"]

    # json 로드
    with open(os.path.join(root, count_path)) as f:
        count_dict = json.load(f)

    with open(os.path.join(root, value_path)) as f:
        value_dict = json.load(f)

    with open(os.path.join(root, unit_path)) as f:
        unit_dict = json.load(f)

    with open(os.path.join(root, unit_value_path)) as f:
        unit_value_dict = json.load(f)

    def filter_chartevent(d):
        """
        key: name1||name2||name3
        name3 == filter 인 것만 유지
        """
        return {
            k: v for k, v in d.items()
            if len(k.split("||")) == 3 and k.split("||")[2] == filter
        }

    # 1️⃣ chartevents 필터
    count_dict = filter_chartevent(count_dict)
    value_dict = filter_chartevent(value_dict)
    unit_dict  = filter_chartevent(unit_dict)
    unit_value_dict = filter_chartevent(unit_value_dict)

    ori_len_count = len(count_dict)
    ori_len_value = len(value_dict)
    ori_len_unit = len(unit_dict)
    ori_len_unit_value = len(unit_value_dict)

    # 2️⃣ count >= min_count 인 key만 선택
    valid_keys = {
        k for k, v in count_dict.items()
        if v >= min_count
    }

    # 3️⃣ 세 dict 모두 동일하게 필터링
    count_dict = {k: v for k, v in count_dict.items() if k in valid_keys}
    value_dict = {k: v for k, v in value_dict.items() if k in valid_keys}
    unit_dict  = {k: v for k, v in unit_dict.items()  if k in valid_keys}
    unit_value_dict = {k: v for k, v in unit_value_dict.items() if k in valid_keys}

    # 결과 확인
    print(f"{filter} features / min count {min_count} count: ", ori_len_count, " --> ",  len(count_dict))
    print(f"{filter} features / min count {min_count} value: ", ori_len_value, " --> ", len(value_dict))
    print(f"{filter} features / min count {min_count} unit : ", ori_len_unit, " --> ", len(unit_dict))
    print(f"{filter} features / min count {min_count} unit : ", ori_len_unit_value, " --> ", len(unit_value_dict))

    # sanity check
    assert set(count_dict) == set(value_dict) == set(unit_dict) == set(unit_value_dict)

    return count_dict, value_dict, unit_dict, unit_value_dict