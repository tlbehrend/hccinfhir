import pytest
import importlib.resources
from hccinfhir.filter import apply_filter
from hccinfhir.extractor import extract_sld_list
import json

# Load an array of ServiceLevelData objects
def load_sample_eob(casenum=2):
   with importlib.resources.open_text('hccinfhir.samples', 
                                      f'sample_eob_{casenum}.json') as f:
       return json.load(f)
   
def load_sample_eob_list():
   output = []
   with importlib.resources.open_text('hccinfhir.samples', 
                                      f'sample_eob_200.ndjson') as f:
        for line in f:
            eob_data = json.loads(line)
            output.append(eob_data)
   for casenum in range(1, 4):
       eob_data = load_sample_eob(casenum)
       output.append(eob_data)
   return output

def load_sample_837(casenum=0):
    with importlib.resources.open_text('hccinfhir.samples', 
                                     f'sample_837_{casenum}.txt') as f:
        return f.read()
    
def load_sample_837_list():
    output = []
    for casenum in range(0, 11):
        eob_data = load_sample_837(casenum)
        output.append(eob_data)
    return output

def test_apply_filter_eob():

    eob_list = load_sample_eob_list()
    sld_list = extract_sld_list(eob_list)    
    filtered_sld_list = apply_filter(sld_list)
    
    assert len(sld_list) == 204
    # after the filtering is applied, we have a lot less ServiceLevelData objects
    assert len(filtered_sld_list) == 15

    filtered_sld_list = apply_filter(sld_list, professional_cpt=set(['E0570']))
    
    assert len(filtered_sld_list) == 13

def test_apply_filter_837():

    x12_list = load_sample_837_list()
    sld_list = extract_sld_list(x12_list, format='837')    
    filtered_sld_list = apply_filter(sld_list)
    
    assert len(sld_list) == 39
    assert len(filtered_sld_list) == 35