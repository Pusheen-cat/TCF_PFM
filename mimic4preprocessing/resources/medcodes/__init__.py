"""
MedCodes (vendored subset)
==========================
Only the ICD-10 -> ICD-9 code map (`icd10to9dict`) is retained: it is the sole
part of the upstream `medcodes` package used by the MIMIC-IV diagnosis
extraction (see `mimic4preprocessing/mimic4csv.py`). The upstream drug (ATC)
classification and the comorbidity / ICD-description tables were removed as unused.
"""
from .diagnoses import icd10to9dict
