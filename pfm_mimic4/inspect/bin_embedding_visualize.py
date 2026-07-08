# 학습이 완료된 10개의 bin의 embedding을 가져와서 visualize하는 것 코드
import matplotlib
matplotlib.use("TkAgg")
import torch
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt
import umap.umap_ as umap
import numpy as np

# 학습되어 저장된 G2 모델 불러오기
checkpoint = torch.load("/path/to/PFM_data/result_pretrained/max_len2048_overlap512_h512_h8_l6_ff2048/"
                        "fcriteria1_bin10_exp1_th10_share0_NOadd_G2DYDTSP_rope:U1M1TS40_0124:001326/check_points/checkpoint_epoch_50.pt", map_location="cpu")

# model state dict 가져오기
state_dict = checkpoint["model_state"]

# 2. token_embedding 이 들어간 key 찾기
embedding_key = None
for k in state_dict.keys():
    if "token_embedding" in k and "weight" in k:
        embedding_key = k
        print(f"Found embedding key: {embedding_key}")
        break

if embedding_key is None:
    raise ValueError("No embedding key containing 'token_embedding' found in state_dict")

# 3. weight 추출
embedding_weight = state_dict[embedding_key]  # (vocab_size, embedding_dim)

print(embedding_weight.shape)

mean = embedding_weight.mean(dim=1, keepdim=True)
std = embedding_weight.std(dim=1, keepdim=True)
embedding_weight = (embedding_weight - mean) / (std + 1e-6)

# 4. 인덱스 178~187 선택
selected_weights = embedding_weight[371:381].cpu()  # 188은 제외 → 10개


# ####################
# x_norm = torch.nn.functional.normalize(selected_weights, p=2, dim=1)
# # 코사인 유사도 (10x10)
# cos_sim = torch.matmul(x_norm, x_norm.T)  # (10, 10)
#
# # numpy로 변환
# cos_sim = cos_sim.cpu().numpy()
#
# # Heatmap 시각화
# plt.figure(figsize=(6, 5))
# plt.imshow(cos_sim, cmap="coolwarm", interpolation="nearest")
# plt.colorbar(label="Cosine Similarity")
# plt.title("10x10 Cosine Similarity Heatmap")
# plt.xlabel("Vector Index")
# plt.ylabel("Vector Index")
#
# # 값 텍스트 표시
# for i in range(cos_sim.shape[0]):
#     for j in range(cos_sim.shape[1]):
#         plt.text(j, i, f"{cos_sim[i, j]:.2f}",
#                  ha="center", va="center", color="black", fontsize=8)
#
# plt.show()
#
# raise AttributeError
# ###################

selected_weights = selected_weights.numpy()

norms = np.linalg.norm(selected_weights, axis=1, keepdims=True)  # 각 row의 L2 norm
selected_weights = selected_weights / norms

# 5. PCA 적용 (2차원)
pca = PCA(n_components=2)
weights_2d = pca.fit_transform(selected_weights)

# 6. 시각화
plt.figure(figsize=(6, 6))
plt.scatter(weights_2d[:, 0], weights_2d[:, 1], c="blue", marker="o")

for i, idx in enumerate(range(0, 10)):
    plt.text(weights_2d[i, 0] + 0.1, weights_2d[i, 1] + 0.1, str(idx), fontsize=9)

plt.title(f"PCA of {embedding_key}[178:187]")
plt.xlabel("PC1")
plt.ylabel("PC2")
plt.grid(True)
plt.show()

# 5. UMAP 적용 (2차원)
reducer = umap.UMAP(n_components=2, random_state=42)
weights_2d = reducer.fit_transform(selected_weights)

# 6. 시각화
plt.figure(figsize=(6, 6))
plt.scatter(weights_2d[:, 0], weights_2d[:, 1], c="blue", marker="o")

for i, idx in enumerate(range(178, 188)):
    plt.text(weights_2d[i, 0] + 0.01, weights_2d[i, 1] + 0.01, str(idx), fontsize=9)

plt.title(f"UMAP of {embedding_key}[178:187]")
plt.xlabel("UMAP-1")
plt.ylabel("UMAP-2")
plt.grid(True)
plt.show()