my_itemid = {
    ### General Feature ####
    'BMI (kg/m2)': [909000, 'kg/m2'],
    'GCS - Total': [909001, None],

    ######## Extras ########
    'Extra':{
        'itemid':1300000,
        'unit': None,
        'values': {f"<extra{i}>": i for i in range(50)},
    },

    ######## Meta IDs ########
    'Question':{
        'itemid':2000000,
        'unit': None,
        'values': None,},
    'Downstream-task':{
        'itemid':2100000,
        'unit': None,
        'values': None,},

    ### Birth Prefix ###
    'Birth':{
        'itemid':1100000,
        'unit': None,
        'values': None,},
    
    'Ethnicity' : {
        'itemid':1100001,
        'unit': None,
        'values':
            {'WHITE': 1,
             'WHITE - RUSSIAN': 1,
             'WHITE - OTHER EUROPEAN': 1,
             'WHITE - EASTERN EUROPEAN': 1,
             'WHITE - BRAZILIAN': 1,
             'PORTUGUESE': 1,

             'BLACK/AFRICAN AMERICAN': 2,
             'BLACK/AFRICAN': 2,
             'BLACK/CAPE VERDEAN': 2,
             'BLACK/CARIBBEAN ISLAND': 2,

             'ASIAN': 3,
             'ASIAN - CHINESE': 3,
             'ASIAN - KOREAN': 3,
             'ASIAN - SOUTH EAST ASIAN': 3,
             'ASIAN - ASIAN INDIAN': 3,

            'HISPANIC OR LATINO': 4,
            'HISPANIC/LATINO - MEXICAN': 4,
            'HISPANIC/LATINO - PUERTO RICAN': 4,
            'HISPANIC/LATINO - DOMINICAN': 4,
            'HISPANIC/LATINO - SALVADORAN': 4,
            'HISPANIC/LATINO - GUATEMALAN': 4,
            'HISPANIC/LATINO - CUBAN': 4,
            'HISPANIC/LATINO - HONDURAN': 4,
            'HISPANIC/LATINO - CENTRAL AMERICAN': 4,
            'HISPANIC/LATINO - COLUMBIAN': 4,
            'SOUTH AMERICAN': 4,

            'AMERICAN INDIAN/ALASKA NATIVE': 5,
            'NATIVE HAWAIIAN OR OTHER PACIFIC ISLANDER': 5,

            'MULTIPLE RACE/ETHNICITY': 6,

            'UNKNOWN/OTHERS': 0,
            'UNKNOWN': 0,
            'UNABLE TO OBTAIN': 0,
            'PATIENT DECLINED TO ANSWER': 0,
            'OTHER': 0,
            '': 0}
    },

    'Gender':{
        'itemid':1100002,
        'unit': None,
        'values':{'Male':0, 'Female':1}
    },

    #####################################################
    'Move':{
        'itemid':1000000,
        'unit': None,
        'values':{'outpatient_visit':0,
                  'ed_admission':1, 'ed_discharge':2,
                  'admission':3, 'discharge':4,
                  'icu-in':5, 'icu-out':6}
    },

    ####### Admission location  ####### - admissions.csv
    'Admission location':{
        'itemid':1000001,
        'unit': None,
        'values':{
            'EMERGENCY ROOM': 1,
            'WALK-IN/SELF REFERRAL': 1,

            'PHYSICIAN REFERRAL': 2,
            'CLINIC REFERRAL': 2,
            'PROCEDURE SITE': 2,
            'AMBULATORY SURGERY TRANSFER': 2,

            'TRANSFER FROM HOSPITAL': 3,
            'TRANSFER FROM SKILLED NURSING FACILITY': 3,

            'PACU': 4,
            'INTERNAL TRANSFER TO OR FROM PSYCH': 4,

            'INFORMATION NOT AVAILABLE': 0,
            'None-admit_loc': 0, # nan 이 있음
        }
    },
    ########################

    ####### Discharge location  ####### - admissions.csv
    'Discharge location':{
        'itemid':1000002,
        'unit': None,
        'values':{
            'HOME':1,
            'HOME HEALTH CARE': 1,

            'SKILLED NURSING FACILITY':2,
            'REHAB':2,
            'ASSISTED LIVING':2,
            'CHRONIC/LONG TERM ACUTE CARE':2,

            'ACUTE HOSPITAL':3,

            'HOSPICE': 4,

            'DIED': 5,

            'PSYCH FACILITY': 6,

            'AGAINST ADVICE': 7,

            'OTHER FACILITY':0,
            'HEALTHCARE FACILITY': 0,
            'None-disch_loc': 0,}
    },
    ########################


    ####### ICU class ####### - icustays.csv
    'ICU class':{
        'itemid':1000003,
        'unit': None,
        'values':{
            'Medical Intensive Care Unit (MICU)': 1,
            'Medicine': 1,

            'Medical/Surgical Intensive Care Unit (MICU/SICU)': 2,
            'Intensive Care Unit (ICU)': 2,
            'Med/Surg': 2,

            'Surgical Intensive Care Unit (SICU)': 3,
            'Neuro Surgical Intensive Care Unit (Neuro SICU)': 3,
            'Surgery/Trauma': 3,
            'Trauma SICU (TSICU)': 3,

            'Cardiac Vascular Intensive Care Unit (CVICU)': 4,

            'Coronary Care Unit (CCU)': 5,

            'Neuro Intermediate': 6,
            'Neuro Stepdown': 6,
            'Neurology': 6,

            'Medicine/Cardiology Intermediate': 7,
            'Surgery/Vascular/Intermediate': 7,

            'PACU': 0,}
    },
    ########################
    "Ending":{
        'itemid':1200000,
        'unit': None,
        'values':{
        'Death-event':1,
        'Censored-event': 0, # No death until 1-year f/u
        },
    }

    ########################


}

