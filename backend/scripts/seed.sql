INSERT INTO orders (id, customer_name, product, amount_cents, status) VALUES
  (4521, 'Dana Whitfield', 'Oak Dining Table', 34000, 'delivered'),
  (4522, 'Marcus Lee', 'Leather Armchair', 89900, 'delivered'),
  (4523, 'Priya Nadar', 'Walnut Bookshelf', 24500, 'in_transit')
ON CONFLICT (id) DO NOTHING;