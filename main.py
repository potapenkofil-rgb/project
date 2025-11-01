from data_loader import DataLoader
from analyzer import Analyzer
from visualizer import Visualizer

def main():
    loader = DataLoader('matches.csv')
    data = loader.load_data()
    data = loader.clean_data()

    analyzer = Analyzer()
    analyzer.train_model(data)
    
    prediction = analyzer.predict_outcome({
        'team1_goals': 2,
        'team2_goals': 1,
        'shots': 10,
        'possession': 55
    })
    print("Прогноз исхода:", prediction)
    
    visualizer = Visualizer()
    visualizer.plot_team_stats(data)

if name == "main":
    main()
