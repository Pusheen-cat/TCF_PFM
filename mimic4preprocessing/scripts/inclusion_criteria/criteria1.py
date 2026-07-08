from mimic4preprocessing.unit_value_cleaning.interchange_csvs import labevents_to, omr_to, outputevents_to
all_to = labevents_to|omr_to|outputevents_to
key_set = set()
for k, v in all_to.items():
    orig_key = v['key']
    key_set.add(orig_key)  # 1. 그대로
    itemid, name, _ = orig_key.split("||")
    _, _, ori_type = k.split("||")
    lab_key = f"{itemid}||{name}||{ori_type}"
    key_set.add(lab_key)   # 2. type만 변경
csvs = ['chartevents', 'labevents', 'omr', 'outputevents']
inclusion = {csv: set() for csv in csvs}
for k in key_set:
    parts = k.split("||")
    if len(parts) != 3:
        raise AttributeError
    typ = parts[2]
    if typ in inclusion:
        inclusion[typ].add(k)


criteria1 = {
    'chartevents':{
        'count_threshold':1_000_000,
        'inclusion_key':{'223951||Capillary Refill R||chartevents',
                         '224308||Capillary Refill L||chartevents',
                         '220339||PEEP set||chartevents',
                         '229357||Absolute Count - Neuts||chartevents',
                         '229358||Absolute Count - Lymphs||chartevents',
                         '229359||Absolute Count - Monos||chartevents',
                         '229361||Absolute Count - Basos||chartevents',
                         '229360||Absolute Count - Eos||chartevents',
                         '224685||Tidal Volume (observed)||chartevents',
                         '226730||Height (cm)||chartevents 827321',
                         '220734||PH (dipstick)||chartevents 819442',
                         '224697||Mean Airway Pressure||chartevents',
                         '220621||Glucose (serum)||chartevents',
                         '224689||Respiratory Rate (spontaneous)||chartevents',
                         '223834||O2 Flow||chartevents',
                         '224690||Respiratory Rate (Total)||chartevents',
                         '220645||Sodium (serum)||chartevents',
                         '220545||Hematocrit (serum)||chartevents',
                         '220602||Chloride (serum)||chartevents',
                         '220228||Hemoglobin||chartevents 598400',
                         '227443||HCO3 (serum)||chartevents 591846',
                         '220615||Creatinine (serum)||chartevents 590337',
                         '227073||Anion gap||chartevents 589377',
                         '225624||BUN||chartevents 588900',
                         '220635||Magnesium||chartevents 574808',
                         '225677||Phosphorous||chartevents 546651',
                         '225667||Ionized Calcium||chartevents',
                         '225625||Calcium non-ionized||chartevents 542376',
                         '224639||Daily Weight||chartevents 541032',
                         '227457||Platelet Count||chartevents 539006',
                         '220546||WBC||chartevents 529983',
                         '223898||Orientation||chartevents',
                         '223830||PH (Arterial)||chartevents',
                         '220224||Arterial O2 pressure||chartevents',
                         '224828||Arterial Base Excess||chartevents',
                         '220235||Arterial CO2 Pressure||chartevents',
                         '225698||TCO2 (calc) Arterial||chartevents',
                         '227466||PTT||chartevents',
                         '227465||Prothrombin time||chartevents',
                         '227467||INR||chartevents',
                         '224691||Flow Rate (L/min)||chartevents',
                         '225668||Lactic Acid||chartevents',
                         '220644||ALT||chartevents',
                         '225690||Total Bilirubin||chartevents',
                         '220587||AST||chartevents',
                         '225612||Alkaline Phosphate||chartevents',
                         '228640||EtCO2||chartevents'}|inclusion['chartevents'],
        'exclusion_key':{'227969||Safety Measures||chartevents',
                         '227958||Less Restrictive Measures||chartevents',
                         '224082||Turn||chartevents',
                         '224080||Head of Bed||chartevents',
                         '224093||Position||chartevents',
                         '228905||Altered Respiratory Status NCP - Interventions||chartevents',
                         '224642||Temperature Site||chartevents',
                         '228868||Assistance||chartevents',
                         '228928||Impaired Tissue Perfusion NCP - Interventions||chartevents',
                         '223792||Pain Management||chartevents 2335905',
                         '228988||Safety Restraints NCP - Interventions||chartevents',
                         '224073||Education Topic||chartevents',
                         '224641||Alarms On||chartevents',
                         '224168||Parameters Checked||chartevents',
                         '227944||Side Rails||chartevents',
                         '223781||Pain Present||chartevents',
                         '224089||Anti Embolic Device||chartevents',
                         '228947||Infection NCP - Interventions||chartevents',
                         '225054||Anti Embolic Device Status||chartevents',
                         '228924||Impaired Tissue Perfusion NCP - Expected outcomes||chartevents',
                         '227947||Reason for Restraint (Non-violent)||chartevents',
                         '224015||Urine Source||chartevents',
                         '228898||Impaired Fluid Balance NCP - Interventions||chartevents',
                         '223795||Pain Assessment Method||chartevents',
                         '224088||Pressure Reducing Device||chartevents',
                         '227954||Status and Comfort||chartevents',
                         '228305||ST Segment Monitoring On||chartevents',
                         '227955||Food and Fluid||chartevents',
                         '226168||Oral Care||chartevents',
                         '224087||Therapeutic Bed||chartevents',
                         '228977||Altered Mental Status  NCP - Interventions||chartevents',
                         '228937||Post-op Care NCP - Interventions||chartevents',
                         '224650||Ectopy Type 1||chartevents',
                         '228890||Pain NCP - Interventions||chartevents',
                         '228397||Commands Response||chartevents',
                         '228902||Altered Respiratory Status NCP - Expected outcomes||chartevents',
                         '228398||Commands||chartevents', '227945||Restraint (Non-violent)||chartevents',
                         '227948||Restraint Device (Non-violent)||chartevents',
                         '223794||Pain Level Acceptable||chartevents',
                         '227950||Restraint Location||chartevents',
                         '227959||Restraints Evaluated||chartevents',
                         '227952||Position Change||chartevents',
                         '227957||Signs of Injury from Intervention||chartevents',
                         '227953||Range of Motion||chartevents',
                         '227961||Side  Rails||chartevents',
                         '224000||Nares R||chartevents',
                         '228298||Daily Wake Up||chartevents',
                         '227956||Urinal/Bedpan||chartevents',
                         '227946||Restraint Ordered (Non-violent)||chartevents',
                         '224879||Nares L||chartevents',
                         '228933||Post-op Care NCP - Expected outcomes||chartevents'},
    },
    'labevents':{
        'count_threshold':100_000,
        'inclusion_key':set()|inclusion['labevents'],
        'exclusion_key':[],
    },
    'omr':{
        'count_threshold':100_000,
        'inclusion_key':set()|inclusion['omr'],
        'exclusion_key':[],
    },
      'outputevents':{
        'count_threshold':100_000,
        'inclusion_key':set()|inclusion['outputevents'],
        'exclusion_key':['226559||Foley||outputevents'],
    },

}

