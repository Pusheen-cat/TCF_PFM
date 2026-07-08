import pandas as pd
import os
from pathlib import Path
import numpy as np
import shutil
# Allow running this file directly (python <path>): put the repo root on sys.path.
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from mimic4preprocessing.my_itemid import my_itemid

def preprocess_csv_file(input_path, output_path=None, only_timestamp = False):
    """
    단일 CSV 파일을 전처리합니다.

    Args:
        input_path (str): 입력 CSV 파일 경로
        output_path (str): 출력 CSV 파일 경로 (None이면 원본 덮어쓰기)
    """
    # CSV 파일 읽기
    df = pd.read_csv(input_path)

    #['subject_id', 'hadm_id', 'stay_id', 'charttime', 'itemid', 'itemname', 'value', 'valueuom', 'linksto', 'order']

    # time 컬럼을 datetime으로 변환
    df['charttime'] = pd.to_datetime(df['charttime'])
    df['subject_id'] = pd.to_numeric(df['subject_id'], errors='coerce').astype('Int64')
    df['hadm_id'] = pd.to_numeric(df['hadm_id'], errors='coerce').astype('Int64')
    df['stay_id'] = pd.to_numeric(df['stay_id'], errors='coerce').astype('Int64')
    df['itemid'] = df['itemid'].astype('int64')

    # 1. time 순으로 정렬
    df = df.sort_values(by=['charttime', 'order'], ascending=[True, False]).reset_index(drop=True)

    # 2. meta가 아닌 각 행에 대해 question 행 추가
    new_rows = []

    # print(df)
    # print(df.columns) #['subject_id', 'hadm_id', 'stay_id', 'charttime', 'itemid', 'itemname', 'value', 'valueuom', 'linksto', 'order']

    for idx, row in df.iterrows():
        if row['itemid'] < 1000000:
            # question 행을 해당 행 바로 위에 추가
            question_row = row.to_dict().copy()
            question_row['value'] = str(question_row['itemid'])
            question_row['itemid'] = my_itemid['Question']['itemid']
            question_row['itemname'] = 'Question'
            new_rows.append(question_row)
            new_rows.append(row.to_dict())
        else:
            # meta 행은 그대로 추가
            new_rows.append(row.to_dict())

    # 새로운 데이터프레임 생성
    result_df = pd.DataFrame(new_rows)

    # time 순으로 정렬하되, 같은 시간에서는 원래 순서 유지를 위해 인덱스 추가
    result_df['original_order'] = range(len(result_df))
    result_df = result_df.sort_values(['charttime', 'original_order']).drop('original_order', axis=1)
    result_df = result_df.reset_index(drop=True)

    # 출력 경로 설정
    if output_path is None:
        output_path = input_path

    # 결과 저장
    result_df.to_csv(output_path, index=False)#, sep='\t')

    print(f"처리 완료: {input_path}")
    print(f"  - 원본 행 수: {len(df)}")
    print(f"  - 처리 후 행 수: {len(result_df)}")
    print(f"  - 추가된 question 행 수: {len(result_df) - len(df)}")

    return True



