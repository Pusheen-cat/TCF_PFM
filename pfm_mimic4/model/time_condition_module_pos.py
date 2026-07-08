import torch
import torch.nn as nn

def make_B_loop(A: torch.Tensor):
    B = torch.zeros_like(A)
    for i in range(1, A.size(-1)):
        same = A[..., i] == A[..., i-1]
        B[..., i] = torch.where(same, B[..., i-1] + 1, 0)
    return B

class timecondition_res_module_pos(nn.Module):
    def __init__(self, input_dim):
        super().__init__()
        self.generation = False
        self.temperature = None
        embed_dim = 32
        self.embed_dim = embed_dim

        self.minute1 = nn.Embedding(10, embed_dim)
        self.minute10 = nn.Embedding(6, embed_dim)
        self.hour1 = nn.Embedding(6, embed_dim)
        self.hour6 = nn.Embedding(4, embed_dim)
        self.day1 = nn.Embedding(7, embed_dim)
        self.week1 = nn.Embedding(5, embed_dim)
        self.month1 = nn.Embedding(3, embed_dim)
        self.month3 = nn.Embedding(4, embed_dim)
        self.year1 = nn.Embedding(10, embed_dim)
        self.year10 = nn.Embedding(10, embed_dim)

        self.pos = nn.Embedding(11, embed_dim)

        self.ff_enc1 = nn.Linear(input_dim, embed_dim*11*4)
        self.ff_enc2 = nn.Linear(embed_dim*11*4, embed_dim*11)

        self.ff_dec1 = nn.Linear(embed_dim*11, embed_dim*11*4)
        self.ff_dec2 = nn.Linear(embed_dim*11*4, input_dim)

        self.activation = nn.GELU()

        self.cycles = {  # 20
            'minute1': 60,  # 1분
            'minute10': 600,  # 10분
            'hour1': 3600,  # 1시간
            'hour6': 21600,  # 6시간
            'day1': 86400,  # 1일
            'week1': 604800,  # 1주일
            'month1': 2678400,  # 31day
            'month3': 7948800,  # 92day
            'year1': 31536000,  # 365day
            'year10': 315360000,  # 3650day
        }

        self.loss_fn = nn.CrossEntropyLoss()

        self.final_ff_enc = nn.Linear(input_dim, 4*input_dim)
        self.final_ff_dec = nn.Linear(4*input_dim, input_dim)

        self.norm1 = nn.LayerNorm(input_dim)
        self.norm2 = nn.LayerNorm(input_dim)

    def forward(self, input, input_time_in_sec, time_next_in_sec = None, time_label_in_sec = None):
        if self.generation:
            return self.generate(input, input_time_in_sec, time_next_in_sec, time_label_in_sec)
        """
        :param input: suppose [batch_size, seq_len, input_dim]
        :param time_next_token: time delta on sec for the very next token
        :param time_label_token: time delta on sec for the label token (0-24hr future prediction objective)
        :return: output with residual connection to input, next time prediction loss
        """
        feat = self.ff_enc2(self.activation(self.ff_enc1(input)))
        batch, length = input_time_in_sec.shape

        logits_minute1 = torch.matmul(feat[...,:self.embed_dim], self.minute1.weight.T)
        logits_minute10 = torch.matmul(feat[..., self.embed_dim:self.embed_dim*2], self.minute10.weight.T)
        logits_hour1 = torch.matmul(feat[..., self.embed_dim*2:self.embed_dim*3], self.hour1.weight.T)
        logits_hour6 = torch.matmul(feat[..., self.embed_dim * 3:self.embed_dim * 4], self.hour6.weight.T)
        logits_day1 = torch.matmul(feat[..., self.embed_dim * 4:self.embed_dim * 5], self.day1.weight.T)
        logits_week1 = torch.matmul(feat[..., self.embed_dim * 5:self.embed_dim * 6], self.week1.weight.T)
        logits_month1 = torch.matmul(feat[..., self.embed_dim * 6:self.embed_dim * 7], self.month1.weight.T)
        logits_month3 = torch.matmul(feat[..., self.embed_dim * 7:self.embed_dim * 8], self.month3.weight.T)
        logits_year1 = torch.matmul(feat[..., self.embed_dim * 8:self.embed_dim * 9], self.year1.weight.T)
        logits_year10 = torch.matmul(feat[..., self.embed_dim * 9:self.embed_dim * 10], self.year10.weight.T) #batch, length, dim

        logits_pos = torch.matmul(feat[..., self.embed_dim * 10:self.embed_dim * 11], self.pos.weight.T)

        # --- 벡터화된 연산 시작 ---
        mask = time_next_in_sec == 0
        next_diff_seconds = time_next_in_sec.long() - input_time_in_sec.long() #batch, length
        next_year10 = next_diff_seconds // self.cycles['year10']
        next_year10 = torch.clamp(next_year10, min=0, max=9)
        remainder = next_diff_seconds % self.cycles['year10']

        next_year1 = remainder // self.cycles['year1']
        remainder = remainder % self.cycles['year1']

        next_month3 = remainder // self.cycles['month3']
        remainder = remainder % self.cycles['month3']

        next_month1 = remainder // self.cycles['month1']
        remainder = remainder % self.cycles['month1']

        next_week1 = remainder // self.cycles['week1']
        remainder = remainder % self.cycles['week1']

        next_day1 = remainder // self.cycles['day1']
        remainder = remainder % self.cycles['day1']

        next_hour6 = remainder // self.cycles['hour6']
        remainder = remainder % self.cycles['hour6']

        next_hour1 = remainder // self.cycles['hour1']
        remainder = remainder % self.cycles['hour1']

        next_minute10 = remainder // self.cycles['minute10']
        remainder = remainder % self.cycles['minute10']

        next_minute1 = remainder // self.cycles['minute1']

        next_minute1[mask] = -100
        next_minute10[mask] = -100
        next_hour1[mask] = -100
        next_hour6[mask] = -100
        next_day1[mask] = -100
        next_week1[mask] = -100
        next_month1[mask] = -100
        next_month3[mask] = -100
        next_year1[mask] = -100
        next_year10[mask] = -100

        next_pos = torch.zeros_like(next_minute1)
        next_pos[mask] = -100

        loss_next = 1/11*(self.loss_fn(logits_minute1.view(batch*length, -1), next_minute1.view(-1))+
                          self.loss_fn(logits_minute10.view(batch*length, -1), next_minute10.view(-1))+
                          self.loss_fn(logits_hour1.view(batch*length, -1), next_hour1.view(-1))+
                          self.loss_fn(logits_hour6.view(batch*length, -1), next_hour6.view(-1))+
                          self.loss_fn(logits_day1.view(batch*length, -1), next_day1.view(-1))+
                          self.loss_fn(logits_week1.view(batch*length, -1), next_week1.view(-1))+
                          self.loss_fn(logits_month1.view(batch*length, -1), next_month1.view(-1))+
                          self.loss_fn(logits_month3.view(batch*length, -1), next_month3.view(-1))+
                          self.loss_fn(logits_year1.view(batch*length, -1), next_year1.view(-1))+
                          self.loss_fn(logits_year10.view(batch*length, -1), next_year10.view(-1))

                          +self.loss_fn(logits_pos.view(batch*length, -1), next_pos.view(-1)))

        # --- 벡터화된 연산 시작 ---
        if len(time_label_in_sec.shape) == 2:
            lable_diff_seconds = time_label_in_sec.long() - input_time_in_sec.long()  # batch, length
            raise "Remove before use"
        elif len(time_label_in_sec.shape) == 3:
            lable_diff_seconds = time_label_in_sec.long() - input_time_in_sec[:,:,None].long()  # batch, length, multiple_label
            input = input[:,:,None] #[batch_size, seq_len, input_dim] --> [batch_size, seq_len, 1, input_dim]

        label_year10 = lable_diff_seconds // self.cycles['year10']
        label_year10 = torch.clamp(label_year10, min=0, max=9)
        remainder = lable_diff_seconds % self.cycles['year10']

        label_year1 = remainder // self.cycles['year1']
        remainder = remainder % self.cycles['year1']

        label_month3 = remainder // self.cycles['month3']
        remainder = remainder % self.cycles['month3']

        label_month1 = remainder // self.cycles['month1']
        remainder = remainder % self.cycles['month1']

        label_week1 = remainder // self.cycles['week1']
        remainder = remainder % self.cycles['week1']

        label_day1 = remainder // self.cycles['day1']
        remainder = remainder % self.cycles['day1']

        label_hour6 = remainder // self.cycles['hour6']
        remainder = remainder % self.cycles['hour6']

        label_hour1 = remainder // self.cycles['hour1']
        remainder = remainder % self.cycles['hour1']

        label_minute10 = remainder // self.cycles['minute10']
        remainder = remainder % self.cycles['minute10']

        label_minute1 = remainder // self.cycles['minute1']

        dec_feat = torch.cat((self.minute1(label_minute1), self.minute10(label_minute10), self.hour1(label_hour1), self.hour6(label_hour6), self.day1(label_day1),
                   self.week1(label_week1), self.month1(label_month1), self.month3(label_month3), self.year1(label_year1), self.year10(label_year10), self.pos(make_B_loop(lable_diff_seconds))), dim=-1)

        dec_feat = self.ff_dec2(self.activation(self.ff_dec1(dec_feat)))

        input = self.norm1(dec_feat+input)

        dec_feat = self.final_ff_dec(self.activation(self.final_ff_enc(input)))

        input = self.norm2(input + dec_feat)

        return loss_next, input
    # dec_feat : [batch_size, seq_len, input_dim] or [batch_size, seq_len, multiple_label, input_dim]

    def generate(self, input, input_time_in_sec, time_next_in_sec=None, time_label_in_sec=None):
        """
        :param input: suppose [batch_size, seq_len, input_dim]
        :param time_next_token: time delta on sec for the very next token
        :param time_label_token: time delta on sec for the label token (0-24hr future prediction objective)
        :return: output with residual connection to input, next time prediction loss
        """
        feat = self.ff_enc2(self.activation(self.ff_enc1(input)))
        batch, length = input_time_in_sec.shape

        logits_minute1 = torch.matmul(feat[..., :self.embed_dim], self.minute1.weight.T)
        logits_minute10 = torch.matmul(feat[..., self.embed_dim:self.embed_dim * 2], self.minute10.weight.T)
        logits_hour1 = torch.matmul(feat[..., self.embed_dim * 2:self.embed_dim * 3], self.hour1.weight.T)
        logits_hour6 = torch.matmul(feat[..., self.embed_dim * 3:self.embed_dim * 4], self.hour6.weight.T)
        logits_day1 = torch.matmul(feat[..., self.embed_dim * 4:self.embed_dim * 5], self.day1.weight.T)
        logits_week1 = torch.matmul(feat[..., self.embed_dim * 5:self.embed_dim * 6], self.week1.weight.T)
        logits_month1 = torch.matmul(feat[..., self.embed_dim * 6:self.embed_dim * 7], self.month1.weight.T)
        logits_month3 = torch.matmul(feat[..., self.embed_dim * 7:self.embed_dim * 8], self.month3.weight.T)
        logits_year1 = torch.matmul(feat[..., self.embed_dim * 8:self.embed_dim * 9], self.year1.weight.T)
        logits_year10 = torch.matmul(feat[..., self.embed_dim * 9:self.embed_dim * 10], self.year10.weight.T)  # batch, length, dim

        label_minute1 = self.sample_from_logits(logits_minute1)
        label_minute10 = self.sample_from_logits(logits_minute10)
        label_hour1 = self.sample_from_logits(logits_hour1)
        label_hour6 = self.sample_from_logits(logits_hour6)
        label_day1 = self.sample_from_logits(logits_day1)
        label_week1 = self.sample_from_logits(logits_week1)
        label_month1 = self.sample_from_logits(logits_month1)
        label_month3 = self.sample_from_logits(logits_month3)
        label_year1 = self.sample_from_logits(logits_year1)
        label_year10 = self.sample_from_logits(logits_year10)

        next_token_sec = (label_minute1*self.cycles['minute1']+
                          label_minute10*self.cycles['minute10']+
                          label_hour1*self.cycles['hour1']+
                          label_hour6*self.cycles['hour6']+
                          label_day1*self.cycles['day1']+
                          label_week1*self.cycles['week1']+
                          label_month1*self.cycles['month1']+
                          label_month3*self.cycles['month3']+
                          label_year1*self.cycles['year1']+
                          label_year10*self.cycles['year10'])

        dec_feat = torch.cat((self.minute1(label_minute1[:, :, None]), self.minute10(label_minute10[:, :, None]), self.hour1(label_hour1[:, :, None]),
                              self.hour6(label_hour6[:, :, None]), self.day1(label_day1[:, :, None]),
                              self.week1(label_week1[:, :, None]), self.month1(label_month1[:, :, None]), self.month3(label_month3[:, :, None]),
                              self.year1(label_year1[:, :, None]), self.year10(label_year10[:, :, None]),
                              self.pos(torch.zeros_like(label_minute1[:, :, None]))), dim=-1)

        dec_feat = self.ff_dec2(self.activation(self.ff_dec1(dec_feat)))

        input = input[:, :, None]

        input = self.norm1(dec_feat + input)

        dec_feat = self.final_ff_dec(self.activation(self.final_ff_enc(input)))

        input = self.norm2(input + dec_feat)

        return next_token_sec, input

    def sample_from_logits(self, logits, temperature=0.2):
        """다차원 logits 텐서에서 temperature 조절 softmax 샘플링 수행."""
        if self.temperature is not None:
            temperature = self.temperature
            if self.temperature ==0:
                return self.greedy_from_logits(logits)
        if temperature <= 0:
            raise ValueError("Temperature must be positive.")

        # 1. Temperature 적용
        logits = logits / temperature

        # 2. Softmax로 확률 분포 생성
        probs = torch.softmax(logits, dim=-1)

        # 3. 마지막 차원 크기
        num_classes = probs.shape[-1]

        # 4. 2D로 변환
        probs_reshaped = probs.view(-1, num_classes)

        # 5. 샘플링
        samples = torch.multinomial(probs_reshaped, num_samples=1)

        # 6. 원래 형태로 복원
        original_shape_without_last_dim = logits.shape[:-1]
        labels = samples.view(original_shape_without_last_dim)

        return labels

    def greedy_from_logits(self, logits):
        """다차원 logits 텐서에서 greedy (argmax) 선택."""
        labels = torch.argmax(logits, dim=-1)
        return labels

