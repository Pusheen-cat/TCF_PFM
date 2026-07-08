"""
이것은 TTE label을 만들기 위한 함수에 사용될 edge-[0.01, 0.05].pkl 를 만드는 함수
./data/unit_value_dicts/~~_update,pkl을 사용
따라서 interchage_csvs 이후에 실행되어야 함
"""

import pickle
from collections import Counter


def weighted_percentile_from_counter(counter, percentile):
    if not counter:
        return None

    items = sorted(counter.items())  # value 기준 정렬
    total = sum(counter.values())
    threshold = total * (percentile / 100.0)

    cum = 0
    for value, count in items:
        cum += count
        if cum >= threshold:
            return value

    return items[-1][0]

def build_percentile_dict(input_dict, percentile_list = [0.01, 0.05]):
    """
    input_dict:
    {
      '220045||Heart Rate||chartevents': {
          '<unit_name>': Counter(...)
      }
    }
    """
    output = {}

    for k, unit_dict in input_dict.items():
        itemid = k.split("||")[0]   # '220045'

        # unit key는 하나뿐
        counter = next(iter(unit_dict.values()))

        p1  = weighted_percentile_from_counter(counter, percentile_list[0]*100)
        p5  = weighted_percentile_from_counter(counter, percentile_list[1]*100)
        p95 = weighted_percentile_from_counter(counter, (1-percentile_list[1])*100)
        p99 = weighted_percentile_from_counter(counter, (1-percentile_list[0])*100)

        output[itemid] = [
            [p1, p5],
            [p99, p95]
        ]

    return output

if __name__ == "__main__":
    main_linkstos = ['chartevents', 'labevents', 'omr', 'outputevents']
    path = './data/unit_value_dicts/'
    all_float_dict = {}
    percentile_list = [0.01, 0.05]
    for main_linksto in main_linkstos:
        with open(path+f"{main_linksto}_unit_value_dict_update.pkl", "rb") as f:
            data = pickle.load(f)
        all_float_dict = all_float_dict | data['float']

    result = build_percentile_dict(all_float_dict, percentile_list)

    with open(f"./data/for_tte/edge-{str(percentile_list)}.pkl", "wb") as f:
        pickle.dump(result, f)


