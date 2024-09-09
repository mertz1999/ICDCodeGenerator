import datetime
from fastapi import FastAPI, Path
from fastapi import APIRouter
import pandas as pd
from typing import List
from dotenv import load_dotenv


class KeyPair:
    def __init__(self):
        self.cd1 = ''
        self.cd2 = ''
        self.cd1RelPrty = ''
        self.aveCd1Prty = 0.0
        self.updateDate = datetime.datetime(2000, 1, 1)


# test url    
# localhost:8888/codes/I69.391,R13.12,R63.30,K21.9,T17.400A,G93.40,I48.91,N18.9,E86.0,N39.0,E46,I10,I69.320,M25.78,S13.150A,M50.30,M27.8,K14.8,M26.52,K08.409

CdngDxCodes = pd.read_csv('./inc/CdngDxCodes.csv')
CdngDxRules = pd.read_csv('./inc/CdngDxRules.csv')

router = APIRouter()
@router.get("/{codes}")
async def read_codes(codes: str = Path(..., description="Comma-separated list of codes")):
    code_list: List[str] = codes.upper().split(",")

    # Establish the connection
    try:

        startingCodes = f"{','.join(code_list)}"

        print(f"starting code_list: {startingCodes}")

        hardCodedDxCodes = ['I69.091', 'I69.191', 'I69.291', 'I69.391', 'I69.891', 'I69.991', 'R13.11', 'R13.12', 'R13.13', 'R13.14', 
                            'R13.19', 'R13.10', 'R63.30','J69.0', 'K22.0', 'K21.9', 'K22.5', 'K22.2', 'K22.4', 'K22.89', 'K44.9', 'T17.920A', 'T17.500A', 
                            'T17.400A']

        # get list of hard coded codes that were passed and put them initialCdList
        initialCdList = []

        # Iterate over the search codes and move them to initialCdList if they are in code_list and remove them from code_list
        for code in hardCodedDxCodes:
            if code in code_list:
                code_list.remove(code)
                initialCdList.append(code.upper())
                
        #print(f"edited code_list: {",".join(code_list)}")
        #print(f"initialCdList: {",".join(initialCdList)}")


    
        # Filter for type = 'RAD' and Code in code_list
        filtered_df = CdngDxCodes[(CdngDxCodes['Type'] == 'RAD') & (CdngDxCodes['Code'].isin(code_list))]

        # Order by PostingPriority in descending order
        sorted_df = filtered_df.sort_values(by='PostingPriority', ascending=False)

        # Extract Code column and convert to list, with uppercase transformation
        radCdList = sorted_df['Code'].str.upper().tolist()

        print("Rad codes: ",radCdList)

        # Iterate over radCdList remove RAD codes from code_list
        if len(radCdList) !=0:
            for code in radCdList:
                if code in code_list:
                    code_list.remove(code)
                
        #print(f"re-edited code_list: {",".join(code_list)}")
        #print(f"radCdList: {",".join(radCdList)}")

        # Filter for type = 'CLN' and Code in code_list
        filtered_df = CdngDxCodes[(CdngDxCodes['Type'] == 'CLN') & (CdngDxCodes['Code'].isin(code_list))]

        # Order by PostingPriority in descending order
        sorted_df = filtered_df.sort_values(by='PostingPriority', ascending=False)

        # Extract Code column, convert to uppercase, and convert to list
        clnCdList = sorted_df['Code'].str.upper().tolist()

        # Print the list as a comma-separated string
        print(f"clnCdList: {', '.join(clnCdList)}")

        # add any codes from code_list that are missing from the clinical codes that were just found in CdngDxCodes - put missing codes
        # at the end of clnCdList
        for code in code_list:
            if code not in clnCdList:
                clnCdList.append(code.upper())

        print(f"""updated clnCdList: {",".join(clnCdList)}""")


        # sort the clinical Dx codes using Piper's saved ordering rules from the legacy Office Manager
        filtered_df = CdngDxRules[(CdngDxRules['type'] == 'CLN') & (CdngDxRules['dxCode'].isin(code_list))]
        dxRuleDt = filtered_df.to_dict(orient='records')
        clnCdList = sort_dx_list_using_legacy_ordering_rules(clnCdList, dxRuleDt)

        # build sortedCodes list, first add hard-coded initialCdList Dx codes
        sortedCodes = []
        for code in initialCdList:
            if code not in sortedCodes:
                sortedCodes.append(code.upper())


        # now add clinical Dx Codes
        # only allow up to 8 clinical Dx codes
        if len(clnCdList) >= 8:
            clnCdList = clnCdList[:8]
        for code in clnCdList:
            if code not in sortedCodes:
                sortedCodes.append(code.upper())

        # now add radiological Dx Codes
        # first, calculate the maximum number of radiological Dx Codes (ensure that max_rad_items is not negative)
        max_rad_items = 20 - (len(initialCdList) + len(clnCdList))
        max_rad_items = max(max_rad_items, 0)
        if len(radCdList) != 0:
            radCdList = radCdList[:max_rad_items]
            for code in radCdList:
                if code not in sortedCodes:
                    sortedCodes.append(code.upper())

        
        # apply custom ordering rules
        sortedCodes = applyCustomOrderingRules(sortedCodes)
        print(f"""sortedCodes: {",".join(sortedCodes)}""")


        msg = "No change"
        if sortedCodes != startingCodes:
            msg = "Order updated!"
        return {"startingCodes": f"{startingCodes}", "sortedCodes": f"""{",".join(sortedCodes)}""", "Message": f"{msg}"}
    
    
    except Exception as e:
        return {"Error 454": str(e)}
    
    
