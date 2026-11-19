from food_catalog import search_food_products

products = search_food_products("Milky Mist Paneer")

for product in products:
    print(product)