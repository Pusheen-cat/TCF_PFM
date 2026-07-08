import os
import torch
import torch.nn as nn
import torch.nn.functional as F
import math
from typing import Tuple, Optional
from modules.dt_head import dt_projection
from pfm_mimic4.tokenizer.multitype_tokenizer import my_tokens

from model.time_condition_module_pos import gen_labelset_pos, timecondition_res_module_pos
from model.Xshare_time_condition_module_pos import Xshare_gen_labelset_pos

class TSmultiRoPE(nn.Module):
    """Timestamp를 위한 RoPE (회전 위치 인코딩)"""

    def __init__(self, dim: int, ):
        super().__init__()
        self.dim = dim

        # 시간 주기들 (초 단위)
        self.cycles = {  # 20
            # '1min': 60,  # 1분
            '5min': 300,  # 5분
            '10min': 600,  # 10분
            '30min': 1800,  # 30분
            'hour': 3600,  # 1시간
            '3hour': 10800,  # 3시간
            '12hour': 43200,  # 12시간
            'day': 86400,  # 1일
            'day2': 172800,  # 2일
            'week': 604800,  # 1주일
            'week2': 1209600,  # 2주일
            'month': 2629746,  # 1/12년
            'season': 7889238,  # 분기 (평균 월 × 3)
            '6month': 15778476,  # 반년
            'year': 31556952,  # 1년 - 윤년 고려
            '2year': 63113904,  # 2년
            '4year': 126227808,  # 4년
            '10year': 315569520,  # 10년
            '30year': 946708560,  # 30년
            '100year': 3155695200,  # 100년
            '300year': 9467085600  # 300년
        }

        # 사용할 주기 수 계산 (dim // 2개의 주기만 사용)
        self.num_cycles = dim // 2
        cycle_values = list(self.cycles.values())[:self.num_cycles]
        self.cycle_values = cycle_values

    def forward(self, timestamps: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            timestamps: [batch_size, seq_len] 또는 [seq_len]
        Returns:
            cos, sin: 각각 [..., dim//2]
        """
        original_shape = timestamps.shape
        device = timestamps.device

        # timestamps를 1차원으로 flatten
        timestamps_flat = timestamps.flatten()

        # broadcasting으로 각 주기에 대한 phase를 계산 → cos/sin
        cycle_values_tensor = torch.tensor(self.cycle_values, device=device)  # [num_cycles]
        phase = ((timestamps_flat[:, None] % cycle_values_tensor[None, :]) / cycle_values_tensor[None,
                                                                             :]) * 2 * math.pi  # [total_positions, num_cycles]
        cos_embeddings = torch.cos(phase)  # [total_positions, num_cycles]
        sin_embeddings = torch.sin(phase)  # [total_positions, num_cycles]

        # 원래 shape으로 복원
        cos_embeddings = cos_embeddings.view(*original_shape, self.dim // 2)
        sin_embeddings = sin_embeddings.view(*original_shape, self.dim // 2)

        return cos_embeddings, sin_embeddings


class TSmonoRoPE(nn.Module):
    """표준 TS RoPE (Day since birth base)"""

    def __init__(self, dim: int, base: float = 17500.0):
        super().__init__()
        self.dim = dim
        self.base = base

        # 주파수 계산
        inv_freq = 1.0 / (base ** (torch.arange(0, max(64, self.dim), 2).float() / max(64, self.dim)))[:(self.dim // 2)]
        self.register_buffer('inv_freq', inv_freq)

    def forward(self, positions: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            positions: [seq_len] 또는 [batch_size, seq_len]
        Returns:
            cos, sin: 각각 [..., dim//2]
        """
        positions = positions / 86400  # To Day
        original_shape = positions.shape

        # 1차원으로 flatten
        positions_flat = positions.flatten().float()

        # [total_positions, dim//2]
        freqs = torch.outer(positions_flat, self.inv_freq)
        cos = torch.cos(freqs)
        sin = torch.sin(freqs)

        # 원래 shape으로 복원 + 마지막 차원 추가
        cos = cos.view(*original_shape, self.dim // 2)
        sin = sin.view(*original_shape, self.dim // 2)
        return cos, sin


class StandardRoPE(nn.Module):
    """표준 RoPE (토큰 위치용)"""

    def __init__(self, dim: int, base: float = 10000.0):
        super().__init__()
        self.dim = dim
        self.base = base

        # 주파수 계산
        inv_freq = 1.0 / (base ** (torch.arange(0, max(64, self.dim), 2).float() / max(64, self.dim)))[:(self.dim // 2)]
        self.register_buffer('inv_freq', inv_freq)

    def forward(self, positions: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            positions: [seq_len] 또는 [batch_size, seq_len]
        Returns:
            cos, sin: 각각 [..., dim//2]
        """
        original_shape = positions.shape

        # 1차원으로 flatten
        positions_flat = positions.flatten().float()

        # [total_positions, dim//2]
        freqs = torch.outer(positions_flat, self.inv_freq)
        cos = torch.cos(freqs)
        sin = torch.sin(freqs)

        # 원래 shape으로 복원 + 마지막 차원 추가
        cos = cos.view(*original_shape, self.dim // 2)
        sin = sin.view(*original_shape, self.dim // 2)
        return cos, sin


def apply_rope(x: torch.Tensor, cos: torch.Tensor, sin: torch.Tensor) -> torch.Tensor:
    """RoPE 적용
    Args:
        x: [batch, seq, heads, dim]
        cos: [batch, seq, heads, dim//2]
        sin: [batch, seq, heads, dim//2]
    """
    *leading_dims, d = x.shape

    # x를 [batch, seq, heads, dim//2, 2]로 변형
    x = x.view(*leading_dims, d // 2, 2)

    # 회전 변환 적용
    x_rotated = torch.stack([
        x[..., 0] * cos - x[..., 1] * sin,  # 실수부
        x[..., 0] * sin + x[..., 1] * cos  # 허수부
    ], dim=-1)

    # 원래 형태로 복원
    return x_rotated.view(*leading_dims, d)


class MultiHeadAttention(nn.Module):
    """멀티헤드 어텐션 - 병렬 연산 최적화 버전"""

    def __init__(self, d_model: int, n_heads: int, use_rope: bool, timestamp_rope_dim: int, multiple_rope_factor: int,
                 dropout: float = 0.1):
        super().__init__()
        self.d_model = d_model
        self.n_heads = n_heads
        self.d_k = d_model // n_heads
        self.dropout = dropout
        self.use_rope = use_rope

        # 각 헤드별 RoPE 차원 계산
        self.timestamp_rope_dim_per_head = timestamp_rope_dim
        self.token_rope_dim_per_head = self.d_k - timestamp_rope_dim

        assert self.timestamp_rope_dim_per_head % 2 == 0, "timestamp_rope_dim은 2로 나누어떨어져야 합니다"
        assert self.token_rope_dim_per_head % 2 == 0, "token_rope_dim은 2로 나누어떨어져야 합니다"

        self.q_proj = nn.Linear(d_model, d_model, bias=False)
        self.k_proj = nn.Linear(d_model, d_model, bias=False)
        self.v_proj = nn.Linear(d_model, d_model, bias=False)
        self.out_proj = nn.Linear(d_model, d_model)

        self.resid_dropout = nn.Dropout(dropout)  # Output dropout

        # RoPE 모듈들 - 헤드별 차원으로 생성
        if self.use_rope:
            if self.token_rope_dim_per_head > 0:
                self.token_rope = StandardRoPE(self.token_rope_dim_per_head)
                if int(os.environ.get("RANK", 0)) == 0:
                    print(f'    RoPE Posi - dim {self.token_rope_dim_per_head}')
            if multiple_rope_factor:
                self.timestamp_rope = TSmultiRoPE(self.timestamp_rope_dim_per_head)
                if int(os.environ.get("RANK", 0)) == 0:
                    print(f'    RoPE Time - Multiple type of dim {self.timestamp_rope_dim_per_head}')
            else:
                self.timestamp_rope = TSmonoRoPE(self.timestamp_rope_dim_per_head)
                if int(os.environ.get("RANK", 0)) == 0:
                    print(f'    RoPE Time - Mono type of dim {self.timestamp_rope_dim_per_head}')

        # Causal mask pre gen
        self.register_buffer("causal_mask", torch.tril(torch.ones(4100, 4100)).bool())

    def forward(self, x: torch.Tensor, mask: Optional[torch.Tensor] = None,
                token_positions: Optional[torch.Tensor] = None,
                timestamps: Optional[torch.Tensor] = None) -> torch.Tensor:
        batch_size, seq_len, d_model = x.shape

        # Q, K, V 계산
        q = self.q_proj(x).view(batch_size, seq_len, self.n_heads, self.d_k)
        k = self.k_proj(x).view(batch_size, seq_len, self.n_heads, self.d_k)
        v = self.v_proj(x).view(batch_size, seq_len, self.n_heads, self.d_k)

        # RoPE 적용 - 병렬화
        if self.use_rope:
            if self.token_rope_dim_per_head != 0:
                # 토큰 위치 RoPE (각 헤드의 앞쪽 부분)
                token_cos, token_sin = self.token_rope(token_positions)  # [batch, seq, token_rope_dim_per_head//2]

                # 모든 헤드에 대해 동시에 RoPE 적용
                # token rope 차원만 추출
                q_token = q[:, :, :, :self.token_rope_dim_per_head]  # [batch, seq, heads, token_rope_dim]
                k_token = k[:, :, :, :self.token_rope_dim_per_head]

                # cos, sin을 헤드 차원으로 확장
                token_cos_expanded = token_cos.unsqueeze(2).expand(-1, -1, self.n_heads,
                                                                   -1)  # [batch, seq, heads, token_rope_dim//2]
                token_sin_expanded = token_sin.unsqueeze(2).expand(-1, -1, self.n_heads, -1)

                # 모든 헤드에 대해 병렬로 RoPE 적용
                q_token_rotated = apply_rope(q_token, token_cos_expanded, token_sin_expanded)
                k_token_rotated = apply_rope(k_token, token_cos_expanded, token_sin_expanded)

                # 결과를 다시 원래 텐서에 할당
                q[:, :, :, :self.token_rope_dim_per_head] = q_token_rotated
                k[:, :, :, :self.token_rope_dim_per_head] = k_token_rotated

            if self.timestamp_rope_dim_per_head != 0:
                # 타임스탬프 RoPE (각 헤드의 뒤쪽 부분)
                timestamp_cos, timestamp_sin = self.timestamp_rope(
                    timestamps)  # [batch, seq, timestamp_rope_dim_per_head//2]

                # 모든 헤드에 대해 동시에 RoPE 적용
                # timestamp rope 차원만 추출
                start_dim = self.d_k - self.timestamp_rope_dim_per_head
                q_timestamp = q[:, :, :, start_dim:]  # [batch, seq, heads, timestamp_rope_dim]
                k_timestamp = k[:, :, :, start_dim:]

                # cos, sin을 헤드 차원으로 확장
                timestamp_cos_expanded = timestamp_cos.unsqueeze(2).expand(-1, -1, self.n_heads,
                                                                           -1)  # [batch, seq, heads, timestamp_rope_dim//2]
                timestamp_sin_expanded = timestamp_sin.unsqueeze(2).expand(-1, -1, self.n_heads, -1)

                # 모든 헤드에 대해 병렬로 RoPE 적용
                q_timestamp_rotated = apply_rope(q_timestamp, timestamp_cos_expanded, timestamp_sin_expanded)
                k_timestamp_rotated = apply_rope(k_timestamp, timestamp_cos_expanded, timestamp_sin_expanded)

                # 결과를 다시 원래 텐서에 할당
                q[:, :, :, start_dim:] = q_timestamp_rotated
                k[:, :, :, start_dim:] = k_timestamp_rotated

        # 어텐션 계산
        q = q.transpose(1, 2)  # [batch, heads, seq, d_k]
        k = k.transpose(1, 2)
        v = v.transpose(1, 2)

        scores = torch.matmul(q, k.transpose(-2, -1)) / math.sqrt(self.d_k)

        # Causal masking 추가 (현재 토큰이 미래 토큰을 보지 못하게)
        causal_mask = self.causal_mask[:seq_len, :seq_len]
        causal_mask = causal_mask.unsqueeze(0).unsqueeze(0)  # [1, 1, seq, seq] boolean

        # 기존 mask와 causal mask 결합
        if mask is not None:
            # mask를 head 차원으로 확장
            if mask.dim() == 3:  # [batch, seq, seq]
                mask = mask.unsqueeze(1)  # [batch, 1, seq, seq]
            combined_mask = mask & causal_mask  # mask: False - not address / True - address
        else:
            combined_mask = causal_mask

        scores = scores.masked_fill(combined_mask == False, torch.finfo(scores.dtype).min)

        attn_weights = F.softmax(scores, dim=-1)

        out = torch.matmul(attn_weights, v)

        # 결과 변형
        out = out.transpose(1, 2).contiguous().view(batch_size, seq_len, d_model)

        # Output projection and residual dropout
        out = self.out_proj(out)
        out = self.resid_dropout(out)
        return out


class TransformerBlock(nn.Module):
    """트랜스포머 블록"""

    def __init__(self, d_model: int, n_heads: int, d_ff: int, use_rope: bool, timestamp_rope_dim: int,
                 multiple_rope_factor: int, dropout: float = 0.1):
        super().__init__()
        self.attention = MultiHeadAttention(d_model, n_heads, use_rope, timestamp_rope_dim, multiple_rope_factor,
                                            dropout)
        self.feed_forward = nn.Sequential(
            nn.Linear(d_model, d_ff),
            nn.ReLU(),
            nn.Dropout(dropout),  # Dropout after first linear layer
            nn.Linear(d_ff, d_model)
        )
        self.norm1 = nn.LayerNorm(d_model)
        self.norm2 = nn.LayerNorm(d_model)

        # Residual dropout for feed-forward
        self.resid_dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor, mask: Optional[torch.Tensor] = None,
                token_positions: Optional[torch.Tensor] = None,
                timestamps: Optional[torch.Tensor] = None) -> torch.Tensor:
        # 어텐션
        attn_out = self.attention(x, mask, token_positions, timestamps)
        x = self.norm1(x + attn_out)

        # 피드포워드 with residual connection and dropout
        ff_out = self.feed_forward(x)
        ff_out = self.resid_dropout(ff_out)
        x = self.norm2(x + ff_out)

        return x


class TimestampTransformer(nn.Module):
    """타임스탬프를 고려한 트랜스포머 모델"""

    def __init__(self, args):
        super().__init__()
        self.generation = False

        self.n_layers = args.model_num_layers
        self.d_model = args.model_hidden_dim
        self.n_heads = args.model_num_heads
        self.d_ff = args.model_d_ff
        self.timestamp_rope_dim = args.model_timestamp_rope_dim
        self.vocab_size = args.vocab_size
        self.dropout = args.model_dropout  # Default to 0.1 if not specified
        self.use_rope = args.use_rope
        self.multiple_rope_factor = args.multiple_rope_factor
        self.use_temperature_adj = args.use_temperature_adj if args.in_pretrain else False
        self.objective = args.objective
        # ETHOS is retained only as the generation-quality comparison baseline
        # (pe_baseline='ETHOS', use_rope=0); every other baseline has been removed.
        self.ethos = args.pe_baseline == 'ETHOS'
        self.NOadd = args.seq_gen == 'NOadd'

        # MIMIC-IV token-type layout
        self.meta_tokens = torch.tensor([0,1,2,3,4,5,6,7,8])
        self.downstream_token = 10
        self.bin_start_idx = 11

        # Check for generation
        self.in_pretrain = args.in_pretrain

        self.eval_ft_range = args.eval_ft_range

        if not args.in_pretrain:
            self.objective = 'NTP'

        # OURS (G2DYDTSP) predicts the next event's time via the time-addressing
        # module; NTP (ETHOS baseline / downstream eval) does not.
        self.use_time_label = self.objective == 'G2DYDTSP'
        self.use_2d_mask = True
        if self.use_time_label:
            self.time_addressing_module = timecondition_res_module_pos(self.d_model)
            if not self.NOadd:
                self.gen_labelset = gen_labelset_pos      # shared-token variant (OURS)
            else:
                self.gen_labelset = Xshare_gen_labelset_pos  # no-share variant (Xshare)

        self.pred_max_dist_hr = args.pred_max_dist_hr

        # Masking 확률: feature 전체 masking / 각 token group masking
        self.mask_feature_p = args.mask_feature_p
        self.mask_token_p = args.mask_token_p

        # separate tokenizer logit gen
        self.tokenizer_ranges = args.tokenizer_ranges
        self.num_token_types = max(self.tokenizer_ranges) + 1
        self.token_embedding = nn.Embedding(self.vocab_size, self.d_model)

        self.layers = nn.ModuleList([
            TransformerBlock(self.d_model, self.n_heads, self.d_ff, self.use_rope, self.timestamp_rope_dim,
                             self.multiple_rope_factor, self.dropout)
            for _ in range(self.n_layers)
        ])

        if self.use_temperature_adj:
            self.temperature_projection = nn.Linear(self.d_model, 2)

        if not self.use_rope:  # ETHOS: learned absolute position embedding instead of RoPE
            self.learnable_embedding = nn.Embedding(2050, self.d_model)  # a little more than max_length


        ## Output projection: weight-tied full projection over the token vocabulary
        ## for pretraining; multi-task downstream head for evaluation.
        if args.in_pretrain:
            self.output_projection = self.full_projection
        else:
            self.output_projection = dt_projection(self.d_model, )
            self.use_temperature_adj = False

    def D2_mask(self, token_types: torch.Tensor, q_group: torch.Tensor) -> torch.Tensor:
        """token_types 기반 random mask 생성 (bool 기반으로 최적화)"""
        '''
        0과 1이 아닌 각 token_types에 대해 0.1 의 확률로 그 종류의 token을 모두 mask 해줘. (0:meta / 1:downsteam-task)
        단 이 경우에는 mask하는 token type들에 대해 그 앞에 있는 token_types == 2 도 함께 mask를 해줘야 해.
        e.g. 0002332425552314 -> 3을 mask하면 000MMM141555MM14
        그리고 남아있는 0과 1이 아닌 token_types에 대해 p의 확률로 각각을 mask 해줘.
        '''
        """ MIMIC4에서 meta 및 question token이 변함 """

        batch_size, length = token_types.shape
        device = token_types.device

        # --------------------------
        # [Step 1] token type 기반 mask
        # --------------------------
        # 3~N까지 각 숫자마다 batch별로 mask 여부 결정
        random_mask_flags = (torch.rand(batch_size, self.num_token_types - self.bin_start_idx, device=device)
                             < self.mask_feature_p)  # bool

        # token_types와 3~N을 비교
        nums = torch.arange(self.bin_start_idx, self.num_token_types, device=device)
        matches = (token_types.unsqueeze(-1) == nums)  # (B, L, num_types-3), bool

        # mask 적용 (해당 값이 선택된 경우)
        masked_matches = matches & random_mask_flags.unsqueeze(1)  # (B, L, num_types-3), bool
        mask_2_n = masked_matches.any(dim=-1)  # (B, L), bool

        if not self.NOadd:
            # mask된 토큰 바로 앞의 token_types == 2 도 mask
            masked_roll_to_type2 = torch.roll(mask_2_n, -1, dims=1)  # (B, L), bool
        else:
            masked_roll_to_type2 = False

        # 최종 1차 mask (B, 1, L)
        mask = ((token_types == self.downstream_token) | masked_roll_to_type2 | mask_2_n).unsqueeze(1)

        # --------------------------
        # [Step 2] q_group 기반 mask
        # --------------------------
        max_val = q_group.max() + 1
        batch_offset = torch.arange(batch_size, device=device).view(-1, 1) * max_val
        group_combinations = batch_offset + q_group  # (B, L)

        unique_vals, inverse_indices = group_combinations.unique(return_inverse=True)
        mask_decisions = (torch.rand(len(unique_vals), device=device) < self.mask_token_p)  # (num_unique,), bool

        mask_rand = mask_decisions[inverse_indices].view_as(q_group)  # (B, L), bool
        mask_rand = (mask_rand & (~torch.isin(token_types, self.meta_tokens.to(device)))).unsqueeze(1)  # (B, 1, L)

        # --------------------------
        # [Step 3] 최종 mask
        # --------------------------
        mask = mask | mask_rand  # OR 결합, bool

        # group mask (include 자기 자신은 항상 볼 수 있게)
        group_diff = q_group.unsqueeze(1) - q_group.unsqueeze(2)

        # mask 합치기
        mask = mask & (group_diff != 0)

        return ~mask  # attend mask로 변환 (True: attend, False: masked)

    def full_projection(self, last_hidden, token_types):  # x: batch, length, hidden_dim

        embedding_weight = self.token_embedding.weight  # [vocab_size, hidden_dim]
        logits = torch.matmul(last_hidden, embedding_weight.T)

        return logits  # Batch, length, vocab_size

    def forward(self, input_tensor, targets, training: bool = False) -> torch.Tensor:
        if self.generation:
            return self.generate(input_tensor, targets, training)
        timestamps = input_tensor[..., 0]
        token_types = input_tensor[..., 1]
        token_ids = input_tensor[..., 2]
        q_group = input_tensor[..., 3]

        if self.eval_ft_range == 0:
            token_ids[token_ids == my_tokens('<DTask>')] = my_tokens('<birth>')

        device = input_tensor.device
        token_positions = torch.arange(token_ids.shape[1], device=device).unsqueeze(0)
        """
        Args:
            timestamps: [batch_size, seq_len] 타임스탬프
            token_types: [batch_size, seq_len] 토큰 타입 (0, 1, 2, ...)
            token_ids: [batch_size, seq_len] 토큰 ID
            token_positions: [batch_size, seq_len] 각 토큰의 상대적 position
            training: 학습 모드 여부
        """
        if self.use_time_label:
            time_next_in_sec, time_label_in_sec, label_token = self.gen_labelset(timestamps, token_types, targets, multi_label = 9, multi_label_threshold_sec = self.pred_max_dist_hr*3600)
        # 임베딩
        x = self.token_embedding(token_ids)

        if not self.use_rope:  # ETHOS
            x = x + self.learnable_embedding(token_positions)


        # 마스크 생성 (2D group mask; disabled when masking probabilities are ~0)
        if self.mask_feature_p < 0.01 and self.mask_token_p < 0.01:
            mask_last = None
            mask_all = None
        else:
            if self.NOadd:
                q_group = token_positions.expand(q_group.shape[0], -1)
            with torch.no_grad():
                mask = self.D2_mask(token_types, q_group)  # False(0) - not attend / True(1) - attend
                mask_last = mask
                mask_all = mask

        # 트랜스포머 레이어들
        for idx, layer in enumerate(self.layers):
            if idx == self.n_layers - 1:  # Last layer mask
                x = layer(x, mask_last, token_positions, timestamps)
            else:
                x = layer(x, mask_all, token_positions, timestamps)

        if self.use_time_label:
            loss_time, x = self.time_addressing_module(x, timestamps, time_next_in_sec, time_label_in_sec)

        # 출력 투영
        logits = self.output_projection(x, token_types)

        if self.use_temperature_adj:
            tmp = F.softmax(self.temperature_projection(x), dim=-1)
            temperature = torch.clamp(tmp[..., 0] / (tmp[..., 1] + 1e-6), min=0.01, max=10.0)
        else:
            temperature = torch.ones_like(x[...,0], dtype=x.dtype)

        if self.use_time_label:
            logits = (logits, label_token, loss_time)

        return logits, temperature

    def prepare_generation(self):
        assert self.in_pretrain == True
        self.generation = True
        if self.objective.endswith('TSP'):
            self.time_addressing_module.generation = True
        self.output_projection = dt_projection(self.d_model,)

    def generate(self, input_tensor, targets = None, training: bool = False) -> torch.Tensor:
        timestamps = input_tensor[..., 0]
        token_types = input_tensor[..., 1]
        token_ids = input_tensor[..., 2]

        token_ids[token_ids == my_tokens('<DTask>')] = my_tokens('<birth>')

        device = input_tensor.device
        token_positions = torch.arange(token_ids.shape[1], device=device).unsqueeze(0)
        """
        Args:
            timestamps: [batch_size, seq_len] 타임스탬프
            token_types: [batch_size, seq_len] 토큰 타입 (0, 1, 2, ...)
            token_ids: [batch_size, seq_len] 토큰 ID
            token_positions: [batch_size, seq_len] 각 토큰의 상대적 position
            training: 학습 모드 여부
        """
        # 임베딩
        x = self.token_embedding(token_ids)

        if self.ethos:
            x = x + self.learnable_embedding(token_positions)

        mask_last = None
        mask_all = None

        # 트랜스포머 레이어들
        for idx, layer in enumerate(self.layers):
            if idx == self.n_layers - 1:  # Last layer mask
                x = layer(x, mask_last, token_positions, timestamps)
            else:
                x = layer(x, mask_all, token_positions, timestamps)

        downstream_logits = self.output_projection(x, token_types) # Before time_addressing_module

        if self.use_time_label:
            interval_to_next_event, x = self.time_addressing_module(x, timestamps, None, None)
            x = x.squeeze(2)
        else:
            interval_to_next_event = None

        # 출력 투영
        embedding_weight = self.token_embedding.weight  # [vocab_size, hidden_dim]
        token_logit = torch.matmul(x, embedding_weight.T)

        if self.use_temperature_adj:
            tmp = F.softmax(self.temperature_projection(x), dim=-1)
            temperature = torch.clamp(tmp[..., 0] / (tmp[..., 1] + 1e-6), min=0.01, max=10.0)
        else:
            temperature = torch.ones_like(timestamps, dtype=x.dtype)

        temperature = temperature.unsqueeze(-1)
        token_logit = token_logit / temperature

        return token_logit, downstream_logits, interval_to_next_event
