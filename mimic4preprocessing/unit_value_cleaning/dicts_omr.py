from mimic4preprocessing.my_itemid import my_itemid

float_value_convert = {
    '220179||Non Invasive Blood Pressure systolic||omr': {'drop': [], 'convert': {}},
    '220180||Non Invasive Blood Pressure diastolic||omr': {'drop': [], 'convert': {}},
    '224639||Daily Weight||omr': {'drop': [], 'convert': {}},
    f'{my_itemid["BMI (kg/m2)"][0]}||BMI (kg/m2)||omr': {'drop': [], 'convert': {}},
    '226707||Height||omr': {'drop': [], 'convert': {}}
}

string_value_convert= {'1000000||outpatient_visit||omr': {'drop': ['nan'], 'convert': {}}}


omr_float_unit_convert = {
    '226707||Height||omr': {'convert': {'Inch': ['cm', lambda x: x * 2.54]}},
}
omr_str_unit_convert = {}

float_inclusion_dict = {
    # [Blood Pressure] - 0은 측정 오류. Systolic 300 / Diastolic 200 이상은 생존 불가능하거나 즉각적 처치 필요한 극단값
    '220179||Non Invasive Blood Pressure systolic||omr': {
        'inclusion': [10.0, 300.0],
        'decimal': 0
    },
    '220180||Non Invasive Blood Pressure diastolic||omr': {
        'inclusion': [10.0, 200.0],
        'decimal': 0
    },

    # [Body Measurements]
    # Weight: max가 95,362,165로 명백한 오류. 95%가 119kg이므로 초고도비만 고려해 600kg 상한.
    # 하한 1.0kg는 신생아/소아 고려 및 0 제외.
    '224639||Daily Weight||omr': {
        'inclusion': [1.0, 600.0],
        'decimal': 1
    },

    # BMI: Weight 오류에 영향을 받아 max가 321,697로 나옴.
    # 생존 가능한 최고 BMI(100~200) 고려하여 200으로 제한. 0 제외.
    f'{my_itemid["BMI (kg/m2)"][0]}||BMI (kg/m2)||omr': {
        'inclusion': [5.0, 200.0],
        'decimal': 1
    },

    # Height: 단위가 Inch. max 73,252는 오류.
    # 120 inch = 약 305cm (세계 최장신 기록보다 높게 설정하여 오류만 제거).
    # 하한 10 inch = 약 25cm (신생아 미숙아 고려).
    '226707||Height||omr': {
        'inclusion': [25, 300],
        'decimal': 0
    }
}

convert_key_float = {
    '226707||Height||omr':{'key':'226730||Height (cm)||omr', 'unit':'cm', 'convert':lambda x: x},
}

