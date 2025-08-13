import os
import json
import csv
# photo_dir = "src/photos/"
# bank = "chase_bus"
# test = photo_dir + bank
# test1 = [file for file in os.listdir(test) if os.path.isfile(os.path.join(test, file)) and "Username" in file]

# print(test1)

class test:
    def __init__(self):
        self.name = "Collin"
        
    base_dir = os.path.dirname(os.path.abspath(__file__))

    def hello(self):
        # print(test.base_dir)
        return(test.base_dir)

downloads = [name[:-12] for name in os.listdir("downloads")]
with open('src/creds/bank_accts.json', 'r') as file:
    bank_accts = json.load(file)

# n_found = set([acct['name'] for acct in bank_accts]) - set(downloads)
# print(n_found)

def check_downloads(d_path, bank_accts):
    downloads = [name[:-12] for name in os.listdir(str(d_path))]
    n_found = set([acct['name'] for acct in bank_accts]) - set(downloads)
    result = []
    for acct_name in n_found:
        matches = [acct for acct in bank_accts if acct['name'] == acct_name]
        result.extend(matches)
    # print(result)
    return(result)

# missing = check_downloads("downloads", bank_accts)
# col_names = ["Details","Posting Date","Description","Amount","Type","Balance","Check or Slip #"]

# for acct in missing:
#     with open(f"downloads/test/{acct['name']}__TEST.csv", "w", newline="") as f:
#         w = csv.DictWriter(f, fieldnames=col_names)
#         w.writeheader()

def logging():
    pass