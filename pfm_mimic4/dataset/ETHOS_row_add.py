import numpy as np
from pfm_mimic4.tokenizer.multitype_tokenizer import my_tokens


# 5m, 15m, 1h, 2h, 6h, 12h, 1d, 3d, 1w, 2w, 1mt, 3mt, 6mt,
def ethos_array(input_array, interval_start_token_index = my_tokens('meta_extra0_for_ETHOS'), threshold=np.array([300, 900, 3600, 7200, 21600, 43200, 86400, 259200, 604800, 1209600, 2628000, 7884000, 15768000])):
    meta_token_types = 8  # 0 for mimic3
    """
    최적화된 버전 - np.insert 반복 대신 세그먼트 단위 처리
    """

    start_idx = 3
    if len(input_array) <= start_idx + 1:
        return input_array.copy()

    # 처리할 구간의 배열들
    current_rows = input_array[start_idx:-1]
    next_rows = input_array[start_idx + 1:]

    # 차이 계산
    diffs = next_rows[:, 0] - current_rows[:, 0]
    insert_mask = diffs >= threshold[0]

    if not np.any(insert_mask):
        return input_array.copy()

    # 삽입이 필요한 인덱스들
    insert_indices = np.where(insert_mask)[0]

    # 세그먼트별로 배열 구성
    segments = []
    last_idx = 0
    max_threshold = threshold[-1]

    for i in insert_indices:
        actual_idx = start_idx + i
        diff = diffs[i]
        base_row = current_rows[i]

        # 현재 위치까지의 원본 데이터 추가
        segments.append(input_array[last_idx:actual_idx + 1])

        # 새로운 row들 생성 및 추가
        if diff <= max_threshold:
            # 단일 row 삽입
            third_value = np.searchsorted(threshold, diff, side='right')-1+interval_start_token_index
            new_rows = np.array([[base_row[0], meta_token_types, third_value]])
        else:
            # 다중 row 삽입
            num_rows = int(np.round(diff / max_threshold))
            third_value = len(threshold)-1+interval_start_token_index
            new_rows = np.tile([base_row[0], meta_token_types, third_value], (num_rows, 1))

        segments.append(new_rows)
        last_idx = actual_idx + 1

    # 마지막 세그먼트 추가
    if last_idx < len(input_array):
        segments.append(input_array[last_idx:])

    return np.vstack(segments)


def ethos_array_label(input_array, label, label_default_list, interval_start_token_index=my_tokens('meta_extra0_for_ETHOS'), threshold=np.array(
    [300, 900, 3600, 7200, 21600, 43200, 86400, 259200, 604800, 1209600, 2628000, 7884000, 15768000])):
    meta_token_types = 8  # 0 for mimic3
    """
    최적화된 버전 - np.insert 반복 대신 세그먼트 단위 처리
    input_array와 함께 label도 처리하여 반환
    """
    start_idx = 3
    if len(input_array) <= start_idx + 1:
        return input_array.copy(), label.copy()

    # 처리할 구간의 배열들
    current_rows = input_array[start_idx:-1]
    next_rows = input_array[start_idx + 1:]

    # 차이 계산
    diffs = next_rows[:, 0] - current_rows[:, 0]
    insert_mask = diffs >= threshold[0]

    if not np.any(insert_mask):
        return input_array.copy(), label.copy()

    # 삽입이 필요한 인덱스들
    insert_indices = np.where(insert_mask)[0]

    # 세그먼트별로 배열 구성
    input_segments = []
    label_segments = []
    last_idx = 0
    max_threshold = threshold[-1]

    for i in insert_indices:
        actual_idx = start_idx + i
        diff = diffs[i]
        base_row = current_rows[i]

        # 현재 위치까지의 원본 데이터 추가
        input_segments.append(input_array[last_idx:actual_idx + 1])
        label_segments.append(label[last_idx:actual_idx + 1])

        # 새로운 row들 생성 및 추가
        if diff <= max_threshold:
            # 단일 row 삽입
            third_value = np.searchsorted(threshold, diff, side='right') - 1 + interval_start_token_index
            new_input_rows = np.array([[base_row[0], meta_token_types, third_value]])
            new_label_rows = np.array([label_default_list])
        else:
            # 다중 row 삽입
            num_rows = int(np.round(diff / max_threshold))
            third_value = len(threshold) - 1 + interval_start_token_index
            new_input_rows = np.tile([base_row[0], meta_token_types, third_value], (num_rows, 1))
            new_label_rows = np.tile(label_default_list, (num_rows, 1))

        input_segments.append(new_input_rows)
        label_segments.append(new_label_rows)
        last_idx = actual_idx + 1

    # 마지막 세그먼트 추가
    if last_idx < len(input_array):
        input_segments.append(input_array[last_idx:])
        label_segments.append(label[last_idx:])

    return np.vstack(input_segments), np.vstack(label_segments)

# 테스트 함수
