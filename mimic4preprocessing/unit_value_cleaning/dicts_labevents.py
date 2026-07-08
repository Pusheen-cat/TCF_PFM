float_value_convert = { #여기에 없는 key는 제거
    '51221||Hematocrit||labevents': {'drop': ['nan', 'ERROR'], 'convert': {}},
    '50912||Creatinine||labevents': {'drop': ['nan'], 'convert': {}},
    '51265||Platelets||labevents': {'drop': ['nan', '___'], 'convert': {}},
    '51006||Blood urea nitrogen||labevents': {'drop': ['nan', '.'], 'convert': {}},
    '51222||Hemoglobin||labevents': {'drop': ['nan'], 'convert': {}},
    '50971||Potassium||labevents': {'drop': ['nan'], 'convert': {}},
    '51301||White blood cell count||labevents': {'drop': ['nan', '___'], 'convert': {'<0.1':0.05}},
    '51249||Mean corpuscular hemoglobin concentration||labevents': {'drop': ['nan', 'ERROR'], 'convert': {}},
    '51279||Red blood cell count||labevents': {'drop': ['nan', 'ERROR'], 'convert': {}},
    '51250||Mean corpuscular volume||labevents': {'drop': ['nan', 'ERROR'], 'convert': {}},
    '51248||Mean corpuscular hemoglobin||labevents': {'drop': ['nan', 'ERROR'], 'convert': {}},
    '51277||RDW||labevents': {'drop': ['nan', 'L', 'ERROR'], 'convert': {}},
    '50983||Sodium||labevents': {'drop': ['nan'], 'convert': {}},
    '50902||Chloride||labevents': {'drop': ['nan'], 'convert': {}},
    '50882||Bicarbonate||labevents': {'drop': ['nan'], 'convert': {}},
    '50868||Anion gap||labevents': {'drop': ['nan'], 'convert': {}},
    '50931||Glucose||labevents': {'drop': ['nan'], 'convert': {}},
    '50893||Calcium||labevents': {'drop': ['nan'], 'convert': {}},
    '50960||Magnesium||labevents': {'drop': ['nan'], 'convert': {}},
    '50970||Phosphate||labevents': {'drop': ['nan'], 'convert': {}},
    '50934||H||labevents': {'drop': ['nan', '-'], 'convert': {}},
    '51678||L||labevents': {'drop': ['nan', '-', '.'], 'convert': {}},
    '50947||I||labevents': {'drop': ['nan'], 'convert': {}},
    '52172||RDW-SD||labevents': {'drop': ['nan', 'ERROR'], 'convert': {}},
    '51237||Prothrombin time||labevents': {'drop': ['nan', 'ERROR', '___', 'UNABLE TO REPORT', 'UNABLE', 'UNABLE TO REPORT,QNS', 'ERRROR', 'CANCELED', 'UNABLE TO REPORT, SPECIMEN QNS', 'INR', 'EERROR', 'CLOTTED', 'UNABLE TO PERFORM', 'LAB ERROR', 'UNABLE TO REPORT, HCT GREATER THAN 55', 'SPECIMEN COMPROMISED. DISREGARD PREVIOUS RESULT OF 3.2.', ':UNABLE TO REPORT', 'UNABLE TO RESULT', 'SPECIMEN CLOTTED. PREVIOUSLY REPORTED AS 0.9.', 'SAMPLE CLOTTED', 'UNABLE TO REPORT INR QNS'],
                                           'convert': {'>20.2':21, '>22.8':23, '>21.8':22, '>14.5':15, '>15.7':16, '>13.1':14, '>13.4':14, '1..0':1, '>19.2':20, '>22':23, 'GREATER THAN 15.7':16, '>15.4':16, '>23.7':24, '>13.8':14, ':>13.1':14}},
    '51274||Prothrombin time||labevents': {'drop': ['nan', 'ERROR', 'UNABLE TO REPORT', '___', 'UNABLE', 'CANCELED', 'PT', 'CLOTTED', 'UNABLE TO REPORT, QNS', 'E', 'LAB ERROR', 'UNABLE TO RPEORT', 'ERROR,DISREGARD PREVIOUS RESULT OF 11.8', '‰', 'UNABLE TO REPORT,QNS'],
                                           'convert': {'>150': 151, '150>': 151, '>150.0': 151, '15,7': 15.7, '18,5': 18.5, '…12.1': 12.1, '22.2.': 22.2, '23.0.': 23.0, '13.41.1': 13.4, '21.42.0': 21.4, '12..5': 12.5, '55.5 NOTIFIED ___ @1:00PM': 55.5, '14.1 CALLED TO ___ AT 12:26 ON ___': 14.1, '10.1.\\':10.1}},
    '50861||Alanine aminotransferase||labevents': {'drop': ['nan', '-'], 'convert': {}},
    '50878||Asparate aminotransferase||labevents': {'drop': ['nan', '-'], 'convert': {}},
    '51275||Partial thromboplastin time||labevents': {'drop': ['nan', '___', 'ERROR', 'UNABLE TO REPORT', 'UNABLE', 'UNABLE TO REPORT,QNS', 'CANCELED', '150:150 IS', 'CLOTTED', 'Y', 'UNLABE TO REPORT', ':ERROR', ':UNABLE TO REPORT', 'LAB ERROR', '29.1 SPECIMEN LIPEMIC', '107/8', 'QNS', 'UNABLE TO PERFORM', 'UNABLE TO REPORT PTT QNS'],
                                                      'convert': {'34,5': 34.5, '>150':151, '143.4 VERIFIED':143.4, '52.0.':52, '67,3':67.3, '115.9 NOTIFIED ___ 7:55AM ___':115.9, '24.1.':24.1, '26..3':26.3, ': 117.4':117.4, '23.6,CHECKED FORCLOT':23.6, '34..3':34.3, '150 150 IS HIGHEST MEEASURED PTT: NOTIFIED ___ AT 4:30PM ON ___':150 }},
    '50885||Bilirubin||labevents': {'drop': ['nan'], 'convert': {}},
    '50863||Alkaline phosphate||labevents': {'drop': ['nan', '-'], 'convert': {}},
    '50920||ESTIMATED GFR (MDRD EQUATION)||labevents': {'drop': ['nan', '0'], 'convert': {}},
    '51256||Neutrophils||labevents': {'drop': ['nan'], 'convert': {}},
    '51244||Lymphocytes||labevents': {'drop': ['nan'], 'convert': {}},
    '51254||Monocytes||labevents': {'drop': ['nan'], 'convert': {}},
    '51146||Basophils||labevents': {'drop': ['nan', '-', 'E'], 'convert': {}},
    '51200||EOSINOPHILS||labevents': {'drop': ['nan', '-'], 'convert': {}},
    '50862||Albumin||labevents': {'drop': ['nan'], 'convert': {}},
    '52075||ABSOLUTE NEUTROPHIL COUNT||labevents': {'drop': ['nan'], 'convert': {}},
    '52073||ABSOLUTE EOSINOPHIL COUNT||labevents': {'drop': ['nan'], 'convert': {}},
    '52074||ABSOLUTE MONOCYTE COUNT||labevents': {'drop': ['nan'], 'convert': {}},
    '51133||Lymphocytes||labevents': {'drop': ['nan'], 'convert': {}},
    '52069||ABSOLUTE BASOPHIL COUNT||labevents': {'drop': ['nan'], 'convert': {}},
    '51491||pH||labevents': {'drop': ['___', 'nan', 'NotDone'], 'convert': {}},
    '51498||SPECIFIC GRAVITY||labevents': {'drop': ['nan', '___', 'NotDone',  'UNABLE TO REPORT, SPECIMEN GROSSLY BLOODY', 'CORRECTED RESULT', 'UNABLE TO REPORT, GROSSLY BLOODY SPECIMEN'],
                                           'convert': {'>1.030':1.035, '>1.035':1.040, '<1.005':1.000, '>=1.035':1.040, '>1.050':1.055, '<=1.005':1.000, '>=1.030':1.035, '>1.040':1.045, '<1.050':1.045, '.1.030':1.030, '1.027.':1.027, '1.0.18':1.018, '>1.035 REFRA':1.040, '1..005':1.005, '>1.35':1.040, '>10.35':1.040, '1.0.17':1.017, '>1.035€':1.040, '1..025':1.025, '1.0188.0':1.018, '>10.30':1.035, '1.000:BY REFRACTOMETER':1.000, '1..016':1.016, '1..006':1.006, '>1.051':1.055, '>1.0358':1.040, "'1.024":1.024, '1..008':1.008, '1.0305.0':1.0305, '?1.010':1.01, '1.025.':1.025, '>1.035 REFRACTOMETER':1.040, '.1.035':1.035, '1.0.15':1.015, '>1.045':1.050, '> 1.035':1.040, '1..024':1.024, ':1.030':1.030, ':>=1.030':1.035, '>1.038':1.040, '1.0.27':1.027, '1/021':1.021, '1.019\\':1.019, '>1.037':1.037, '1..050':1.050, '1.0056.5':1.006, '1.005L':1.005, '.1.012':1.012, 'LESS THAN 1.005':1.000, 'GREATER THAN 1.030':1.035, '1.0.16':1.016, '1.0.14':1.014, '>1.080':1.040}},
    '51478||Glucose||labevents': {'drop': ['nan', '___'], 'convert': {'NEG':0, 'N':0, '>1000':1100, 'TR':5}},
    '51492||PROTEIN||labevents': {'drop': ['nan', '___',], 'convert': {'NEG':0, 'TR':5, '>300':310, '>=300':310, '>600':610, 'NEGATIVE':0, 'N':0, 'TRACE':5}},
    '51484||KETONE||labevents': {'drop': ['nan', '___'], 'convert': {'NEG':0, 'TR':5, '>80':90, '>=160':170, 'N':0, '>150':160, 'TRACE':5, 'T':5}},
    '51514||UROBILINOGEN||labevents': {'drop': ['nan', '___'], 'convert': {'NEG':0, '>8':9, 'NORMAL':0.2, '>=8':9, 'N':0}},
    '50820||pH||labevents': {'drop': ['nan'], 'convert': {}},
    '51087||LENGTH OF URINE COLLECTION||labevents': {'drop': ['nan'], 'convert': {}},
    '50821||PO2||labevents': {'drop': ['nan'], 'convert': {}},
    '50804||CO2 (ETCO2, PCO2, etc.)||labevents': {'drop': ['nan', '___'], 'convert': {}},
    '50802||BASE EXCESS||labevents': {'drop': ['nan', '-', '.'], 'convert': {}},
    '50818||Partial pressure of carbon dioxide||labevents': {'drop': ['nan'], 'convert': {}},
    '50813||Lactate||labevents': {'drop': ['nan', '-'], 'convert': {}},
    '50954||Lactate dehydrogenase||labevents': {'drop': ['nan'], 'convert': {}},
    '52135||IMMATURE GRANULOCYTES||labevents': {'drop': ['nan', '___'], 'convert': {}},
    '51516||White blood cell count||labevents': {'drop': ['nan',  '___', 'UNABLE TO REPORT', '2--50',  '3-53O', ':QNS', 'NOT DONE'],
                                                 'convert': {'0-2':1, '3-5':4, '6-10':8, '>50':51, '11-20':16, '21-50':36, 'O-2':1, '0--2':1, '0.-2':1, '0-':0, '0-2.':1, '6-10-':8, 'O':0, '0-2R':1, '6--10':8, '<1':0, '>1000':1001, '>182':183, '3.-5':4, '0=2':1,}},
    '51493||Red blood cell count||labevents': {'drop': [ '___', 'NOT DONE',  '11-203-5', '<A'],
                                               'convert': {'nan':0, '0-2':1, '3-5':4, '>50':51, '6-10':8, '11-20':16, '21-50':36, '<1':0, '>1000':1001, '>182':183, '0-20-2':1, '0\\':0, '1/HPF':1, '0.-2':1, '6-10.':8, '3-5-':4, '.0-2':1, '0-2\\':1, '0-20-2R':1, '6-106-10':8, 'O-2':1, '0-':0, '11-200-2':16, '3--5':4, '>50.':51, '0-2 3-5':3, '0-2+':1, 'O':0}},
    '51476||EPITHELIAL CELLS||labevents': {'drop': ['___', 'NOT DONE'],
                                           'convert': {'0-2':1, '3-5':4, '<1':0, '6-10':8, '11-20':16, '21-50':36, '>50':51, '>1000':1001, '0-':0, 'O-2':1, '<1/HPF':0, '.21-50':36, "0-2'ONE(1) LARGE CLUMP":1, '3-':3, '0-2 TRANS':1, 'N':0, '11-20-':16, 'FEW':5, '1/HPF':1}},
    '51003||Troponin-T||labevents': {'drop': [], 'convert': {'nan':0.0 }},
    '50808||Calcium||labevents': {'drop': ['nan'], 'convert': {}},
    '50993||THYROID STIMULATING HORMONE||labevents': {'drop': ['nan'], 'convert': {}},
    '50822||Potassium||labevents': {'drop': ['nan'], 'convert': {}},
    '50910||CREATINE KINASE (CK)||labevents': {'drop': ['nan'], 'convert': {}},
    '51266||PLATELET SMEAR||labevents': {'drop': ['nan'], 'convert': {}},
    '51000||TRIGLYCERIDES||labevents': {'drop': ['nan', 'E'], 'convert': {}},
    '50809||Glucose||labevents': {'drop': ['nan'], 'convert': {}},
    '51267||POIKILOCYTOSIS||labevents': {'drop': ['nan', '11', '22', '1', '21', '0'], 'convert': {}},
    '51137||ANISOCYTOSIS||labevents': {'drop': ['nan', '11', '1', '0.0', '0'], 'convert': {}},
    '50907||Cholesterol||labevents': {'drop': ['nan'], 'convert': {}},
    '50956||LIPASE||labevents': {'drop': ['nan', 'A'], 'convert': {}},
    '50904||Cholesterol||labevents': {'drop': ['nan'], 'convert': {}},
    '50903||CHOLESTEROL RATIO (TOTAL/HDL)||labevents': {'drop': ['nan'], 'convert': {}},
    '50911||CREATINE KINASE, MB ISOENZYME||labevents': {'drop': [], 'convert': {'nan':0}},
    '50852||Hemoglobin||labevents': {'drop': ['nan'], 'convert': {}},
    '51246||MACROCYTES||labevents': {'drop': ['nan', '0', '11', '4', '22'], 'convert': {}},
    '51268||POLYCHROMASIA||labevents': {'drop': ['nan', '0', '12', '1', '0.0'], 'convert': {}},
    '51233||HYPOCHROMIA||labevents': {'drop': ['nan', '0', '4', '1.0'], 'convert': {}},
    '51144||BANDS||labevents': {'drop': ['nan', '-'], 'convert': {}},
    '51252||MICROCYTES||labevents': {'drop': ['nan', '0', '5', '11'], 'convert': {}},
    '50905||Cholesterol||labevents': {'drop': ['nan'], 'convert': {}},
    '50817||Oxygen saturation||labevents': {'drop': ['nan'], 'convert': {}},
    '51613||EAG||labevents': {'drop': ['nan'], 'convert': {}},
    '51082||Creatinine||labevents': {'drop': ['nan'], 'convert': {}},
    '51251||METAMYELOCYTES||labevents': {'drop': ['nan', '-'], 'convert': {}},
    '51255||MYELOCYTES||labevents': {'drop': ['nan', '-'], 'convert': {}},
    #'50979||RED TOP HOLD||labevents': {'drop': ['nan', '0'], 'convert': {}},
    '51143||Lymphocytes||labevents': {'drop': ['nan', '-'], 'convert': {}},
    '50976||PROTEIN, TOTAL||labevents': {'drop': ['nan'], 'convert': {}},
    '51007||URIC ACID||labevents': {'drop': ['nan'], 'convert': {}},
    '50924||FERRITIN||labevents': {'drop': ['nan'], 'convert': {}},
    '50889||C-REACTIVE PROTEIN||labevents': {'drop': ['nan'], 'convert': {}},
    '50930||GLOBULIN||labevents': {'drop': ['nan'], 'convert': {}},
    '50824||Sodium||labevents': {'drop': ['nan'], 'convert': {}},
    '51214||FIBRINOGEN, FUNCTIONAL||labevents': {'drop': ['nan', '___', 'ERROR', 'UNABLE TO REPORT',  '666 VERIFIED BY DILUTION', 'SPECIMEN OLD NOTIFIED ___ @710 ON ___'],
                                                 'convert': {'LESS THAN 35':34, '35:<35':34, '<35':34, '117.4117.4': 117.4}},
    '50952||IRON||labevents': {'drop': ['nan', '-'], 'convert': {}},
    '51260||OVALOCYTES||labevents': {'drop': ['nan', '1','11', '0', '4'], 'convert': {}},
    '50810||Hematocrit||labevents': {'drop': ['nan'], 'convert': {}},
    '50811||Hemoglobin||labevents': {'drop': ['nan'], 'convert': {}},
    '50998||TRANSFERRIN||labevents': {'drop': ['nan'], 'convert': {}},
    '50953||IRON BINDING CAPACITY, TOTAL||labevents': {'drop': ['nan'], 'convert': {}},
    '50986||TACROFK||labevents': {'drop': ['nan'], 'convert': {}},
    '51482||HYALINE CASTS||labevents': {'drop': ['___', 'nan'],
                                        'convert': {'0-2':1, '3-5':4, '<1':0, '6-10':8, '11-20':16, '21-50':36, '>50':51, '0-2.':1, '0--2':1, '14/LPF':14}},
    '50825||TEMPERATURE||labevents': {'drop': ['___', 'nan'],
                                      'convert': {'36.7 C':36.7, '37.2 C':37.2, '37 C':37, '37.1 C':37.1, '36.9 C':36.9, '36.8 C':36.8, '36.6 C':36.6, '37.3 C':37.3, '36.4 C':36.4, '36.5 C':36.5, '36.1 C':36.1, '37.7 C':37.7, '36.3 C':36.3, '37.5 C':37.5, '36.2 C':36.2, '38.3 C':38.3, '38.1 C':38.1, '35.6 C':35.6, '34.5 C':34.5}},
    '51010||VITAMIN B12||labevents': {'drop': ['nan'], 'convert': {}},
    '51009||VANCOMYCIN||labevents': {'drop': ['nan', 'A'], 'convert': {}},
    '50995||THYROXINE (T4), FREE||labevents': {'drop': ['nan'], 'convert': {}},
    '50883||Bilirubin||labevents': {'drop': ['___'], 'convert': {'nan':0}},
    '51102||TOTAL PROTEIN, URINE||labevents': {'drop': ['nan', '___'], 'convert': {}},
    '50806||Chloride||labevents': {'drop': ['nan'], 'convert': {}},
    '50884||Bilirubin||labevents': {'drop': ['nan'], 'convert': {}},
    '51257||NUCLEATED RED CELLS||labevents': {'drop': ['nan', '-'], 'convert': {}},
    '50922||ETHANOL||labevents': {'drop': ['nan'], 'convert': {'NEG':0}},
    '50853||25-OH VITAMIN D||labevents': {'drop': ['nan'], 'convert': {}},
    '51218||GRANULOCYTE COUNT||labevents': {'drop': ['nan', 'ERROR'], 'convert': {'O':0}},
    '51099||PROTEIN/CREATININE RATIO||labevents': {'drop': [], 'convert': {'nan':0.0}},
    '50963||NTPROBNP||labevents': {'drop': ['nan'], 'convert': {}},
    '50981||SALICYLATE||labevents': {'drop': ['nan', 'NEG'], 'convert': {}},
    '51296||TEARDROP CELLS||labevents': {'drop': ['nan', '0', '11', '4'], 'convert': {}},
    '50867||AMYLASE||labevents': {'drop': ['nan'], 'convert': {}},
    '51100||SODIUM, URINE||labevents': {'drop': ['nan'], 'convert': {}},
    '50816||OXYGEN||labevents': {'drop': ['nan', '.', '-'], 'convert': {}},
    '53161||ESTIMATED GFR (CKD- EPI REFIT)||labevents': {'drop': ['nan'], 'convert': {}},
    '51287||SCHISTOCYTES||labevents': {'drop': ['nan', '1', '14', '4'], 'convert': {}},
    '51501||TRANSITIONAL EPITHELIAL CELLS||labevents': {'drop': ['nan', '___'],
                                                        'convert': {'0-2':1, '3-5':4, '<1':0, '6-10':8, '11-20':16, '21-50':36, '>50':51}},
    '52171||RBC MORPHOLOGY||labevents': {'drop': ['nan', '1', '4', '2', '3'], 'convert': {}},
    '50974||PROSTATE SPECIFIC ANTIGEN||labevents': {'drop': [], 'convert': {'nan':0}},
    '51093||OSMOLALITY, URINE||labevents': {'drop': ['nan'], 'convert': {}},
    '51069||Albumin||labevents': {'drop': [ '___'], 'convert': {'nan':0.0}},
    '51070||ALBUMIN/CREATININE, URINE||labevents': {'drop': [], 'convert': {'nan':0}},
    '51283||RETICULOCYTE COUNT, AUTOMATED||labevents': {'drop': ['nan'], 'convert': {'VOID':0.0}},
    '50925||FOLATE||labevents': {'drop': ['nan'], 'convert': {}},
    '50940||HEPATITIS B SURFACE ANTIBODY||labevents': {'drop': ['nan', 'POS', 'NEG', 'POS', 'NEG'], 'convert': {}},
    '50965||PARATHYROID HORMONE||labevents': {'drop': ['nan'], 'convert': {}},
    '50950||IMMUNOGLOBULIN G||labevents': {'drop': ['nan'], 'convert': {}},
    '50935||HAPTOGLOBIN||labevents': {'drop': ['nan'], 'convert': {}},
    '51288||SEDIMENTATION RATE||labevents': {'drop': ['nan'], 'convert': {}},
    '50964||OSMOLALITY, MEASURED||labevents': {'drop': ['nan'], 'convert': {}},
    '50949||IMMUNOGLOBULIN A||labevents': {'drop': ['nan', '-'], 'convert': {}},
    '50900||CARCINOEMBYRONIC ANTIGEN (CEA)||labevents': {'drop': [], 'convert': {'nan':0}},
    '50942||HEPATITIS B VIRUS CORE ANTIBODY||labevents': {'drop': ['nan', 'NEG', 'POS', 'POSITIVE', '0.17'], 'convert': {}},
    '51097||POTASSIUM, URINE||labevents': {'drop': ['nan'], 'convert': {}},
    '50951||IMMUNOGLOBULIN M||labevents': {'drop': ['nan'], 'convert': {}},
    '51104||UREA NITROGEN, URINE||labevents': {'drop': ['nan'], 'convert': {}},
    '51078||Chloride||labevents': {'drop': ['nan'], 'convert': {}},
    '52111||ECHINOCYTES||labevents': {'drop': ['nan', '4', '0', '10'], 'convert': {}},
    '51733||STX2||labevents': {'drop': ['nan'], 'convert': {}},
    '50906||Cholesterol||labevents': {'drop': ['nan'], 'convert': {}},
    '51734||STX3||labevents': {'drop': ['nan'], 'convert': {}},
    '52007||UTX4||labevents': {'drop': ['nan'], 'convert': {}},
    '52006||UTX3||labevents': {'drop': ['nan'], 'convert': {}},
    '52004||UTX1||labevents': {'drop': ['nan'], 'convert': {}},
    '52008||UTX5||labevents': {'drop': ['nan'], 'convert': {}},
    '51732||STX1||labevents': {'drop': ['nan'], 'convert': {}},
    '52010||UTX7||labevents': {'drop': ['nan'], 'convert': {}},
    '52005||UTX2||labevents': {'drop': ['nan'], 'convert': {}},
    '52009||UTX6||labevents': {'drop': ['nan'], 'convert': {}},
    '51282||RETICULOCYTE COUNT, ABSOLUTE||labevents': {'drop': ['nan', ], 'convert': {'VOID':0.0}},
    '51657||HPE1||labevents': {'drop': ['nan'], 'convert': {}},
    '50864||ALPHA-FETOPROTEIN||labevents': {'drop': ['nan'], 'convert': {}},
    '50946||HUMAN CHORIONIC GONADOTROPIN||labevents': {'drop': ['nan'], 'convert': {}},
    '51564||ARCH-1||labevents': {'drop': ['nan'], 'convert': {}},
    '50909||CORTISOL||labevents': {'drop': ['nan'], 'convert': {}},
    '51148||BLASTS||labevents': {'drop': ['nan'], 'convert': {}},
    '51706||PROBLEM SPECIMEN||labevents': {'drop': ['nan', '___', '1', '6', '12', '6.0', '5'], 'convert': {}},
    '51658||HPE2||labevents': {'drop': ['nan'], 'convert': {}},
    '50803||Bicarbonate||labevents': {'drop': ['nan'], 'convert': {}},
    '51176||CD3 CELLS, PERCENT||labevents': {'drop': ['DONE', 'D', 'nan', '___', 'DOE'], 'convert': {'<1':0}},
    '51180||CD4 CELLS, PERCENT||labevents': {'drop': ['DONE', 'D', 'nan'], 'convert': {'<1':0 , '55:CORRECTED RESULTS:PREVIOUSLY REPORTED AS 555:NOTIFY ___':55}},
    '51194||CD8 CELLS, PERCENT||labevents': {'drop': ['DONE', 'D', 'nan', 'DOME', "DONE'"], 'convert': {'<1':0}},
    '51659||HPE3||labevents': {'drop': ['nan'], 'convert': {}},
    '51131||ABSOLUTE CD4 COUNT||labevents': {'drop': ['nan'], 'convert': {}},
    '51130||ABSOLUTE CD3 COUNT||labevents': {'drop': ['nan'], 'convert': {}},
    '51132||ABSOLUTE CD8 COUNT||labevents': {'drop': ['nan'], 'convert': {}},
    '51181||CD4/CD8 RATIO||labevents': {'drop': ['nan'], 'convert': {}},
    '51245||Lymphocytes||labevents': {'drop': ['nan'], 'convert': {}},
    '51300||White blood cell count||labevents': {'drop': ['nan'], 'convert': {}},
    '52769||ABSOLUTE LYMPHOCYTE COUNT||labevents': {'drop': ['nan', '___'], 'convert': {}},
    '51294||TARGET CELLS||labevents': {'drop': ['nan', '0', '23', '11'], 'convert': {}},
    '50914||CYCLOSPORIN||labevents': {'drop': ['nan'], 'convert': {}},
    '50967||PHENYTOIN||labevents': {'drop': ['nan'], 'convert': {}},
    '50994||THYROXINE (T4)||labevents': {'drop': ['nan'], 'convert': {}},
    '51625||FREE KAPPA||labevents': {'drop': ['nan'], 'convert': {}},
    '51627||FREE LAMBDA||labevents': {'drop': ['nan'], 'convert': {}},
    '51626||FREE KAPPA/FREE LAMBDA RATIO||labevents': {'drop': ['nan', 'A'], 'convert': {}},
    '51001||TRIIODOTHYRONINE (T3)||labevents': {'drop': ['nan'], 'convert': {}},
    '51752||VOIDED SPECIMEN||labevents': {'drop': ['nan', '___', '1'], 'convert': {}},
    '51197||ELLIPTOCYTES||labevents': {'drop': ['nan', '0', '8'], 'convert': {}},
    '51196||D-DIMER||labevents': {'drop': ['nan'], 'convert': {}},
    '50927||GAMMA GLUTAMYLTRANSFERASE||labevents': {'drop': ['nan'], 'convert': {}},
    '50915||D-DIMER||labevents': {'drop': ['nan'], 'convert': {}},
    '52264||LYMPHS||labevents': {'drop': ['nan'], 'convert': {}},
    '52272||MONOCYTES||labevents': {'drop': ['nan'], 'convert': {}},
    '52281||POLYS||labevents': {'drop': ['nan'], 'convert': {}},
    '52286||TOTAL NUCLEATED CELLS, CSF||labevents': {'drop': ['nan'], 'convert': {}},
    '52285||RBC, CSF||labevents': {'drop': ['nan'], 'convert': {}},
    '51292||SPHEROCYTES||labevents': {'drop': ['nan', '0'], 'convert': {}},
    '50988||TESTOSTERONE||labevents': {'drop': ['nan'], 'convert': {}},
    '50892||CA-125||labevents': {'drop': ['nan'], 'convert': {}},
    '51228||HEPARIN||labevents': {'drop': ['___'], 'convert': {'nan':0.0, 'GREATER THAN 2.00':2.01, 'LESS THAN 0.04':0.03, '>2.00':2.01}},
    '51479||GRANULAR CASTS||labevents': {'drop': [ '___', 'nan', ],
                                         'convert': {'0-2':1, '0-2 FINE GRANULAR CASTS':1, '3-5 FINE GRANULAR CASTS':4, 'O-2':1, '3-5':4, '<1':0, '6-10':8, '11-20':16, '6/LPF':6, '21-50':36, '>50':51, '0-2 COARSE GRANULAR CASTS':1, '3-5 COARSE GRANULAR CASTS':4, '0-2 COARSE':1, '0-2,COARSE':1, '0-2 COARSE & FINE GRANULAR CASTS':1, 'COARSE 0-2':1, 'RARE COARSE GRANULAR CAST':1, '6-10 COARSE GRANULAR CASTS':8, '0-2COARSE':1}},
    '51134||ACANTHOCYTES||labevents': {'drop': ['nan', '0', '11'], 'convert': {}},
    '52065||TOTAL NUCLEATED CELLS, ASCITES||labevents': {'drop': ['nan'], 'convert': {}},
    '51116||Lymphocytes||labevents': {'drop': ['nan'], 'convert': {}},
    '51120||MONOCYTES||labevents': {'drop': ['nan'], 'convert': {}},
    '51125||POLYS||labevents': {'drop': ['nan'], 'convert': {}},
    '50823||REQUIRED O2||labevents': {'drop': ['nan'], 'convert': {}},
    '51145||BASOPHILIC STIPPLING||labevents': {'drop': ['nan', '0'], 'convert': {}},
    '51127||Red blood cell count||labevents': {'drop': ['nan'], 'convert': {}},
    '50996||TISSUE TRANSGLUTAMINASE AB, IGA||labevents': {'drop': ['nan'], 'convert': {}},
    '50891||C4||labevents': {'drop': ['nan'], 'convert': {}},
    '51802||TOTAL PROTEIN, CSF||labevents': {'drop': ['nan'], 'convert': {}},
    '52024||CREATININE, WHOLE BLOOD||labevents': {'drop': ['nan'], 'convert': {}},
    '51008||VALPROIC ACID||labevents': {'drop': ['nan'], 'convert': {}},
    '51790||GLUCOSE, CSF||labevents': {'drop': ['nan'], 'convert': {}},
    '50890||C3||labevents': {'drop': ['nan'], 'convert': {}},
    '50917||DIGOXIN||labevents': {'drop': [], 'convert': {'nan':0}},
    '51117||MACROPHAGE||labevents': {'drop': ['nan'], 'convert': {}},
    '51749||TREPONEMA PALLIDUM (SYPHILIS) VALUE||labevents': {'drop': ['nan'], 'convert': {}},
    '51259||OTHER CELLS||labevents': {'drop': ['nan', '.'], 'convert': {}},
    '50978||RAPAMYCIN||labevents': {'drop': ['nan'], 'convert': {}},
    '51269||PROMYELOCYTES||labevents': {'drop': ['-', 'nan'], 'convert': {}},
    '51108||URINE VOLUME||labevents': {'drop': ['nan'], 'convert': {}},
    '51094||pH||labevents': {'drop': ['nan'], 'convert': {}},
    '50980||RHEUMATOID FACTOR||labevents': {'drop': [], 'convert': {'nan':0}},
    '51118||MESOTHELIAL CELL||labevents': {'drop': ['nan'], 'convert': {}},
    '50849||TOTAL PROTEIN, ASCITES||labevents': {'drop': ['nan'], 'convert': {}},
    '51660||HPE4||labevents': {'drop': ['nan'], 'convert': {}},
    '52391||TOTAL NUCLEATED CELLS, PLEURAL||labevents': {'drop': ['nan'], 'convert': {}},
    '51446||Lymphocytes||labevents': {'drop': ['nan'], 'convert': {}},
    '51450||MONOS||labevents': {'drop': ['nan'], 'convert': {}},
    '51455||POLYS||labevents': {'drop': ['nan'], 'convert': {}},

    '50856||ACETAMINOPHEN||labevents': {'drop': [], 'convert': {'NEG': 0, 'POS': 1, 'nan': 0}},
    '50827||VENTILATION RATE||labevents': {'drop': ['___'],
                                           'convert': {'16/.': 16, '20/.': 20, '/20.': 30, '18/.': 18, '14/.': 14,
                                                       '/16.': 16, '/18.': 18, '24/.': 24, '22/.': 22, '/12.': 12,
                                                       '30/.': 30, '/14.': 14, '28/.': 28, '/22.': 22, '26/.': 26,
                                                       '/24.': 24, '12/.': 12, '32/.': 32, '/15.': 15, '/10.': 10,
                                                       '/17.': 17, '/30.': 30, '/26.': 26, '/28.': 28, '/25.': 25,
                                                       '/21.': 21, '15/.': 15, '/19.': 19, '34/.': 34, '/23.': 23,
                                                       '10/.': 10, '/13.': 13, '20/0.': 20, '25/.': 25, '/8 .': 8,
                                                       '16/0.': 16, '/27.': 27, '/11.': 11, '18/0.': 18, '35/.': 35,
                                                       '/32.': 32, '24/0.': 24, '22/0.': 22, '30/0.': 30, '14/0.': 14,
                                                       '/9 .': 9, '28/0.': 28, '/29.': 29, '26/0.': 26, '/35.': 35,
                                                       '/34.': 34, '/40.': 40, '/33.': 33, '16/2.': 16, '36/.': 36,
                                                       '20/2.': 20, '32/0.': 32, '12/0.': 12, '/36.': 36, '8/ .': 8,
                                                       '/31.': 31, '16/4.': 16, '14/2.': 14, '9/ .': 9, '17/.': 17,
                                                       '23/.': 23, '18/2.': 18, '15/0.': 15, '14/4.': 14, '20/4.': 20,
                                                       '20/20.': 20, '34/0.': 34, '16/1.': 16, '13/.': 13, '22/2.': 22,
                                                       '24/2.': 24, '14/3.': 14, '/7 .': 7, '14/6.': 14, '/38.': 38,
                                                       '27/.': 27, '20/3.': 20, '14/14.': 14, '25/0.': 25, '24/24.': 24,
                                                       '20/1.': 20, '11/.': 11, '20/5.': 20, '21/.': 21, '18/1.': 18,
                                                       '16/3.': 16, '18/4.': 18, '38/.': 38, '18/18.': 18, '16/16.': 16,
                                                       '19/.': 19, '35/0.': 35, '14/1.': 14, '24/4.': 24, '18/3.': 18,
                                                       '16/5.': 16, '16/6.': 16, '14/10.': 14, '26/2.': 26, '12/4.': 12,
                                                       '0/16.': 16, '12/2.': 12, '24/1.': 24, '30/30.': 30, '22/3.': 33,
                                                       '16/10.': 16, '26/26.': 26, '28/2.': 28, '22/22.': 22,
                                                       '22/4.': 22, '33/.': 33, '24/3.': 24, '/6 .': 6, '14/5.': 14,
                                                       '30/2.': 30, '0/18.': 18, '/37.': 37, '0/22.': 22, '18/5.': 18,
                                                       '18/6.': 18, '0/20.': 20, '20/6.': 20, '24/6.': 24, '28/28.': 28,
                                                       '16/8.': 16, '12/12.': 12, '10/0.': 10, '22/1.': 22, '12/1.': 12,
                                                       '20/10.': 20, '0/12.': 12, '26/4.': 26, '14/8.': 14,
                                                       '14/16.': 16, '0/14.': 14, '30/1.': 30, '22/6.': 22, '20/7.': 20,
                                                       '24/5.': 24, '32/32.': 32, '/5 .': 5, '12/3.': 12, '26/1.': 26,
                                                       '31/.': 31, '40/.': 40, '14/7.': 14, '12/5.': 12, '26/3.': 26,
                                                       '12/8.': 12, '28/4.': 28, '16/18.': 18, '15/3.': 15, '/45.': 45,
                                                       '28/1.': 28, '18/10.': 18, '20/8.': 20, '14/12.': 14,
                                                       '18/20.': 20, '30/4.': 30, '15/5.': 15, '0/15.': 15, '18/7.': 18,
                                                       '28/3.': 28, '29/.': 29, '20/22.': 22, '6/ .': 6, '12/6.': 12,
                                                       '0/26.': 26, '14/15.': 15, '15/2.': 15, '/44.': 44, '16/7.': 16,
                                                       '10/2.': 10, '18/8.': 18, '7/ .': 7, '32/2.': 32, '/39.': 39,
                                                       '14/20.': 20, '22/5.': 22, '30/3.': 30, '22/8.': 22, '/0 .': 0,
                                                       '/42.': 42, '0/19.': 19, '0/24.': 24, '12/10.': 12, '20/12.': 20,
                                                       '0/17.': 17, '5/ .': 5, '26/5.': 26, '16/20.': 20, '16/14.': 16,
                                                       '21/0.': 21, '0/13.': 13, '0/25.': 25, '10/10.': 10, '15/4.': 15,
                                                       '0/28.': 28, '34/2.': 34, '12/13.': 13, '0/10.': 10,
                                                       '25/25.': 25, '0/21.': 21, '23/0.': 23, '0/23.': 23, '15/1.': 15,
                                                       '36/0.': 36, '20/9.': 20, '24/7.': 24, '17/0.': 17, '34/34.': 34,
                                                       '/2 .': 2, '10/5.': 10, '16/9.': 16, '15/15.': 15, '22/10.': 22,
                                                       '15/6.': 15, '16/19.': 19, '18/19.': 19, '/4 .': 4, '/41.': 41,
                                                       '18/12.': 18, '20/24.': 24, '2/ .': 2, '24/8.': 24, '22/23.': 23,
                                                       '10/12.': 12, '16/12.': 16, '22/7.': 22, '25/4.': 25,
                                                       '26/6.': 26, '0/11.': 11, '28/5.': 28, '12/14.': 14, '15/7.': 15,
                                                       '14/19.': 19, '15/8.': 15, '10/4.': 10, '25/2.': 25,
                                                       '20/11.': 20, '32/4.': 32, '24/27.': 27, '22/24.': 24,
                                                       '18/9.': 18, '14/17.': 17, '33/0.': 33, '24/26.': 26,
                                                       '18/23.': 23, '16/22.': 22, '16/17.': 17, '30/5.': 30,
                                                       '14/9.': 14, '/50.': 50, '24/10.': 24, '0/32.': 32, '/.': 0,
                                                       '10/6.': 10, '25/5.': 25, '24/28.': 28, '32/1.': 32, '10/3.': 10,
                                                       '34/1.': 34, '30/32.': 32, '12/7.': 12, '8/0.': 8, '16/25.': 25,
                                                       '18/22.': 22, '30/6.': 30, '22/25.': 25, '16/15.': 16,
                                                       '15/10.': 15, '28/6.': 28, '18/24.': 24, '14/18.': 18,
                                                       '25/3.': 25, '20/16.': 20, '14/22.': 22, '14/24.': 24,
                                                       '10/1.': 10, '12/20.': 20, '0/30.': 30, '20/28.': 28, '0/8.': 8,
                                                       '10/8.': 10, '20/21.': 21, '12/16.': 16, '16/11.': 16,
                                                       '27/0.': 27, '25/1.': 25, '17/17.': 17, '0/9.': 9, '20/15.': 20,
                                                       '22/26.': 26, '39/.': 39, '18/21.': 21, '19/0.': 19,
                                                       '24/30.': 30, '20/23.': 23, '12/18.': 18, '12/17.': 17}},

    '50819||Positive end-expiratory pressure||labevents': {'drop': [], 'convert': {}},
    '50826||TIDAL VOLUME||labevents': {'drop': [], 'convert': {}},
    '51737||STX6||labevents': {'drop': [], 'convert': {}},
    '51663||HPE7||labevents': {'drop': [], 'convert': {}},
    '50908||CK-MB INDEX||labevents': {'drop': [], 'convert': {}},
    '50801||ALVEOLAR-ARTERIAL GRADIENT||labevents': {'drop': [], 'convert': {}},
    '51903||PAN1||labevents': {'drop': [], 'convert': {}},
    '52020||UTX10||labevents': {'drop': [], 'convert': {}},
    '51735||STX4||labevents': {'drop': [], 'convert': {}},
    '51736||STX5||labevents': {'drop': [], 'convert': {}},
    '50815||O2 FLOW||labevents': {'drop': [], 'convert': {}},
    '53174||COV8MC||labevents': {'drop': [], 'convert': {}},
    '53173||COV8IC||labevents': {'drop': [], 'convert': {}},
    '51067||Creatinine||labevents': {'drop': [], 'convert': {}}
}

