'''
ITEMID
30051	Vasopressin		inputevents_cv	0
42273	vasopressin unit/min		inputevents_cv	0
42802	VASOPRESSIN  CC/HR.		inputevents_cv	0
222315	Vasopressin	units	inputevents_mv	0

30042	Dobutamine		inputevents_cv	0
30306	Dobutamine Drip		inputevents_cv	0
221653	Dobutamine	mg	inputevents_mv	0

30309	Epinephrine Drip		inputevents_cv	0
30119	Epinephrine-k		inputevents_cv	0
30044	Epinephrine		inputevents_cv	0
221289	Epinephrine	mg	inputevents_mv	0	Medications
221906	Norepinephrine	mg	inputevents_mv	0


30043	Dopamine		inputevents_cv	0
30307	Dopamine Drip		inputevents_cv	0
221662	Dopamine	mg	inputevents_mv	0

'''

import os
import pandas as pd

# Preprocessing roots (edit or set these env vars; see README).
MIMIC4_ROOT = os.environ.get("MIMIC4_ROOT", "/path/to/mimiciv/3.1")
_ICU = os.path.join(MIMIC4_ROOT, "icu")
_RESOURCES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "resources")


def preproc():
    #필요한 itemid 목록 정의
    """MIMIC4는 MV only"""
    """
    inputevents_cv_itemids = [
        30051, 42273, 42802,    # Vasopressin (CV)
        30042, 30306,           # Dobutamine (CV)
        30309, 30119, 30044, 30047, 30120,    # Epinephrine, Norepinephrine (CV)
        30043, 30307            # Dopamine (CV)
    ]
    """

    inputevents_mv_itemids = [
        222315,                 # Vasopressin (MV)
        221653,                 # Dobutamine (MV)
        221289, 221906,         # Epinephrine, Norepinephrine (MV)
        221662                  # Dopamine (MV)
    ]

    # 파일 경로를 설정합니다
    inputevents_path = os.path.join(_ICU, 'inputevents.csv')

    # 2. CSV 파일 로드 및 필터링
    df = pd.read_csv(inputevents_path, low_memory=False)

    filtered = df[df['itemid'].isin(inputevents_mv_itemids)]

    print(f'filtered length: ', len(filtered))

    df_existence = (df[['subject_id', 'hadm_id', 'stay_id']].drop_duplicates().reset_index(drop=True))

    filtered = filtered.sort_values(by=['subject_id', 'starttime']).reset_index(drop=True)

    filtered = filtered.drop(columns=['caregiver_id'])

    # AMOUNT와 RATE가 모두 NaN 또는 0인 행 필터링
    filtered = filtered[~(
        (filtered['amount'].fillna(0) == 0) &
        (filtered['rate'].fillna(0) == 0)
    )].reset_index(drop=True)

    print('columns: ',filtered.columns)


    # 결측값이 있을 수도 있는 경우
    filtered['hadm_id'] = filtered['hadm_id'].astype('Int64')
    filtered['stay_id'] = filtered['stay_id'].astype('Int64')

    combined_df = filtered

    # testset.csv 파일 읽기
    print("mimic4-testset.csv 파일 읽는 중...")
    testset_df = pd.read_csv(os.path.join(_RESOURCES, 'mimic4-testset.csv'), header=None, names=['subject_id', 'split'])

    # train/test 분할 정보를 딕셔너리로 저장
    split_dict = dict(zip(testset_df['subject_id'], testset_df['split']))

    # 4. train/test로 분할하여 저장
    print("데이터를 train/test로 분할하여 저장 중...")

    # train 데이터
    train_subjects = [sid for sid, split in split_dict.items() if split == 0]
    train_vaso = combined_df[combined_df['subject_id'].isin(train_subjects)]
    train_existence = df_existence[df_existence['subject_id'].isin(train_subjects)]
    # test 데이터
    test_subjects = [sid for sid, split in split_dict.items() if split == 1]
    test_vaso = combined_df[combined_df['subject_id'].isin(test_subjects)]
    test_existence = df_existence[df_existence['subject_id'].isin(test_subjects)]

    # 결과 저장
    train_vaso.to_pickle(os.path.join(_ICU, 'inputevents_train_vaso.pkl'))

    test_vaso.to_pickle(os.path.join(_ICU, 'inputevents_test_vaso.pkl'))

    train_existence.to_pickle(os.path.join(_ICU, 'inputevents_train_existence.pkl'))

    test_existence.to_pickle(os.path.join(_ICU, 'inputevents_test_existence.pkl'))


if __name__ == "__main__":
    preproc()
