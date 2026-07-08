
import torch
import torch.nn as nn

class dt_projection(nn.Module):
    def __init__(self, d_model):
        '''
        ['IHM', 'Phe', 'DEC_death', 'DEC_arrest', 'LOS', 'HUO', 'VASO']
        'IHM' - 1: 0/1
        'DEC_death' - 1: 0/1
        'DEC_arrest' - 1: 0/1
        !'ICI-in' - 1: 0/1
        !'prognosis' - 6: 0/1
        !'LOS' - 2: 0/1/2/3/4/5/6/7/8/9

        'Phe' - 25: 0/1
        'VASO' - 1: 0/1
        'HUO' - 2: 0/1
        '''
        super().__init__()
        self.d_model = d_model

        self.ihm = nn.Sequential(nn.Linear(d_model, 128), nn.ReLU(), nn.Linear(128, 2))
        self.dec_death = nn.Sequential(nn.Linear(d_model, 128), nn.ReLU(), nn.Linear(128, 2))
        self.dec_arrest = nn.Sequential(nn.Linear(d_model, 128), nn.ReLU(), nn.Linear(128, 2))

        self.icu_in = nn.Sequential(nn.Linear(d_model, 128), nn.ReLU(), nn.Linear(128, 2))
        self.prognosis = nn.Sequential(nn.Linear(d_model, 128), nn.ReLU(), nn.Linear(128, 12))
        self.los1 = nn.Sequential(nn.Linear(d_model, 128), nn.ReLU(), nn.Linear(128, 10))
        self.los2 = nn.Sequential(nn.Linear(d_model, 128), nn.ReLU(), nn.Linear(128, 10))

        self.phe = nn.Sequential(nn.Linear(d_model, 128), nn.ReLU(), nn.Linear(128, 50))
        self.vaso = nn.Sequential(nn.Linear(d_model, 128), nn.ReLU(), nn.Linear(128, 2))
        self.huo = nn.Sequential(nn.Linear(d_model, 128), nn.ReLU(), nn.Linear(128, 4))


    def forward(self, x, _): # batch, length, 512
        batch_size, length, _ = x.shape

        #print(x[0])

        ihm_out = self.ihm(x).view(batch_size, length, 2, 1)
        dec_death_out = self.dec_death(x).view(batch_size, length, 2, 1)
        dec_arrest_out = self.dec_arrest(x).view(batch_size, length, 2, 1)

        icu_in_out = self.icu_in(x).view(batch_size, length, 2, 1)
        prognosis_out = self.prognosis(x).view(batch_size, length, 2, 6)
        los1_out = self.los1(x).view(batch_size, length, 10, 1)
        los2_out = self.los2(x).view(batch_size, length, 10, 1)

        phe_out = self.phe(x).view(batch_size, length, 2, 25)
        vaso_out = self.vaso(x).view(batch_size, length, 2, 1)
        huo_out = self.huo(x).view(batch_size, length, 2, 2)


        return (ihm_out, dec_death_out, dec_arrest_out, icu_in_out, prognosis_out, los1_out, los2_out, phe_out, vaso_out, huo_out)