string_value_convert = {
    '51463||BACTERIA||labevents': {'drop': ['___', 'O9', 'NOT DONE', ],
                                   'convert': {'NEG': 0, 'nan': 0, 'N': 0, 'O\\N': 0, 'O': 0, 'NONE': 0, 'TR': 1,
                                               'RARE': 2, 'R': 2, 'RARE\\': 2, 'FEW': 3, "FEW'": 3, 'F': 3, "F'": 3,
                                               'SMALL': 4, 'SM': 4, 'F-MOD': 5, 'OCCASSIONAL': 6, 'OCCAS': 6, '0CC': 6,
                                               'OCC.': 6, 'OCC': 6, 'MODERATE': 7, 'M': 7, 'MO': 7, 'MOD': 7, 'MOD.': 7,
                                               'MOD-': 7, 'MANY': 8, 'MA': 8, 'LRG': 9, 'LG': 9, }},
    '51512||URINE MUCOUS||labevents': {'drop': ['___', ],
                                       'convert': {'NONE': 0, 'nan': 0, 'RARE': 1, 'FEW': 2, 'FEW]': 2, 'OCC': 3,
                                                   '0CC': 3, 'MOD': 4, 'MANY': 5}},
    '50999||TRICYCLIC ANTIDEPRESSANT SCREEN||labevents': {'drop': ['nan', 'A'], 'convert': {'NEG': 0, 'POS': 1}},
    '51075||BENZODIAZEPINE SCREEN, URINE||labevents': {'drop': ['nan', '-339'], 'convert': {'NEG': 0, 'POS': 1}},
    '51085||HCG, URINE, QUALITATIVE||labevents': {'drop': ['nan'], 'convert': {'NEG': 0, 'POS': 1}},
    '50880||BENZODIAZEPINE SCREEN||labevents': {'drop': ['nan', 'A'], 'convert': {'NEG': 0, 'POS': 1}},
    '50879||BARBITURATE SCREEN||labevents': {'drop': ['nan', '-65'], 'convert': {'NEG': 0, 'POS': 1}},
    ## 여기 위쪽은 원래 value에서 옴
    '52033||SPECIMEN TYPE||labevents': {'drop': ['nan'], 'convert': {'ART.': 1, 'VEN.': 2, 'MIX.': 3, 'CENTRAL VENOUS.':4}},
    '51486||LEUKOCYTES||labevents': {'drop': ['___', '500'], 'convert': {'NEG': 0, 'nan':0, 'N': 0, 'TRACE': 1, 'TR': 1, 'SMALL': 2, 'S': 2, 'SM': 2, 'MOD': 3, 'MD': 3, 'LG': 4,  'LARGE': 4, 'L':4}},
    '51506||URINE APPEARANCE||labevents': {'drop': ['___'], 'convert': {'nan':1, 'Clear':1, 'CL':1, 'CLEAR':1, 'AMBER':1,
                                                                        'SlHazy':2, 'Slcldy':2, 'SLHAZY':2, 'SLCLOUDY':2, 'SL':2, 'S':2, 'SLCLDY':2,
                                                                        'H':3, 'HA':3, 'Cloudy':3, 'CLOUDY':3, 'CLDY':3, 'CLO':3, 'CLOU':3, 'Hazy':3, 'HAZY':3,
                                                                        'TURBID':4, 'BLOODY':4, 'PINK':4, 'RED':4}},
    '51508||URINE COLOR||labevents': {'drop': ['___', 'Other', 'OTHER', 'OPAQUE', 'HAZY', 'REP', '1', 'B', 'E'], 'convert': {'Yellow':0, 'nan':0, 'YELLOW':0, 'YEL':0, 'Y':0, 'YELLO':0, 'YELL':0, 'YELLLOW':0, 'UELLOW':0, 'YRLLOW':0, 'Straw':0, 'STRAW':0, 'STR':0, 'Colorless':0, 'LtAmb':0, 'LTAMBER':0, 'LTAMB':0,
                                                                   'Amber':1, 'AMBER':1, 'AMB':1, 'ANBER':1, 'AMNER':1, 'DLAMB':1, 'A':1, 'AM':1, 'DKAMB':1, 'DkAmb':1, 'DKAMBER':1, 'DKAM':1, 'DKA':1, 'DKYELLOW':1, 'DKAML':1, 'DKYEL':1, 'DKYELLO':1, 'DRKYELLOW':1, 'DARKYELLOW':1,
                                                                   'Orange':2, 'ORANGE':2, 'ORAN':2, 'ORNAGE':2, 'O':2, 'OR':2, 'DK':2,
                                                                   'Brown':3, 'BROWN':3, 'BRO':3, 'BR':3, 'LTBROWN':3, 'DKBROWN':3, 'DKBRWN':3, 'DKMB':3, 'DRKMB':3, 'DKRMB':3, 'TAN':3, 'GREY':3, 'Black':3,
                                                                   'Red':4, 'RED':4, 'RE':4, 'REDD':4, 'R':4, 'Pink':4, 'PINK':4, 'P':4, 'DKRED':4,
                                                                   'Green':5, 'GREEN':5, 'DKGREEN':5, 'Blue':5, 'BLUE':5, 'White':5, 'MAUVE':5}},
    '51466||BLOOD||labevents': {'drop': ['___', '1.020'], 'convert': {'NEG':0, 'nan':0, 'NEGATIVE':0, 'N':0,
                                                                      'TRACE':1, 'TR':1, 'T':1,
                                                                      'SMALL':2, 'SM':2, 'SMA':2, 'S':2,
                                                                      'MODERATE':3, 'MOD':3, 'MO':3, 'M':3,
                                                                      'LARGE':4, 'LG':4, 'LGE':4, 'LRG':4, 'L':4, 'LA':4}},
    '51464||Bilirubin||labevents': {'drop': ['___', 'BEH'], 'convert': {'NEGATIVE':0, 'NEG':0, 'N':0, 'nan':0,
                                                                        'SMALL':1, 'SM':1,
                                                                        'MOD':2, 'MO':2, 'M':2,
                                                                        'LARGE':3, 'LG':3}},
    '51487||NITRITE||labevents': {'drop': ['___'], 'convert': {'NEGATIVE':0, 'NEG':0, 'N':0, 'nan':0,
                                                               'POSITIVE':1, 'POS':1, 'P':1}},
    '51519||YEAST||labevents': {'drop': ['___'], 'convert': {'NONE': 0, 'nan': 0, 'N': 0, 'NEG': 0, 'O': 0, '0': 0,
                                                             'FEW': 1, 'RARE': 1, 'F': 1,
                                                             'OCCASIONAL': 2, 'OCCAS': 2, 'OCC': 2,
                                                             'MODERATE': 3, 'MOD': 3,
                                                             'MANY': 4, 'M': 4}},
    '50933||GREEN TOP HOLD (PLASMA)||labevents': {'drop': ['HOLD.  DISCARD GREATER THAN 4 HOURS OLD.', 'DONE.  DISCARD GREATER THAN 4 HOURS OLD.', '___'], 'convert': {}},
    '50887||BLUE TOP HOLD||labevents': {'drop': ['HOLD.  DISCARD GREATER THAN 24 HRS OLD.', 'DONE.  DISCARD GREATER THAN 24 HRS OLD.', '___'], 'convert': {}},
    '50955||LIGHT GREEN TOP HOLD||labevents': {'drop': ['___'], 'convert': {}},
    '50812||INTUBATED||labevents': {'drop': [], 'convert': {'INTUBATED.': 1, 'NOT INTUBATED.': 0}},
    '51103||UHOLD||labevents': {'drop': ['HOLD.', 'DONE.', '___'], 'convert': {}},
    '51107||URINE TUBE, HELD||labevents': {'drop': ['HOLD.  SPECIMEN TO BE HELD 48 HOURS AND DISCARDED.', '___'], 'convert': {}},
    '50919||EDTA HOLD||labevents': {'drop': ['nan'], 'convert': {}},
    '51092||OPIATE SCREEN, URINE||labevents': {'drop': ['nan'], 'convert': {'NEG': 0, 'POS':1}},
    '51079||COCAINE, URINE||labevents': {'drop': ['nan'], 'convert': {'NEG': 0, 'POS':1}},
    '51071||AMPHETAMINE SCREEN, URINE||labevents': {'drop': ['nan'], 'convert': {'NEG': 0, 'POS':1}},
    '51090||METHADONE, URINE||labevents': {'drop': ['nan'], 'convert': {'NEG': 0, 'POS':1}},
    '51074||BARBITURATE SCREEN, URINE||labevents': {'drop': ['nan'], 'convert': {'NEG': 0, 'POS':1}},
    '50828||VENTILATOR||labevents': {'drop': [], 'convert': {'CONTROLLED.': 0, 'SPONTANEOUS.': 1, 'IMV.': 2}},
    '50941||HEPATITIS B SURFACE ANTIGEN||labevents': {'drop': ['nan', 'NEG', 'POS'], 'convert': {}},
    '50943||HEPATITIS C VIRUS ANTIBODY||labevents': {'drop': ['nan', 'NEG', 'POS'], 'convert': {}},
    '53153||HIV SCREEN||labevents': {'drop': ['nan', '___'], 'convert': {}},
    '50975||PROTEIN ELECTROPHORESIS||labevents': {'drop': ['nan', '-'], 'convert': {}},
    '51989||OXYCODONE||labevents': {'drop': ['nan'], 'convert': {'NEG': 0, 'POS':1}},
    '51462||AMORPHOUS CRYSTALS||labevents': {'drop': ['nan', '___'], 'convert': {'NONE': 0, '0': 0, 'RARE': 1, 'RAE': 1, 'FEW': 1, 'OCC': 2, 'MOD': 3, 'M0D': 3, 'M': 3, 'MANY': 4, 'MAN': 4}},
    '50873||ANTI-NUCLEAR ANTIBODY||labevents': {'drop': ['nan', '___'], 'convert': {}},
    '51865||INFLUENZA A BY PCR||labevents': {'drop': ['nan', 'NEG', 'POS'], 'convert': {}},
    '51873||INFLUENZA B BY PCR||labevents': {'drop': ['nan', 'NEG', 'POS'], 'convert': {}},
    '52023||ASSIST/CONTROL||labevents': {'drop': ['nan'], 'convert': {}},
    '51098||PROT. ELECTROPHORESIS, URINE||labevents': {'drop': ['nan'], 'convert': {}},
    '52425||XUCU||labevents': {'drop': ['nan', 'DONE'], 'convert': {}},
    '51518||WBC CLUMPS||labevents': {'drop': ['nan', '___'], 'convert': {'NONE': 0, 'O': 0, 'RARE': 1, 'FEW': 1, 'FEW SMALL': 2, 'OCC SMALL CLUMPS': 2, 'OCC': 3, 'MOD': 4, 'MANY': 5}},
    '50937||HEPATITIS A VIRUS ANTIBODY||labevents': {'drop': ['nan', '___'], 'convert': {}},
    '51219||H/O SMEAR||labevents': {'drop': ['nan', 'SENT', 'DONE', 'D', 'S', 'SEND', 'AV', 'DIF', '___', 'DIFF', 'SWENT', 'MADE', '33', 'SEMT', 'SENY', 'SEMNT', 'SEN', '37', 'SONE', 'SENTS', 'DENT', 'ENT', 'SNT', 'SEVT', 'AVAI', 'DEONG', 'SNET', 'DEONE', 'SERNT', 'SD', 'DOME', 'COMPLETE', 'SEWNT', 'DEON', 'AVA', 'DONT', 'SSENT', 'SR'], 'convert': {}},
    '51469||CALCIUM OXALATE CRYSTALS||labevents': {'drop': ['nan', 'FEW', 'OCC', 'RARE', 'MOD', 'MANY', 'NONE', '___'], 'convert': {}},
    '51846||CHLAMYDIA TRACHOMATIS||labevents': {'drop': ['nan', 'POS', 'NEG'], 'convert': {}},
    '51879||NEISSERIA GONORRHOEAE||labevents': {'drop': ['nan', 'NEG', 'POS'], 'convert': {}},
    '51980||FENTANYL||labevents': {'drop': ['nan', '___'], 'convert': {}},
    '51748||TREPONEMA PALLIDUM (SYPHILIS) AB||labevents': {'drop': ['nan', '___'], 'convert': {}},
    '50948||IMMUNOFIXATION||labevents': {'drop': ['nan'], 'convert': {}},
    '51089||MARIJUANA||labevents': {'drop': ['nan', 'NEG', 'POS'], 'convert': {}},
    '51933||C. DIFF PCR||labevents': {'drop': ['nan', 'NEG'], 'convert': {}},
    '51956||CDT027||labevents': {'drop': ['nan', '___'], 'convert': {}}}

