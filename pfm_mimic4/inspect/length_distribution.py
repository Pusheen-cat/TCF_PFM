import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import numpy as np
import pickle

path = '/path/to/PFM_data/PFM_pretraining/processed_criteria1/tokenized_splited/maxlen2048_overlap512_processed_criteria1_share0_ethosFalse_bin10_exp1_th10/NOadd/'
# 예시 데이터 (실제 데이터로 교체)
with open(path+"train/sample_lens.pkl", "rb") as f:
    train_lengths = pickle.load(f)

with open(path+"test/sample_lens.pkl", "rb") as f:
    test_lengths = pickle.load(f)

print(f'{len(train_lengths)} | train token total: {sum(train_lengths.values())}, avg: {sum(train_lengths.values())/len(train_lengths)}, max: {max(train_lengths.values())}')
print(f'{len(test_lengths)} | test token total: {sum(test_lengths.values())}, avg: {sum(test_lengths.values())/len(test_lengths)}, max: {max(test_lengths.values())}')

path = '/path/to/PFM_data/PFM_pretraining/tensor_saved/max_len_2048_overlap_512/featurecriteria1_bin10_exp0.5_th10_share0_NOadd/'
# 예시 데이터 (실제 데이터로 교체)
with open(path+"train_subject_id_index.pkl", "rb") as f:
    train_lengths = pickle.load(f)

with open(path+"test_subject_id_index.pkl", "rb") as f:
    test_lengths = pickle.load(f)

print(f'{sum(v for _, v in train_lengths)}')
print(f'{sum(v for _, v in test_lengths)}')
# 전체 최소/최대 길이
min_len = min(min(train_lengths), min(test_lengths))
max_len = max(max(train_lengths), max(test_lengths))

print(max_len) #393337
max_len = 10000

# bin 정의 (20개 구간)
bins = np.linspace(min_len, max_len, 101)

# 각 구간별 count 계산
train_counts, _ = np.histogram(train_lengths, bins=bins)
test_counts, _ = np.histogram(test_lengths, bins=bins)

# 막대 위치 (bin 중앙값)
bin_centers = (bins[:-1] + bins[1:]) / 2
bar_width = (bins[1] - bins[0]) * 0.4  # bin 폭의 40% 사용 (train/test 나눠서 2개)

# 그래프 그리기
plt.bar(bin_centers - bar_width/2, train_counts, width=bar_width, color='red', alpha=0.7, label='Train')
plt.bar(bin_centers + bar_width/2, test_counts, width=bar_width, color='blue', alpha=0.7, label='Test')

plt.xlabel("Sample Length")
plt.ylabel("Count")
plt.title("Distribution of Sample Token Lengths (Train vs Test)")
plt.legend()

# PDF로 저장
plt.savefig("sample_length_distribution.pdf", format="pdf")

plt.show()
