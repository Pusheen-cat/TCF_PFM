import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Tuple
# from prepocessing.mimic3.lab_unit_numeric_matching.itemid_reference_range import reference_range_dict
# Allow running this file directly (python <path>): put the repo root on sys.path.
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from functools import partial
import pickle
import time
from mimic4preprocessing.my_itemid import my_itemid
from pfm_mimic4.dataset.ETHOS_row_add import ethos_array, ethos_array_label


def try_convert_int(s):
    try:
        return int(s)
    except (ValueError, TypeError):
        return s

def encode_with_given_tokenizer(input_data: List[Tuple], label_data: np.array, tokenizer) -> np.array:
    """
    주어진 tokenizer를 사용하여 input_data를 토큰화
    Args:
        input_data: [(time_str, datatype, [value]), ...]
        label_data: [np.array, np.array,...]
        tokenizer: tokenizer.encode(input_data) 메소드를 가진 객체
    Returns:
        [(time_str, datatype, token_idx), ...]
    """
    # tokenizer.encode()를 호출하여 토큰화
    encoded_result, encoded_labels = tokenizer.encode(input_data, label_data)
    return encoded_result, encoded_labels


def parse_csv_to_input_data(csv_path: str, csv_name, processor) -> List[Tuple]:
    """
    CSV 파일을 input_data 형태로 변환 (pandas 벡터화 연산 사용)
    """
    df = pd.read_csv(csv_path / csv_name) #
    #/path/to/PFM_data/PFM_pretraining/addQ/test, 162/16228161.csv

    df['time'] = pd.to_datetime(df['charttime'], format='mixed')
    assert df['time'].is_monotonic_increasing, f"{csv_path}/{csv_name}"


    # time을 문자열로 변환
    df['time'] = df['time'].astype(str)

    #print(df.columns)
    '''['subject_id', 'hadm_id', 'stay_id', 'charttime', 'itemid', 'itemname', 'value', 'valueuom', 'linksto', 'order', 'time']'''
    # --------------------------------------------------------------------------
    # 1. Parallel 실행
    # --------------------------------------------------------------------------
    # Parallel 결과는 원본 df의 index를 유지해야 정확한 비교가 가능합니다.
    df = processor.encode_parallel(df)

    out_path = (
            csv_path.parent.parent
            / f"processed_{processor.criteria_name}"
            / csv_path.parent.name
            / csv_path.name
            / Path(csv_name).with_suffix(".pkl")
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_pickle(out_path)

    # # 조건에 따라 value 변환 (완전 벡터화)
    # mask = df['itemid'].astype(int) > 1_000_000
    # df['converted_value'] = df['value'].astype(str)  # 먼저 모두 string으로
    # df.loc[~mask, 'converted_value'] = df.loc[~mask, 'value'].astype(float)  # 조건에 따라 float로
    """-> 위 코드가 이미 되어서 나옴 """




def find_split_position(sample: List[Tuple], max_length: int) -> int:
    """
    max_length를 넘지 않으면서 question 앞에서 자를 위치 찾기
    """
    if len(sample) <= max_length:
        return len(sample)

    # max_length 범위 내에서 마지막 question 찾기
    last_question_idx = -1
    find_question = False
    for i in range(max_length):
        if sample[(max_length - 1 - i)][1] == my_itemid['Question']['itemid']:
            find_question = True
            last_question_idx = max_length - 1 - i
        else:
            if find_question:
                break

    if last_question_idx == -1:
        # question이 없으면 max_length에서 자르기
        return max_length

    return last_question_idx


def split_sample_with_overlap(sample: np.array, label: np.array, max_length: int, overlap_size: int = 50) -> List[np.array]:
    """
    긴 sample을 여러 개로 분할 (overlap 포함)
    """
    if len(sample) <= max_length:
        return [sample], [label]

    # 처음 3개의 meta 정보 추출
    meta_prefix = sample[:3]
    meta_label_prefix = label[:3]
    for idx in range(3):
        assert meta_prefix[idx, 1] <= 6

    splits = []
    splits_labels = []
    current_pos = 0

    while current_pos < len(sample):
        # 현재 위치에서 시작하는 부분 샘플
        if current_pos == 0:
            # 첫 번째 분할: 원본 그대로 시작
            remaining_sample = sample[current_pos:]
            remaining_label = label[current_pos:]
        else:
            # 이후 분할: meta prefix + overlap + 새로운 부분
            overlap_start = find_split_position(remaining_sample, max_length - overlap_size)
            assert 3 < overlap_start
            # If error happens/ this means too long ans sequence compair to max length

            remaining_sample = np.concatenate([meta_prefix, remaining_sample[overlap_start:]], axis=0)
            remaining_label = np.concatenate([meta_label_prefix, remaining_label[overlap_start:]], axis=0)

        if len(remaining_sample) <= max_length:
            # 마지막 분할
            splits.append(remaining_sample)
            splits_labels.append(remaining_label)
            break
        else:
            # 분할 위치 찾기
            split_pos = find_split_position(remaining_sample, max_length)
            assert 3 < split_pos
            # If error happens/ this means too long ans sequence compair to max length

            splits.append(remaining_sample[:split_pos])
            splits_labels.append(remaining_label[:split_pos])
            current_pos = split_pos

    return splits, splits_labels



def _list_csv_filenames(dst_dir):
    """
    dst_dir / */ *.csv 구조에서
    모든 csv 파일의 '파일명만' 리스트로 반환
    """
    filenames = []

    with os.scandir(dst_dir) as it:
        for mid_entry in it:
            if not mid_entry.is_dir():
                continue

            with os.scandir(mid_entry.path) as file_it:
                for file_entry in file_it:
                    if file_entry.is_file() and file_entry.name.endswith(".csv"):
                        filenames.append(file_entry.name)

    return filenames

def process_folder_to_dataset(folder_path: str, tte_threshold_path, tokenizer, processor, max_length: int = 1000,
                              overlap_size: int = 50, basic_dir=None, tte_dir=None, addQ=True,
                              ethos=False, raw=False):
    """
    비병렬 버전 — parallel version과 완전히 동일한 동작 수행
    """
    min_length = 200 if addQ else 100
    folder_path = Path(folder_path)
    csv_files = _list_csv_filenames(folder_path)
    csv_files.sort()
    num_files = len(csv_files)
    print(f"처리할 CSV 파일 수: {num_files}")

    # ─────────────────────────────────────────────────────────────────────────
    # [1단계] CSV → processed pkl
    # ─────────────────────────────────────────────────────────────────────────
    print('1 Processing', end='')
    processed_path = (
        folder_path.parent.parent
        / f"processed_{processor.criteria_name}"
        / folder_path.parent.name
        / folder_path.name
    )
    if not os.path.exists(os.path.join(processed_path, "done.txt")):
        for csv_file in csv_files:
            parse_csv_to_input_data(folder_path, f'{csv_file[:3]}/{str(csv_file)}', processor)
        with open(os.path.join(processed_path, "done.txt"), "w") as f:
            f.write("done")
        print(' End')
    print(' Loaded (already done)')

    # ─────────────────────────────────────────────────────────────────────────
    # [2단계] TTE Threshold 로딩
    # ─────────────────────────────────────────────────────────────────────────
    with open(tte_threshold_path, 'rb') as f:
        tte_threshold = pickle.load(f)

    candidate = list(tokenizer.config.keys())
    tte_features = list(set(tte_threshold.keys()) & set(candidate))
    n_tte_features = len(tte_features)
    ref_dict = None
    event_per_feature = 4

    thresholds_df = {}
    for gender in ['Male', 'Female']:
        flat_thresholds_info = []
        global_idx_counter = 0
        for key_ in tte_threshold.keys():
            if key_ not in candidate:
                continue
            key_reference = try_convert_int(key_)
            if ref_dict is not None:
                flat_thresholds_info.append({
                    'key': key_, 'threshold_val': float(ref_dict[gender][key_reference][0]),
                    'event_type': 'less_than', 'global_idx': global_idx_counter
                })
                global_idx_counter += 1
            for val in tte_threshold[key_][0]:
                flat_thresholds_info.append({
                    'key': key_, 'threshold_val': val,
                    'event_type': 'less_than', 'global_idx': global_idx_counter
                })
                global_idx_counter += 1
            if ref_dict is not None:
                flat_thresholds_info.append({
                    'key': key_, 'threshold_val': float(ref_dict[gender][key_reference][1]),
                    'event_type': 'greater_than', 'global_idx': global_idx_counter
                })
                global_idx_counter += 1
            for val in tte_threshold[key_][1]:
                flat_thresholds_info.append({
                    'key': key_, 'threshold_val': val,
                    'event_type': 'greater_than', 'global_idx': global_idx_counter
                })
                global_idx_counter += 1
        thresholds_df[gender] = pd.DataFrame(flat_thresholds_info)
    print('2 TTE event 생성하는 threshold 완료.')

    # ─────────────────────────────────────────────────────────────────────────
    # [3단계] 경로 설정 및 Resume 로직
    # ─────────────────────────────────────────────────────────────────────────
    _share = 0 if tokenizer.args.bin.startswith('bin') else tokenizer.args.share_tokens
    _bin   = tokenizer.args.bin
    _tag   = f"maxlen{max_length}_overlap{overlap_size}_processed_{processor.criteria_name}_share{_share}_ethos{ethos}_{_bin}"

    tokenize_split_path = (
        folder_path.parent.parent
        / f"processed_{processor.criteria_name}"
        / "tokenized_splited"
        / _tag
        / folder_path.parent.name
        / folder_path.name
    )
    tokenize_split_path_tte = (
        folder_path.parent.parent
        / f"processed_{processor.criteria_name}"
        / "tokenized_splited"
        / _tag
        / folder_path.parent.name
        / f"tte_{folder_path.name}"
    )

    # Resume: 프로세스별 로그 디렉토리 (single process이므로 고정 파일명 사용)
    logs_dir = tokenize_split_path / "process_logs"
    os.makedirs(logs_dir, exist_ok=True)

    done_files = set()
    for log_file in glob.glob(os.path.join(logs_dir, "done_*.txt")):
        with open(log_file, "r") as f:
            for line in f:
                done_files.add(line.strip())

    files_to_process = [f for f in csv_files if f not in done_files]
    print(f"이미 처리된 파일: {len(done_files)}, 남은 파일: {len(files_to_process)}")

    # 이전 실행에서 저장된 길이 dict 이어받기
    sample_len_dict = {}
    sample_lens_path = tokenize_split_path / "sample_lens.pkl"
    if os.path.exists(sample_lens_path):
        with open(sample_lens_path, "rb") as f:
            sample_len_dict = pickle.load(f)

    padding_for_generation = np.array([-100], dtype=float)
    padding_sample    = np.array([0, 0, 0], dtype=int)
    padding_tte_label = np.ones((n_tte_features * event_per_feature, 2), dtype=int) * -100

    if len(files_to_process) > 0:
        log_file_path = os.path.join(logs_dir, "done_single.txt")  # single-process 전용 로그

        for csv_file in tqdm(files_to_process):
            subject_id = csv_file.replace(".csv", "")
            pkl_path   = os.path.join(processed_path, f'{subject_id[:3]}/{subject_id}.pkl')

            if not os.path.exists(pkl_path):
                print(f'경로 없는 문제 발생! {pkl_path}')
                raise AttributeError

            with open(pkl_path, "rb") as f:
                df = pickle.load(f)

            # ── parallel version과 동일한 중복 제거 ──────────────────────────
            df['charttime'] = pd.to_datetime(df['charttime'], format='mixed', errors='coerce')
            df = df.drop_duplicates(
                subset=['subject_id', 'hadm_id', 'charttime', 'itemid', 'value']
            ).reset_index(drop=True)
            df_len = len(df)

            if df_len < min_length:
                # min_length 미만도 로그에 기록 (Resume 일관성 유지)
                with open(log_file_path, "a") as f:
                    f.write(f"{csv_file}\n")
                continue

            df['value']  = df['value'].apply(lambda x: [x])
            one_sample   = list(df[['time', 'itemid', 'value']].itertuples(index=False, name=None))

            print(f"{csv_file} - {df_len}")
            sample_len_dict[subject_id] = df_len

            # TTE Label 생성
            if tte_dir is not None:
                # TODO - for generation
                #print(df['value'])
                val = df['value'].apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else np.nan)
                tte_label = pd.to_numeric(val, errors='coerce').to_numpy()
                tte_label[np.isnan(tte_label)] = -100
                tte_label = tte_label[:, None]
                #print(tte_label)
            else:
                tte_label = np.zeros((len(one_sample), 10, 2))

            assert len(one_sample) == len(tte_label)

            # Tokenization
            encoded_sample, encoded_labels = encode_with_given_tokenizer(one_sample, tte_label, tokenizer)

            if tte_dir is None and ethos:
                encoded_sample = ethos_array(encoded_sample)
                encoded_labels = encoded_sample

            elif ethos: #TODO for generation
                encoded_sample,encoded_labels = ethos_array_label(encoded_sample, tte_label, [-100])

            # 분할
            split_samples, split_labels = split_sample_with_overlap(
                encoded_sample, encoded_labels, max_length, overlap_size
            )

            # 패딩 & 저장
            dtype_sample = float if raw else int
            for idx_split, (split_sample, split_label) in enumerate(zip(split_samples, split_labels)):
                actual_len   = len(split_sample)
                padded_sample = np.full((max_length, 3), padding_sample, dtype=dtype_sample)
                padded_sample[:actual_len] = split_sample[:actual_len].astype(dtype_sample)

                save_path = tokenize_split_path / f"{subject_id[:3]}/{subject_id}/{idx_split}.pkl"
                os.makedirs(save_path.parent, exist_ok=True)
                with open(save_path, "wb") as f:
                    pickle.dump(padded_sample, f)

                if tte_dir is not None:
                    # padded_tte = np.full((max_length, n_tte_features * event_per_feature, 2),padding_tte_label, dtype=np.float16)
                    #TODO - for generation
                    padded_tte = np.full((max_length, 1), padding_for_generation, dtype=float)
                    padded_tte[:actual_len] = split_label[:actual_len]

                    tte_save_path = tokenize_split_path_tte / f"{subject_id[:3]}/{subject_id}/{idx_split}.pkl"
                    os.makedirs(tte_save_path.parent, exist_ok=True)
                    with open(tte_save_path, "wb") as f:
                        pickle.dump(padded_tte, f)

            # 처리 완료 로그 기록
            with open(log_file_path, "a") as f:
                f.write(f"{csv_file}\n")

            # 주기적 중간 저장 (안전장치)
            if len(sample_len_dict) % 1000 == 0:
                with open(sample_lens_path, "wb") as f:
                    pickle.dump(sample_len_dict, f)

        print("All tasks completed. Saving length dictionary.")
        with open(sample_lens_path, "wb") as f:
            pickle.dump(sample_len_dict, f)
    else:
        print('Tokenization & TTE labeling already done')

    # ── 처리 완료 검증 ────────────────────────────────────────────────────────
    done_files = set()
    for log_file in glob.glob(os.path.join(logs_dir, "done_*.txt")):
        with open(log_file, "r") as f:
            for line in f:
                done_files.add(line.strip())

    files_to_process = [f for f in csv_files if f not in done_files]
    print(f"처리 안돼 남은 파일: {len(files_to_process)}")
    if len(files_to_process) > 0:
        raise ValueError("코드를 돌렸는데도 처리 안된 값 계속 있음")

    # ─────────────────────────────────────────────────────────────────────────
    # [4단계] 최종 dataset 조립 (1000개씩 묶기) — parallel version과 동일
    # ─────────────────────────────────────────────────────────────────────────
    basic_dir = Path(str(basic_dir))
    pairs_sample = _collect_subject_idx_pairs(tokenize_split_path)
    set_sample   = set(pairs_sample)

    if tte_dir is not None:
        tte_dir   = Path(str(tte_dir))
        pairs_tte = _collect_subject_idx_pairs(tokenize_split_path_tte)
        set_tte   = set(pairs_tte)
    elif (not ethos) and (not addQ):
        orig_path = basic_dir.parent / f"{basic_dir.name}_subject_id_index.pkl"
        new_path  = Path(re.sub(r"bin10.*?share0", "bin10_exp0_th10_share0", str(orig_path)))
        with open(new_path, "rb") as f:
            set_tte = pickle.load(f)
        set_tte = set(set_tte)
    else:
        set_tte = set_sample

    if set_sample != set_tte:
        missing_in_tte    = set_sample - set_tte
        missing_in_sample = set_tte - set_sample
        raise ValueError(
            f"Mismatch detected!\n"
            f"Missing in tte: {len(missing_in_tte)}\n"
            f"Missing in sample: {len(missing_in_sample)}"
        )

    print(f"✓ Pair check passed: {len(set_sample)} samples")

    sorted_pairs = sorted(set_sample, key=lambda x: (int(x[0]), x[1]))

    with open(basic_dir.parent / f"{basic_dir.name}_subject_id_index.pkl", "wb") as f:
        pickle.dump(sorted_pairs, f)

    # padded_sample 1000개씩 묶어서 저장
    basic_dir = Path(basic_dir)
    basic_dir.mkdir(parents=True, exist_ok=True)

    processed_samples = []
    final_idx = 0
    for subject_id, idx__ in sorted_pairs:
        sample_path = tokenize_split_path / subject_id[:3] / subject_id / f"{idx__}.pkl"
        with open(sample_path, "rb") as f:
            padded_sample = pickle.load(f)

        processed_samples.append(np.expand_dims(padded_sample, axis=0))
        final_idx += 1

        if final_idx % 1000 == 0:
            out_path = basic_dir / f"{final_idx // 1000 - 1}.pkl"
            arr = np.concatenate(processed_samples, axis=0)
            with open(out_path, "wb") as f:
                pickle.dump(arr, f)
            processed_samples = []

    if processed_samples:
        out_path = basic_dir / f"{final_idx // 1000}.pkl"
        arr = np.concatenate(processed_samples, axis=0)
        with open(out_path, "wb") as f:
            pickle.dump(arr, f)

    # padded_tte_label_arr는 copy만 수행
    if tte_dir is not None:
        tte_dir   = Path(tte_dir)
        final_idx = 0
        for subject_id, idx__ in sorted_pairs:
            src       = tokenize_split_path_tte / subject_id[:3] / subject_id / f"{idx__}.pkl"
            group_dir = tte_dir / str(final_idx // 1000)
            group_dir.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, group_dir / f"{final_idx % 1000}.pkl")
            final_idx += 1


