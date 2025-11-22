from data_loader import DataLoader
from analyzer import Analyzer
from visualizer import Visualizer
import os

def main():
    filename = 'matches.csv'

    if not os.path.exists(filename):
        print(f"Ошибка: файл {filename} не найден.")
        return

    loader = DataLoader(filename)
    data = loader.load_data()
    data = loader.clean_data()

    print(f"Загружено матчей: {len(data)}")

    print("\nПервые строки данных:")
    print(data.head())

    analyzer = Analyzer()
    analyzer.train_model(data)

    input_data = {
        'team1_goals': 2,
        'team2_goals': 1,
        'shots': 10,
        'possession': 55
    }

    try:
        prediction = analyzer.predict_outcome(input_data)
        print("\nПрогноз исхода:", prediction)
    except Exception as e:
        print("\nОшибка при прогнозе:", e)

    visualizer = Visualizer()
    visualizer.plot_team_stats(data)
    
if __name__ == "__main__":
    main()
