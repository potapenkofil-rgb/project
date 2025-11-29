import pandas as pd

class DataLoader:
    def __init__(self, filename):
        self.filename = filename

    def load_data(self):
        try:
            data = pd.read_csv(self.filename)
            print("Файл успешно загружен.")
            return data
        except Exception as e:
            print("Ошибка при загрузке файла:", e)
            return None

    def clean_data(self):
        def drop_invalid(df):
            df = df.dropna()
            df = df.drop_duplicates()
            return df

        try:
            df = pd.read_csv(self.filename)
            df = drop_invalid(df)
            print("Очистка завершена.")
            return df
        except Exception as e:
            print("Ошибка при очистке данных:", e)
            return None