def preprocess_folder(train_folder_path, output_folder_path=None, only_timestamp = False):
    """
    train 폴더 내의 모든 CSV 파일을 전처리합니다.

    Args:
        train_folder_path (str): train 폴더 경로
        output_folder_path (str): 출력 폴더 경로 (None이면 원본 폴더에 덮어쓰기)
    """
    train_path = Path(train_folder_path)

    if not train_path.exists():
        print(f"train 폴더가 존재하지 않습니다: {train_folder_path}")
        return

    # 출력 폴더 설정
    if output_folder_path is not None:
        output_path = Path(output_folder_path)
        output_path.mkdir(parents=True, exist_ok=True)
    else:
        output_path = train_path

    # 내부 폴더 이름 (subject_id) 찾기
    folder_names = [
        p.name
        for p in train_path.iterdir()
        if p.is_dir()
    ]

    if not folder_names:
        print(f"train 폴더에 내부 폴더가 파일이 없습니다: {train_folder_path}")
        return

    ## 10000032 와 같이 8자리 int이고 10000000이상이고 20000000 미만인지 assert
    assert all(
        name.isdigit() and
        len(name) == 8 and
        10_000_000 <= int(name) < 20_000_000
        for name in folder_names
    ), "folder_names에 8자리 숫자가 아니거나 범위를 벗어난 값이 있습니다"

    print(f"총 {len(folder_names)}개의 subject_id를 처리합니다...")

    success_count = 0
    fail_count = 0

    for subject_id_folder in folder_names:
        if output_folder_path is not None:
            output_file_path = output_path / str(subject_id_folder[:3])
            output_file_path.mkdir(parents=True, exist_ok=True)
            output_file_path = output_file_path / f"{subject_id_folder}.csv"
        else:
            output_file_path = None

        if preprocess_csv_file(str(train_path)+'/'+str(subject_id_folder)+'/events.csv', str(output_file_path) if output_file_path else None, only_timestamp):
            success_count += 1
        else:
            fail_count += 1

        print("-" * 50)

    print(f"\n전처리 완료!")
    print(f"성공: {success_count}개")
    print(f"실패: {fail_count}개")


def preview_file(file_path, num_rows=20):
    """
    처리된 파일의 일부를 미리보기합니다.
    """
    try:
        df = pd.read_csv(file_path)#, sep='\t')
        print(f"\n파일 미리보기: {file_path}")
        print(f"총 행 수: {len(df)}")
        print("\n처음 {num_rows}행:")
        print(df.head(num_rows).to_string(index=False))

        # question 행 개수 확인
        question_count = len(df[df['datatype'] == 'question'])
        meta_count = len(df[df['datatype'] == 'meta'])
        other_count = len(df[df['datatype'].isin(['question', 'meta']) == False])

        print(f"\nDatatype 분포:")
        print(f"  - question: {question_count}개")
        print(f"  - meta: {meta_count}개")
        print(f"  - 기타: {other_count}개")

    except Exception as e:
        print(f"미리보기 오류: {str(e)}")

def copy_events_to_sharded_dir(src_dir, dst_dir):
    """
    src_dir/
        └─ subject_id/
            └─ events.csv

    dst_dir/
        └─ subject_id[:3]/
            └─ subject_id.csv
    """
    os.makedirs(dst_dir, exist_ok=True)

    with os.scandir(src_dir) as it:
        for entry in it:
            if not entry.is_dir():
                continue

            subject_id = entry.name
            src_file = os.path.join(entry.path, "events.csv")

            if not os.path.isfile(src_file):
                continue

            mid_folder = subject_id[:3]
            dst_mid_dir = os.path.join(dst_dir, mid_folder)
            os.makedirs(dst_mid_dir, exist_ok=True)

            dst_file = os.path.join(dst_mid_dir, f"{subject_id}.csv")

            # copy + 원본 유지 (메타데이터 포함)
            shutil.copy2(src_file, dst_file)
# 사용 예시
if __name__ == "__main__":
    # Insert a Question token before every event (addQ) and also shard the raw
    # event stream (NOadd). Set PFM_DATA_ROOT to your preprocessing output tree.
    DATA_ROOT = os.environ.get("PFM_DATA_ROOT", "/path/to/PFM_data")
    for split in ["train", "test"]:
        in_folder = os.path.join(DATA_ROOT, "B_train_test_split", split)
        preprocess_folder(in_folder, os.path.join(DATA_ROOT, "PFM_pretraining", "addQ", split))
        noadd_out = os.path.join(DATA_ROOT, "PFM_pretraining", "NOadd", split)
        os.makedirs(noadd_out, exist_ok=True)
        copy_events_to_sharded_dir(in_folder, noadd_out)