""" ##Parallel## """
from multiprocess import Pool, current_process
import glob
import shutil
import re
from tqdm import tqdm
from typing import List, Tuple
# -------------------------------------------------------------------------
# Worker Function (병렬로 실행될 함수)
# -------------------------------------------------------------------------
def _collect_subject_idx_pairs(base_path: Path):
    """
    base_path/
      └── 123/
          └── 123456/
              └── 0.pkl, 1.pkl, ...
    에서 (subject_id, idx__) 튜플 수집
    """
    pairs = []

    for sub3 in base_path.iterdir():
        if not sub3.is_dir() or not sub3.name.isdigit() or len(sub3.name) != 3:
            continue

        for subject_dir in sub3.iterdir():
            if not subject_dir.is_dir() or not subject_dir.name.isdigit():
                continue

            subject_id = subject_dir.name

            for pkl in subject_dir.iterdir():
                if pkl.suffix != ".pkl":
                    continue
                idx__ = pkl.stem
                if not idx__.isdigit():
                    continue

                pairs.append((subject_id, int(idx__)))

    return pairs
def _parse_single_file(file_info):
    """
    Pool에서 호출하기 위해 단일 인자(tuple)를 받는 래퍼 함수입니다.
    """
    csv_file, folder_path, processor = file_info

    # 원본 코드의 경로 생성 로직 유지
    csv_subpath = f'{csv_file[:3]}/{str(csv_file)}'

    try:
        parse_csv_to_input_data(folder_path, csv_subpath, processor)
    except Exception as e:
        print(f"Error processing {csv_file}: {e}")
        return None  # 에러 발생 시 None 반환


