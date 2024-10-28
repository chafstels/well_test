import os
import csv
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

class WellDataScraper:
    def __init__(self, input_file, output_file, error_file):
        self.input_file = input_file
        self.output_file = output_file
        self.error_file = error_file
        self.driver = self.setup_driver()
        self.url = "https://webapps2.rrc.texas.gov/EWA/wellboreQueryAction.do"
        self.counter = 0

        # Инициализация файлов
        self.initialize_csv(self.output_file, [
            "API", "API No.", "District", "Lease No.", "Lease Name", "Well No.",
            "Field Name", "Operator Name", "County", "On Schedule", "API Depth"
        ])
        self.initialize_csv(self.error_file, ["API", "Error"])

    @staticmethod
    def setup_driver():
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service)

    @staticmethod
    def initialize_csv(file_path, headers):
        with open(file_path, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(headers)

    def fetch_well_data(self, api_prefix, api_suffix, api_full):
        self.driver.get(self.url)

        # Заполнение формы API-префиксом и суффиксом
        self.driver.find_element(By.NAME, "searchArgs.apiNoPrefixArg").send_keys(api_prefix)
        self.driver.find_element(By.NAME, "searchArgs.apiNoSuffixArg").send_keys(api_suffix)

        # Выбор Both
        both_radio_button = self.driver.find_element(By.ID, "scheduleTypeArg3")
        both_radio_button.click()

        # Нажатие на Submit
        submit_button = self.driver.find_element(By.XPATH, '//input[@type="submit" and @value="Submit"]')
        submit_button.click()

        # Ожидание таблицы с данными
        try:
            table = WebDriverWait(self.driver, 4).until(
                EC.presence_of_element_located((By.CLASS_NAME, "DataGrid"))
            )
        except:
            self.log_error(api_full, "Data not found")
            return None

        # Извлечение данных из таблицы
        parsed_data = []
        rows = table.find_elements(By.TAG_NAME, "tr")[1:]  # Пропуск заголовка

        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            col_texts = [col.text.strip() for col in cols if col.text.strip() and "Links" not in col.text]

            # Убедимся, что у нас есть все нужные ячейки
            if len(col_texts) >= 4 and all(col_texts):  # Ожидаем 10 заполненных столбцов
                parsed_data.append(col_texts)

        return parsed_data

    def log_error(self, api, message):
        with open(self.error_file, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([api, message])
        print(f"Error logged for API: {api} - {message}")

    def write_to_csv(self, data):
        with open(self.output_file, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerows(data)

    def process_api_list(self):
        df = pd.read_csv(self.input_file)

        for _, row in df.iterrows():
            self.counter += 1
            api_full = str(row['API_8'])
            api_prefix, api_suffix = api_full[:3], api_full[3:]
            print(f"Processing {self.counter}/{len(df)}: API {api_full}")

            response_data = self.fetch_well_data(api_prefix, api_suffix, api_full)
            if response_data:
                data_with_api = [[api_full] + record for record in response_data]
                self.write_to_csv(data_with_api)

    def close_driver(self):
        self.driver.quit()

    def run(self):
        try:
            self.process_api_list()
        finally:
            self.close_driver()
            print("Scraping completed.")

if __name__ == "__main__":
    scraper = WellDataScraper(
        input_file='unique_apis.csv',
        output_file='api_well_data.csv',
        error_file='error_log.csv'
    )
    scraper.run()
