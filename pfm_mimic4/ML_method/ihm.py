features = ['50812', '50813', '50852', '50882', '50884', '50889', '50903', '50904', '50905', '50907', '50924', '50930', '50934', '50947', '50952', '50953', '50954', '50976', '50986', '50993', '50995', '50998', '51003', '51007', '51010', '51082', '51143', '51248', '51249', '51250', '51251', '51255', '51257', '51265', '51277', '51279', '51463', '51464', '51466', '51476', '51478', '51482', '51484', '51486', '51487', '51492', '51493', '51506', '51512', '51514', '51516', '51519', '51613', '51678', '52033', '52172', '220045', '220048', '220050', '220051', '220052', '220179', '220180', '220181', '220210', '220224', '220228', '220235', '220277', '220339', '220545', '220546', '220587', '220602', '220615', '220621', '220635', '220644', '220645', '220734', '220739', '223762', '223783', '223784', '223830', '223834', '223835', '223898', '223900', '223901', '223907', '223934', '223935', '223943', '223947', '223951', '223976', '223979', '223982', '223983', '223986', '223987', '223988', '223989', '223991', '223992', '223999', '224001', '224003', '224004', '224016', '224026', '224027', '224028', '224054', '224055', '224056', '224057', '224058', '224059', '224084', '224086', '224308', '224639', '224685', '224689', '224690', '224691', '224697', '224733', '224767', '224769', '224771', '224773', '224828', '224860', '224876', '225612', '225624', '225625', '225634', '225638', '225639', '225640', '225641', '225642', '225643', '225651', '225664', '225667', '225668', '225672', '225677', '225690', '225693', '225698', '226560', '226588', '226606', '226730', '226732', '227073', '227121', '227288', '227442', '227443', '227445', '227455', '227456', '227457', '227465', '227466', '227467', '227468', '227471', '227510', '227951', '228096', '228299', '228409', '228410', '228411', '228412', '228414', '228640', '229321', '229356', '229357', '229358', '229359', '229360', '229361', '229381', '909000', '909001']

import os
import glob
import pandas as pd
import numpy as np
from tqdm import tqdm
from multiprocessing import Pool
from functools import partial
import warnings

# Scikit-learn & Models
from sklearn.metrics import roc_auc_score, average_precision_score
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier

# 경고 무시
warnings.filterwarnings('ignore')

# ==========================================
# 1. 경로 및 설정
# ==========================================
PATH_FEATURE_ROOT = '/path/to/PFM_data/PFM_downstream/processed_criteria1/NOadd/'
PATH_LABEL_ROOT = '/path/to/PFM_data/PFM_downstream/NOadd/'

CACHE_PATH = './'  # 전처리된 데이터를 저장할 경로
TRAIN_PKL = os.path.join(CACHE_PATH, 'train_mimic_processed.pkl')
TEST_PKL = os.path.join(CACHE_PATH, 'test_mimic_processed.pkl')

# 사용할 Feature List (예시 - 실제 리스트로 교체 필요)
# 문제에서 'features' 변수가 주어진다고 가정
FEATURES = ['50812', '50813', '50852', '50882', '50884', '50889', '50903', '50904', '50905', '50907',
            '50924', '50930', '50934', '50947', '50952', '50953', '50954', '50976', '50986', '50993',
            '50995', '50998', '51003', '51007', '51010', '51082', '51143', '51248', '51249', '51250',
            '51251', '51255', '51257', '51265', '51277', '51279', '51463', '51464', '51466', '51476',
            '51478', '51482', '51484', '51486', '51487', '51492', '51493', '51506', '51512', '51514',
            '51516', '51519', '51613', '51678', '52033', '52172', '220045', '220048', '220050', '220051',
            '220052', '220179', '220180', '220181', '220210', '220224', '220228', '220235', '220277', '220339',
            '220545', '220546', '220587', '220602', '220615', '220621', '220635', '220644', '220645', '220734',
            '220739', '223762', '223783', '223784', '223830', '223834', '223835', '223898', '223900', '223901',
            '223907', '223934', '223935', '223943', '223947', '223951', '223976', '223979', '223982', '223983',
            '223986', '223987', '223988', '223989', '223991', '223992', '223999', '224001', '224003', '224004',
            '224016', '224026', '224027', '224028', '224054', '224055', '224056', '224057', '224058', '224059',
            '224084', '224086', '224308', '224639', '224685', '224689', '224690', '224691', '224697', '224733',
            '224767', '224769', '224771', '224773', '224828', '224860', '224876', '225612', '225624', '225625',
            '225634', '225638', '225639', '225640', '225641', '225642', '225643', '225651', '225664', '225667',
            '225668', '225672', '225677', '225690', '225693', '225698', '226560', '226588', '226606', '226730',
            '226732', '227073', '227121', '227288', '227442', '227443', '227445', '227455', '227456', '227457',
            '227465', '227466', '227467', '227468', '227471', '227510', '227951', '228096', '228299', '228409',
            '228410', '228411', '228412', '228414', '228640', '229321', '229356', '229357', '229358', '229359',
            '229360', '229361', '229381', '909000', '909001']

