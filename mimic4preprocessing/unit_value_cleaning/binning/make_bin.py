import numpy as np
from collections import defaultdict, Counter
from scipy.stats import norm
import json
import pickle

def assign_weights_to_values(item_counter, weight_th, exp_ = 1.0):
    """
    각 itemid에 대해 value들에 weight을 할당하는 함수

    Args:
        item_counter: defaultdict(Counter) - 120개의 itemid와 각각의 value count

    Returns:
        dict: {itemid: {value: weight}} 형태의 딕셔너리
    """
    result = {}

    total = len(item_counter)
    for i, (itemid, counter) in enumerate(item_counter.items(), 1):
        if i % 5 == 0 or i == total:
            print(f'Progress: {i}/{total} ({i / total:.1%})')
        if len(counter) == 0:
            result[itemid] = {}
            continue

        # 1. value들을 count만큼 반복하여 실제 분포 생성
        values = []
        all_values = []
        value_counts = []
        for value, count in counter.items():
            all_values.extend([value] * count)
            values.extend([value])
            value_counts.extend([count])
        all_values = np.array(all_values)
        values = np.array(values)
        value_counts = np.array(value_counts)

        min_val = values.min()
        max_val = values.max()
        std_val = all_values.std()

        # 단일 값인 경우 처리
        if std_val == 0:
            result[itemid] = {val: 1.0 for val in values}
            continue

        # 2. Split points 생성 (0.05 * std 간격)
        interval = 0.05 * std_val
        n_splits = int(np.ceil((max_val - min_val) / interval)) + 1
        split_points = np.linspace(min_val, min_val + (n_splits - 1) * interval, n_splits)

        # 마지막 값이 max_val보다 크거나 같도록 보정
        if split_points[-1] < max_val:
            raise AttributeError
            split_points[-1] = max_val

        # 3. Gaussian kernel을 사용한 convolution 계산
        # 각 split point에서의 density 계산 (모든 value들과의 gaussian weighted sum)
        densities = []
        for split_point in split_points:
            # 각 value에서 split_point까지의 gaussian weight 계산
            #gaussian_weights = norm.pdf(values, loc=split_point, scale=std_val)
            squared_distances = (values - split_point) ** 2
            gaussian_weights = np.exp(-squared_distances / (2 * (0.1*std_val) ** 2))
            # 모든 값들의 gaussian weight 합으로 density 계산
            density = np.mean(gaussian_weights*value_counts)
            densities.append(density)
        densities = np.array(densities)

        # 4. Weight 계산 (density의 역수)
        # density가 0인 경우를 피하기 위해 작은 값 추가
        weights = 1.0 / (densities + 1e-10)

        # 5. Weight 정규화 (최소값이 1이 되도록)
        min_weight = weights.min()
        weights = weights / min_weight

        """ 여기서 새롭게 exp_ 도입 """
        weights = weights**exp_

        # 6. 최대값을 10으로 클리핑
        weights = np.clip(weights, 1.0, weight_th)

        # 7. 각 value에 가장 가까운 split point의 weight 할당
        value_weights = {}
        unique_values = list(counter.keys())  # 원래 unique values
        for value in unique_values:
            # 가장 가까운 split point 찾기
            distances = np.abs(split_points - value)
            closest_idx = np.argmin(distances)
            value_weights[value] = weights[closest_idx]

        result[itemid] = value_weights

    return result

