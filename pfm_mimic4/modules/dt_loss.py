import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.distributed as dist
import numpy as np
from sklearn.metrics import roc_auc_score, average_precision_score
from sklearn.metrics import (
    accuracy_score, f1_score, precision_score, recall_score,
    log_loss, cohen_kappa_score, confusion_matrix
)


def gather_tensors_from_all_gpus(tensor):
    """
    모든 GPU에서 텐서를 수집하여 하나로 합치는 함수
    """
    if not dist.is_initialized():
        return tensor

    # 현재 GPU의 텐서 크기를 모든 GPU에 브로드캐스트
    local_size = torch.tensor([tensor.size(0)], device=tensor.device)
    size_list = [torch.zeros_like(local_size) for _ in range(dist.get_world_size())]
    dist.all_gather(size_list, local_size)

    # 최대 크기 계산
    max_size = max([size.item() for size in size_list])

    # 텐서를 최대 크기로 패딩 (크기가 다를 수 있으므로)
    if tensor.size(0) < max_size:
        padding_size = max_size - tensor.size(0)
        if len(tensor.shape) == 1:
            padding = torch.zeros(padding_size, device=tensor.device, dtype=tensor.dtype)
        else:
            padding_shape = [padding_size] + list(tensor.shape[1:])
            padding = torch.zeros(padding_shape, device=tensor.device, dtype=tensor.dtype)
        tensor = torch.cat([tensor, padding], dim=0)

    # 모든 GPU에서 텐서 수집
    gathered_list = [torch.zeros_like(tensor) for _ in range(dist.get_world_size())]
    dist.all_gather(gathered_list, tensor)

    # 실제 데이터만 추출 (패딩 제거)
    valid_tensors = []
    for i, gathered_tensor in enumerate(gathered_list):
        valid_size = size_list[i].item()
        valid_tensors.append(gathered_tensor[:valid_size])

    # 모든 텐서를 하나로 합치기
    return torch.cat(valid_tensors, dim=0)