# 만약 Features가 비어있다면 자동 탐색 로직을 켤 수 있음
if not FEATURES:
    AUTO_DISCOVER = True
else:
    AUTO_DISCOVER = False

N_BOOTSTRAPS = 200
CI_ALPHA = 0.95
NUM_CORES = 32  # 병렬 처리에 사용할 코어 수


# ==========================================
# 2. 데이터 전처리 함수 (Core Logic)
# ==========================================

def get_label_path(pkl_path, feature_root, label_root):
    """
    Feature pkl 경로를 기반으로 대응되는 Label csv 경로를 생성
    """
    # 1. Feature Root 이후의 상대 경로 추출 (예: train/100/12345678/abc.pkl)
    rel_path = os.path.relpath(pkl_path, feature_root)

    # 2. 디렉토리 부분과 파일명 분리
    dir_name, file_name = os.path.split(rel_path)

    # 3. Label 파일명 생성 (label_ihm_{pkl이름}.csv)
    # 확장자 .pkl을 제거한 이름을 사용할지, 포함할지에 대한 명세가 "pkl 파일 이름"이므로
    # 보통 파일 이름(stem)을 의미한다고 가정 (abc.pkl -> label_ihm_abc.csv)
    file_stem = os.path.splitext(file_name)[0]
    label_filename = f"label_ihm_{file_stem}.csv"

    # 4. 최종 경로 결합
    return os.path.join(label_root, dir_name, label_filename)


def process_single_sample(pkl_path, feature_root, label_root, feature_names):
    """
    하나의 pkl 파일과 대응되는 label 파일을 읽어 처리
    """
    # ---------------------------
    # 1. Label Load & Parsing
    # ---------------------------
    label_path = get_label_path(pkl_path, feature_root, label_root)

    if not os.path.exists(label_path):
        raise AttributeError

    df_label = pd.read_csv(label_path)

    if df_label.empty:
        return None

    # 첫 번째 row 사용 (row는 최대 1개)
    row_label = df_label.iloc[0]

    # Charttime 변환

    chart_time = pd.to_datetime(row_label['charttime'])
    label_val = int(row_label['ihm'])

    if label_val not in [0, 1]:
        raise AttributeError

    # ---------------------------
    # 2. Feature Load & Filtering
    # ---------------------------
    df_feat = pd.read_pickle(pkl_path)

    # 필요한 컬럼 확인
    required_cols = {'itemid', 'value', 'time'}
    if not required_cols.issubset(df_feat.columns):
        raise AttributeError

    # Time 변환 및 Charttime 이전 데이터만 필터링
    # df_feat['time']은 이미 datetime일 수도 있지만 안전하게 변환
    df_feat['time'] = pd.to_datetime(df_feat['time'], errors='coerce')

    # Time이 유효하고(Not NaT), Charttime보다 이른(Strictly less than) 데이터만 남김
    df_filtered = df_feat[df_feat['time'] < chart_time]

    if df_filtered.empty:
        # 데이터가 없으면 Feature는 모두 NaN, Label은 유지할지 결정해야 함.
        # 일반적으로 정보가 없으면 학습에 방해되므로 skip 하거나 NaN으로 채워서 리턴.
        # 여기서는 NaN으로 채워서 리턴하는 전략 사용 (모델이 처리하도록)
        raise AttributeError

    # ---------------------------
    # 3. Aggregation
    # ---------------------------
    # 우리가 관심 있는 Feature(itemid)만 남김
    # itemid는 string 형식이므로 feature_names와 타입 일치해야 함
    df_relevant = df_filtered[df_filtered['itemid'].isin(feature_names)].copy()

    # Value Float 변환
    def to_float(x):
        try:
            return float(x)
        except:
            raise ValueError

    df_relevant['value'] = df_relevant['value'].apply(to_float)


    # 평균 계산
    grouped = df_relevant.groupby('itemid')['value'].mean()

    # 결과 딕셔너리 생성
    result = {}
    for feat in feature_names:
        result[feat] = grouped.get(feat, np.nan)

    result['label'] = label_val

    return result


