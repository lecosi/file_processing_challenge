import csv
import random
from datetime import datetime, timedelta

def generate_sales_data(file_name, num_records):
    header = ['date', 'product_id', 'quantity', 'price']
    start_date = datetime(2026, 1, 1)
    
    print(f"🚀 Generando {num_records} registros en {file_name}...")
    
    with open(file_name, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        
        for i in range(num_records):
            # Simulamos datos variados
            row_date = (start_date + timedelta(days=random.randint(0, 30))).strftime('%Y-%m-%d')
            product_id = random.randint(1000, 5000)
            quantity = random.randint(1, 10)
            price = round(random.uniform(5.0, 150.0), 2)
            
            writer.writerow([row_date, product_id, quantity, price])
            
            if i % 500000 == 0 and i > 0:
                print(f"{i} registros escritos...")

    print("Archivo generado con éxito.")

if __name__ == "__main__":
    generate_sales_data("test_big_sales.csv", 2000000)