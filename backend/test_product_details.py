from food_catalog import get_product_by_barcode
from pprint import pprint

barcode = "8904083300021"

product = get_product_by_barcode(barcode)

if product:
    pprint(product)
else:
    print("Product not found")