class dt_ce_loss(nn.Module):
    def __init__(self, weight=None, eval_dataset = 'M4'):
        """
        Args:
            weight (Tensor, optional): 클래스별 가중치 텐서 of shape (num_classes,)
            reduction (str): 'mean', 'sum', or 'none'
        """
        super().__init__()
        self.register_buffer('weight_ihm', torch.tensor([0.5178382918828109, 14.514794782055361]))
        self.register_buffer('weight_dd', torch.tensor([0.5023869328916404, 105.23692028609533]))
        if not eval_dataset == 'M4':
            print("#### Not trained on M4. So Label balancing weight changed")
            self.register_buffer('weight_ihm', torch.tensor([0.5639247, 4.4108508]))
            self.register_buffer('weight_dd', torch.tensor([0.5345866, 7.728224]))

        self.register_buffer('weight_da', torch.tensor([0.5025705018411096, 97.75727326928501]))

        self.register_buffer('weight_icuin', torch.tensor([0.5132831319282652, 19.320862530772917]))
        # prognosis
        self.register_buffer('weight_los1', torch.tensor([0.6484568313110336,  0.7670747314830417,  0.9459846908343483,
                                                          1.1874207230792382,  1.4931835309745807,  1.8609059628429234,
                                                          2.287687078268447,  2.7843768510162317,  0.7694650469311431,  0.5122935323243464]))
        self.register_buffer('weight_los2', torch.tensor([0.8490348594817486,  0.9119096971218982,  1.001523600066051,
                                                          1.1284091759359187,  1.348182230386926,  1.6214524063901774,
                                                          1.9364063210326683,  2.3037969004388823,  0.6217411086197464,  0.5198676280280509]))

        # phenotype
        self.register_buffer('weight_vaso', torch.tensor([0.536896739715897, 7.27566641185609]))
        # huo

        self.criterion_ihm = nn.CrossEntropyLoss(weight=self.weight_ihm)
        self.criterion_dd = nn.CrossEntropyLoss(weight=self.weight_dd)
        self.criterion_da = nn.CrossEntropyLoss(weight=self.weight_da)

        self.criterion_icuin = nn.CrossEntropyLoss(weight=self.weight_icuin)
        self.criterion_alos = nn.CrossEntropyLoss(weight=self.weight_los1)
        self.criterion_ilos = nn.CrossEntropyLoss(weight=self.weight_los2)

        self.criterion_vaso = nn.CrossEntropyLoss(weight=self.weight_vaso)

        self.criterion_prog = MultiFeatureWeightedSoftmaxLoss([{0: 0.6392634967590377, 1: 2.2951581413510347},
                                                              {0: 0.751178928804202, 1: 1.495306418377471},
                                                               {0: 0.9497231677366539, 1: 1.0558975341612675},
                                                               {0: 0.516067007322341, 1: 16.05983606557377},
                                                               {0: 0.5373605075665694, 1: 7.191557911908646},
                                                               {0: 0.5915165542920399, 1: 3.2317462062898614}])

        self.criterion_phe = MultiFeatureWeightedSoftmaxLoss([{0: 0.6133048323630875, 1: 2.7064372258975693},
                                                              {0: 0.5194647514367078, 1: 13.343729385032617},
                                                              {0: 0.5222754240205641, 1: 11.723130916350055},
                                                              {0: 0.6619512177384753, 1: 2.0436747157017927},
                                                              {0: 0.6150058612686691, 1: 2.6738022500954677},
                                                              {0: 0.5543802644481123, 1: 5.097256054878902},
                                                              {0: 0.570334528001604, 1: 4.054441994610365},
                                                              {0: 0.5422273650600758, 1: 6.42033151119732},
                                                              {0: 0.6169650694239691, 1: 2.6373902587430824},
                                                              {0: 0.6260458542389551, 1: 2.4834051782937276},
                                                              {0: 0.5744123307985991, 1: 3.8596582356308438},
                                                              {0: 0.597538599900218, 1: 3.063087846819107},
                                                              {0: 0.803717749483462, 1: 1.3231326632216238},
                                                              {0: 0.8078442074807745, 1: 1.3120990875412624},
                                                              {0: 0.6746384975133966, 1: 1.9315285779461226},
                                                              {0: 0.5212167454963983, 1: 12.283145536738411},
                                                              {0: 0.6293224141566733, 1: 2.433152900294039},
                                                              {0: 0.5672459134900011, 1: 4.217698028403957},
                                                              {0: 0.5444864497874975, 1: 6.119688718569315},
                                                              {0: 0.5169849631533361, 1: 15.218901521484701},
                                                              {0: 0.5302156995235155, 1: 8.773844522627597},
                                                              {0: 0.5399052748334747, 1: 6.764835940693397},
                                                              {0: 0.5554763924402106, 1: 5.006421362373842},
                                                              {0: 0.5421417829330395, 1: 6.432354603914917},
                                                              {0: 0.5163353924521666, 1: 15.804193072315305},])

        self.criterion_huo = MultiFeatureWeightedSoftmaxLoss([{0: 0.7691870271221769, 1: 1.4287223187264948},
                                                              {0: 0.6390665648003635, 1: 2.2977002621650047}])



        self.task_dict = {
            0:'IHM',
            1:'Dec_death',
            2:'Dec_arrest',

            3:'Icu_in',
            4:'Prog', #
            5:'Los_adm',
            6:'Los_icu',

            7:'Phe', #
            8:'Vaso',
            9:'Huo' #
        }

    def forward(self, outputs, temperature, targets, loss_idx = None):
        '''
        :param outputs: Batch, length, classes, features  (ihm_out, phe_out, dec_death_out, dec_arrest_out, los_out, huo_out, vaso_out)
        :param temperature: Not used
        :param targets: Batch, length, 32 (all features)
        :return:
        '''
        #self.get_criterion()
        batch,length,_ = targets.shape
        targets = targets.long()
        # print('outputs',outputs[0].shape)
        # print('targets', targets.shape)
        loss = 0
        target_ihm = targets[:, :, :1].flatten(0, 1)
        target_dec_death = targets[:, :, 1:2].flatten(0, 1)
        target_dec_arrest = targets[:, :, 2:3].flatten(0, 1)

        target_icu_in = targets[:, :, 3:4].flatten(0, 1)
        target_prognosis = targets[:, :, 4:10].flatten(0, 1)
        target_los1 = targets[:, :, 10:11].flatten(0, 1)
        target_los2 = targets[:, :, 11:12].flatten(0, 1)

        target_phe = targets[:, :, 12:37].flatten(0, 1)
        target_vaso = targets[:, :, 37:38].flatten(0, 1)
        target_huo = targets[:, :, 38:40].flatten(0, 1)


        outputs_0 = outputs[0].flatten(0, 1)
        outputs_1 = outputs[1].flatten(0, 1)
        outputs_2 = outputs[2].flatten(0, 1)
        outputs_3 = outputs[3].flatten(0, 1)
        outputs_4 = outputs[4].flatten(0, 1)
        outputs_5 = outputs[5].flatten(0, 1)
        outputs_6 = outputs[6].flatten(0, 1)
        outputs_7 = outputs[7].flatten(0, 1)
        outputs_8 = outputs[8].flatten(0, 1)
        outputs_9 = outputs[9].flatten(0, 1)

        # print('0',outputs_0.shape) #torch.Size([45078, 2, 1])
        # print('1', outputs_1.shape) #torch.Size([45078, 2, 25])
        # print('2', outputs_2.shape) #torch.Size([45078, 2, 1])
        # print('3', outputs_3.shape) #torch.Size([45078, 2, 1])



        #0
        if (target_ihm != -100).sum() == 0: # nn.CrossEntropyLoss 인 경우 이 조건문 필요
            loss_ihm = (outputs_0.sum()) * 0.0
        else:
            loss_ihm = self.criterion_ihm(outputs_0, target_ihm)
        if loss_idx is None:
            loss += loss_ihm
        else:
            raise "Remove before use"
            loss += loss_ihm if loss_idx == 0 else loss_ihm*0.0
        #1
        if (target_dec_death != -100).sum() == 0:
            loss_dd = (outputs_1.sum()) * 0.0
        else:
            loss_dd = self.criterion_dd(outputs_1, target_dec_death)
        if loss_idx is None:
            loss += loss_dd
        else:
            raise "Remove before use"
            loss += loss_dd if loss_idx == 1 else loss_dd*0.0
        #2
        if (target_dec_arrest != -100).sum() == 0:
            loss_da = (outputs_2.sum()) * 0.0
        else:
            loss_da = self.criterion_da(outputs_2, target_dec_arrest)
        if loss_idx is None:
            loss += loss_da
        else:
            raise "Remove before use"
            loss += loss_da if loss_idx == 2 else loss_da*0.0
        #3
        if (target_icu_in != -100).sum() == 0:
            loss_icuin = (outputs_3.sum()) * 0.0
        else:
            loss_icuin = self.criterion_da(outputs_3, target_icu_in)
        if loss_idx is None:
            loss += loss_icuin
        else:
            raise "Remove before use"
            loss += loss_icuin if loss_idx == 3 else loss_icuin * 0.0
        #4
        loss_prog = self.criterion_prog(outputs_4, target_prognosis)
        if loss_idx is None:
            loss += loss_prog
        else:
            raise "Remove before use"
            loss += loss_prog if loss_idx == 4 else loss_prog * 0.0
        #5
        if (target_los1 != -100).sum() == 0:
            loss_los1 = (outputs_5.sum()) * 0.0
        else:
            loss_los1 = self.criterion_alos(outputs_5, target_los1)
        if loss_idx is None:
            loss += loss_los1
        else:
            raise "Remove before use"
            loss += loss_los1 if loss_idx == 5 else loss_los1*0.0
        #6
        if (target_los2 != -100).sum() == 0:
            loss_los2 = (outputs_6.sum()) * 0.0
        else:
            loss_los2 = self.criterion_ilos(outputs_6, target_los2)
        if loss_idx is None:
            loss += loss_los2
        else:
            raise "Remove before use"
            loss += loss_los2 if loss_idx == 6 else loss_los2 * 0.0

        #7
        loss_phe = self.criterion_phe(outputs_7, target_phe)
        if loss_idx is None:
            loss += loss_phe
        else:
            raise "Remove before use"
            loss += loss_phe if loss_idx == 7 else loss_phe*0.0
        #8
        if (target_vaso != -100).sum() == 0:
            loss_vaso = (outputs_8.sum()) * 0.0
        else:
            loss_vaso = self.criterion_vaso(outputs_8, target_vaso)
        if loss_idx is None:
            loss += loss_vaso
        else:
            raise "Remove before use"
            loss += loss_vaso if loss_idx == 8 else loss_vaso*0.0
        #9
        loss_huo = self.criterion_huo(outputs_9, target_huo)
        if loss_idx is None:
            loss += loss_huo
        else:
            raise "Remove before use"
            loss += loss_huo if loss_idx == 9 else loss_huo*0.0


        if not self.train_phase:
            idx = 0
            # 2. target에서 모든 feature가 -100인 row mask 만들기
            valid_mask = ~(target_ihm == -100).all(dim=1)  # [B*L], True if not all -100
            # 3. target과 logit 모두 해당 마스크로 필터링
            target_filtered = target_ihm[valid_mask][:,0]  # [N, F]
            logit_filtered = outputs_0[valid_mask]  # [N, C, F]
            logit_softmax = F.softmax(logit_filtered, dim=1)[:,1,0]
            self.logit_list[idx].append(logit_softmax)
            self.label_list[idx].append(target_filtered)

            idx = 1
            # 2. target에서 모든 feature가 -100인 row mask 만들기
            valid_mask = ~(target_dec_death == -100).all(dim=1)  # [B*L], True if not all -100
            # 3. target과 logit 모두 해당 마스크로 필터링
            target_filtered = target_dec_death[valid_mask][:,0]  # [N, F]
            logit_filtered = outputs_1[valid_mask]  # [N, C, F]
            logit_softmax = F.softmax(logit_filtered, dim=1)[:,1,0]
            self.logit_list[idx].append(logit_softmax)
            self.label_list[idx].append(target_filtered)

            idx = 2
            # 2. target에서 모든 feature가 -100인 row mask 만들기
            valid_mask = ~(target_dec_arrest == -100).all(dim=1)  # [B*L], True if not all -100
            # 3. target과 logit 모두 해당 마스크로 필터링
            target_filtered = target_dec_arrest[valid_mask][:,0]  # [N, F]
            logit_filtered = outputs_2[valid_mask]  # [N, C, F]
            logit_softmax = F.softmax(logit_filtered, dim=1)[:,1,0]
            self.logit_list[idx].append(logit_softmax)
            self.label_list[idx].append(target_filtered)

            idx = 3
            # 2. target에서 모든 feature가 -100인 row mask 만들기
            valid_mask = ~(target_icu_in == -100).all(dim=1)  # [B*L], True if not all -100
            # 3. target과 logit 모두 해당 마스크로 필터링
            target_filtered = target_icu_in[valid_mask][:, 0]  # [N, F]
            logit_filtered = outputs_3[valid_mask]  # [N, C, F]
            logit_softmax = F.softmax(logit_filtered, dim=1)[:, 1, 0]
            self.logit_list[idx].append(logit_softmax)
            self.label_list[idx].append(target_filtered)

            idx = 4
            # 2. target에서 모든 feature가 -100인 row mask 만들기
            valid_mask = ~(target_prognosis == -100).all(dim=1)  # [B*L], True if not all -100
            # 3. target과 logit 모두 해당 마스크로 필터링
            target_filtered = target_prognosis[valid_mask]  # [N, F]
            logit_filtered = outputs_4[valid_mask]  # [N, C, F]
            logit_softmax = F.softmax(logit_filtered, dim=1)[:,1]
            self.logit_list[idx].append(logit_softmax)
            self.label_list[idx].append(target_filtered)

            idx = 5
            # 2. target에서 모든 feature가 -100인 row mask 만들기
            valid_mask = ~(target_los1 == -100).all(dim=1)  # [B*L], True if not all -100
            # 3. target과 logit 모두 해당 마스크로 필터링
            target_filtered = target_los1[valid_mask][:,0]  # [N, F]
            logit_filtered = outputs_5[valid_mask]  # [N, C, F]
            logit_softmax = F.softmax(logit_filtered, dim=1)[:,:,0]
            self.logit_list[idx].append(logit_softmax)
            self.label_list[idx].append(target_filtered)

            idx = 6
            # 2. target에서 모든 feature가 -100인 row mask 만들기
            valid_mask = ~(target_los2 == -100).all(dim=1)  # [B*L], True if not all -100
            # 3. target과 logit 모두 해당 마스크로 필터링
            target_filtered = target_los2[valid_mask][:, 0]  # [N, F]
            logit_filtered = outputs_6[valid_mask]  # [N, C, F]
            logit_softmax = F.softmax(logit_filtered, dim=1)[:, :, 0]
            self.logit_list[idx].append(logit_softmax)
            self.label_list[idx].append(target_filtered)

            idx = 7
            # 2. target에서 모든 feature가 -100인 row mask 만들기
            valid_mask = ~(target_phe == -100).all(dim=1)  # [B*L], True if not all -100
            # 3. target과 logit 모두 해당 마스크로 필터링
            target_filtered = target_phe[valid_mask] # [N, F]
            logit_filtered = outputs_7[valid_mask]  # [N, C, F]
            logit_softmax = F.softmax(logit_filtered, dim=1)[:,1]
            self.logit_list[idx].append(logit_softmax)
            self.label_list[idx].append(target_filtered)

            idx = 8
            # 2. target에서 모든 feature가 -100인 row mask 만들기
            valid_mask = ~(target_vaso == -100).all(dim=1)  # [B*L], True if not all -100
            # 3. target과 logit 모두 해당 마스크로 필터링
            target_filtered = target_vaso[valid_mask][:,0]  # [N, F]
            logit_filtered = outputs_8[valid_mask]  # [N, C, F]
            logit_softmax = F.softmax(logit_filtered, dim=1)[:,1,0]
            self.logit_list[idx].append(logit_softmax)
            self.label_list[idx].append(target_filtered)

            idx = 9
            # 2. target에서 모든 feature가 -100인 row mask 만들기
            valid_mask = ~(target_huo == -100).all(dim=1)  # [B*L], True if not all -100
            # 3. target과 logit 모두 해당 마스크로 필터링
            target_filtered = target_huo[valid_mask]  # [N, F]
            logit_filtered = outputs_9[valid_mask]  # [N, C, F]
            logit_softmax = F.softmax(logit_filtered, dim=1)[:,1]
            self.logit_list[idx].append(logit_softmax)
            self.label_list[idx].append(target_filtered)

        return loss

    def in_train(self, bool):
        if bool:
            self.train_phase = True
            self.logit_list = [[], [], [], [], [], [], [], [], [], []]
            self.label_list = [[], [], [], [], [], [], [], [], [], []]
        else:
            self.train_phase = False
            self.logit_list = [[], [], [], [], [], [], [], [], [], []]
            self.label_list = [[], [], [], [], [], [], [], [], [], []]

    def calc_results(self, save_path = None, idxs = 10):
        'IHM'
        for idx in range(10):
            self.logit_list[idx] = torch.cat(self.logit_list[idx], dim=0)
            self.label_list[idx] = torch.cat(self.label_list[idx], dim=0)

        results = {}
        # 모든 rank에서 모으기
        for idx in range(idxs):
            # 각 GPU에서 logit과 label 수집
            gathered_logits = gather_tensors_from_all_gpus(self.logit_list[idx])
            gathered_labels = gather_tensors_from_all_gpus(self.label_list[idx])

            # CPU로 이동
            gathered_logits = gathered_logits.cpu()
            gathered_labels = gathered_labels.cpu()


            if dist.get_rank() == 0:
                '''
                ihm_out, phe_out, dec_death_out, dec_arrest_out, los_out, huo_out, vaso_out
                '''
                # numpy로 변환
                logits_np = gathered_logits.numpy()
                labels_np = gathered_labels.numpy()

                np.savetxt(save_path+self.task_dict[idx]+'_logit.csv', logits_np, delimiter=',')
                np.savetxt(save_path +self.task_dict[idx]+'_label.csv', labels_np.astype(np.int8) , delimiter=',')

                if idx in [0,1,2,3,8]: #ihm, dec_d, dec_a, Icu_in, vaso
                    auroc = roc_auc_score(labels_np, logits_np)
                    auprc = average_precision_score(labels_np, logits_np)
                    results[idx] = {'auroc': auroc, 'auprc': auprc}

                elif idx in [4,7,9]:
                    results[idx] = {} #Prog, phe, huo
                    #logits_np & labels_np: (batch_, feature)
                    for idx_feat in range(logits_np.shape[1]):
                        auroc = roc_auc_score(labels_np[:,idx_feat], logits_np[:,idx_feat])
                        auprc = average_precision_score(labels_np[:,idx_feat], logits_np[:,idx_feat])
                        results[idx][f'auroc_{idx_feat}'] = auroc
                        results[idx][f'auprc_{idx_feat}'] = auprc

                    macro_auc = roc_auc_score(labels_np, logits_np, average='macro')
                    micro_auc = roc_auc_score(labels_np, logits_np, average='micro')
                    results[idx][f'macro_auc'] = macro_auc
                    results[idx][f'micro_auc'] = micro_auc

                elif idx in [5,6]: #Los_adm, Los_icu
                    preds_np = np.argmax(logits_np, axis=1)
                    results[idx] = {
                        "accuracy": accuracy_score(labels_np, preds_np),
                        "macro_f1": f1_score(labels_np, preds_np, average='macro'),
                        "micro_f1": f1_score(labels_np, preds_np, average='micro'),
                        "precision_macro": precision_score(labels_np, preds_np, average='macro', zero_division=0),
                        "recall_macro": recall_score(labels_np, preds_np, average='macro', zero_division=0),
                        "kappa": cohen_kappa_score(labels_np, preds_np),
                        "log_loss": log_loss(labels_np, logits_np),  # 여기는 그대로 logits_np 사용
                        "confusion_matrix": confusion_matrix(labels_np, preds_np).tolist()
                    }

            else:
                results[idx] = None
        return results