def load_dataset_parallel(feature_root, label_root, split_type, feature_names):
    """
    feature_root/{split_type}/... 내의 모든 pkl 파일을 찾아 병렬 처리
    split_type: 'train' or 'test'
    """
    # 파일 검색 패턴: root/split/chunk(100-200)/subject_id/*.pkl
    # glob.glob는 recursive=True와 **를 사용하면 편리함
    search_pattern = os.path.join(feature_root, split_type, '**', '*.pkl')
    print(f"Scanning files for {split_type} dataset...")

    # recursive=True를 사용하여 하위 폴더 전체 검색
    all_pkl_files = glob.glob(search_pattern, recursive=True)

    if not all_pkl_files:
        print(f"No files found in {search_pattern}")
        return pd.DataFrame()

    print(f"Found {len(all_pkl_files)} files. Processing with {NUM_CORES} cores...")

    # Partial function으로 고정 인자 전달
    process_func = partial(
        process_single_sample,
        feature_root=feature_root,
        label_root=label_root,
        feature_names=feature_names
    )

    # Multiprocessing
    with Pool(processes=NUM_CORES) as pool:
        results = list(tqdm(pool.imap(process_func, all_pkl_files), total=len(all_pkl_files)))

    # None 제거
    valid_results = [r for r in results if r is not None]

    return pd.DataFrame(valid_results)


# ==========================================
# 3. Bootstrap CI 계산 함수
# ==========================================
def calculate_bootstrap_ci(y_true, y_pred, n_bootstraps=200, rng_seed=42):
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    rng = np.random.RandomState(rng_seed)
    n_samples = len(y_true)

    auroc_scores = []
    auprc_scores = []

    point_auroc = roc_auc_score(y_true, y_pred)
    point_auprc = average_precision_score(y_true, y_pred)

    for _ in range(n_bootstraps):
        indices = rng.randint(0, n_samples, n_samples)
        if len(np.unique(y_true[indices])) < 2: continue

        try:
            auroc_scores.append(roc_auc_score(y_true[indices], y_pred[indices]))
            auprc_scores.append(average_precision_score(y_true[indices], y_pred[indices]))
        except:
            continue

    lower_p = (1.0 - CI_ALPHA) / 2.0 * 100
    upper_p = (1.0 + CI_ALPHA) / 2.0 * 100

    return point_auroc, np.percentile(auroc_scores, [lower_p, upper_p]), \
        point_auprc, np.percentile(auprc_scores, [lower_p, upper_p])


