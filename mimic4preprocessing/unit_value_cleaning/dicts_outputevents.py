float_value_convert = {
    '226559||Foley||outputevents': {'drop': [], 'convert': {}},
    '226560||Void||outputevents': {'drop': [], 'convert': {}},
    '226588||Chest Tube #1||outputevents': {'drop': [], 'convert': {}},
    '226606||Cerebral Ventricular #1||outputevents': {'drop': [], 'convert': {}},
    '227510||TF Residual||outputevents': {'drop': [], 'convert': {}},
    '226561||Condom Cath||outputevents': {'drop': [], 'convert': {}},
    '226599||Jackson Pratt #1||outputevents': {'drop': [], 'convert': {}},
    '226589||Chest Tube #2||outputevents': {'drop': [], 'convert': {}},
    '226575||Nasogastric||outputevents': {'drop': [], 'convert': {}},
    '226576||Oral Gastric||outputevents': {'drop': [], 'convert': {}},
    '226600||Jackson Pratt #2||outputevents': {'drop': [], 'convert': {}},
    '226567||Straight Cath||outputevents': {'drop': [], 'convert': {}},
    '226613||Wound Vac #1||outputevents': {'drop': [], 'convert': {}},
    '226627||OR Urine||outputevents': {'drop': [], 'convert': {}},
    '226580||Fecal Bag||outputevents': {'drop': [], 'convert': {}},
    '226582||Ostomy (output)||outputevents': {'drop': [], 'convert': {}},
    '226610||Lumbar||outputevents': {'drop': [], 'convert': {}},
    '226597||JP Medial||outputevents': {'drop': [], 'convert': {}},
    '226579||Stool||outputevents': {'drop': [], 'convert': {}},
    '226598||JP Lateral||outputevents': {'drop': [], 'convert': {}},
    '227701||Drainage Bag||outputevents': {'drop': [], 'convert': {}},
    '226592||Mediastinal||outputevents': {'drop': [], 'convert': {}},
    '226633||Pre-Admission||outputevents': {'drop': [], 'convert': {}},
    '226563||Suprapubic||outputevents': {'drop': [], 'convert': {}},
    '226590||L Pleural #1||outputevents': {'drop': [], 'convert': {}},
    '226626||OR EBL||outputevents': {'drop': [], 'convert': {}},
    '226573||Gastric Tube||outputevents': {'drop': [], 'convert': {}},
    '226593||R Pleural #1||outputevents': {'drop': [], 'convert': {}},
    '227511||TF Residual Output||outputevents': {'drop': [], 'convert': {}},
    '226571||Emesis||outputevents': {'drop': [], 'convert': {}},
    '226583||Rectal Tube||outputevents': {'drop': [], 'convert': {}},
    '226601||Jackson Pratt #3||outputevents': {'drop': [], 'convert': {}}
}

string_value_convert = {}

outputevents_float_unit_convert = {}
outputevents_str_unit_convert = {}