labevents_str_unit_convert = {
    '51464||Bilirubin||labevents': {'convert': {'nan': 'mg/dL', 'EU/dL': 'mg/dL'}},
    '51463||BACTERIA||labevents': {'convert': {'nan': '/hpf'}},
    '51519||YEAST||labevents': {'convert': {'nan': '/hpf'}},
    '51512||URINE MUCOUS||labevents': {'convert': {'nan': '/hpf'}},
    '51085||HCG, URINE, QUALITATIVE||labevents': {'convert': {'nan': '+/-'}},
    '51462||AMORPHOUS CRYSTALS||labevents': {'convert': {'nan': '/hpf'}},
    '51518||WBC CLUMPS||labevents': {'convert': {'nan': '/hpf'}}}


labevents_float_unit_convert = {
    '51221||Hematocrit||labevents': {'convert': {'nan': '%'}},
    '50912||Creatinine||labevents': {'convert': {'nan': 'mg/dL'}},
    '51265||Platelets||labevents': {'convert': {'nan': 'K/uL'}},
    '51006||Blood urea nitrogen||labevents': {'convert': {'nan': 'mg/dL'}},
    '51222||Hemoglobin||labevents': {'convert': {'nan': 'g/dL'}},
    '50971||Potassium||labevents': {'convert': {'nan': 'mEq/L'}},
    '51301||White blood cell count||labevents': {'convert': {'nan': 'K/uL'}},
    '51249||Mean corpuscular hemoglobin concentration||labevents': {'convert': {'%': 'g/dL', 'nan': 'g/dL'}},
    '51279||Red blood cell count||labevents': {'convert': {'nan': 'm/uL'}},
    '51250||Mean corpuscular volume||labevents': {'convert': {'nan': 'fL'}},
    '51248||Mean corpuscular hemoglobin||labevents': {'convert': {'nan': 'pg'}},
    '51277||RDW||labevents': {'convert': {'nan': '%'}},
    '50983||Sodium||labevents': {'convert': {'nan': 'mEq/L'}},
    '50902||Chloride||labevents': {'convert': {'nan': 'mEq/L'}},
    '50882||Bicarbonate||labevents': {'convert': {'nan': 'mEq/L'}},
    '50868||Anion gap||labevents': {'convert': {'nan': 'mEq/L'}},
    '50931||Glucose||labevents': {'convert': {'nan': 'mg/dL'}},
    '50893||Calcium||labevents': {'convert': {'nan': 'mg/dL'}},
    '50960||Magnesium||labevents': {'convert': {'nan': 'mg/dL'}},
    '50970||Phosphate||labevents': {'convert': {'nan': 'mg/dL'}},
    '50934||H||labevents': {'convert': {'U': 'nan'}},
    '51678||L||labevents': {'convert': {'U': 'nan'}},
    '50947||I||labevents': {'convert': {'U': 'nan'}},
    '52172||RDW-SD||labevents': {'convert': {'nan': 'fL'}},
    '51274||Prothrombin time||labevents': {'convert': {'nan': 'sec'}},
    '51275||Partial thromboplastin time||labevents': {'convert': {'nan': 'sec'}},
    '51498||SPECIFIC GRAVITY||labevents': {'convert': {' ': 'nan'}},
    '50993||THYROID STIMULATING HORMONE||labevents': {'convert': {'uU/ML': 'uIU/mL'}},
    '51613||EAG||labevents': {'convert': {'nan': 'mg/dL'}},
    '50889||C-REACTIVE PROTEIN||labevents': {'convert': {'nan': 'mg/L'}},
    '51099||PROTEIN/CREATININE RATIO||labevents': {'convert': {'Ratio': 'mg/mg'}},
    '53161||ESTIMATED GFR (CKD- EPI REFIT)||labevents': {'convert': {'nan': 'mL/min/1.73m2'}},
    '50974||PROSTATE SPECIFIC ANTIGEN||labevents': {'convert': {'nan': 'ng/mL'}},
    '51070||ALBUMIN/CREATININE, URINE||labevents': {'convert': {'nan': 'mg/g'}},
    '50909||CORTISOL||labevents': {'convert': {'nan': 'ug/dL'}},
    '51196||D-DIMER||labevents': {'convert': {'ng/mL': 'ng/mL FEU'}},
    '50915||D-DIMER||labevents': {'convert': {'ng/mL FEU': 'ng/mL'}},
    '51228||HEPARIN||labevents': {'convert': {'U/mL': 'IU/mL'}},
    '50818||Partial pressure of carbon dioxide||labevents': {'convert': {'mm Hg': 'mmHg'}},
    '50821||PO2||labevents': {'convert': {'mm Hg': 'mmHg'}},
    '50825||TEMPERATURE||labevents': {'convert': {'nan': '°C'}},
}