def applyCustomOrderingRules(sortedCodes):

    CdList = []

    if len(sortedCodes) < 1:
        return CdList

    for code in sortedCodes:
        if code not in CdList:
            CdList.append(code.upper())


    # ensure Z93.1 - gastrostomy, if present, is always in the 9th or 10TH position - per Piper 1/29/2024
    code_to_move = 'Z93.1'  
    code_to_move = code_to_move.upper()
    if code_to_move in CdList:
        currIdx = CdList.index(code_to_move)
        if currIdx < 8 or currIdx > 9:
            CdList.remove(code_to_move)
            if currIdx < 8:
                CdList.insert(8, code_to_move)
            else:
                CdList.insert(9, code_to_move)

    """
        T17.920A should be removed - per Piper august 19th
        Piper told that this code need to remove and it's not essential nowdays.
    """
    if 'T17.920A' in CdList: CdList.remove('T17.920A')

    """
        E11.22 should be removed - per Piper
        Because this code is not important for insurance
    """
    if 'E11.22' in CdList: CdList.remove('E11.22')

    

    # ADD OTHER CUSTOM ORDERING LOGIC HERE, GEN AI, ETC.
    # ADD OTHER CUSTOM ORDERING LOGIC HERE, GEN AI, ETC.
    # ADD OTHER CUSTOM ORDERING LOGIC HERE, GEN AI, ETC.

    return CdList

    
