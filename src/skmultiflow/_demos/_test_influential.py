from skmultiflow.data import influential_stream, random_rbf_generator
from skmultiflow.evaluation import evaluate_influential
from skmultiflow.trees import HoeffdingTreeClassifier
from skmultiflow.bayes import naive_bayes
from skmultiflow.core import Pipeline
from prettytable import PrettyTable
from skmultiflow.data.random_rbf_generator import RandomRBFGenerator
from skmultiflow.data.random_rbf_generator_drift import RandomRBFGeneratorDrift
from skmultiflow.data.concept_drift_stream import ConceptDriftStream
import matplotlib.pyplot as plt
import matplotlib.backends.backend_pdf


def demo():
    """ _test_influential

    This demo tests if the streams are correctly created and
    if the classifier chooses a new sample based on the weights
    of the streams.

    :return:
    """
    runs = 100
    n_comparisons = 1

    equal_pos = PrettyTable()
    equal_neg = PrettyTable()
    fulfilling_pos = PrettyTable()
    fulfilling_neg = PrettyTable()
    defeating_pos = PrettyTable()
    defeating_neg = PrettyTable()

    abs_mean_pos = [[] for _ in range(3)]
    abs_mean_neg = [[] for _ in range(3)]
    influence_on_positive = [[[] for _ in range(n_comparisons)] for _ in range(3)]
    influence_on_negative = [[[] for _ in range(n_comparisons)] for _ in range(3)]
    accuracy = [[] for _ in range(3)]
    significant_pvalues = [[] for _ in range(3)]
    significantppos = [[] for _ in range(3)]
    significantpneg = [[] for _ in range(3)]
    final_weights = [[] for _ in range(3)]
    table_names_pos = ["Run", "Feature number", "time period", "length subset TP", "TP sample mean", "length subset FN",
                       "FN sample mean", "abs difference in mean", "p value"]
    table_names_neg = ["Run", "Feature number", "time period", "length subset TN", "TN sample mean", "length subset FP",
                       "FP sample mean", "abs difference in mean", "p value"]

    defeating_pos.field_names = table_names_pos
    equal_pos.field_names = table_names_pos
    fulfilling_pos.field_names = table_names_pos
    defeating_neg.field_names = table_names_neg
    equal_neg.field_names = table_names_neg
    fulfilling_neg.field_names = table_names_neg
    negative_table = [equal_neg, fulfilling_neg, defeating_neg]
    positive_table = [equal_pos, fulfilling_pos, defeating_pos]
    weightA = [1, 1.003, 0.997]
    weightB = [1, 0.997, 1.003]
    for i in range(runs):
        list_of_streams = []
        for x in range(5):
            list_of_streams.append(RandomRBFGeneratorDrift(model_random_state=101, sample_random_state=51,
                                                           n_classes=2, n_features=1,
                                                           n_centroids=10, num_drift_centroids=int(10/runs*i),
                                                           change_speed=0.75,
                                                           class_weights=[1, 0]))
        for x in range(5):
            list_of_streams.append(RandomRBFGeneratorDrift(model_random_state=101, sample_random_state=50,
                                                           n_classes=2, n_features=1,
                                                           n_centroids=10, num_drift_centroids=int(10/runs*i),
                                                           change_speed=0.75,
                                                           class_weights=[0, 1]))
        for j in range(3):
            stream = influential_stream.InfluentialStream(self_fulfilling=weightA[j], self_defeating=weightB[j],
                                                          streams=list_of_streams)
            classifier = naive_bayes.NaiveBayes()

            # Setup the evaluator
            evaluator = evaluate_influential.EvaluateInfluential(show_plot=False,
                                                                 pretrain_size=200,
                                                                 max_samples=2200,
                                                                 batch_size=1,
                                                                 batch_size_update=False,
                                                                 n_time_windows=n_comparisons+1,
                                                                 n_intervals=8,
                                                                 metrics=['accuracy'],
                                                                 data_points_for_classification=False,
                                                                 weight_output=True,
                                                                 weight_plot=False)
            pipe = Pipeline([('Naive Bayes', classifier)])

            # 4. Run evaluation
            evaluator.evaluate(stream=stream, model=pipe)
            final_weights[j].append(evaluator.stream.weight)
            accuracy[j].append(evaluator.accuracy[0])
            idx_pos, idx_neg = [], []
            feature, mean_diff, pvalue = 0, 7, 8
            for result in evaluator.table_influence_on_positive:
                result.insert(0, i)
                if result[1] == 0:
                    if result[pvalue] is not None and result[pvalue] < 0.01:
                        idx_pos.append(i)
                    time = result[2]
                    influence_on_positive[j][time].append(result[pvalue])
                    abs_mean_pos[j].append(result[mean_diff])
                    positive_table[j].add_row(result)

            for result in evaluator.table_influence_on_negative:
                result.insert(0, i)
                if result[1] == 0:
                    if result[pvalue] is not None:
                        if result[pvalue] < 0.01:
                            idx_neg.append(i)
                    time = result[2]
                    influence_on_negative[j][time].append(result[pvalue])
                    abs_mean_neg[j].append(result[mean_diff])
                    negative_table[j].add_row(result)
            idx = [i for i, j in zip(idx_pos, idx_neg) if i == j]

            # idx = idx_pos + list(set(idx_neg) - set(idx_pos))
            significant_pvalues[j].extend(idx)
            significantpneg[j].extend(idx_neg)
            significantppos[j].extend(idx_pos)
    title = ['no prediction influence', 'self fulfilling approach', 'self defeating approach']
    for i in range(3):
        print(title[i])
        print("influence positive instances")
        print(positive_table[i])
        print("influence negative instances")
        print(negative_table[i])
        print("how many times a p value below 0.01 both:", len(significant_pvalues[i]))
        print("significant p value pos instances: ", len(significantppos[i]))
        print("significant p value neg instances: ", len(significantpneg[i]))

    x = list(range(0, runs, 1))
    y = [[] for _ in range(3)]
    for i in range(runs):
        for j in range(3):
            t = [item[i] for item in influence_on_positive[j]]
            if len(list(filter(None, t))) != 0:
                averagep = sum(filter(None, t)) / len(list(filter(None, t)))
            else:
                averagep = 0
            y[j].append(averagep)
    plt.figure(1)
    run = 0
    for i in y:
        label = "Strategy " + title[run]
        plt.plot(x, i, label=label)
        run += 1
    plt.xlabel('Runs')
    plt.ylabel('Average p-value')
    plt.title('Average p-value per strategy per run')
    plt.legend()

    y = list(range(0, runs, 1))

    plt.figure(2)
    plt.plot(y, accuracy[0], label="accuracy without prediction influence", color="grey")
    plt.plot(y, accuracy[1], label="accuracy in self fulfilling approach", color="blue")
    plt.plot(y, accuracy[2], label="accuracy in self defeating approach", color="purple")
    plt.xlabel('Runs')
    plt.ylabel("Accuracy")
    plt.title("Accuracy per strategy")
    plt.legend()

    plt.figure(3)
    plt.boxplot(significant_pvalues)
    plt.xticks([1, 2, 3], title)
    plt.title("Significant p values")

    # pdf = matplotlib.backends.backend_pdf.PdfPages("output.pdf")
    # for fig in range(1, plt.figure().number):
    #     pdf.savefig(fig)
    # pdf.close()
    plt.show()


if __name__ == '__main__':
    demo()