e_map = {'WHITE': 1, 'WHITE - RUSSIAN': 1, 'WHITE - OTHER EUROPEAN': 1, 'WHITE - EASTERN EUROPEAN': 1, 'WHITE - BRAZILIAN': 1, 'PORTUGUESE': 1,

         'BLACK/AFRICAN AMERICAN': 2, 'BLACK/AFRICAN': 2, 'BLACK/CAPE VERDEAN': 2, 'BLACK/CARIBBEAN ISLAND': 2,

         'ASIAN': 3, 'ASIAN - CHINESE': 3, 'ASIAN - KOREAN': 3, 'ASIAN - SOUTH EAST ASIAN': 3, 'ASIAN - ASIAN INDIAN': 3,

         'HISPANIC OR LATINO': 4, 'HISPANIC/LATINO - MEXICAN': 4, 'HISPANIC/LATINO - PUERTO RICAN': 4,
         'HISPANIC/LATINO - DOMINICAN': 4, 'HISPANIC/LATINO - SALVADORAN': 4, 'HISPANIC/LATINO - GUATEMALAN': 4,
         'HISPANIC/LATINO - CUBAN': 4, 'HISPANIC/LATINO - HONDURAN': 4, 'HISPANIC/LATINO - CENTRAL AMERICAN': 4,
         'HISPANIC/LATINO - COLUMBIAN': 4, 'SOUTH AMERICAN': 4, 'PORTUGUESE': 4,

         'AMERICAN INDIAN/ALASKA NATIVE': 5, 'NATIVE HAWAIIAN OR OTHER PACIFIC ISLANDER': 5,

         'MULTIPLE RACE/ETHNICITY': 6,

         'UNKNOWN': 0, 'UNABLE TO OBTAIN': 0, 'PATIENT DECLINED TO ANSWER': 0, 'OTHER': 0,
         '': 0} # from preprocessing.py

name_to_id = {}