def sort_dx_list_using_legacy_ordering_rules(clnCdList, dxRuleDt):

    # sort the clinical Dx codes using Piper's saved ordering rules from the legacy Office Manager 
    # (rules are passed in dxRuleDt - from PIEMRDB..CdngDxRules)

    CdList = []

    if len(clnCdList) < 1:
        return CdList


    # The first step is to build sort_key_info - sort_key_info is a list of KeyPair objects where the KeyPair's indicate the relative priority 
    # for 2 Dx codes, k.cd1 and k.cd2.
    #
    # The rp value (relative priority, from c.split('~') below) is a string of 1's and 0's from the last 10 times the rule was saved for the 
    # specified Dx code (d_x_cd2). If k.cd1 preceeds k.cd2 when the rule was saved, a 1 is saved in the rp value; otherwise a 0 is saved in the rp 
    # value. The rp value is converted to an average priority value below (k.aveCd1Prty). There are 2 KeyPair's stored for each pair of Dx codes 
    # passed in clnCdList. For a given set of 2 KeyPair's, the KeyPair with highest k.aveCd1Prty value will have sort priority, meaning that that 
    # KeyPair's k.cd1 Dx code will sort before the k.cd2 Dx code. Because of the way the rules are saved it is possible that the set of KeyPair's 
    # for 2 Dx codes will have the same k.aveCd1Prty value, or the k.aveCd1Prty values for both KeyPair's can be less than 0.5 (in which case 
    # aveCd1Prty is set to -1). When the aveCd1Prty are the same, the 2 Dx codes get # sorted together and their respective order is randomly 
    # determinied. 
    # 
    # The reason each pair Dx codes gets 2 KeyPair's is that there can be a separate rule saved for each of the Dx codes. Normally the 2 KeyPair's 
    # will have k.aveCd1Prty values that agree with each other (they add up to 1.0, for example, one is 0.8 and the other is 0.2). However, there can 
    # be cases where the 2 aveCd1Prty values do not add up to 1.0 (due to the way rules are saved). This logic then has to go with the most likely 
    # Dx code as the higher priority Dx code, based on the Dx code KeyPair with the higher aveCd1Prty value.

    sort_key_info = []

    qry_cds = "|"
    for c in clnCdList:
        if f"|{c.strip()}|" not in qry_cds:
            if qry_cds != "":
                qry_cds += "|"
            qry_cds += c.strip().upper()

    qry_cds2 = f"""('{qry_cds.strip('|').replace('|', "', '")}')"""

    startDxCd = "";
    startDxCdAvePrty = 0;
    if len(dxRuleDt) < 1:
        return clnCdList
    else:
        for row_dict in dxRuleDt:
            dx_code = row_dict['dxCode']
            assoc_dx_code_prty = row_dict['assocDxCodePrty']
            update_date = row_dict['updateDate'] if isinstance(row_dict['updateDate'], datetime.datetime) else datetime.datetime(2000, 1, 1)
            c_a = assoc_dx_code_prty.split('|')
            for c in c_a:
                if "~" not in c:
                    continue
                d_x_cd2, rp = c.split('~')
                d_x_cd2 = d_x_cd2.strip()
                rp = rp.strip()
                if rp == "": rp = "0"
                rp_ave = len(rp.replace("0", "")) / len(rp)
                if f"|{d_x_cd2}|" in qry_cds:
                    k = KeyPair()
                    k.cd1 = d_x_cd2
                    k.cd2 = dx_code
                    k.cd1RelPrty = rp
                    k.aveCd1Prty = rp_ave
                    k.updateDate = update_date

                    k2 = next((x for x in sort_key_info if x.cd1 == k.cd2 and x.cd2 == k.cd1), None)
                    if k2:
                        sort_key_info.remove(k2)
                        if k.aveCd1Prty >= 0.5 and k2.aveCd1Prty >= 0.5 and k.aveCd1Prty != k2.aveCd1Prty:
                            if k.aveCd1Prty > k2.aveCd1Prty:
                                k2.aveCd1Prty = 0.1
                            else:
                                k.aveCd1Prty = 0.1
                        elif k.aveCd1Prty < 0.5 and k2.aveCd1Prty < 0.5 or k.aveCd1Prty == k2.aveCd1Prty:
                            k.aveCd1Prty = -1
                            k2.aveCd1Prty = -1
                        sort_key_info.append(k2)

                    k3 = next((x for x in sort_key_info if x.cd1 == k.cd1 and x.cd2 == k.cd2), None)
                    if k3:
                        sort_key_info.remove(k3)
                    sort_key_info.append(k)

                    if k.aveCd1Prty > startDxCdAvePrty:
                        startDxCdAvePrty = k.aveCd1Prty
                        startDxCd = dx_code


    # add codes to CdList in priority order - starting with codes where priority order is known
    low_prty_cds_found = "|"
    if startDxCd != "": 

        CdList.append(startDxCd.upper());

        for c in clnCdList:
            c1 = c.strip()
            if c1 == startDxCd: continue

            code_added = False
            for i in range(len(CdList)):
                c2 = CdList[i]

                if c1 == c2:
                    continue

                kp = next((x for x in sort_key_info if x.cd1 == c1 and x.cd2 == c2), None)

                if kp is None:
                    if i + 1 >= len(CdList) and f"|{c1}|" not in low_prty_cds_found:
                        low_prty_cds_found += f"{c1}|"
                    continue

                if kp.aveCd1Prty >= 0.5 and c1 not in CdList:
                    CdList.insert(i, c1.upper())
                    code_added = True
                    break

                if kp.aveCd1Prty >= 0.5 and i + 1 >= len(CdList) and c1 not in CdList:
                    CdList.append(c1.upper())
                    code_added = True
                    break

            if code_added:
                low_prty_cds_found = low_prty_cds_found.replace(f"|{c.strip()}|", "|")


    lowPrtyCdList = low_prty_cds_found.split("|")
    print(f"low_prty_cds_found: {low_prty_cds_found}")
    print(f"""lowPrtyCdList: {",".join(lowPrtyCdList)}""")

    # add any codes not found in sort_key_info to the end of the returned CdList
    for code in clnCdList:
        if code not in CdList:
            CdList.append(code.upper())

    return CdList
