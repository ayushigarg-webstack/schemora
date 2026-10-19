class Product:
    def __init__(self, product_id: str, name: str, price: float):
        self.product_id = product_id
        self.name = name
        self.price = price

class ShoppingCart:
    def __init__(self, customer_id: str):
        self.customer_id = customer_id
        self.items = []

    def add_product(self, product: Product, quantity: int = 1):
        self.items.append({"product": product, "quantity": quantity})

    def calculate_total(self, discount_rate: float = 0.0) -> float:
        subtotal = sum(item["product"].price * item["quantity"] for item in self.items)
        return subtotal * (1.0 - discount_rate)

# Example execution
p1 = Product("P100", "Wireless Mouse", 29.99)
p2 = Product("P101", "Mechanical Keyboard", 89.99)
cart = ShoppingCart("CUST_42")
cart.add_product(p1, 2)
cart.add_product(p2, 1)
total = cart.calculate_total(0.10)