"""
#labevents
50971||Potassium||labevents 4325279
51221||Hematocrit||labevents 4290027
50912||Creatinine||labevents 4158858
51222||Hemoglobin||labevents 4142775
50983||Sodium||labevents 4120641
51006||Blood urea nitrogen||labevents 4038353
51265||Platelets||labevents 4026494
50902||Chloride||labevents 4016413
51301||White blood cell count||labevents 4001582
51249||Mean corpuscular hemoglobin concentration||labevents 3971662
51250||Mean corpuscular volume||labevents 3971463
51279||Red blood cell count||labevents 3971381
51248||Mean corpuscular hemoglobin||labevents 3971015
51277||RDW||labevents 3967625
50882||Bicarbonate||labevents 3826400
50868||Anion gap||labevents 3788180
50931||Glucose||labevents 3766537
50893||Calcium||labevents 2916866
50960||Magnesium||labevents 2898351
50970||Phosphate||labevents 2779295
50934||H||labevents 2540209
51678||L||labevents 2540182
50947||I||labevents 2540166
52172||RDW-SD||labevents 2152902
51237||PT INR||labevents 1735950
51274||Prothrombin time||labevents 1735659
50861||Alanine aminotransferase||labevents 1716884
50878||Asparate aminotransferase||labevents 1702240
51275||Partial thromboplastin time||labevents 1594533
50863||Alkaline phosphate||labevents 1532572
50885||Bilirubin||labevents 1512792
51244||Lymphocytes||labevents 1475868
51254||Monocytes||labevents 1475868
51256||Neutrophils||labevents 1475861
51200||EOSINOPHILS||labevents 1475861
51146||Basophils||labevents 1475853
50862||Albumin||labevents 983453
52033||SPECIMEN TYPE||labevents 835538
52075||ABSOLUTE NEUTROPHIL COUNT||labevents 809850
51133||Lymphocytes||labevents 773025
51491||pH (urine)||labevents 767216
52074||ABSOLUTE MONOCYTE COUNT||labevents 759554
51486||LEUKOCYTES (urine)||labevents 758116
51506||URINE APPEARANCE||labevents 758115
51487||NITRITE (urine)||labevents 758109
51466||BLOOD (urine)||labevents 758108
51464||Bilirubin (urine)||labevents 758106
51508||URINE COLOR||labevents 758004
50820||pH||labevents 750957
51498||SPECIFIC GRAVITY (urine)||labevents 745776
50802||BASE EXCESS||labevents 695284
50818||Partial pressure of carbon dioxide||labevents 695217
50804||CO2 (ETCO2, PCO2, etc.)||labevents 694987
50821||PO2||labevents 694353
50813||Lactate||labevents 651940
52069||ABSOLUTE BASOPHIL COUNT||labevents 647835
50954||Lactate dehydrogenase||labevents 640009
52073||ABSOLUTE EOSINOPHIL COUNT||labevents 638258
52135||IMMATURE GRANULOCYTES||labevents 613623
51519||YEAST (urine)||labevents 544782
51463||BACTERIA (urine)||labevents 544767
51493||Red blood cell count (urine)||labevents 544517
51516||White blood cell count (urine)||labevents 460666
51492||PROTEIN (urine)||labevents 450072
51003||Troponin-T||labevents 441717
51476||EPITHELIAL CELLS (urine)||labevents 440057
50808||Calcium-ionized||labevents 368712
51512||URINE MUCOUS||labevents 362150
50993||THYROID STIMULATING HORMONE||labevents 353753
50910||CREATINE KINASE (CK)||labevents 321987
51000||TRIGLYCERIDES||labevents 282657
50907||Cholesterol, Total||labevents 272037
50956||LIPASE||labevents 267147
50904||Cholesterol, HDL||labevents 265418
50903||CHOLESTEROL RATIO (TOTAL/HDL)||labevents 264629
50852||% Hemoglobin A1c||labevents 261059
51144||BANDS||labevents 245225
50905||Cholesterol, LDL, Calculated||labevents 242750
50817||Oxygen saturation||labevents 237570
51613||EAG||labevents 232269
51082||Creatinine (urine)||labevents 226071
51251||METAMYELOCYTES||labevents 224227
51255||MYELOCYTES||labevents 221452
50911||CREATINE KINASE, MB ISOENZYME||labevents 216487
51143||Lymphocytes||labevents 212060
50976||PROTEIN, TOTAL||labevents 203519
51007||URIC ACID||labevents 187769
50812||INTUBATED||labevents 186842
50924||FERRITIN||labevents 176335
51484||KETONE (urine)||labevents 173853
51478||Glucose (urine)||labevents 165261
50889||C-REACTIVE PROTEIN||labevents 160145
50930||GLOBULIN||labevents 158383
51214||FIBRINOGEN, FUNCTIONAL||labevents 150286
50952||IRON||labevents 146211
50998||TRANSFERRIN||labevents 130623
50953||IRON BINDING CAPACITY, TOTAL||labevents 130421
51482||HYALINE CASTS (urine)||labevents 125824
50986||TACROFK||labevents 123785
50825||TEMPERATURE||labevents 120345
50995||THYROXINE (T4), FREE||labevents 118226
51009||VANCOMYCIN||labevents 117917
51010||VITAMIN B12||labevents 115046
50884||Bilirubin, Indirect||labevents 105000
51514||UROBILINOGEN (urine)||labevents 103265
51257||NUCLEATED RED CELLS||labevents 100251
"""