def _process_single_file(
        csv_file,
        folder_path,
        processed_path,
        tokenize_split_path,
        tokenize_split_path_tte,
        min_length,
        max_length,
        overlap_size,
        tokenizer,
        thresholds_df,
        tte_features,
        event_per_feature,
        n_tte_features,
        tte_dir,
        ethos,
        raw,
        logs_dir
):
    """
    개별 CSV 파일을 처리하는 Worker 함수입니다.
    """
    try:
        subject_id = csv_file.replace(".csv", "")
        pkl_path = os.path.join(processed_path, f'{subject_id[:3]}/{str(subject_id)}.pkl')

        # 파일이 없는 경우 예외처리 혹은 skip
        if not os.path.exists(pkl_path):
            print(f'경로 없는 문제 발생! {pkl_path}')
            raise AttributeError

        with open(pkl_path, "rb") as f:
            df = pickle.load(f)

        ###########################################################
        # 중복제거처리
        ###########################################################
        df['charttime'] = pd.to_datetime(df['charttime'], format='mixed', errors='coerce')
        #before = len(df)
        df = df.drop_duplicates(subset=['subject_id', 'hadm_id', 'charttime', 'itemid', 'value']).reset_index(drop=True)
        df_len = len(df)
        #print(f"Dropped rows: {before - df_len}")
        if df_len < min_length:

            # --- Resume 기능을 위한 로그 기록 ---
            # 각 프로세스(Core) ID별로 별도 파일에 기록하여 Lock 없이 안전하게 저장
            pid = current_process().pid
            log_file_path = os.path.join(logs_dir, f"done_{pid}.txt")
            with open(log_file_path, "a") as f:
                f.write(f"{csv_file}\n")

            return None  # min_length 미만은 무시

        # 리스트로 감싸기 & 튜플 리스트 변환
        df['value'] = df['value'].apply(lambda x: [x])
        one_sample = list(df[['time', 'itemid', 'value']].itertuples(index=False, name=None))

        # TTE Label 생성
        if tte_dir is not None:
            # 외부 함수가 전역 혹은 import되어 있어야 함
            # TODO - for generation
            #print(df['value'])
            val = df['value'].apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else np.nan)
            tte_label = pd.to_numeric(val, errors='coerce').to_numpy()
            tte_label[np.isnan(tte_label)] = -100
            tte_label = tte_label[:, None]
            #print(tte_label)
        else:
            tte_label = np.zeros((len(one_sample), 10, 2))

        # Tokenization
        encoded_sample, encoded_labels = encode_with_given_tokenizer(one_sample, tte_label, tokenizer)

        if tte_dir is None:
            if ethos:
                encoded_sample = ethos_array(encoded_sample)
                encoded_labels = encoded_sample
        elif ethos:  # TODO for generation
            encoded_sample, encoded_labels = ethos_array_label(encoded_sample, tte_label, [-100])

        # 분할 (Split)
        split_samples, split_labels = split_sample_with_overlap(encoded_sample, encoded_labels, max_length,
                                                                overlap_size)

        # 패딩 및 저장
        padding_for_generation = np.array([-100], dtype=float)
        padding_sample = np.array([0, 0, 0], dtype=int) if not raw else np.array([0, 0, 0], dtype=float)
        padding_tte_label = np.ones((n_tte_features * event_per_feature, 2), dtype=int) * -100

        for idx__, (split_sample, split_label) in enumerate(zip(split_samples, split_labels)):
            actual_len = len(split_sample)

            # Sample Padding
            dtype_sample = float if raw else int
            padded_sample = np.full((max_length, 3), padding_sample, dtype=dtype_sample)
            padded_sample[:actual_len] = split_sample[:actual_len].astype(dtype_sample)

            # Label Padding
            if tte_dir is not None:
                # TODO - for generation
                padded_tte_label_arr = np.full((max_length, 1), padding_for_generation, dtype=float)
                padded_tte_label_arr[:actual_len] = split_label[:actual_len]

                # padded_tte_label_arr = np.full((max_length, n_tte_features * event_per_feature, 2), padding_tte_label, dtype=np.float16)
                # padded_tte_label_arr[:actual_len] = split_label[:actual_len].astype(np.float16)

            # Save
            save_path = (tokenize_split_path / f"{subject_id[:3]}/{str(subject_id)}/{idx__}.pkl")
            os.makedirs(save_path.parent, exist_ok=True)
            with open(save_path, "wb") as f:
                pickle.dump(padded_sample, f)

            if tte_dir is not None:

                tte_save_path = (tokenize_split_path_tte / f"{subject_id[:3]}/{str(subject_id)}/{idx__}.pkl")
                os.makedirs(tte_save_path.parent, exist_ok=True)
                with open(tte_save_path, "wb") as f:
                    pickle.dump(padded_tte_label_arr, f)

        # --- Resume 기능을 위한 로그 기록 ---
        # 각 프로세스(Core) ID별로 별도 파일에 기록하여 Lock 없이 안전하게 저장
        pid = current_process().pid
        log_file_path = os.path.join(logs_dir, f"done_{pid}.txt")
        with open(log_file_path, "a") as f:
            f.write(f"{csv_file}\n")

        return (subject_id, df_len)

    except Exception as e:
        print(f"Error processing {csv_file}: {e}")
        return None
