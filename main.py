
from rdflib import Graph

from flask import Flask, render_template, request, redirect, url_for
from owlready2 import get_ontology, Thing, DataProperty, ObjectProperty
import csv

# Створення онтології
onto = get_ontology("http://example.org/computation_ontology.owl")

app = Flask(__name__)

with onto:
    # Класи
    class Node(Thing):
        pass

    class Task(Thing):
        pass

    class User(Thing):
        pass

    class AccessRight(Thing):
        pass

    # Об'єктні властивості
    class hasAccessRight(ObjectProperty):
        domain = [User]
        range = [AccessRight]

    class assignedToNode(ObjectProperty):
        domain = [Task]
        range = [Node]

    # Датні властивості

    class userLogin(DataProperty):
        domain = [User]
        range = [str]

    class userPassword(DataProperty):
        domain = [User]
        range = [str]

    class hasAvailableCores(DataProperty):
        domain = [Node]
        range = [int]

    class requiresCores(DataProperty):
        domain = [Task]
        range = [int]


    # Додавання індивідів через CSV-файл
    with open("computation_data.csv", newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row['type'] == 'Node':
                node = onto.Node(f"Node_{row['id']}")  # Створення індивіда класу Node в онтології
                node.hasAvailableCores = [int(row['hasAvailableCores'])]
                print(f"Created {node.name} with {node.hasAvailableCores} cores")

            elif row['type'] == 'Task':
                task = onto.Task(f"Task_{row['id']}")  # Створення індивіда класу Task
                task.requiresCores = [int(row['requiresCores'])]
                print(f"Created {task.name} requiring {task.requiresCores} cores.")

            elif row['type'] == 'User':
                user = onto.User(f"User_{row['id']}")  # Створення індивіда класу User
                access_right = onto.AccessRight(f"AccessRight_{row['accessRight']}")  # Створення індивіда AccessRight
                user.hasAccessRight = [access_right]
                user.userLogin = [str(row['userLogin'])]
                user.userPassword = [str(row['userPassword'])]
                print(f"Created {user.name} with access right {access_right.name}")

    onto.save(file="computation_ontology.owl", format="rdfxml")
    g = Graph()
    g.parse("computation_ontology.owl", format="xml")


def get_all_individuals_info(onto):
    for individual in onto.individuals():
        print(f"Індивід: {individual.name}")

        # Виведення значень датних та об'єктних властивостей
        for prop in individual.get_properties():
            prop_value = getattr(individual, prop.python_name)
            if prop_value:  # Якщо властивість має значення
                for value in prop_value:
                    print(f"  {prop.python_name}: {value}")

        print()

get_all_individuals_info(onto)


def get_users_info(onto):
    users_info = []
    for individual in onto.individuals():
        if isinstance(individual, onto.User):
            login = getattr(individual, 'userLogin', [None])[0]  # Отримати логін
            password = getattr(individual, 'userPassword', [None])[0]  # Отримати пароль
            if login and password:
                users_info.append((login, password))  # Додати логін і пароль у список
    return users_info


@app.route("/", methods=["GET", "POST"])
def index():
    users_info = get_users_info(onto)  # Отримати список користувачів

    if request.method == "POST":
        user = request.form['username']
        userPassword = request.form['password']

        # Перевірка логіна і пароля
        for login, password in users_info:
            if user == login and userPassword == password:
                if user == "admin":
                    return redirect(url_for('home'))  # Перенаправлення на домашню сторінку для admin
                elif user == "user":
                    return redirect(url_for('home_for_defaults'))  # Перенаправлення на іншу сторінку для defaultuser

        # Якщо логін або пароль неправильні
        return "Invalid credentials, please try again."

    return render_template("index.html")


                                            # в індексі будуть форми авторизації і кнопка "authorize"
                                            # або "sign in" яка буде мати посилання на функцію
                                            #  і сторінку в якій якщо admin можна буде добавляти таски і дивитись, якщо лох то просто дивитись
@app.route("/home")
def home():
    data = request.form
    taskId = data.get("taskId")
    requiresCores = data.get("requiresCores")
    query=f"""
        PREFIX onto: <http://example.org/computation_ontology#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        
        INSERT {
            onto:{taskId} a onto:Task ;
            onto:requiresCores "{requiresCores}"^^xsd:integer .
        }
    """
    g.query(query)
    g.serialize("computation_ontology.owl", format="xml")

    return render_template("home.html")

@app.route("/assign_task")
def assign_task():
    data = request.form
    taskId = data.get("taskId")
    assignToNode = data.get("assignedToNode")
    query = f"""
        PREFIX onto: <http://example.org/computation_ontology#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

        # Обчислюємо загальну кількість ядер вузла та поточне навантаження
        SELECT ?totalCores (SUM(?taskCores) AS ?currentLoad) WHERE {{
            # Отримуємо загальну кількість ядер вузла
            onto:{assignedToNode} onto:hasAvailableCores ?totalCores .

            # Знаходимо всі завдання, присвоєні вузлу, та їхні requiresCores
            OPTIONAL {{
                ?task onto:assignedToNode onto:{assignedToNode} ;
                      onto:requiresCores ?taskCores .
            }}
        }}
        GROUP BY ?totalCores
    """

    # Виконати запит для перевірки
    results = g.query(query)

    # Обробка результатів
    for row in results:
        totalCores = row.totalCores
        currentLoad = row.currentLoad if row.currentLoad else 0  # Якщо нема навантаження, то 0

        # Обчислюємо кількість доступних ядер
        availableCores = totalCores - currentLoad

        # Перевірка, чи достатньо доступних ядер
        if availableCores >= requiresCores:
            # Присвоєння завдання до вузла
            query_assign = f"""
                PREFIX onto: <http://example.org/computation_ontology#>
                INSERT {{
                    onto:{taskId} onto:assignedToNode onto:{assignedToNode} .
                }}
            """
            g.update(query_assign)
            print(f"Завдання {taskId} успішно присвоєно вузлу {assignedToNode}.")
        else:
            print(f"Node overloaded: недостатньо доступних ядер для присвоєння завдання (потрібно: {requiresCores}, доступно: {availableCores}).")

    # Зберегти зміни
    g.serialize(destination="computation_ontology.owl", format="xml")

@app.route("/home_for_defaults")
def home_for_defaults():

    return render_template("home_for_defaults.html")


@app.route("/show_load", methods=["POST"])
def show_load():
    data = request.form
    nodeId = data.get("nodeId")
    print(f"Отриманий вузол: {nodeId}")

    query = f"""
        PREFIX ex: <http://example.org/computation_ontology.owl#>

        SELECT ?nodeId ?hasAvailableCores
        WHERE {{
            VALUES ?nodeId {{ ex:{nodeId} }}
            ?nodeId ex:hasAvailableCores ?hasAvailableCores .
        }}
    """

    # Виконання запиту
    result = g.query(query)

    # Обробка результатів
    node_load = []
    for row in result:
        node_load.append({
            "nodeId": str(row.nodeId),
            "availableCores": str(row.hasAvailableCores)
            #"taskCount": str(row.taskCount)
        })

    print("Результат пошуку вузла:  %s", node_load)
    # Передача результатів у шаблон
    return render_template("show_load.html", node_load=node_load)

if __name__=="__main__":
    app.run(debug=True, port=5005)