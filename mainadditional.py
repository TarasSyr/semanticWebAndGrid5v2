
from rdflib import Graph
from flask import Flask, render_template, request, redirect, url_for, session
from owlready2 import get_ontology, Thing, DataProperty, ObjectProperty
import csv



# Створення онтології
onto = get_ontology("http://example.org/computation_ontology.owl")

app = Flask(__name__)
app.secret_key = '123'
g = Graph()
g.parse("computation_ontology.owl", format="xml")

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

    class assignedToUser(ObjectProperty):
        domain = [Task]
        range = [User]

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

    class maxTimeUsage(DataProperty):
        domain = [User]
        range = [int]

    class maxTasksAssignNumber(DataProperty):
        domain = [User]
        range = [int]



    # Додавання індивідів через CSV-файл
    with open("computation_data_additional.csv", newline='') as csvfile:
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
                user.maxTimeUsage = [int(row['maxTimeUsage'])]
                user.maxTasksAssignNumber = [int(row['maxTasksAssignNumber'])]
                print(f"Created {user.name} with access right {access_right.name}")

    onto.save(file="computation_ontology.owl", format="rdfxml")


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
                session['user'] = user
                session['userPassword'] = userPassword
                if user == "admin":
                    return redirect(url_for('home_for_admins'))  # Перенаправлення на домашню сторінку для admin
                elif user == "user":
                    return redirect(url_for('home_for_defaults'))  # Перенаправлення на іншу сторінку для defaultuser

        # Якщо логін або пароль неправильні
        return "Invalid credentials, please try again."

    return render_template("index.html")


@app.route("/home_for_defaults")
def home_for_defaults():
    return render_template("home_for_defaults.html")


@app.route("/assign_task", methods=["POST"])
def assign_task():
    message = ""
    data = request.form
    taskId = data.get("taskId")
    nodeId = data.get("nodeIdForTask")
    taskTime = int(data.get("timeUsage"))  # отримуємо taskTime з форми
    user = session.get('user')


    # Запит для отримання максимального часу та кількості завдань для користувача
    query_get_task_time_and_number_for_user = f"""
        PREFIX onto: <http://example.org/computation_ontology.owl#>
        SELECT ?user ?maxTimeUsage ?maxTasksAssignNumber 
        WHERE {{
            ?user onto:userLogin ?userLogin .
            ?user onto:maxTimeUsage ?maxTimeUsage .
            ?user onto:maxTasksAssignNumber ?maxTasksAssignNumber .
            FILTER (STR(?userLogin) = "{user}")
        }}
    """
    results = g.query(query_get_task_time_and_number_for_user)
    maxTimeUsage = 0
    maxTasksAssignNumber = 0

    if not results:
        print(f"Не знайдено користувача {user} або відсутні дані для maxTimeUsage та maxTasksAssignNumber.")
    else:
        for row in results:
            maxTimeUsage = int(row.maxTimeUsage)
            maxTasksAssignNumber = int(row.maxTasksAssignNumber)

    print(f"Максимальний час для {user}: {maxTimeUsage} хвилин, максимальна кількість завдань: {maxTasksAssignNumber}")

    # Додайте виведення для налагодження
    print(f"Максимальний час завдання для користувача: {maxTimeUsage} хвилин")
    print(f"Час для цього завдання: {taskTime} хвилин")

    # Перевірка, чи не перевищує час завдання дозволену межу
    if taskTime > maxTimeUsage:
        message = f"Час завдання перевищує максимально дозволений для користувача ({maxTimeUsage} хвилин)."
        return render_template("assign_result.html", message=message)

    # Запит для підрахунку кількості вже призначених завдань для користувача
    query_task_count_for_user = f"""
        PREFIX onto: <http://example.org/computation_ontology.owl#>
        SELECT (COUNT(?task) AS ?taskCount)
        WHERE {{
            ?task onto:assignedToUser ?user .
            ?task onto:assignedToNode <{nodeId}> .
        }}
    """
    task_count_results = g.query(query_task_count_for_user)
    taskCount = 0

    for row in task_count_results:
        taskCount = int(row.taskCount)

    # Додайте виведення для налагодження
    print(f"Кількість призначених завдань для користувача: {taskCount}")
    print(f"Максимальна кількість завдань для користувача: {maxTasksAssignNumber}")

    # Перевірка, чи не перевищує кількість завдань максимальну кількість для користувача
    if taskCount >= maxTasksAssignNumber:
        message = f"Кількість призначених завдань перевищує максимально дозволену кількість ({maxTasksAssignNumber})."
        return render_template("assign_result.html", message=message)

    # Запит для отримання суми requiresCores для вже призначених завдань на вузлі
    query_sum_requires_cores = f"""
        PREFIX onto: <http://example.org/computation_ontology.owl#>
        SELECT (SUM(?requiresCores) AS ?totalRequiresCores)
        WHERE {{
            ?task onto:assignedToNode <{nodeId}> .
            ?task onto:requiresCores ?requiresCores .
        }}
    """
    results = g.query(query_sum_requires_cores)
    totalRequiresCores = 0

    for row in results:
        totalRequiresCores = int(row.totalRequiresCores) if row.totalRequiresCores else 0

    # Запит для отримання доступних ядер вузла
    query_available_cores = f"""
        PREFIX onto: <http://example.org/computation_ontology.owl#>
        SELECT ?availableCores
        WHERE {{
            <{nodeId}> onto:hasAvailableCores ?availableCores .
        }}
    """

    # Виконання запиту для отримання доступних ядер
    available_cores_results = g.query(query_available_cores)
    availableCores = 0

    for row in available_cores_results:
        availableCores = int(row.availableCores)

    # Розрахунок кількості незавантажених ядер
    coresLeft = availableCores - totalRequiresCores

    # Запит для отримання requiresCores для нової задачі
    query_new_task_requires_cores = f"""
        PREFIX onto: <http://example.org/computation_ontology.owl#>
        SELECT ?requiresCores
        WHERE {{
            <{taskId}> onto:requiresCores ?requiresCores .
        }}
    """

    new_task_results = g.query(query_new_task_requires_cores)
    requiresCores = 0

    for row in new_task_results:
        requiresCores = int(row.requiresCores)

    # Перевірка, чи достатньо незавантажених ядер для нової задачі
    if coresLeft >= requiresCores:
        # Призначення задачі вузлу
        query_assign = f"""
            PREFIX onto: <http://example.org/computation_ontology.owl#>
            INSERT DATA {{
                <{taskId}> onto:assignedToNode <{nodeId}> .
                <{taskId}> onto:assignedToUser <{user}> .
            }}
        """
        g.update(query_assign)
        g.serialize(destination="computation_ontology.owl", format="xml")
        onto.save("computation_ontology.owl")
        message = f"Завдання {taskId} успішно присвоєно вузлу {nodeId}."
    else:
        message = f"Node overloaded: недостатньо доступних ядер для присвоєння завдання (потрібно: {requiresCores}, доступно: {coresLeft})."

    g.serialize(destination="computation_ontology.owl", format="xml")
    onto.save("computation_ontology.owl")

    return render_template("assign_result.html", message=message)



