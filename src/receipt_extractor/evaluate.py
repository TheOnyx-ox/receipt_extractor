import json
from typing import List

from models import Receipt, Item
from pathlib import Path
from difflib import SequenceMatcher
from extractor import extract_receipt

ROOT = Path(__file__).resolve().parent.parent.parent
CORD_TEST = ROOT / "data" / "cord_test"
CORD_PREDICTIONS = ROOT / "data" / "cord_predictions"
CONVERTED_CORD = ROOT / "data" / "converted_cord"
VALIDATION_PATH = ROOT / 'data' / 'validations'


LIMIT = 10



def check_empty(value):
    if value == 'null' or value == False or value is None or value == "" or value == [] or value == " " or value == "-" or value == "0":
        return True
    return value

def increase_score(score, overall_acc, prop):
    overall_acc[prop] = True
    return score + 1, overall_acc


def keep_score(score, overall_acc, prop):
    overall_acc[prop] = False
    return score, overall_acc


def get_max_similarity(indexes):
    max_sim = 0
    max_idx = -1
    for idx in indexes:
        for k, v in indexes[idx].items():
            if k == 'similarity' and v > max_sim:
                max_sim = v
                max_idx = idx

    return max_idx

def validate_receipt(receipt: Receipt, ground_truth: Receipt, receipt_json = None):
    score = 0
    overall_acc = dict()
    overall_acc["receipt"] = receipt_json

    count = 1
    used = set()
    for product in receipt.products:

        indexes = {}
        idx = 0
        for gp in ground_truth.products:

            if idx not in used:
                indexes[idx] = {
                    "name": gp.name,
                    "similarity": SequenceMatcher(None, product.name.lower(), gp.name.lower()).ratio(),
                    "unit_price": product.unit_price == gp.unit_price,
                    "quantity": product.quantity == gp.quantity,
                    "line_total": product.line_total == gp.line_total
                }
            idx += 1

        max_sim = get_max_similarity(indexes)

        # an unmatched product
        product_acc = {"name": False, "unit_price": False, "quantity": False, "line_total": False}
        overall_acc[f"product-{count}"] = product_acc

        if max_sim in indexes and indexes[max_sim]['similarity'] > 0.8:

            used.add(max_sim)

            score += 1 # for name
            product_acc['name'] = True
            product_acc['matched_name'] = indexes[max_sim]['name']

            score += 1 if indexes[max_sim]['unit_price'] else 0
            product_acc['unit_price'] = indexes[max_sim]['unit_price']

            score += 1 if indexes[max_sim]['quantity'] else 0
            product_acc['quantity'] = indexes[max_sim]['quantity']

            score += 1 if indexes[max_sim]['line_total'] else 0
            product_acc['line_total'] = indexes[max_sim]['line_total']

        count += 1


    score, overall_acc = increase_score(score, overall_acc, "subtotal") if check_empty(receipt.subtotal) == check_empty(ground_truth.subtotal) else keep_score(score, overall_acc, "subtotal")

    score, overall_acc = increase_score(score, overall_acc, "total") if check_empty(receipt.total) == check_empty(ground_truth.total) else keep_score(score, overall_acc, "total")

    score, overall_acc = increase_score(score, overall_acc, "cash") if check_empty(receipt.cash) == check_empty(ground_truth.cash) else keep_score(score, overall_acc, "cash")

    score, overall_acc = increase_score(score, overall_acc, "card") if check_empty(receipt.card) == check_empty(ground_truth.card) else keep_score(score, overall_acc, "card")

    score, overall_acc = increase_score(score, overall_acc, "change") if check_empty(receipt.change) == check_empty(ground_truth.change) else keep_score(score, overall_acc, "change")

    score, overall_acc = increase_score(score, overall_acc, "tax") if check_empty(receipt.tax) == check_empty(ground_truth.tax) else keep_score(score, overall_acc, "tax")

    score, overall_acc = increase_score(score, overall_acc, "service_charge") if check_empty(receipt.service_charge) == check_empty(ground_truth.service_charge) else keep_score(score, overall_acc, "service_charge")

    score, overall_acc = increase_score(score, overall_acc, "discount") if check_empty(receipt.discount) == check_empty(ground_truth.discount) else keep_score(score, overall_acc, "discount")


    num_products = max(len(receipt.products), len(ground_truth.products))

    overall_acc["num_products"] = num_products
    overall_acc["score"] = score


    final_score = (score * 100) / (len(Receipt.model_fields.keys()) - 2 + (num_products * len(Item.model_fields.keys()))) # CORD doesn't have currency field (-1), and -1 for products field

    overall_acc["accuracy"] = final_score

    return final_score, overall_acc

def main():
   VALIDATION_PATH.mkdir(parents=True, exist_ok=True)
   overall_model_accuracy = 0
   processed = 0

   for receipt_path in sorted(CORD_TEST.rglob("*.jpg")) [:LIMIT]:
       prediction_path = CORD_PREDICTIONS / f'{receipt_path.stem}.json'
       if prediction_path.exists():
           receipt = Receipt.model_validate_json(prediction_path.read_text())
       else:
           receipt = extract_receipt(CORD_TEST / f'{receipt_path.stem}.jpg', CORD_PREDICTIONS)


       with open(CONVERTED_CORD / f'{receipt_path.stem}.json') as json_file:
           data = json.load(json_file)
           ground_truth = Receipt.model_validate(data)

       x, dct = validate_receipt(receipt, ground_truth, f'{receipt_path.stem}.json')
       overall_model_accuracy += x
       processed += 1

       with open(VALIDATION_PATH / f'{receipt_path.stem}.json', 'w') as json_file:
           json_file.write(json.dumps(dct, indent=2))


   overall_model_accuracy = overall_model_accuracy / processed if processed else 0

   with open(VALIDATION_PATH / 'model_accuracy.json', 'w') as outfile:
        outfile.write(
            json.dumps({
                'average_accuracy' : overall_model_accuracy,
                'processed' : processed,
            }, indent=2)
        )



if __name__ == "__main__":
    main()