from data_loader import DataLoader
from analyzer import Analyzer
from visualizer import Visualizer
import os

def main():
    filename = "matches.csv"

    if not os.path.exists(filename):
        print(f"Файл {filename} не найден.")
        return

    loader = DataLoader(filename)
    data = loader.load_data()
    data = loader.clean_data()

    if data is None:
        print("Данные не загружены. Завершение программы.")
        return

    print("\nПервые 5 записей:")
    print(data.head())

    analyzer = Analyzer()
    analyzer.train_model(data)

    match_example = {
        "team1_goals": 2,
        "team2_goals": 1,
        "shots": 12,
        "possession": 58
    }

    prediction = analyzer.predict_outcome(match_example)
    print("\nПрогноз на матч:")
    print(prediction)

    visualizer = Visualizer()
    visualizer.plot_team_stats(data)

if __name__ == "__main__":
    main()
