import torch
import torch.nn as nn

class time_prediction_loss(nn.Module):
    def __init__(self, is_simple, lamba_timeloss = 1.0):
        super().__init__()
        self.lamba_timeloss = lamba_timeloss

        self.criterion = nn.CrossEntropyLoss()

        self.time_loss = None
        self.token_loss = None

        self.is_simple = is_simple

    def forward(self, outputs, temperature, targets):
        logits, label_token, loss_time = outputs

        # simple mode에서 logit과 label 차원 추가로 맞춰야 함

        temperature = temperature.unsqueeze(-1)
        scaled_logits = logits / temperature

        if self.is_simple:
            #scaled_logits = scaled_logits.expand(-1, -1, 12, -1)
            scaled_logits = scaled_logits.reshape(-1, logits.size(-1))

        else:
            scaled_logits = scaled_logits.view(-1, logits.size(-1))
        label_token = label_token.view(-1)

        loss = self.criterion(scaled_logits, label_token)

        self.time_loss = loss_time.item()
        self.token_loss = loss.item()

        return loss+self.lamba_timeloss*loss_time