def shift_masked_labels_vec(label, mask, N, pad_value=-100):
    """
    label: [B, L]
    mask : [B, L] (0/1 or bool) - mask:1=used label
    N    : 최대 shift 크기
    pad_value: 빈 칸 채울 값 (-100)

    return: [B, L, N]
    """
    B, L = label.shape
    device = label.device

    # mask==1인 값들을 앞으로 모으기 위한 정렬 인덱스
    sort_idx = torch.argsort(mask.to(torch.int8), dim=1, descending=True)
    batch_idx = torch.arange(B, device=device).unsqueeze(1).expand(B, L)

    # mask 값 앞으로 모은 label
    sorted_labels = label[batch_idx, sort_idx]

    # batch별 mask 개수
    counts = mask.sum(dim=1)  # [B]

    # 위치 인덱스
    arange_idx = torch.arange(L, device=device).unsqueeze(0).expand(B, L)  # [B, L]

    # shift 크기 (1~N)
    shifts = torch.arange(1, N + 1, device=device).view(1, 1, N)  # [1, 1, N]

    # shift 인덱스 계산
    shift_idx = arange_idx.unsqueeze(-1) + shifts  # [B, L, N]

    # counts 비교 (broadcast)
    valid = shift_idx < counts.view(B, 1, 1)  # [B, L, N]

    # gather용 batch/l pos 확장
    batch_idx_exp = batch_idx.unsqueeze(-1).expand(B, L, N)

    # shift 값 가져오기
    shifted_vals = torch.full((B, L, N), pad_value, device=device, dtype=label.dtype)
    shifted_vals[valid] = sorted_labels[batch_idx_exp[valid], shift_idx[valid]]

    # --- 수정된 부분 ---
    # 다시 inverse permutation
    # torch.gather를 사용하여 L 차원(dim=1)을 기준으로 역정렬합니다.
    inv_sort_idx = torch.argsort(sort_idx, dim=1)

    # gather에 사용할 수 있도록 inv_sort_idx를 [B, L, N]으로 확장합니다.
    unscramble_idx = inv_sort_idx.unsqueeze(-1).expand(B, L, N)

    final_labels = torch.gather(shifted_vals, 1, unscramble_idx)

    return final_labels