# ==========================================
# 4. 메인 실행 블록
# ==========================================
if __name__ == '__main__':

    # ----------------------------------
    # A. 데이터 로드 (캐시 확인 or 생성)
    # ----------------------------------
    if os.path.exists(TRAIN_PKL) and os.path.exists(TEST_PKL):
        print(f"Loading cached datasets from {CACHE_PATH}...")
        train_df = pd.read_pickle(TRAIN_PKL)
        test_df = pd.read_pickle(TEST_PKL)

        # 저장된 데이터에서 Feature List 복원
        FEATURES = [c for c in train_df.columns if c != 'label']
        print(f"Loaded successfully. {len(FEATURES)} features.")

    else:
        print("Cached datasets not found. Starting preprocessing...")

        # (옵션) Feature List가 비어있다면 Train 파일 일부를 스캔해서 Feature 찾기
        if AUTO_DISCOVER and not FEATURES:
            print("Auto-discovering features from a subset of files...")
            # 여기서는 복잡도를 줄이기 위해 하드코딩된 리스트 사용을 권장하지만,
            # 필요하다면 파일 몇 개를 열어 unique itemid를 수집하는 로직 추가 가능
            pass  # prompt에서 features가 주어진다고 했으므로 생략

        # Test 데이터 생성
        test_df = load_dataset_parallel(PATH_FEATURE_ROOT, PATH_LABEL_ROOT, 'test', FEATURES)
        # Train 데이터 생성
        train_df = load_dataset_parallel(PATH_FEATURE_ROOT, PATH_LABEL_ROOT, 'train', FEATURES)

        print(f"Saving to pickle: {TRAIN_PKL}, {TEST_PKL}")
        train_df.to_pickle(TRAIN_PKL)
        test_df.to_pickle(TEST_PKL)
        print("Save complete.")

    # ----------------------------------
    # B. 데이터 준비 (X, y 분리)
    # ----------------------------------
    X_train = train_df[FEATURES]
    y_train = train_df['label']
    X_test = test_df[FEATURES]
    y_test = test_df['label']

    print(f"\nTrain Shape: {X_train.shape}, Test Shape: {X_test.shape}")
    print(f"Label Distribution (Train): {y_train.value_counts().to_dict()}")

    # 결측치 처리 (Linear Model용)
    imputer = SimpleImputer(strategy='mean')
    X_train_imputed = imputer.fit_transform(X_train)
    X_test_imputed = imputer.transform(X_test)

    # ----------------------------------
    # C. 모델 정의
    # ----------------------------------
    models = {
        "Logistic Regression": LogisticRegression(max_iter=1000, random_state=42),
        "Decision Tree": DecisionTreeClassifier(random_state=42),
        "Random Forest": RandomForestClassifier(n_estimators=100, random_state=42),
        "XGBoost": xgb.XGBClassifier(use_label_encoder=False, eval_metric='logloss', random_state=42),
        "CatBoost": CatBoostClassifier(verbose=0, random_state=42),
        "LightGBM": lgb.LGBMClassifier(random_state=42, verbose=-1)
    }

    # ----------------------------------
    # D. 학습 및 평가
    # ----------------------------------
    print("\n" + "=" * 85)
    print(f"{'Model':<20} | {'AUROC (95% CI)':<30} | {'AUPRC (95% CI)':<30}")
    print("=" * 85)

    result_rows = []

    for name, model in models.items():
        try:
            # 트리 기반 모델은 NaN 처리 가능 -> 원본 사용
            # 선형 모델은 Imputed 사용
            if name == "Logistic Regression":
                X_tr, X_te = X_train_imputed, X_test_imputed
            else:
                X_tr, X_te = X_train, X_test

            # 학습
            model.fit(X_tr, y_train)

            # 예측
            y_pred_prob = model.predict_proba(X_te)[:, 1]

            # CI 계산
            pt_auroc, ci_auroc, pt_auprc, ci_auprc = calculate_bootstrap_ci(
                y_test, y_pred_prob, n_bootstraps=N_BOOTSTRAPS
            )

            # 포맷팅
            auroc_str = f"{pt_auroc:.3f} ({ci_auroc[0]:.3f}-{ci_auroc[1]:.3f})"
            auprc_str = f"{pt_auprc:.3f} ({ci_auprc[0]:.3f}-{ci_auprc[1]:.3f})"

            print(f"{name:<20} | {auroc_str:<30} | {auprc_str:<30}")

            result_rows.append({
                'Model': name,
                'AUROC_Point': pt_auroc, 'AUROC_Low': ci_auroc[0], 'AUROC_High': ci_auroc[1],
                'AUPRC_Point': pt_auprc, 'AUPRC_Low': ci_auprc[0], 'AUPRC_High': ci_auprc[1]
            })

        except Exception as e:
            print(f"{name:<20} | Error: {str(e)}")

    print("=" * 85)