float_inclusion_dict = {
    # CBC & Hematology
    '51221||Hematocrit||labevents': {'inclusion': [5.0, 70.0], 'decimal': 1},
    '51222||Hemoglobin||labevents': {'inclusion': [3.0, 25.0], 'decimal': 1},
    '51265||Platelets||labevents': {'inclusion': [5, 2000], 'decimal': 0},
    '51301||White blood cell count||labevents': {'inclusion': [0.1, 500.0], 'decimal': 1},
    '51279||Red blood cell count||labevents': {'inclusion': [1.0, 10.0], 'decimal': 2},
    '51249||Mean corpuscular hemoglobin concentration||labevents': {'inclusion': [20.0, 45.0], 'decimal': 1},
    '51250||Mean corpuscular volume||labevents': {'inclusion': [40.0, 150.0], 'decimal': 1},
    '51248||Mean corpuscular hemoglobin||labevents': {'inclusion': [15.0, 50.0], 'decimal': 1},
    '51277||RDW||labevents': {'inclusion': [10.0, 50.0], 'decimal': 1},
    '52172||RDW-SD||labevents': {'inclusion': [15.0, 100.0], 'decimal': 1},

    # Differential Count (%) - 0 is valid here (e.g., no basophils found)
    '51256||Neutrophils||labevents': {'inclusion': [0.0, 100.0], 'decimal': 1},
    '51244||Lymphocytes||labevents': {'inclusion': [0.0, 100.0], 'decimal': 1},
    '51254||Monocytes||labevents': {'inclusion': [0.0, 100.0], 'decimal': 1},
    '51146||Basophils||labevents': {'inclusion': [0.0, 100.0], 'decimal': 1},
    '51200||EOSINOPHILS||labevents': {'inclusion': [0.0, 100.0], 'decimal': 1},

    # Coagulation
    '51237||Prothrombin time||labevents': {'inclusion': [0.5, 20.0], 'decimal': 1},  # Likely INR based on range
    '51274||Prothrombin time||labevents': {'inclusion': [8.0, 150.0], 'decimal': 1},  # Seconds
    '51275||Partial thromboplastin time||labevents': {'inclusion': [15.0, 200.0], 'decimal': 1},

    # Chemistry (Kidney/Electrolytes) - 0 is generally Error
    '50912||Creatinine||labevents': {'inclusion': [0.1, 40.0], 'decimal': 1},  # >40 is extreme failure
    '51006||Blood urea nitrogen||labevents': {'inclusion': [1, 250], 'decimal': 0},
    '50971||Potassium||labevents': {'inclusion': [1.0, 10.0], 'decimal': 1},  # <1 or >10 incompatible with life usually
    '50983||Sodium||labevents': {'inclusion': [100, 180], 'decimal': 0},
    '50902||Chloride||labevents': {'inclusion': [60, 150], 'decimal': 0},
    '50882||Bicarbonate||labevents': {'inclusion': [2, 60], 'decimal': 0},
    '50868||Anion gap||labevents': {'inclusion': [0, 60], 'decimal': 0},
    '50931||Glucose||labevents': {'inclusion': [10, 2500], 'decimal': 0},  # 23200 is error
    '50893||Calcium||labevents': {'inclusion': [2.0, 20.0], 'decimal': 1},
    '50960||Magnesium||labevents': {'inclusion': [0.5, 15.0], 'decimal': 1},
    '50970||Phosphate||labevents': {'inclusion': [0.5, 20.0], 'decimal': 1},

    # Liver Enzymes - Can be very high in failure
    '50861||Alanine aminotransferase||labevents': {'inclusion': [1, 10000], 'decimal': 0},
    '50878||Asparate aminotransferase||labevents': {'inclusion': [1, 10000], 'decimal': 0},
    '50885||Bilirubin||labevents': {'inclusion': [0.1, 80.0], 'decimal': 1},
    '50863||Alkaline phosphate||labevents': {'inclusion': [10, 5000], 'decimal': 0},
    '50862||Albumin||labevents': {'inclusion': [1.0, 6.0], 'decimal': 1},

    # Blood Gas / Acid-Base
    '50820||pH||labevents': {'inclusion': [6.50, 7.80], 'decimal': 2},  # Arterial pH
    '50821||PO2||labevents': {'inclusion': [20, 700], 'decimal': 0},
    '50804||CO2 (ETCO2, PCO2, etc.)||labevents': {'inclusion': [5, 150], 'decimal': 0},  # Total CO2
    '50818||Partial pressure of carbon dioxide||labevents': {'inclusion': [10, 200], 'decimal': 0},  # pCO2
    '50802||BASE EXCESS||labevents': {'inclusion': [-50, 50], 'decimal': 0},  # Can be negative

    # Urine Analysis
    '51491||pH||labevents': {'inclusion': [4.0, 9.0], 'decimal': 1},  # Urine pH
    '51498||SPECIFIC GRAVITY||labevents': {'inclusion': [1.000, 1.060], 'decimal': 3},
    '51478||Glucose||labevents': {'inclusion': [0, 2000], 'decimal': 0},  # Urine Glucose
    '51492||PROTEIN||labevents': {'inclusion': [0, 2000], 'decimal': 0},  # Urine Protein
    '51484||KETONE||labevents': {'inclusion': [0, 200], 'decimal': 0},
    '51514||UROBILINOGEN||labevents': {'inclusion': [0.1, 20.0], 'decimal': 1},
    '51087||LENGTH OF URINE COLLECTION||labevents': {'inclusion': [0, 100], 'decimal': 1},

    # Others / Unknowns (Processed based on stats)
    '50934||H||labevents': {'inclusion': [0, 5000], 'decimal': 0},  # Likely Differential count or markers
    '51678||L||labevents': {'inclusion': [0, 6000], 'decimal': 0},
    '50947||I||labevents': {'inclusion': [0, 100], 'decimal': 0},
    # Stats were all 0, set to standard medical range

    # 0이 생리학적으로 불가능하여 제외한 항목들 (Min > 0)
    '50813||Lactate||labevents': {'inclusion': [0.1, 30.0], 'decimal': 1},
    '50954||Lactate dehydrogenase||labevents': {'inclusion': [10.0, 5000.0], 'decimal': 0},
    '50808||Calcium||labevents': {'inclusion': [0.5, 5.0], 'decimal': 2},
    '50993||THYROID STIMULATING HORMONE||labevents': {'inclusion': [0.001, 200.0], 'decimal': 2},
    '50822||Potassium||labevents': {'inclusion': [1.0, 10.0], 'decimal': 1}, # 0은 오류로 처리, 상한은 10으로 넉넉히 잡음
    '50910||CREATINE KINASE (CK)||labevents': {'inclusion': [5.0, 50000.0], 'decimal': 0}, # Rhabdomyolysis 고려 상한 높게 설정
    '51000||TRIGLYCERIDES||labevents': {'inclusion': [10.0, 5000.0], 'decimal': 0},
    '50809||Glucose||labevents': {'inclusion': [10.0, 2500.0], 'decimal': 0}, # DKA/HHS 고려 상한 높게 설정
    '50907||Cholesterol||labevents': {'inclusion': [10.0, 1500.0], 'decimal': 0},
    '50956||LIPASE||labevents': {'inclusion': [1.0, 30000.0], 'decimal': 0},
    '50904||Cholesterol||labevents': {'inclusion': [1.0, 200.0], 'decimal': 0}, # HDL
    '50903||CHOLESTEROL RATIO (TOTAL/HDL)||labevents': {'inclusion': [0.1, 50.0], 'decimal': 1},
    '50911||CREATINE KINASE, MB ISOENZYME||labevents': {'inclusion': [0.1, 1000.0], 'decimal': 1},
    '50852||Hemoglobin||labevents': {'inclusion': [2.0, 25.0], 'decimal': 1}, # HbA1c로 추정됨 (단위 %)
    '50905||Cholesterol||labevents': {'inclusion': [1.0, 1000.0], 'decimal': 0}, # LDL
    '50817||Oxygen saturation||labevents': {'inclusion': [20.0, 100.0], 'decimal': 0}, # 20 미만은 생존 어려움/오류 가능성
    '51613||EAG||labevents': {'inclusion': [40.0, 600.0], 'decimal': 0},
    '51082||Creatinine||labevents': {'inclusion': [1.0, 2500.0], 'decimal': 0}, # 수치 분포상 umol/L로 추정되어 해당 스케일 적용
    '50976||PROTEIN, TOTAL||labevents': {'inclusion': [1.0, 15.0], 'decimal': 1},
    '50924||FERRITIN||labevents': {'inclusion': [1.0, 50000.0], 'decimal': 0},
    '50889||C-REACTIVE PROTEIN||labevents': {'inclusion': [0.1, 500.0], 'decimal': 1},
    '50930||GLOBULIN||labevents': {'inclusion': [0.5, 10.0], 'decimal': 1},
    '50824||Sodium||labevents': {'inclusion': [100.0, 180.0], 'decimal': 0}, # 생존 가능 범위 고려
    '51214||FIBRINOGEN, FUNCTIONAL||labevents': {'inclusion': [20.0, 2000.0], 'decimal': 0},
    '50952||IRON||labevents': {'inclusion': [1.0, 1000.0], 'decimal': 0},
    '50810||Hematocrit||labevents': {'inclusion': [5.0, 70.0], 'decimal': 1},
    '50811||Hemoglobin||labevents': {'inclusion': [2.0, 25.0], 'decimal': 1}, # Blood Hb
    '50998||TRANSFERRIN||labevents': {'inclusion': [10.0, 800.0], 'decimal': 0},
    '50953||IRON BINDING CAPACITY, TOTAL||labevents': {'inclusion': [10.0, 1000.0], 'decimal': 0},
    '50986||TACROFK||labevents': {'inclusion': [0.1, 100.0], 'decimal': 1},

    # 0이 유효한 값인 항목들 (세포 카운트, 소변 검사, 미검출 등)
    '52135||IMMATURE GRANULOCYTES||labevents': {'inclusion': [0.0, 100.0], 'decimal': 1},
    '51516||White blood cell count||labevents': {'inclusion': [0.0, 1000.0], 'decimal': 1}, # 단위 #/hpf (체액/소변 등)
    '51493||Red blood cell count||labevents': {'inclusion': [0.0, 5000.0], 'decimal': 1}, # 단위 #/hpf
    '51476||EPITHELIAL CELLS||labevents': {'inclusion': [0.0, 500.0], 'decimal': 0},
    '51003||Troponin-T||labevents': {'inclusion': [0.0, 50.0], 'decimal': 2}, # 0.00 (Undetectable) 가능
    '51266||PLATELET SMEAR||labevents': {'inclusion': [0.0, 100.0], 'decimal': 0},
    '51144||BANDS||labevents': {'inclusion': [0.0, 100.0], 'decimal': 1},
    '51251||METAMYELOCYTES||labevents': {'inclusion': [0.0, 100.0], 'decimal': 1},
    '51255||MYELOCYTES||labevents': {'inclusion': [0.0, 100.0], 'decimal': 1},
    '51143||Lymphocytes||labevents': {'inclusion': [0.0, 100.0], 'decimal': 1},
    '51007||URIC ACID||labevents': {'inclusion': [0.0, 30.0], 'decimal': 1}, # 0.0에 가까운 저수치는 드물지만 이론상 가능
    '51482||HYALINE CASTS||labevents': {'inclusion': [0.0, 500.0], 'decimal': 0},

    # 1. Vital Signs & Basic Measurements (0 is error)
    '50825||TEMPERATURE||labevents': {'inclusion': [14.0, 45.0], 'decimal': 1},  # 0.0/57.0 removed
    '50816||OXYGEN||labevents': {'inclusion': [20.0, 100.0], 'decimal': 0},
    # % saturation, <20 incompatible with life usually, >100 error
    '50819||Positive end-expiratory pressure||labevents': {'inclusion': [0.0, 40.0], 'decimal': 0}, #!??
    # PEEP can be 0 (ZEEP)
    '50826||TIDAL VOLUME||labevents': {'inclusion': [100.0, 2000.0], 'decimal': 0}, #!??
    # 0 or >2000 unlikely for spontaneous/vent

    # 2. Electrolytes & Metabolites (Physiologically cannot be 0)
    '50806||Chloride||labevents': {'inclusion': [50.0, 160.0], 'decimal': 0},  # 1.9 and 405 removed
    '51078||Chloride||labevents': {'inclusion': [0.0, 500.0], 'decimal': 0},  # Urine chloride can vary widely
    '51100||SODIUM, URINE||labevents': {'inclusion': [0.0, 1000.0], 'decimal': 0},
    '51097||POTASSIUM, URINE||labevents': {'inclusion': [0.0, 500.0], 'decimal': 0},
    '51104||UREA NITROGEN, URINE||labevents': {'inclusion': [0.0, 10000.0], 'decimal': 0},

    # 3. Liver & Kidney Function (Serum 0 is error)
    '50883||Bilirubin||labevents': {'inclusion': [0.01, 70.0], 'decimal': 1},  # Total Bilirubin
    '50884||Bilirubin||labevents': {'inclusion': [0.0, 30.0], 'decimal': 1},  # Direct/Indirect
    '51069||Albumin||labevents': {'inclusion': [0.5, 10.0], 'decimal': 1},  # Serum Albumin. Max 3629 is error.
    '53161||ESTIMATED GFR (CKD- EPI REFIT)||labevents': {'inclusion': [0.0, 300.0], 'decimal': 0},

    # 4. Proteins & Enzymes
    '51102||TOTAL PROTEIN, URINE||labevents': {'inclusion': [0.0, 30000.0], 'decimal': 0},
    # 19900 possible in heavy proteinuria
    '51099||PROTEIN/CREATININE RATIO||labevents': {'inclusion': [0.0, 700.0], 'decimal': 2},
    '51070||ALBUMIN/CREATININE, URINE||labevents': {'inclusion': [0.0, 150000.0], 'decimal': 1},
    '50867||AMYLASE||labevents': {'inclusion': [0.0, 50000.0], 'decimal': 0},  # Pancreatitis can spike high
    '50974||PROSTATE SPECIFIC ANTIGEN||labevents': {'inclusion': [0.0, 20000.0], 'decimal': 2},
    # High max maintained for cancer
    '50900||CARCINOEMBYRONIC ANTIGEN (CEA)||labevents': {'inclusion': [0.0, 50000.0], 'decimal': 1},

    # 5. Hematology & Cells
    '51218||GRANULOCYTE COUNT||labevents': {'inclusion': [0.0, 500000.0], 'decimal': 0},
    '51257||NUCLEATED RED CELLS||labevents': {'inclusion': [0.0, 2000.0], 'decimal': 1},
    '51283||RETICULOCYTE COUNT, AUTOMATED||labevents': {'inclusion': [0.0, 100.0], 'decimal': 1},
    '51501||TRANSITIONAL EPITHELIAL CELLS||labevents': {'inclusion': [0.0, 1000.0], 'decimal': 0},
    '51288||SEDIMENTATION RATE||labevents': {'inclusion': [0.0, 200.0], 'decimal': 0},  # ESR

    # 6. Hormones & Vitamins
    '50995||THYROXINE (T4), FREE||labevents': {'inclusion': [0.01, 20.0], 'decimal': 2},  # Min 0.1
    '51010||VITAMIN B12||labevents': {'inclusion': [0.0, 10000.0], 'decimal': 0},
    '50853||25-OH VITAMIN D||labevents': {'inclusion': [0.0, 300.0], 'decimal': 0},
    '50925||FOLATE||labevents': {'inclusion': [0.0, 100.0], 'decimal': 1},
    '50965||PARATHYROID HORMONE||labevents': {'inclusion': [0.0, 5000.0], 'decimal': 0},
    '50963||NTPROBNP||labevents': {'inclusion': [0.0, 150000.0], 'decimal': 0},  # Heart failure marker

    # 7. Drugs & Toxicology (0 is valid "Not Detected")
    '51009||VANCOMYCIN||labevents': {'inclusion': [0.0, 200.0], 'decimal': 1},  # 706 is likely error
    '50922||ETHANOL||labevents': {'inclusion': [0.0, 1000.0], 'decimal': 0},
    '50981||SALICYLATE||labevents': {'inclusion': [0.0, 200.0], 'decimal': 1},

    # 8. Immunology & Serology
    '50950||IMMUNOGLOBULIN G||labevents': {'inclusion': [0.0, 20000.0], 'decimal': 0},
    '50949||IMMUNOGLOBULIN A||labevents': {'inclusion': [0.0, 10000.0], 'decimal': 0},
    '50951||IMMUNOGLOBULIN M||labevents': {'inclusion': [0.0, 10000.0], 'decimal': 0},
    '50940||HEPATITIS B SURFACE ANTIBODY||labevents': {'inclusion': [0.0, 1000.0], 'decimal': 1},
    '50935||HAPTOGLOBIN||labevents': {'inclusion': [0.0, 1000.0], 'decimal': 0},

    # 9. Others / Technical
    '51093||OSMOLALITY, URINE||labevents': {'inclusion': [0.0, 2000.0], 'decimal': 0},
    '50964||OSMOLALITY, MEASURED||labevents': {'inclusion': [100.0, 600.0], 'decimal': 0},  # Serum usually tight range
    '50906||Cholesterol||labevents': {'inclusion': [10.0, 1000.0], 'decimal': 0},  # Min 4 is suspiciously low, set 10

    # Rare/Technical variables (High variance allowed but trimmed extremes)
    '51733||STX2||labevents': {'inclusion': [-50.0, 600.0], 'decimal': 0},
    '51734||STX3||labevents': {'inclusion': [0.0, 600.0], 'decimal': 1},
    '52007||UTX4||labevents': {'inclusion': [-1000.0, 1000.0], 'decimal': 0},  # Negative values exist
    '52006||UTX3||labevents': {'inclusion': [0.0, 1000000.0], 'decimal': 0},

# 1. Unknown/Technical Measures (Coordinates/Vectors/Scores) - Allow negatives
    '52004||UTX1||labevents': {'inclusion': [-700.0, 400.0], 'decimal': 0},
    '52005||UTX2||labevents': {'inclusion': [-1500.0, 600.0], 'decimal': 0},
    '52008||UTX5||labevents': {'inclusion': [-500.0, 700.0], 'decimal': 0},
    '52009||UTX6||labevents': {'inclusion': [-400.0, 400.0], 'decimal': 0},
    '52010||UTX7||labevents': {'inclusion': [-800.0, 600.0], 'decimal': 0},
    '51732||STX1||labevents': {'inclusion': [0.0, 100.0], 'decimal': 2},
    '51564||ARCH-1||labevents': {'inclusion': [0.0, 50.0], 'decimal': 2},   # 95% is 0.23, Max 2116 likely error/outlier
    '51657||HPE1||labevents': {'inclusion': [0.0, 50.0], 'decimal': 2},     # 95% is 0.5, Max 6311 likely error
    '51658||HPE2||labevents': {'inclusion': [0.0, 2000.0], 'decimal': 1},   # 95% is 705

    # 2. Tumor Markers & Hormones (Can represent pathology with very high values)
    '50864||ALPHA-FETOPROTEIN||labevents': {'inclusion': [0.0, 2000000.0], 'decimal': 1}, # Cancer marker can be very high
    '50946||HUMAN CHORIONIC GONADOTROPIN||labevents': {'inclusion': [0.0, 2000000.0], 'decimal': 0}, # Pregnancy/Cancer
    '50909||CORTISOL||labevents': {'inclusion': [0.0, 200.0], 'decimal': 1}, # ug/dL unit. Max 2807 is likely unit error(nmol/L). Cap at 200.

    # 3. Hematology (Percentages)
    '51148||BLASTS||labevents': {'inclusion': [0.0, 100.0], 'decimal': 0},  # % cannot exceed 100
    '51176||CD3 CELLS, PERCENT||labevents': {'inclusion': [0.0, 100.0], 'decimal': 0}, # Max 520 is error
    '51180||CD4 CELLS, PERCENT||labevents': {'inclusion': [0.0, 100.0], 'decimal': 0},

    # 4. Electrolytes (Physiologically critical)
    '50803||Bicarbonate||labevents': {'inclusion': [2.0, 60.0], 'decimal': 0}, # 0 is impossible. High alkalosis rarely >50-60.

    # 세포 비율 (Percentage) - 0~100% 범위, 소수점 1자리
    '51194||CD8 CELLS, PERCENT||labevents': {'inclusion': [0, 100], 'decimal': 1},
    '51245||Lymphocytes||labevents': {'inclusion': [0, 100], 'decimal': 1},
    '52264||LYMPHS||labevents': {'inclusion': [0, 100], 'decimal': 1},
    '52272||MONOCYTES||labevents': {'inclusion': [0, 100], 'decimal': 1},
    '52281||POLYS||labevents': {'inclusion': [0, 100], 'decimal': 1},
    '51116||Lymphocytes||labevents': {'inclusion': [0, 100], 'decimal': 1},
    '51120||MONOCYTES||labevents': {'inclusion': [0, 100], 'decimal': 1},
    '51125||POLYS||labevents': {'inclusion': [0, 100], 'decimal': 1},
    '51117||MACROPHAGE||labevents': {'inclusion': [0, 100], 'decimal': 1},
    '51259||OTHER CELLS||labevents': {'inclusion': [0, 100], 'decimal': 1},
    '51269||PROMYELOCYTES||labevents': {'inclusion': [0, 100], 'decimal': 1},
    '51118||MESOTHELIAL CELL||labevents': {'inclusion': [0, 100], 'decimal': 1},

    # 혈액 내 절대 세포 수 (Absolute Counts) - 0 제외(기기 오류 간주), 상한은 95%tile 고려하여 조정, 정수
    '51131||ABSOLUTE CD4 COUNT||labevents': {'inclusion': [1, 5000], 'decimal': 0},
    '51130||ABSOLUTE CD3 COUNT||labevents': {'inclusion': [10, 8000], 'decimal': 0},
    '51132||ABSOLUTE CD8 COUNT||labevents': {'inclusion': [1, 5000], 'decimal': 0},
    '52769||ABSOLUTE LYMPHOCYTE COUNT||labevents': {'inclusion': [10, 10000], 'decimal': 0},
    '51300||White blood cell count||labevents': {'inclusion': [0.1, 200.0], 'decimal': 1},  # 백혈병 등 고려 상한 높게, 소수점 1

    # 비율 및 기타 수치
    '51659||HPE3||labevents': {'inclusion': [0.01, 3.0], 'decimal': 2},
    '51181||CD4/CD8 RATIO||labevents': {'inclusion': [0.01, 20.0], 'decimal': 2},
    '51626||FREE KAPPA/FREE LAMBDA RATIO||labevents': {'inclusion': [0.01, 500.0], 'decimal': 2},

    # 약물 농도 (Therapeutic Drugs) - 0 제외
    '50914||CYCLOSPORIN||labevents': {'inclusion': [1.0, 2000.0], 'decimal': 0},
    '50967||PHENYTOIN||labevents': {'inclusion': [0.1, 100.0], 'decimal': 1},
    '51008||VALPROIC ACID||labevents': {'inclusion': [1.0, 200.0], 'decimal': 0},
    '50917||DIGOXIN||labevents': {'inclusion': [0.1, 10.0], 'decimal': 2},
    '50978||RAPAMYCIN||labevents': {'inclusion': [0.1, 50.0], 'decimal': 1},
    '51228||HEPARIN||labevents': {'inclusion': [0.01, 3.0], 'decimal': 2},

    # 호르몬 및 단백질 (Hormones & Proteins)
    '50994||THYROXINE (T4)||labevents': {'inclusion': [0.1, 50.0], 'decimal': 1},
    '51001||TRIIODOTHYRONINE (T3)||labevents': {'inclusion': [10, 600], 'decimal': 0},
    '50988||TESTOSTERONE||labevents': {'inclusion': [1, 2000], 'decimal': 0},
    '51625||FREE KAPPA||labevents': {'inclusion': [0.1, 5000.0], 'decimal': 1},  # Myeloma 등 고려 상한 높게
    '51627||FREE LAMBDA||labevents': {'inclusion': [0.1, 2000.0], 'decimal': 1},
    '50892||CA-125||labevents': {'inclusion': [1, 10000], 'decimal': 0},
    '50996||TISSUE TRANSGLUTAMINASE AB, IGA||labevents': {'inclusion': [0, 200], 'decimal': 1},
    '50980||RHEUMATOID FACTOR||labevents': {'inclusion': [0, 1000], 'decimal': 0},

    # 보체 및 효소 (Complements & Enzymes)
    '50891||C4||labevents': {'inclusion': [1, 150], 'decimal': 0},
    '50890||C3||labevents': {'inclusion': [1, 400], 'decimal': 0},
    '50927||GAMMA GLUTAMYLTRANSFERASE||labevents': {'inclusion': [1, 5000], 'decimal': 0},  # 간부전 등 고려
    '50915||D-DIMER||labevents': {'inclusion': [10, 80000], 'decimal': 0},  # DIC/Covid 등 고려

    # 체액 검사 (Body Fluids: CSF, Ascites) - 정상적으로 0일 수 있음
    '52286||TOTAL NUCLEATED CELLS, CSF||labevents': {'inclusion': [0, 10000], 'decimal': 1},
    '52285||RBC, CSF||labevents': {'inclusion': [0, 500000], 'decimal': 0},  # Traumatic tap 고려
    '52065||TOTAL NUCLEATED CELLS, ASCITES||labevents': {'inclusion': [0, 50000], 'decimal': 0},
    '51127||Red blood cell count||labevents': {'inclusion': [0, 1000000], 'decimal': 0},  # 체액 내 RBC
    '51802||TOTAL PROTEIN, CSF||labevents': {'inclusion': [1, 1000], 'decimal': 0},
    '51790||GLUCOSE, CSF||labevents': {'inclusion': [5, 600], 'decimal': 0},

    # 소변 및 기타 (Urine & Others)
    '51479||GRANULAR CASTS||labevents': {'inclusion': [0, 1000], 'decimal': 0},
    '51108||URINE VOLUME||labevents': {'inclusion': [0, 10000], 'decimal': 0},  # 55L는 오류
    '51094||pH||labevents': {'inclusion': [4.0, 9.0], 'decimal': 1},  # 생리학적 소변 pH 범위 고려 (1.0, 11.0은 오류 가능성 높음)

    # 기타 화학
    '52024||CREATININE, WHOLE BLOOD||labevents': {'inclusion': [0.1, 30.0], 'decimal': 2},
    '50823||REQUIRED O2||labevents': {'inclusion': [21, 100], 'decimal': 0},  # Room air 21% 미만은 불가능
    '51749||TREPONEMA PALLIDUM (SYPHILIS) VALUE||labevents': {'inclusion': [0, 20.0], 'decimal': 2},

    # 체액 화학 검사 (Body Fluid Chemistry)
    '50849||TOTAL PROTEIN, ASCITES||labevents': {'inclusion': [0.1, 15.0], 'decimal': 1},

    # 전기영동 등 특수 검사 (Electrophoresis/Special)
    '51660||HPE4||labevents': {'inclusion': [0.001, 60.0], 'decimal': 3},

    # 흉수 세포 검사 (Pleural Fluid Cells) - 0 포함
    '52391||TOTAL NUCLEATED CELLS, PLEURAL||labevents': {'inclusion': [0, 100000], 'decimal': 0},

    # 흉수 세포 분획 (Pleural Fluid Differential) - 0~100%
    '51446||Lymphocytes||labevents': {'inclusion': [0, 100], 'decimal': 1},
    '51450||MONOS||labevents': {'inclusion': [0, 100], 'decimal': 1},
    '51455||POLYS||labevents': {'inclusion': [0, 100], 'decimal': 1},

    # [Blood Counts] - 0은 오류로 간주하여 0.01부터 시작 (Agarnulocytosis라도 완전 0은 드묾)
    '52075||ABSOLUTE NEUTROPHIL COUNT||labevents': {'inclusion': [0.01, 100.0], 'decimal': 2},  # 95%가 14, Max 880은 너무 큼, 백혈병 등 고려해도 100 정도 컷
    '52073||ABSOLUTE EOSINOPHIL COUNT||labevents': {'inclusion': [0.01, 60.0], 'decimal': 2},   # Max 56.5는 호산구 증가증으로 가능
    '52074||ABSOLUTE MONOCYTE COUNT||labevents': {'inclusion': [0.01, 120.0], 'decimal': 2},    # Max 116 수용
    '51133||Lymphocytes||labevents': {'inclusion': [0.01, 650.0], 'decimal': 2},                # Max 629 수용 (CLL 등 고려)
    '52069||ABSOLUTE BASOPHIL COUNT||labevents': {'inclusion': [0.01, 35.0], 'decimal': 2},     # Max 31.9 수용
    '51282||RETICULOCYTE COUNT, ABSOLUTE||labevents': {'inclusion': [0.01, 5.0], 'decimal': 2}, # 95% 0.2, Max 2.5

    # [Toxicology] - 약물 농도 0은 '검출 안됨'으로 유효한 정보일 수 있어 0 포함
    '50856||ACETAMINOPHEN||labevents': {'inclusion': [0.0, 700.0], 'decimal': 1},               # Max 643 수용

    # [Vitals & Ventilator] - 호흡수 0은 무호흡/기기오류.
    '50827||VENTILATION RATE||labevents': {'inclusion': [2.0, 60.0], 'decimal': 0},             # 60회 이상은 기계적 한계 근처
    '50815||O2 FLOW||labevents': {'inclusion': [0.0, 80.0], 'decimal': 1},                      # Max 800은 오류(High Flow도 보통 60L, 80L max)

    # [Technical Codes/Indices] - STX, HPE 등은 장비 내부 코드나 Index로 추정. 음수 허용.
    '51737||STX6||labevents': {'inclusion': [-200.0, 200.0], 'decimal': 0},
    '51663||HPE7||labevents': {'inclusion': [0.0, 230.0], 'decimal': 3},                       # 값이 작으므로 소수점 3자리
    '51903||PAN1||labevents': {'inclusion': [0.0, 2600.0], 'decimal': 0},
    '52020||UTX10||labevents': {'inclusion': [-250.0, 100.0], 'decimal': 0},
    '51735||STX4||labevents': {'inclusion': [-100.0, 300.0], 'decimal': 0},
    '51736||STX5||labevents': {'inclusion': [-110.0, 130.0], 'decimal': 0},
    '53174||COV8MC||labevents': {'inclusion': [0.1, 0.3], 'decimal': 3},                       # 범위가 매우 좁음 (0.11~0.23)
    '53173||COV8IC||labevents': {'inclusion': [20.0, 40.0], 'decimal': 2},

    # [Chemistry & Others]
    '50908||CK-MB INDEX||labevents': {'inclusion': [0.0, 100.0], 'decimal': 1},                 # Index(%) 이므로 100까지. 0은 정상 가능
    '51196||D-DIMER||labevents': {'inclusion': [0.0, 25000.0], 'decimal': 0},                   # Max 21600 수용 (DIC시 매우 높음)
    '50801||ALVEOLAR-ARTERIAL GRADIENT||labevents': {'inclusion': [0.0, 800.0], 'decimal': 0},  # 이론적 Max 근처
    '51067||Creatinine||labevents': {'inclusion': [10.0, 5000.0], 'decimal': 1},
}