@app.route("/home_for_admins")
def home_for_admins():
    task_query = """
            PREFIX ex: <http://example.org/computation_ontology.owl#>
            SELECT ?task 
            WHERE {
                ?task a ex:Task.
            }
        """
    # Запит для отримання вузлів
    node_query = """
            PREFIX ex: <http://example.org/computation_ontology.owl#>
            SELECT ?node 
            WHERE {
                ?node a ex:Node.
            }
        """

    graph = Graph()
    graph.parse("computation_ontology.owl", format="xml")

    # Отримання завдань
    tasks = [str(row.task) for row in graph.query(task_query)]

    # Отримання вузлів
    nodes = [str(row.node) for row in graph.query(node_query)]

    # Передача списків у шаблон
    return render_template("home_for_admins.html", tasks=tasks, nodes=nodes)


@app.route("/show_load", methods=["POST"])
def show_load():
    data = request.form
    nodeId = data.get("nodeId")

    query = f"""
        PREFIX ex: <http://example.org/computation_ontology.owl#>

        SELECT ?nodeId ?hasAvailableCores (COUNT(?task) AS ?taskCount) (SUM(?requiresCores) AS ?occupiedCores)
        WHERE {{
            VALUES ?nodeId {{ ex:{nodeId} }}

            # Загальна кількість ядер у вузлі
            ?nodeId ex:hasAvailableCores ?hasAvailableCores .

            # Завдання, призначені для вузла, і кількість ядер, які вони потребують
            OPTIONAL {{
                ?task ex:assignedToNode ?nodeId ;
                      ex:requiresCores ?requiresCores .
            }}
        }}
        GROUP BY ?nodeId ?hasAvailableCores
    """

    # Виконання запиту
    result = g.query(query)

    # Обробка результатів
    node_load = []
    for row in result:
        total_cores = int(row.hasAvailableCores)
        occupied_cores = int(
            row.occupiedCores) if row.occupiedCores is not None else 0  # Якщо немає завдань, зайняті ядра = 0
        available_cores = total_cores - occupied_cores  # Розрахунок вільних ядер

        node_load.append({
            "nodeId": str(row.nodeId),
            "availableCores": available_cores,
            "taskCount": int(row.taskCount)
        })
    # Передача результатів у шаблон
    return render_template("show_load.html", node_load=node_load)



if __name__=="__main__":
    g.parse("computation_ontology.owl", format="xml")
    app.run(debug=True, port=5005)