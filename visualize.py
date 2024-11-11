# visualize_graph.py

from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
import networkx as nx
from rdflib import Graph


class RDFGraphWindow(QMainWindow):
    def __init__(self, rdf_graph):
        super().__init__()

        # Ініціалізація вікна PyQt5
        self.setWindowTitle("RDF Graph Visualization")
        self.setGeometry(100, 100, 1600, 900)

        # Ініціалізація холста для Matplotlib
        self.canvas = FigureCanvas(plt.figure())
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # Побудова графа
        self.rdf_graph = rdf_graph
        self.build_graph()

    def build_graph(self):
        # Ініціалізація NetworkX графа
        G = nx.DiGraph()

        # Додавання вузлів і ребер з RDF-графа
        for subject, predicate, obj in self.rdf_graph:
            G.add_node(str(subject))
            G.add_node(str(obj))
            G.add_edge(str(subject), str(obj), label=str(predicate))

        # Візуалізація графа
        pos = nx.circular_layout(G)
        nx.draw(G, pos, with_labels=True, node_color="lightblue", edge_color="gray", font_size=10, ax=self.canvas.figure.gca())

        # Додавання міток до ребер
        edge_labels = nx.get_edge_attributes(G, 'label')
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_color='red', ax=self.canvas.figure.gca())

        self.canvas.draw()  # Оновлення холста


def show_rdf_graph():
    rdf_graph = Graph()
    rdf_graph.parse("computation_ontology.owl", format="xml")

    app = QApplication([])
    window = RDFGraphWindow(rdf_graph)
    window.show()
    app.exec_()


if __name__ == "__main__":
    show_rdf_graph()