def create_percentile_bins(item_counter, bin = 100, value_weights = None, tag = 'float'):
    """
    각 itemid에 대해 percentile 기반 bin threshold를 생성

    Args:
        item_counter: defaultdict(Counter) - itemid별 value count

    Returns:
        dict: {itemid: {'thresholds': list, 'bin_assignment': dict}}
    """
    result = {}
    result_save = {}

    for fullitemid, counter in item_counter.items():
        itemid, itemname, csvtype = fullitemid.split("||")
        itemid = int(itemid)
        # value들을 정렬하여 가져오기
        values = sorted(counter.keys())
        if value_weights is None:
            counts = [counter[v] for v in values]
        else:
            counts = [counter[v]*value_weights[fullitemid][v] for v in values]
        N = len(values)
        min_val, max_val = values[0], values[-1]

        # 항상 99개의 threshold 생성
        thresholds = [None] * (bin-1)
        bin_assignment = {}

        if N > bin:
            # bin개 이상인 경우: 1-percentile씩 나누어 threshold 생성
            total_count = sum(counts)
            cumulative_counts = np.cumsum(counts)

            # 1%, 2%, ..., 99% percentile에 해당하는 threshold 찾기
            for p in range(1, bin):
                target_count = total_count * p / bin
                idx = np.searchsorted(cumulative_counts, target_count, side='right')
                if idx < N-1:
                    thresholds[p - 1] = values[idx+1]
                else:
                    thresholds[p - 1] = values[-1]+0.0001

            # bin assignment: threshold 값은 오른쪽 bin에 포함
            for value in values:
                bin_idx = 0
                for i, threshold in enumerate(thresholds):
                    if threshold is not None and value < threshold:
                        break
                    bin_idx += 1
                bin_assignment[value] = bin_idx

        elif N >= bin//2:
            # 49 <= N <= 100인 경우: 각 값을 중간 N개 bin에 할당
            start_bin = (bin - N) // 2
            end_bin = start_bin + N - 1

            # bin assignment 먼저 생성
            for i, value in enumerate(values):
                bin_assignment[value] = start_bin + i

            # threshold 생성: 실제 사용되는 bin 사이에만 threshold 설정
            for i in range(bin-1):
                bin_num = i + 1  # threshold i는 bin i와 bin i+1 사이
                if bin_num < start_bin:
                    # 왼쪽 빈 구간: 최소값 사용
                    thresholds[i] = min_val
                elif bin_num > end_bin:
                    # 오른쪽 빈 구간: 최대값 사용
                    thresholds[i] = max_val+0.001
                else:
                    # 실제 사용되는 구간: 해당 bin의 값 사용
                    value_idx = bin_num - start_bin
                    if value_idx < len(values):
                        thresholds[i] = values[value_idx]
                    else:
                        thresholds[i] = max_val

        else:  # N < 49
            # N < 49인 경우: 100//N의 stride로 bin 할당
            stride = bin // N

            # bin assignment 먼저 생성
            assigned_bins = []
            for i, value in enumerate(values):
                bin_num = (i) * stride + (stride//2)
                bin_assignment[value] = bin_num
                assigned_bins.append(bin_num)

            # threshold 생성
            for i in range(bin-1):
                threshold_bin = i + 1  # threshold i는 bin i와 bin i+1 사이

                # 이 threshold가 실제 할당된 bin들 사이에 있는지 확인
                if threshold_bin in assigned_bins:
                    # 할당된 bin의 값 찾기
                    for value, assigned_bin in bin_assignment.items():
                        if assigned_bin == threshold_bin:
                            thresholds[i] = value
                            break
                else:
                    # 할당되지 않은 bin: 가장 가까운 할당된 bin의 값 사용
                    # 또는 양끝이면 min/max 사용
                    if threshold_bin < min(assigned_bins):
                        thresholds[i] = min_val
                    elif threshold_bin > max(assigned_bins):
                        thresholds[i] = max_val+0.001
                    else:
                        # 중간 빈 구간: 왼쪽 또는 오른쪽 값 사용
                        left_bins = [b for b in assigned_bins if b < threshold_bin]
                        right_bins = [b for b in assigned_bins if b > threshold_bin]

                        if left_bins:
                            closest_left_bin = max(left_bins)
                            for value, assigned_bin in bin_assignment.items():
                                if assigned_bin == closest_left_bin:
                                    thresholds[i] = value
                                    break
                        elif right_bins:
                            closest_right_bin = min(right_bins)
                            for value, assigned_bin in bin_assignment.items():
                                if assigned_bin == closest_right_bin:
                                    thresholds[i] = value
                                    break

            # None인 threshold들을 인접한 값으로 채우기
        for i in range(bin-1):
            if thresholds[i] is None:
                if i > 0 and thresholds[i - 1] is not None:
                    thresholds[i] = thresholds[i - 1]
                elif i < bin-2 and thresholds[i + 1] is not None:
                    thresholds[i] = thresholds[i + 1]
                else:
                    thresholds[i] = min_val  # 기본값

        result[itemid] = {
            'thresholds': thresholds,
            'bin_assignment': bin_assignment,
            'item_name': itemname,
            'item_csv': csvtype,
            'tag':tag,
            'num_features': sum(counter.values()),
            f'threshold_rule': f'threshold 값은 오른쪽 bin에 포함, {bin-1 if tag == "float" else bin}개 threshold 생성'
        }
        result_save[itemid] = thresholds

    return result, result_save

def create_percentile_bins_str(item_counter, bin = 100, value_weights = None, tag = 'string'):
    """
    String 및 Binary 형태의 feature들에 대해 bin 설정하는 함수
    기본적으로 value를 int로 대응이 이미 이루어진 상태로 가정
    float은 threshold를 bin-1개를 사용하나 여기서는 제일 앞에 하나를 추가해서 bin개 사용함
    threshold가 사실상 value와 동일

    Args:
        item_counter: defaultdict(Counter) - itemid별 value count

    Returns:
        dict: {itemid: {'thresholds': list, 'bin_assignment': dict}}
    """
    assert tag in ['string', 'binary']
    result = {}
    result_save = {}
    for fullitemid, counter in item_counter.items():
        itemid, itemname, csvtype = fullitemid.split("||")
        itemid = int(itemid)
        # value들을 정렬하여 가져오기
        values = sorted(counter.keys())
        if value_weights is None:
            counts = [counter[v] for v in values]
        else:
            counts = [counter[v]*value_weights[fullitemid][v] for v in values]
        N = len(values)
        min_val, max_val = values[0], values[-1]

        # 100개의 threshold 생성
        thresholds = [None] * (bin)
        bin_assignment = {}

        assert N<=bin, print(f"{itemid}")

        if N >= bin // 2:
            # 49 <= N <= 100인 경우: 각 값을 중간 N개 bin에 할당
            start_bin = (bin - N) // 2
            end_bin = start_bin + N - 1

            # bin assignment 먼저 생성
            for i, value in enumerate(values):
                bin_assignment[value] = start_bin + i

            # threshold 생성: 실제 사용되는 bin 사이에만 threshold 설정
            for i in range(N):
                thresholds[start_bin+i] = values[i]

        else:  # N < 49
            # N < 49인 경우: 100//N의 stride로 bin 할당
            stride = bin // N

            # bin assignment 먼저 생성
            assigned_bins = []
            for i, value in enumerate(values):
                bin_num = (i) * stride + (stride // 2)
                bin_assignment[value] = bin_num
                assigned_bins.append(bin_num)

                thresholds[bin_num] = value
        result[itemid] = {
            'thresholds': thresholds,
            'bin_assignment': bin_assignment,
            'item_name': itemname,
            'item_csv': csvtype,
            'tag': tag,
            'num_features': sum(counter.values()),
            f'threshold_rule': f'threshold 값은 오른쪽 bin에 포함, {bin - 1 if tag == "float" else bin}개 threshold 생성'
        }
        result_save[itemid] = thresholds

    return result, result_save

def std_based_bins(item_counter, std_multipliers = [-10, -3, -1, -0.5, 0.5, 1, 3, 10], tag = 'float'):
    """
    각 itemid에 대해 표준편차 기반 bin threshold를 생성
    Args:
        item_counter: defaultdict(Counter) - itemid별 value count
    Returns:
        dict: {itemid: {'thresholds': list, 'bin_assignment': dict}}
    """
    # 각 item_id에 대해 bin assignment 생성
    result = {}
    result_save = {}

    for item_id, counter in item_counter.items():
        item_id, itemname, csvtype = item_id.split("||")
        item_id = int(item_id)
        # 각 item_id별 평균과 표준편차 계산
        item_values = []
        for value, count in counter.items():
            item_values.extend([value] * count)

        item_mean = np.mean(item_values)
        item_std = np.std(item_values)+(1e-6)

        print(item_id, item_mean, item_std)
        print(min(item_values), max(item_values))

        # 해당 item의 평균 + 표준편차를 기반으로 threshold 생성
        item_thresholds = [item_mean + mult * item_std for mult in std_multipliers]

        # 각 value에 대해 bin 할당
        bin_assignment = {}

        for value in counter.keys():
            # value가 어느 bin에 속하는지 찾기
            bin_idx = 0
            for i, threshold in enumerate(item_thresholds):
                if value < threshold:
                    bin_idx = i
                    break
            else:
                # 모든 threshold보다 큰 경우 마지막 bin (8)
                bin_idx = 8

            bin_assignment[value] = bin_idx

        result[item_id] = {
            'thresholds': item_thresholds,
            'bin_assignment': bin_assignment,
            'item_name': itemname,
            'item_csv': csvtype,
            'tag': tag,
            'num_features': sum(counter.values()),
            f'threshold_rule': f'threshold 값은 오른쪽 bin에 포함, 항상 8개 threshold 생성'
        }
        result_save[item_id] = item_thresholds

    return result, result_save

def mean_std_feature(item_counter, std_multipliers = [-10, -3, -1, -0.5, 0.5, 1, 3, 10]):
    """
    각 itemid에 대해 mean, std를 구하고 tokenizer에서 사용하기 위해 저장
    Args:
        item_counter: defaultdict(Counter) - itemid별 value count
    Returns:
        dict: {itemid: [mean, std]}
    """
    # 각 item_id에 대해 bin assignment 생성
    result = {}
    result_save = {}

    for item_id, counter in item_counter.items():
        item_id, itemname, csvtype = item_id.split("||")
        item_id = int(item_id)
        # 각 item_id별 평균과 표준편차 계산
        item_values = []
        for value, count in counter.items():
            item_values.extend([value] * count)

        item_mean = np.mean(item_values)
        item_std = np.std(item_values)+(1e-6)

        print('#',item_id, item_mean, item_std)
        print(min((item_values-item_mean)/item_std), max((item_values-item_mean)/item_std))

        result[item_id] = [item_mean, item_std]
        result_save[item_id] = [item_mean, item_std]

    return result, result_save

if __name__ == "__main__":

    train_counter_path = '/path/to/PFM_data/1_vital_table/train_17_100/counter_value.json'
    save_rootpath = '/path/to/PFM_data/thresholds/'
    itemid100 = [51221, 50971, 50983, 50912, 50902, 51006, 50882, 51265, 50868, 51301, 51222, 51249, 51279, 51248,
                 51250, 51277, 50960, 50893, 50970, 50802, 50804, 50821, 50818, 51275, 51237, 51274, 50808, 50885,
                 50861, 50878, 50863, 50822, 50813, 51244, 51256, 51254, 51200, 51146, 50862, 50910, 51498, 50911,
                 50954, 51492, 51514, 51484, 51508, 51506, 51466, 51464, 51487, 51486, 50810, 50811, 51003, 50819,
                 51519, 51516, 51493, 51476, 51144, 51463, 50824, 50956, 50867, 50920, 51233, 51137, 51246, 51143,
                 51251, 51255, 51252, 51267, 51009, 50806, 51268, 51214, 50883, 50884, 51266, 51082, 50993, 51100,
                 51000, 51218, 50908, 50967, 50801, 50907, 51093, 50964, 51007, 50904, 50952, 50903, 50924, 50998,
                 50953, 50852]
    key_117 = ['v_crr', 'v_sbp', 'v_mbp', 'v_dbp', 'v_fio2', 'v_hr', 'v_rr', 'v_gcse',
               'v_gcsm', 'v_gcsv', 'v_gcs', 'v_glu', 'v_sat', 'v_ph', 'v_tem', 'v_hei',
               'v_wei', ] + [str(tt) for tt in itemid100]
    with open(train_counter_path, 'r') as f:
        data_dict = json.load(f)
    # 안쪽 value들을 float으로 변환
    for outer_key, inner_dict in data_dict.items():
        data_dict[outer_key] = {float(k): int(v) for k, v in inner_dict.items()}

    sorted_item_counter = {}
    for key in key_117:
        if key in data_dict:
            sorted_item_counter[key] = data_dict[key]
        else:
            sorted_item_counter[key] = {0: 100}
    data_dict = sorted_item_counter

    ## STD based bin for TRADE  - No clipping##
    result, result_save = std_based_bins(data_dict, clipping=False)
    # pkl 파일로 저장
    with open(save_rootpath + f'bin{9}NoClip_weight{False}.pkl', 'wb') as f:
        pickle.dump(result_save, f)
    print(f'done std base')
    raise AttributeError

    ## STD/Mean for STraTS processing ##
    result, result_save = mean_std_feature(data_dict)
    # pkl 파일로 저장
    with open(save_rootpath + f'raw_mean_std.pkl', 'wb') as f:
        pickle.dump(result_save, f)
    print(f'done raw_mean_std')
    raise AttributeError

    ## STD based bin for TRADE ##
    result, result_save = std_based_bins(data_dict)
    # pkl 파일로 저장
    with open(save_rootpath + f'bin{9}_weight{False}.pkl', 'wb') as f:
        pickle.dump(result_save, f)
    print(f'done std base')
    raise AttributeError

    ## No weight 10 bin ##
    bin =10
    useweight = False
    result, result_save = create_percentile_bins(data_dict, bin=bin, value_weights=None)
    # pkl 파일로 저장
    with open(save_rootpath+f'bin{bin}_weight{useweight}.pkl', 'wb') as f:
        pickle.dump(result_save, f)
    print(f'done A')

    ## No weight 100 bin ##
    bin = 100
    useweight = False
    result, result_save = create_percentile_bins(data_dict, bin=bin, value_weights=None)
    # pkl 파일로 저장
    with open(save_rootpath + f'bin{bin}_weight{useweight}.pkl', 'wb') as f:
        pickle.dump(result_save, f)
    print(f'done B')

    ###
    weight_th = 10
    weight = assign_weights_to_values(data_dict, weight_th)

    ## Yes weight threshold 10, 10 bin ##
    bin = 10
    useweight = True
    result, result_save = create_percentile_bins(data_dict, bin=bin, value_weights=None if not useweight else weight)
    # pkl 파일로 저장
    with open(save_rootpath + f'bin{bin}_weight{useweight}_th{weight_th}.pkl', 'wb') as f:
        pickle.dump(result_save, f)
    print(f'done 1')

    ## Yes weight threshold 10, 10 bin ##
    bin = 100
    useweight = True
    result, result_save = create_percentile_bins(data_dict, bin=bin, value_weights=None if not useweight else weight)
    # pkl 파일로 저장
    with open(save_rootpath + f'bin{bin}_weight{useweight}_th{weight_th}.pkl', 'wb') as f:
        pickle.dump(result_save, f)
    print(f'done 2')

    ###
    weight_th = 5
    weight = assign_weights_to_values(data_dict, weight_th)

    ## Yes weight threshold 10, 10 bin ##
    bin = 10
    useweight = True
    result, result_save = create_percentile_bins(data_dict, bin=bin, value_weights=None if not useweight else weight)
    # pkl 파일로 저장
    with open(save_rootpath + f'bin{bin}_weight{useweight}_th{weight_th}.pkl', 'wb') as f:
        pickle.dump(result_save, f)
    print(f'done 3')

    ## Yes weight threshold 10, 10 bin ##
    bin = 100
    useweight = True
    result, result_save = create_percentile_bins(data_dict, bin=bin, value_weights=None if not useweight else weight)
    # pkl 파일로 저장
    with open(save_rootpath + f'bin{bin}_weight{useweight}_th{weight_th}.pkl', 'wb') as f:
        pickle.dump(result_save, f)
    print(f'done 4')

    ###
    weight_th = 2
    weight = assign_weights_to_values(data_dict, weight_th)

    ## Yes weight threshold 10, 10 bin ##
    bin = 10
    useweight = True
    result, result_save = create_percentile_bins(data_dict, bin=bin, value_weights=None if not useweight else weight)
    # pkl 파일로 저장
    with open(save_rootpath + f'bin{bin}_weight{useweight}_th{weight_th}.pkl', 'wb') as f:
        pickle.dump(result_save, f)
    print(f'done 5')

    ## Yes weight threshold 10, 10 bin ##
    bin = 100
    useweight = True
    result, result_save = create_percentile_bins(data_dict, bin=bin, value_weights=None if not useweight else weight)
    # pkl 파일로 저장
    with open(save_rootpath + f'bin{bin}_weight{useweight}_th{weight_th}.pkl', 'wb') as f:
        pickle.dump(result_save, f)
    print(f'done 6')