class MultiFeatureWeightedSoftmaxLoss(nn.Module):
    def __init__(self, feature_weights, ignore_index=-100):
        """
        Args:
            feature_weights: List of dictionaries, each containing weights for classes 0 and 1
            Example: [{0: 0.7, 1: 1.3}, {0: 1.4, 1: 0.8}, ...]
            ignore_index: Index to ignore in loss computation (default: -100)
        """
        super().__init__()
        self.feature_weights = feature_weights
        self.num_features = len(feature_weights)
        self.ignore_index = ignore_index

        # Convert to tensors for efficient computation
        weights_0 = torch.tensor([fw[0] for fw in feature_weights])
        weights_1 = torch.tensor([fw[1] for fw in feature_weights])
        # Register as buffers so they move with the model to GPU/CPU
        self.register_buffer('weights_0', weights_0)
        self.register_buffer('weights_1', weights_1)

    def forward(self, logits, targets):
        """
        Args:
            logits: Tensor of shape (batch, num_classes, num_features) - typically (batch, 2, num_features)
            targets: Tensor of shape (batch, num_features) - class indices (0, 1, or ignore_index)
        Returns:
            loss: Scalar tensor
        """

        # Create mask for valid samples (batch-level mask)
        # Check if first feature is valid (since all features in a sample are either all valid or all -100)
        valid_mask = (targets[:, 0] != self.ignore_index)  # (batch,)

        # If no valid samples, return zero loss
        if not valid_mask.any():
            return (logits.sum()) * 0.0

        # Filter to only valid samples
        valid_logits = logits[valid_mask]  # (valid_batch, num_classes, num_features)
        valid_targets = targets[valid_mask]  # (valid_batch, num_features)
        valid_batch_size = valid_logits.size(0)

        # Apply softmax along class dimension to get probabilities
        probs = F.softmax(valid_logits, dim=1)  # (valid_batch, num_classes, num_features)

        # Extract probabilities for the target classes
        target_probs = torch.gather(probs, 1, valid_targets.unsqueeze(1).long())  # (valid_batch, 1, num_features)
        target_probs = target_probs.squeeze(1)  # (valid_batch, num_features)

        # Compute negative log likelihood
        nll_loss = -torch.log(target_probs + 1e-8)  # (valid_batch, num_features)

        # Apply feature-specific weights based on target class
        weights = torch.where(
            valid_targets == 0,
            self.weights_0.unsqueeze(0).expand(valid_batch_size, -1),
            self.weights_1.unsqueeze(0).expand(valid_batch_size, -1)
        )

        # Apply weights and compute mean
        weighted_loss = nll_loss * weights
        return weighted_loss.mean()