# -------------------------------------------------------------------------
# Main Function
# -------------------------------------------------------------------------
def process_folder_to_dataset_parallel(folder_path: str, tte_threshold_path, tokenizer, processor, max_length: int = 1000,
                              overlap_size: int = 50, basic_dir=None, tte_dir=None, addQ=True,
                              ethos=False, raw=False):
    # (선택사항) 토크나이저 내부 병렬화와 충돌 방지를 위해 환경변수 설정
    # HuggingFace Tokenizer 등을 사용한다면 필수적인 설정입니다.
    os.environ["TOKENIZERS_PARALLELISM"] = "false"

    """ 사용할 데이터의 최소길이 """
    min_length = 200 if addQ else 100
    folder_path = Path(folder_path)
    csv_files = _list_csv_filenames(folder_path)
    csv_files.sort()
    num_files = len(csv_files)
    print(f"전체 CSV 파일 수: {num_files}")

    # 병렬 처리를 위한 인자 리스트 생성
    # (파일이름, 폴더경로, 프로세서객체) 형태의 튜플 리스트를 만듭니다.
    # processor 객체가 너무 무거우면 pickle 오버헤드가 있을 수 있으나,
    # 일반적인 전처리용 객체라면 괜찮습니다.
    tasks = [(csv_file, folder_path, processor) for csv_file in csv_files]

    # CPU 코어 수 확인 (시스템 부하에 따라 -1 등을 할 수 있음)
    num_cores = 16
    print(f"사용할 CPU 코어 수: {num_cores}")

    #########################################################
    # 여기서 inclusion criteria로 사용할 feature만 남김 + processor로 각 feature id, value 전처리 // 중복 제거 처리 하기 전!!
    #########################################################
    print('1 Processing with Parallelism...')
    print('1 Processing', end='')
    processed_path = (folder_path.parent.parent / f"processed_{processor.criteria_name}" / folder_path.parent.name / folder_path.name)
    # /path/to/PFM_data/PFM_pretraining/f"processed_{processor.criteria_name}"/addQ/test
    if not os.path.exists(os.path.join(processed_path, "done.txt")):
        # --------------------------------------------------------------------------
        # Parallel 실행
        # --------------------------------------------------------------------------
        # chunksize는 파일 수에 따라 조절 가능하지만, 기본값으로도 보통 충분합니다.
        with Pool(processes=num_cores) as pool:
            # imap_unordered가 순서 상관없이 완료되는대로 리턴하므로 가장 빠르고 효율적입니다.
            # list()로 감싸서 제너레이터를 즉시 실행시킵니다.
            list(tqdm(pool.imap_unordered(_parse_single_file, tasks), total=num_files))

        with open(os.path.join(processed_path, "done.txt"), "w") as f:
            f.write("done")
        print(' End')
    print(' Loaded (already done)')

    # [2단계: TTE Threshold 로딩 (기존 코드와 동일)]
    with open(tte_threshold_path, 'rb') as f:
        tte_threshold = pickle.load(f)

    candidate = list(tokenizer.config.keys())
    tte_features = list(set(tte_threshold.keys()) & set(candidate))
    n_tte_features = len(tte_features)
    ref_dict = None
    event_per_feature = 4

    thresholds_df = {}
    for gender in ['Male', 'Female']:
        flat_thresholds_info = []
        global_idx_counter = 0
        for key_ in tte_threshold.keys():
            if key_ not in candidate: continue
            key_reference = try_convert_int(key_)

            if ref_dict is not None:
                flat_thresholds_info.append({
                    'key': key_,
                    'threshold_val': float(ref_dict[gender][key_reference][0]),
                    'event_type': 'less_than',  # 이벤트 유형: 이 값보다 작을 때
                    'global_idx': global_idx_counter
                })
                global_idx_counter += 1
            for val in tte_threshold[key_][0]:
                flat_thresholds_info.append({
                    'key': key_,
                    'threshold_val': val,
                    'event_type': 'less_than',  # 이벤트 유형: 이 값보다 작을 때
                    'global_idx': global_idx_counter
                })
                global_idx_counter += 1
            if ref_dict is not None:
                flat_thresholds_info.append({
                    'key': key_,
                    'threshold_val': float(ref_dict[gender][key_reference][1]),
                    'event_type': 'greater_than',  # 이벤트 유형: 이 값보다 클 때
                    'global_idx': global_idx_counter
                })
                global_idx_counter += 1
            for val in tte_threshold[key_][1]:
                flat_thresholds_info.append({
                    'key': key_,
                    'threshold_val': val,
                    'event_type': 'greater_than',  # 이벤트 유형: 이 값보다 클 때
                    'global_idx': global_idx_counter
                })
                global_idx_counter += 1

        # 전처리된 threshold 정보를 DataFrame으로 변환
        # 'threshold_val', 'global_idx', 'key', 'event_type' 포함
        thresholds_df[gender] = pd.DataFrame(flat_thresholds_info)
    print('2 TTE event 생성하는 threshold 완료.')

    # [3단계: Parallel Processing 준비]

    # 경로 설정
    tokenize_split_path = (folder_path.parent.parent / f"processed_{processor.criteria_name}" / "tokenized_splited" /
                           f"maxlen{max_length}_overlap{overlap_size}_processed_{processor.criteria_name}_share{0 if tokenizer.args.bin.startswith('bin') else tokenizer.args.share_tokens}_ethos{ethos}_{tokenizer.args.bin}" /
                           folder_path.parent.name / folder_path.name)
    tokenize_split_path_tte = (folder_path.parent.parent / f"processed_{processor.criteria_name}" / "tokenized_splited" /
                               f"maxlen{max_length}_overlap{overlap_size}_processed_{processor.criteria_name}_share{0 if tokenizer.args.bin.startswith('bin') else tokenizer.args.share_tokens}_ethos{ethos}_{tokenizer.args.bin}" /
                               folder_path.parent.name / f"tte_{folder_path.name}")

    # Resume을 위한 로그 디렉토리 생성
    logs_dir = tokenize_split_path / "process_logs"
    os.makedirs(logs_dir, exist_ok=True)

    # 이미 처리된 파일 목록 로드 (Resume Logic)
    done_files = set()
    log_files = glob.glob(os.path.join(logs_dir, "done_*.txt"))
    for log_file in log_files:
        with open(log_file, "r") as f:
            for line in f:
                done_files.add(line.strip())

    # 처리해야 할 파일 필터링
    files_to_process = [f for f in csv_files if f not in done_files]
    print(f"이미 처리된 파일: {len(done_files)}, 남은 파일: {len(files_to_process)}")

    if len(files_to_process) > 0:


        # sample_len_dict 복원 (이미 처리된 것들에 대해 길이를 알고 싶다면 별도 저장 로직이 필요하지만,
        # 보통 sample_lens.pkl을 마지막에 덮어쓰므로 여기서는 새로 처리된 것 + 기존 pkl 병합 방식을 고려해야 함.
        # 간단하게는, 이전에 저장된 sample_lens.pkl이 있다면 로드합니다.)
        sample_len_dict = {}
        sample_lens_path = tokenize_split_path / "sample_lens.pkl"
        if os.path.exists(sample_lens_path):
            with open(sample_lens_path, "rb") as f:
                sample_len_dict = pickle.load(f)

        # Worker 함수에 고정 인자 바인딩 (Partial)
        worker = partial(
            _process_single_file,
            folder_path=folder_path,
            processed_path=processed_path,
            tokenize_split_path=tokenize_split_path,
            tokenize_split_path_tte=tokenize_split_path_tte,
            min_length=min_length,
            max_length=max_length,
            overlap_size=overlap_size,
            tokenizer=tokenizer,
            thresholds_df=thresholds_df,
            tte_features=tte_features,
            event_per_feature=event_per_feature,
            n_tte_features=n_tte_features,
            tte_dir=tte_dir,
            ethos=ethos,
            raw=raw,
            logs_dir=logs_dir
        )

        # 병렬 처리 실행
        # CPU 코어 수의 약 80~90% 사용 추천 (예: os.cpu_count() - 2)
        num_workers = min(64, os.cpu_count() - 2)
        print(f"Starting parallel processing with {num_workers} workers...")

        # imap_unordered 사용: 작업이 끝나는 대로 결과 반환 (Dynamic Allocation 효과)
        with Pool(processes=num_workers) as pool:
            try:
                from tqdm import tqdm
                iterator = tqdm(pool.imap_unordered(worker, files_to_process), total=len(files_to_process))
            except ImportError:
                iterator = pool.imap_unordered(worker, files_to_process)
                print("tqdm not installed. Running without progress bar.")

            for result in iterator:
                if result is not None:
                    subj_id, length = result
                    sample_len_dict[subj_id] = length

                    # (Optional) 주기적으로 sample_len_dict 저장 (안전장치)
                    if len(sample_len_dict) % 1000 == 0:
                        with open(sample_lens_path, "wb") as f:
                            pickle.dump(sample_len_dict, f)

        # 최종 sample_len_dict 저장
        print("All tasks completed. Saving length dictionary.")
        with open(sample_lens_path, "wb") as f:
            pickle.dump(sample_len_dict, f)
    else:
        print('Tokenization & TTE labeling already done')

    """ 빠진거 없이 처리되었나 확인"""
    # 이미 처리된 파일 목록 로드 (Resume Logic)
    done_files = set()
    log_files = glob.glob(os.path.join(logs_dir, "done_*.txt"))
    for log_file in log_files:
        with open(log_file, "r") as f:
            for line in f:
                done_files.add(line.strip())

    # 처리해야 할 파일 필터링
    files_to_process = [f for f in csv_files if f not in done_files]
    print(f"처리 안돼 남은 파일: {len(files_to_process)}")
    if len(files_to_process)>0:
        raise "코드를 돌렸는데도 처리 안된 값 계속 있음"

    #return #!#! TODO 여기까지만 돌려놓기

    ##########################################################
    # 3. 원래와 동일하게 1000개씩 묶어서 dataset 만들기
    # basic_dir / tte_dir
    ##########################################################
    basic_dir = Path(str(basic_dir))
    pairs_sample = _collect_subject_idx_pairs(tokenize_split_path)
    set_sample = set(pairs_sample)

    if tte_dir is not None:
        tte_dir = Path(str(tte_dir))
        pairs_tte = _collect_subject_idx_pairs(tokenize_split_path_tte)
        set_tte = set(pairs_tte)
    elif (not ethos) and (not addQ):
        orig_path = basic_dir.parent / f"{basic_dir.name}_subject_id_index.pkl"
        new_path = Path(
            re.sub(
                r"bin10.*?share0",
                "bin10_exp0_th10_share0",
                str(orig_path)
            )
        )
        with open(new_path, "rb") as f:
            set_tte = pickle.load(f)
        set_tte = set(set_tte)
    else:
        set_tte = set_sample

    if set_sample != set_tte:
        missing_in_tte = set_sample - set_tte
        missing_in_sample = set_tte - set_sample

        raise ValueError(
            f"Mismatch detected!\n"
            f"Missing in tte: {len(missing_in_tte)}\n"
            f"Missing in sample: {len(missing_in_sample)}"
        )

    print(f"✓ Pair check passed: {len(set_sample)} samples")

    sorted_pairs = sorted(set_sample, key=lambda x: (int(x[0]), x[1]))

    with open(basic_dir.parent / f"{basic_dir.name}_subject_id_index.pkl", "wb") as f:
        pickle.dump(sorted_pairs, f)


    """padded_sample 1000개씩 묶어서 저장"""

    basic_dir = Path(basic_dir)
    basic_dir.mkdir(parents=True, exist_ok=True)

    processed_samples = []
    final_idx = 0

    for i, (subject_id, idx__) in enumerate(sorted_pairs):
        sample_path = (
                tokenize_split_path
                / subject_id[:3]
                / subject_id
                / f"{idx__}.pkl"
        )

        with open(sample_path, "rb") as f:
            padded_sample = pickle.load(f)

        processed_samples.append(np.expand_dims(padded_sample, axis=0))
        final_idx += 1

        # 1000개 단위로 저장
        if final_idx % 1000 == 0:
            out_idx = final_idx // 1000 - 1
            out_path = basic_dir / f"{out_idx}.pkl"

            arr = np.concatenate(processed_samples, axis=0)
            with open(out_path, "wb") as f:
                pickle.dump(arr, f)

            processed_samples = []

    # 남은 것 처리
    if processed_samples:
        out_idx = final_idx // 1000
        out_path = basic_dir / f"{out_idx}.pkl"

        arr = np.concatenate(processed_samples, axis=0)
        with open(out_path, "wb") as f:
            pickle.dump(arr, f)

    """padded_tte_label_arr는 copy만 수행"""
    if tte_dir is not None:
        tte_dir = Path(tte_dir)

        final_idx = 0
        for subject_id, idx__ in sorted_pairs:
            src = (
                    tokenize_split_path_tte
                    / subject_id[:3]
                    / subject_id
                    / f"{idx__}.pkl"
            )

            group_dir = tte_dir / str(final_idx // 1000)
            group_dir.mkdir(parents=True, exist_ok=True)

            dst = group_dir / f"{final_idx % 1000}.pkl"

            shutil.copyfile(src, dst)
            final_idx += 1



def csv_to_tensor(folder_path: str, tte_threshold_path, tokenizer, processor, max_length: int = 1000,
                  overlap_size: int = 50,
                  basic_dir = None, tte_dir = None, n_workers: int = None, addQ = True,
                  ethos = False, raw = False):
    # 타입별 정보 출력
    if basic_dir is not None:
        print(os.path.dirname(os.path.dirname(basic_dir))+'/tokenizer.txt')
        with open(os.path.dirname(os.path.dirname(basic_dir))+'/tokenizer.txt', 'w', encoding='utf-8') as f:
            print("\n=== Tokenizer 설명 ===")
            type_info = tokenizer.get_type_info()
            for data_type, info in type_info.items():
                if data_type != 'total_vocab_size' and data_type !='tokenizer_ranges':
                    print(f"{data_type}: idx={info['tokenizer_idx']}, vocab_size={info['vocab_size']}, offset={info['token_offset']}, type={info['type']}")
                    f.write(f"{data_type}: idx={info['tokenizer_idx']}, vocab_size={info['vocab_size']}, offset={info['token_offset']}, type={info['type']}" + '\n')
            print(f"Total vocabulary size: {type_info['total_vocab_size']}")
            print(f"Total tokenizer_ranges: {type_info['tokenizer_ranges']}")
            f.write(f"Total vocabulary size: {type_info['total_vocab_size']}" + '\n')
            f.write(f"Total tokenizer_ranges: {type_info['tokenizer_ranges']}")

    print("=== Dataset Tensor 생성 시작 ===")
    start = time.time()

    if tte_dir is not None:
        raise  "Generation 하느라 TTe 부분 수정해놨으니 확인하고 사용"

    #TODO####### - Fore generation
    tte_dir = basic_dir[:-20]+basic_dir[-20:].replace("train", "gen_train").replace("test", "gen_test")

    if (n_workers is None) or (n_workers==1):
        """
        기존 비병렬 버전 (호환성 유지)
        """
        process_folder_to_dataset(folder_path, tte_threshold_path, tokenizer, processor, max_length, overlap_size, basic_dir, tte_dir, addQ, ethos, raw)
    else:
        process_folder_to_dataset_parallel(folder_path, tte_threshold_path, tokenizer, processor, max_length, overlap_size, basic_dir, tte_dir, addQ, ethos, raw)

    end = time.time()
    print(f"\n=== 결과 ===")

    print(f"  - 총 처리 시간: {(end - start) / 3600:.2f} 시간")
    print(f"  - 사용된 워커 수: {n_workers}")

    return True


# 사용 예시
if __name__ == "__main__":
    import argparse
    from mimic4preprocessing.key_value_unit_processer import key_value_unit_processer
    from pfm_mimic4.tokenizer.multitype_tokenizer import MultiTypeTokenizer
    from pfm_mimic4.tokenizer.tokenizing_setting import token_bin_range

    parser = argparse.ArgumentParser()
    parser.add_argument("--sample_max_length", type=int, default=2048)
    parser.add_argument("--sample_overlap", type=int, default=512)
    parser.add_argument("--sample_n_workers", type=int, default=1)
    parser.add_argument("--data_dir", type=str, default="/path/to/PFM_data/PFM_pretraining/tensor_saved/")
    parser.add_argument("--qa_table_dir", type=str, default="/path/to/PFM_data/PFM_pretraining/")
    parser.add_argument("--binning_threshold", type=str, default="mimic4preprocessing/unit_value_cleaning/data/")
    parser.add_argument("--tte_threshold", type=str, default="mimic4preprocessing/unit_value_cleaning/data/for_tte/edge-[0.01, 0.05].pkl")
    parser.add_argument("--data", type=str, default='criteria1', help='criteria is in - mimic4preprocessing/scripts/inclusion_criteria')
    parser.add_argument("--bin", type=str, default='bin10_exp0_th10',
                        help='value binning; thresholds live in mimic4preprocessing/unit_value_cleaning/data/ (generated by mimic4preprocessing/unit_value_cleaning/binning/make_bin.py). bin{N}_exp{E}_th{T} = N percentile bins, density-weight exponent E (exp0 = no weighting), weight-clip threshold T. Used: bin10_exp1_th10 [OURS], bin10_exp0_th10 [ETHOS generation baseline]. Also generated: bin10_exp{0.5,1.5,2}_th10.')
    parser.add_argument("--share_tokens", type=int, default=0, help='0 - not share token; use each bin'
                                                                    '1 - share token')
    parser.add_argument("--seq_gen", type=str, default='addQ', help='addQ - add info token with timestamp and '
                                                                    'addTS - share token'
                                                                    'NOadd - no adding info token')
    parser.add_argument("--objective", type=str, default='G2DYDTSP',
                        help='G1DYDTSP - Generative multi-timw dynamic mono TimeStamp P'
                             'G2DYDTSP - G1 with position'
                             'GSDYDTSP - Generative simple dynamic mono TimeStamp P'
                             'DYMTSP - dynamic mono TimeStamp P'
                             'DYDTSP - dynamic dual TimeStamp P'
                             'TANTP - time-aware NTP'
                             'NTP - remove timestamp'
                             'TTE - time to event')
    parser.add_argument("--in_pretrain", type=int, default=1)
    parser.add_argument("--eval_seed", type=int, default=0)
    parser.add_argument("--eval_max_length", type=int, default=2048)
    parser.add_argument("--eval_overlap", type=int, default=512)

    parser.add_argument("--eval_task_dir", type=str, default="/path/to/PFM_data/4_eval_tasks/")
    parser.add_argument("--eval_data_dir", type=str, default="/path/to/PFM_data/tensor_downstream_tasks/")

    parser.add_argument("--pe_baseline", type=str, default='ETHOS', help='None - OURS (default). ETHOS - generation-comparison baseline.')
    args = parser.parse_args()
    processor = key_value_unit_processer(args.data)
    config = token_bin_range(args, processor.inclusion_dict_processed)
    # print(config)
    # print(len(config))
    tokenizer = MultiTypeTokenizer(config, args)
    # print(tokenizer.type_to_idx.keys())
    # print(len(tokenizer.idx_to_type))
    # raise AttributeError
    # 기존 함수와 동일한 인터페이스로 사용 가능
    # 단, n_workers 파라미터를 추가로 받아서 워커 수를 조절할 수 있음
    tte_threshold_path = "mimic4preprocessing/unit_value_cleaning/data/for_tte/edge-[0.01, 0.05].pkl"

    _DATA_ROOT = os.environ.get("PFM_DATA_ROOT", "/path/to/PFM_data")
    # Tokenize the split matching --seq_gen (addQ for share_tokens=1, NOadd for share_tokens=0).
    for folder_path in [os.path.join(_DATA_ROOT, "PFM_pretraining", args.seq_gen, _split)
                        for _split in ["test", "train"]]:
        process_folder_to_dataset_parallel(folder_path, args.tte_threshold, tokenizer, processor, max_length = args.sample_max_length,
                                           overlap_size = args.sample_overlap, 
                              basic_dir = None, tte_dir = None, addQ = "NOadd" in str(folder_path),
                              ethos = args.pe_baseline == 'ETHOS', raw = args.bin.startswith('raw'))