def gen_labelset_pos(timestamps, token_types, label, multi_label = 10, multi_label_threshold_sec = 24*3600):
    # MIMIC-IV token-type layout
    meta_tokens = torch.tensor([0, 1, 2, 3, 4, 5, 6, 7, 8], device=token_types.device)
    question_token = 9
    """
    :param timestamps: [batch, length] int second in time-stamp (0 for padding)
    :param token_types: [batch, length] (0 for padding)
    :param label: [batch, length] (-100 for padding)
    :param q_group:
    :param multi_label: # Additionsl label num added to next label ## if multi_label is 0, only the next label is used

    :return: time_next_in_sec, time_label_in_sec, label_token
        time_next_in_sec: [batch, length]
        time_label_in_sec: [batch, length] or [batch, length, multi-label]
        label_token: [batch, length] or [batch, length, multi-label]
    """
    time_next_in_sec = torch.zeros_like(timestamps)
    time_next_in_sec[:, :-1] = timestamps[:,1:]

    mask_nexttoken_type_02 = torch.zeros_like(token_types)
    mask_nexttoken_type_02[:, :-1] = ((torch.isin(token_types, meta_tokens)) | (token_types == question_token)).long()[:, 1:] #여러 예측이 이루어져야 하는 위치를 표시하는 bool mask

    if (multi_label == 0) or (multi_label_threshold_sec <1):
        return time_next_in_sec, time_next_in_sec[:,:, None], label[:,:, None]

    else:
        label_mask = torch.where(mask_nexttoken_type_02 == 1, label, torch.full_like(label, -100))
        label_time_mask = torch.where(mask_nexttoken_type_02 == 1, time_next_in_sec, torch.full_like(label, 0))

        multiple_labels = shift_masked_labels_vec(label_mask, mask_nexttoken_type_02, N = multi_label, pad_value = -100)
        multiple_times = shift_masked_labels_vec(label_time_mask, mask_nexttoken_type_02, N=multi_label, pad_value=0)

        time_24hr_mask = multiple_times - timestamps[:,:,None] > multi_label_threshold_sec

        multiple_times = multiple_times.masked_fill(time_24hr_mask, 0)
        multiple_labels = multiple_labels.masked_fill(time_24hr_mask, -100)

        return time_next_in_sec, torch.cat((time_next_in_sec[:, :, None], multiple_times), dim=-1), torch.cat((label[:, :, None], multiple_labels), dim=-1)