convert_key_float = {
    '50810||Hematocrit||labevents':{'key':'51221||Hematocrit||labevents', 'unit':'%', 'convert':lambda x: x * 1.0},
    '52024||CREATININE, WHOLE BLOOD||labevents':{'key':'50912||Creatinine||labevents', 'unit':'mg/dL', 'convert':lambda x: x * 1.0},
    '50811||Hemoglobin||labevents':{'key':'51222||Hemoglobin||labevents', 'unit':'g/dL', 'convert':lambda x: x * 1.0},
    '50822||Potassium||labevents':{'key':'50971||Potassium||labevents', 'unit':'mEq/L', 'convert':lambda x: x * 1.0},
    '51300||White blood cell count||labevents':{'key':'51301||White blood cell count||labevents', 'unit':'K/uL', 'convert':lambda x: x * 1.0},
    '50824||Sodium||labevents':{'key':'50983||Sodium||labevents', 'unit':'mEq/L', 'convert':lambda x: x * 1.0},
    '50806||Chloride||labevents':{'key':'50902||Chloride||labevents', 'unit':'mEq/L', 'convert':lambda x: x * 1.0},
    '50803||Bicarbonate||labevents':{'key':'50882||Bicarbonate||labevents', 'unit':'mEq/L', 'convert':lambda x: x * 1.0},
    '50809||Glucose||labevents':{'key':'50931||Glucose||labevents', 'unit':'mg/dL', 'convert':lambda x: x * 1.0},

    # key 이름이 부적절하여 이름(+unit)만 변경하는 애들
    '50808||Calcium||labevents':{'key':'50808||Calcium-ionized||labevents', 'unit':'mmol/L', 'convert':lambda x: x},
    '51237||Prothrombin time||labevents':{'key':'51237||PT INR||labevents', 'unit':'nan', 'convert':lambda x: x * 1.0},
    '50885||Bilirubin||labevents':{'key':'50885||Bilirubin, Total||labevents', 'unit':'mg/dL', 'convert':lambda x: x * 1.0},
    '50883||Bilirubin||labevents': {'key': '50883||Bilirubin, Direct||labevents', 'unit': 'mg/dL', 'convert': lambda x: x * 1.0},
    '50884||Bilirubin||labevents': {'key': '50884||Bilirubin, Indirect||labevents', 'unit': 'mg/dL', 'convert': lambda x: x * 1.0},
    '51069||Albumin||labevents':{'key':'51069||Albumin (urine)||labevents', 'unit':'mg/dL', 'convert':lambda x: x * 1.0},
    '51491||pH||labevents':{'key':'51491||pH (urine)||labevents', 'unit':'units', 'convert':lambda x: x * 1.0},
    '51478||Glucose||labevents':{'key':'51478||Glucose (urine)||labevents', 'unit':'mg/dL', 'convert':lambda x: x * 1.0},
    '51492||PROTEIN||labevents':{'key':'51492||PROTEIN (urine)||labevents', 'unit':'mg/dL', 'convert':lambda x: x * 1.0},
    '51484||KETONE||labevents':{'key':'51484||KETONE (urine)||labevents', 'unit':'mg/dL', 'convert':lambda x: x * 1.0},
    '51514||UROBILINOGEN||labevents':{'key':'51514||UROBILINOGEN (urine)||labevents', 'unit':'mg/dL', 'convert':lambda x: x * 1.0},
    '51516||White blood cell count||labevents':{'key':'51516||White blood cell count (urine)||labevents', 'unit':'#/hpf', 'convert':lambda x: x * 1.0},
    '51493||Red blood cell count||labevents':{'key':'51493||Red blood cell count (urine)||labevents', 'unit':'#/hpf', 'convert':lambda x: x * 1.0},
    '51476||EPITHELIAL CELLS||labevents':{'key':'51476||EPITHELIAL CELLS (urine)||labevents', 'unit':'#/hpf', 'convert':lambda x: x * 1.0},
    '50907||Cholesterol||labevents':{'key':'50907||Cholesterol, Total||labevents', 'unit':'mg/dL', 'convert':lambda x: x * 1.0},
    '50904||Cholesterol||labevents':{'key':'50904||Cholesterol, HDL||labevents', 'unit':'mg/dL', 'convert':lambda x: x * 1.0},
    '50905||Cholesterol||labevents':{'key':'50905||Cholesterol, LDL, Calculated||labevents', 'unit':'mg/dL', 'convert':lambda x: x * 1.0},
    '50906||Cholesterol||labevents':{'key':'50906||Cholesterol, LDL, Measured||labevents', 'unit':'mg/dL', 'convert':lambda x: x * 1.0},
    '50852||Hemoglobin||labevents':{'key':'50852||% Hemoglobin A1c||labevents', 'unit':'%', 'convert':lambda x: x * 1.0},
    '51082||Creatinine||labevents':{'key':'51082||Creatinine (urine)||labevents', 'unit':'mg/dL', 'convert':lambda x: x * 1.0},
    '51482||HYALINE CASTS||labevents':{'key':'51482||HYALINE CASTS (urine)||labevents', 'unit':'#/lpf', 'convert':lambda x: x * 1.0},
    '51099||PROTEIN/CREATININE RATIO||labevents':{'key':'51099||PROTEIN/CREATININE RATIO (urine)||labevents', 'unit':'mg/mg', 'convert':lambda x: x * 1.0},
    '51501||TRANSITIONAL EPITHELIAL CELLS||labevents':{'key':'51501||TRANSITIONAL EPITHELIAL CELLS (urine)||labevents', 'unit':'#/hpf', 'convert':lambda x: x * 1.0},
    '51078||Chloride||labevents':{'key':'51078||Chloride (urine)||labevents', 'unit':'mEq/L', 'convert':lambda x: x * 1.0},
    '51245||Lymphocytes||labevents':{'key':'51244||Lymphocytes||labevents', 'unit':'%', 'convert':lambda x: x * 1.0},

    # 변환 타겟(key 에 있는 이름)이 위에서 이름이 변경된 애들인 것
    '51094||pH||labevents':{'key':'51491||pH (urine)||labevents', 'unit':'units', 'convert':lambda x: x * 1.0},
    '51102||TOTAL PROTEIN, URINE||labevents':{'key':'51492||PROTEIN (urine)||labevents', 'unit':'mg/dL', 'convert':lambda x: x * 1.0},

    '51133||Lymphocytes||labevents':{'key':'51133||ABSOLUTE LYMPHOCYTE COUNT||labevents', 'unit':'K/uL', 'convert':lambda x: x * 1.0},
    '52769||ABSOLUTE LYMPHOCYTE COUNT||labevents':{'key':'51133||ABSOLUTE LYMPHOCYTE COUNT||labevents', 'unit':'K/uL', 'convert':lambda x: x / 1000.0}

}