float_inclusion_dict = {
    # [Urine Output] - 방광 용적 및 1회 배출량 고려.
    # Foley/Void: 30L, 876L 등은 오류. 1회/Shift 누적 최대 4~5L 허용.
    '226559||Foley||outputevents': {'inclusion': [0.0, 4000.0], 'decimal': 0},
    '226560||Void||outputevents': {'inclusion': [0.0, 1500.0], 'decimal': 0},
    '226561||Condom Cath||outputevents': {'inclusion': [0.0, 4000.0], 'decimal': 0},
    '226567||Straight Cath||outputevents': {'inclusion': [0.0, 2000.0], 'decimal': 0},
    '226563||Suprapubic||outputevents': {'inclusion': [0.0, 3200.0], 'decimal': 0},
    '226627||OR Urine||outputevents': {'inclusion': [0.0, 5000.0], 'decimal': 0}, # 수술 중 총량이라도 10L 육박은 과함

    # [GI Output & Stool] - 위/장 용적 고려.
    # NG Tube: Max 100만은 오류. Rectal Tube: Max 400만은 오류.
    '227510||TF Residual||outputevents': {'inclusion': [0.0, 2000.0], 'decimal': 0},
    '226575||Nasogastric||outputevents': {'inclusion': [0.0, 3000.0], 'decimal': 0},
    '226576||Oral Gastric||outputevents': {'inclusion': [0.0, 3000.0], 'decimal': 0},
    '226573||Gastric Tube||outputevents': {'inclusion': [0.0, 3000.0], 'decimal': 0},
    '226580||Fecal Bag||outputevents': {'inclusion': [0.0, 4000.0], 'decimal': 0},
    '226582||Ostomy (output)||outputevents': {'inclusion': [0.0, 4000.0], 'decimal': 0},
    '226579||Stool||outputevents': {'inclusion': [0.0, 4000.0], 'decimal': 0},
    '226583||Rectal Tube||outputevents': {'inclusion': [0.0, 4000.0], 'decimal': 0},
    '226571||Emesis||outputevents': {'inclusion': [0.0, 3000.0], 'decimal': 0},
    '227511||TF Residual Output||outputevents': {'inclusion': [0.0, 2500.0], 'decimal': 0},

    # [Drains - Chest/Pleural] - 흉관 배액.
    # 시간당 200ml 이상이면 응급. Shift 누적 고려해 2.5L~3L 상한.
    '226588||Chest Tube #1||outputevents': {'inclusion': [0.0, 2500.0], 'decimal': 0},
    '226589||Chest Tube #2||outputevents': {'inclusion': [0.0, 2500.0], 'decimal': 0},
    '226592||Mediastinal||outputevents': {'inclusion': [0.0, 2500.0], 'decimal': 0},
    '226590||L Pleural #1||outputevents': {'inclusion': [0.0, 3000.0], 'decimal': 0},
    '226593||R Pleural #1||outputevents': {'inclusion': [0.0, 3000.0], 'decimal': 0},

    # [Drains - Jackson Pratt (JP) & Wound] - 소형 흡입 배액관.
    # 6500mL는 JP백 용량(100-200mL)상 불가능. 자주 비웠다 해도 1.5L 상한.
    '226599||Jackson Pratt #1||outputevents': {'inclusion': [0.0, 1500.0], 'decimal': 0},
    '226600||Jackson Pratt #2||outputevents': {'inclusion': [0.0, 1500.0], 'decimal': 0},
    '226601||Jackson Pratt #3||outputevents': {'inclusion': [0.0, 1500.0], 'decimal': 0},
    '226597||JP Medial||outputevents': {'inclusion': [0.0, 1500.0], 'decimal': 0},
    '226598||JP Lateral||outputevents': {'inclusion': [0.0, 1500.0], 'decimal': 0},
    '226613||Wound Vac #1||outputevents': {'inclusion': [0.0, 3000.0], 'decimal': 0}, # 상처 부위 크기에 따라 다름
    '227701||Drainage Bag||outputevents': {'inclusion': [0.0, 5000.0], 'decimal': 0},

    # [Neurological Drains] - 뇌척수액(CSF).
    # 하루 생성량(~500mL) 및 시간당 배액 제한 고려.
    '226606||Cerebral Ventricular #1||outputevents': {'inclusion': [0.0, 500.0], 'decimal': 0},
    '226610||Lumbar||outputevents': {'inclusion': [0.0, 500.0], 'decimal': 0},

    # [Others - OR & Pre-admission]
    # OR EBL(출혈량): 70L는 오류. 15L(15000) 이상은 생존 희박한 극단값.
    # Pre-Admission: 129L는 오류. 10L 상한.
    '226626||OR EBL||outputevents': {'inclusion': [0.0, 15000.0], 'decimal': 0},
    '226633||Pre-Admission||outputevents': {'inclusion': [0.0, 10000.0], 'decimal': 0},
}

convert_key_float = {}
